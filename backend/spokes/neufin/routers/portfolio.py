"""
Neufin Portfolio Router — CSV manual import.

Endpoint
--------
POST /portfolio/upload
    Accepts a multipart form with:
      - user_id  (UUID, form field)
      - file     (CSV file, UploadFile)

    Expected CSV columns (case-insensitive, extra columns are ignored):
      Ticker        — ticker symbol, e.g. "AAPL"
      Quantity      — number of shares / units held
      Average Price — cost basis per unit

    Behaviour:
      - Existing CSV holdings for this (venture_id, user_id) are deleted
        and replaced in a single transaction.
      - Rows with missing/invalid data are skipped and reported in `errors`.
      - Returns a summary: rows imported, skipped, and error details.

    No external API calls — pure Python csv module, no pandas.
"""
from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query, UploadFile, File, Form, status
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.orm import NeufinPortfolioHolding

router = APIRouter(tags=["neufin-portfolio"])

# ── Column aliases (accept various spellings) ─────────────────────────────────

_TICKER_COLS    = {"ticker", "symbol", "stock"}
_QUANTITY_COLS  = {"quantity", "qty", "shares", "units", "amount"}
_AVGPRICE_COLS  = {"average price", "avg price", "avg_price", "averageprice",
                   "cost basis", "cost_basis", "price", "purchase price"}


# ── Response model ─────────────────────────────────────────────────────────────

class HoldingOut(BaseModel):
    ticker: str
    quantity: float
    avg_price: float
    source: str
    imported_at: datetime


class UploadSummary(BaseModel):
    imported: int
    skipped: int
    errors: list[str]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalise(header: str) -> str:
    return header.strip().lower()


def _find_col(headers: list[str], candidates: set[str]) -> str | None:
    for h in headers:
        if _normalise(h) in candidates:
            return h
    return None


def _parse_csv(content: bytes) -> tuple[list[dict], list[str]]:
    """
    Parse CSV bytes into a list of validated position dicts.

    Returns (positions, errors) where positions is a list of
    {"ticker": str, "quantity": float, "avg_price": float}
    and errors is a list of human-readable problem descriptions.
    """
    text = content.decode("utf-8-sig").strip()  # strip BOM if present
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []

    ticker_col    = _find_col(headers, _TICKER_COLS)
    quantity_col  = _find_col(headers, _QUANTITY_COLS)
    avgprice_col  = _find_col(headers, _AVGPRICE_COLS)

    missing = []
    if not ticker_col:
        missing.append("Ticker")
    if not quantity_col:
        missing.append("Quantity")
    if not avgprice_col:
        missing.append("Average Price")

    if missing:
        raise ValueError(
            f"CSV is missing required column(s): {', '.join(missing)}. "
            f"Found headers: {list(headers)}"
        )

    positions: list[dict] = []
    errors: list[str] = []

    for row_num, row in enumerate(reader, start=2):  # row 1 = header
        ticker = (row.get(ticker_col) or "").strip().upper()
        raw_qty = (row.get(quantity_col) or "").strip().replace(",", "")
        raw_price = (row.get(avgprice_col) or "").strip().replace(",", "").lstrip("$")

        if not ticker:
            errors.append(f"Row {row_num}: ticker is empty — skipped")
            continue

        try:
            quantity = float(raw_qty)
            if quantity <= 0:
                raise ValueError("must be > 0")
        except ValueError:
            errors.append(f"Row {row_num} ({ticker}): invalid quantity {raw_qty!r} — skipped")
            continue

        try:
            avg_price = float(raw_price)
            if avg_price < 0:
                raise ValueError("must be >= 0")
        except ValueError:
            errors.append(f"Row {row_num} ({ticker}): invalid price {raw_price!r} — skipped")
            continue

        positions.append({"ticker": ticker, "quantity": quantity, "avg_price": avg_price})

    return positions, errors


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/holdings",
    response_model=list[HoldingOut],
    summary="List portfolio holdings for a user",
)
async def get_holdings(
    user_id: uuid.UUID = Query(..., description="UUID of the user"),
    x_venture_id: str = Header(..., alias="X-Venture-ID"),
    db: AsyncSession = Depends(get_db),
) -> list[HoldingOut]:
    try:
        uuid.UUID(str(x_venture_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid X-Venture-ID")

    stmt = (
        select(NeufinPortfolioHolding)
        .where(NeufinPortfolioHolding.user_id == user_id)
        .order_by(NeufinPortfolioHolding.ticker)
    )
    rows = list((await db.execute(stmt)).scalars().all())
    return [
        HoldingOut(
            ticker=r.ticker,
            quantity=float(r.quantity),
            avg_price=float(r.avg_price),
            source=r.source,
            imported_at=r.imported_at,
        )
        for r in rows
    ]


@router.post(
    "/upload",
    response_model=UploadSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Import portfolio holdings from CSV",
    description=(
        "Accepts a CSV file with columns Ticker, Quantity, and Average Price. "
        "Replaces existing CSV-sourced holdings for this user in one transaction. "
        "Returns a summary of imported, skipped, and errored rows."
    ),
)
async def upload_portfolio(
    user_id: uuid.UUID = Form(..., description="UUID of the user uploading the portfolio"),
    file: UploadFile = File(..., description="CSV file with Ticker, Quantity, Average Price columns"),
    x_venture_id: str = Header(..., alias="X-Venture-ID"),
    db: AsyncSession = Depends(get_db),
) -> UploadSummary:
    try:
        v_id = uuid.UUID(x_venture_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid X-Venture-ID")

    # Validate content type loosely (accept text/csv and application/octet-stream)
    ct = (file.content_type or "").lower()
    if ct and "csv" not in ct and "text" not in ct and "octet" not in ct:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Expected a CSV file, got content-type: {file.content_type}",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        positions, errors = _parse_csv(raw)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    skipped = len(errors)

    # Replace old CSV holdings for this user inside the same transaction
    await db.execute(
        delete(NeufinPortfolioHolding).where(
            NeufinPortfolioHolding.venture_id == v_id,
            NeufinPortfolioHolding.user_id == user_id,
            NeufinPortfolioHolding.source == "csv",
        )
    )

    now = datetime.now(timezone.utc)
    for pos in positions:
        db.add(
            NeufinPortfolioHolding(
                venture_id=v_id,
                user_id=user_id,
                ticker=pos["ticker"],
                quantity=pos["quantity"],
                avg_price=pos["avg_price"],
                source="csv",
                imported_at=now,
            )
        )

    return UploadSummary(
        imported=len(positions),
        skipped=skipped,
        errors=errors,
    )
