"""
Neufin Plaid Router — brokerage account linking.

Endpoints
---------
POST /plaid/create-link-token
    Returns a short-lived Plaid Link token.  The frontend embeds this token
    in the Plaid Link SDK to present the account connection UI.

POST /plaid/exchange-token
    Receives the one-time public_token from Plaid Link, exchanges it for a
    persistent access_token, fetches the user's investment holdings, and
    upserts them into neufin_portfolio_holdings.

Provider
--------
Uses the plaid-python SDK (v14+) with the host environment selected by
settings.plaid_env ("sandbox" | "development" | "production").

All Plaid API calls are synchronous (the SDK doesn't support asyncio) so
they run in a thread-pool executor via asyncio.to_thread().
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

import plaid
from plaid.api import plaid_api
from plaid.model.country_code import CountryCode
from plaid.model.investments_holdings_get_request import (
    InvestmentsHoldingsGetRequest,
)
from plaid.model.item_public_token_exchange_request import (
    ItemPublicTokenExchangeRequest,
)
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from models.orm import NeufinPlaidConnection, NeufinPortfolioHolding

router = APIRouter(tags=["neufin-plaid"])

# ── Plaid client factory ───────────────────────────────────────────────────────

_PLAID_ENV_MAP = {
    "sandbox":     plaid.Environment.Sandbox,
    "development": "https://development.plaid.com",  # plaid-python v14+ removed Environment.Development
    "production":  plaid.Environment.Production,
}


def _plaid_client() -> plaid_api.PlaidApi:
    env = _PLAID_ENV_MAP.get(settings.plaid_env, plaid.Environment.Sandbox)
    configuration = plaid.Configuration(
        host=env,
        api_key={
            "clientId": settings.plaid_client_id,
            "secret":   settings.plaid_secret,
        },
    )
    return plaid_api.PlaidApi(plaid.ApiClient(configuration))


# ── Request / Response models ─────────────────────────────────────────────────

class LinkTokenRequest(BaseModel):
    user_id: uuid.UUID


class LinkTokenResponse(BaseModel):
    link_token: str
    expiration: str


class ExchangeTokenRequest(BaseModel):
    user_id: uuid.UUID
    public_token: str
    institution_name: str = ""


class ExchangeTokenResponse(BaseModel):
    holdings_imported: int
    institution: str
    item_id: str


class HoldingOut(BaseModel):
    ticker: str
    quantity: float
    avg_price: float
    source: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _create_link_token_sync(user_id: str) -> dict:
    """Blocking — runs in thread executor."""
    client = _plaid_client()
    req = LinkTokenCreateRequest(
        products=[Products("investments")],
        client_name="Neufin Wealth Manager",
        country_codes=[CountryCode("US")],
        language="en",
        user=LinkTokenCreateRequestUser(client_user_id=user_id),
    )
    resp = client.link_token_create(req)
    return {"link_token": resp["link_token"], "expiration": str(resp["expiration"])}


def _exchange_and_fetch_sync(public_token: str) -> dict:
    """Blocking — exchange public token + fetch holdings. Runs in thread executor."""
    client = _plaid_client()

    # Exchange
    exchange_resp = client.item_public_token_exchange(
        ItemPublicTokenExchangeRequest(public_token=public_token)
    )
    access_token = exchange_resp["access_token"]
    item_id = exchange_resp["item_id"]

    # Fetch holdings
    holdings_resp = client.investments_holdings_get(
        InvestmentsHoldingsGetRequest(access_token=access_token)
    )
    raw_holdings = holdings_resp["holdings"]
    securities = {s["security_id"]: s for s in holdings_resp["securities"]}

    positions = []
    for h in raw_holdings:
        sec = securities.get(h["security_id"], {})
        ticker = sec.get("ticker_symbol") or sec.get("name", "UNKNOWN")
        positions.append({
            "ticker":     ticker.upper().strip(),
            "quantity":   float(h["quantity"]),
            "avg_price":  float(h.get("cost_basis", 0) / max(float(h["quantity"]), 1e-9)),
        })

    return {
        "access_token": access_token,
        "item_id":      item_id,
        "positions":    positions,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/create-link-token",
    response_model=LinkTokenResponse,
    summary="Create a Plaid Link token",
    description=(
        "Returns a short-lived Plaid Link token for the given user.  "
        "Pass this to the Plaid Link SDK in your frontend to initiate the "
        "account-linking flow.  Requires PLAID_CLIENT_ID and PLAID_SECRET."
    ),
)
async def create_link_token(
    body: LinkTokenRequest,
    x_venture_id: str = Header(..., alias="X-Venture-ID"),
) -> LinkTokenResponse:
    if not settings.plaid_client_id or not settings.plaid_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Plaid credentials are not configured on this server.",
        )
    result = await asyncio.to_thread(_create_link_token_sync, str(body.user_id))
    return LinkTokenResponse(**result)


@router.post(
    "/exchange-token",
    response_model=ExchangeTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Exchange Plaid public token and import holdings",
    description=(
        "Exchanges the one-time public_token from Plaid Link for a persistent "
        "access_token, fetches investment holdings, and upserts them into "
        "neufin_portfolio_holdings (replacing any previous Plaid import for "
        "this user).  Also stores the access_token in neufin_plaid_connections."
    ),
)
async def exchange_token(
    body: ExchangeTokenRequest,
    x_venture_id: str = Header(..., alias="X-Venture-ID"),
    db: AsyncSession = Depends(get_db),
) -> ExchangeTokenResponse:
    if not settings.plaid_client_id or not settings.plaid_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Plaid credentials are not configured on this server.",
        )

    try:
        v_id = uuid.UUID(x_venture_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid X-Venture-ID")

    # Run blocking Plaid calls in thread pool
    try:
        data = await asyncio.to_thread(_exchange_and_fetch_sync, body.public_token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Plaid API error: {exc}",
        )

    positions  = data["positions"]
    access_tok = data["access_token"]
    item_id    = data["item_id"]

    # Upsert Plaid connection (delete + insert in same transaction)
    await db.execute(
        delete(NeufinPlaidConnection).where(
            NeufinPlaidConnection.venture_id == v_id,
            NeufinPlaidConnection.user_id == body.user_id,
        )
    )
    db.add(
        NeufinPlaidConnection(
            venture_id=v_id,
            user_id=body.user_id,
            access_token=access_tok,
            item_id=item_id,
            institution_name=body.institution_name or None,
        )
    )

    # Replace previous Plaid holdings for this user
    await db.execute(
        delete(NeufinPortfolioHolding).where(
            NeufinPortfolioHolding.venture_id == v_id,
            NeufinPortfolioHolding.user_id == body.user_id,
            NeufinPortfolioHolding.source == "plaid",
        )
    )
    now = datetime.now(timezone.utc)
    for pos in positions:
        db.add(
            NeufinPortfolioHolding(
                venture_id=v_id,
                user_id=body.user_id,
                ticker=pos["ticker"],
                quantity=pos["quantity"],
                avg_price=pos["avg_price"],
                source="plaid",
                imported_at=now,
            )
        )

    return ExchangeTokenResponse(
        holdings_imported=len(positions),
        institution=body.institution_name or "Unknown",
        item_id=item_id,
    )
