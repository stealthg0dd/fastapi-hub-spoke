"""
Router node — selects the venture's System Persona from the database.

Responsibilities
----------------
- Receives the venture_id from the graph state.
- Queries hub.organizations for a matching record (RLS is already active on
  the session passed via config — only the owning venture's rows are visible).
- Derives a system persona string from the organization's name and description.
- Falls back to a generic multi-venture assistant persona when no record is
  found (allows the graph to operate in development without pre-seeded data).

Config keys expected (via RunnableConfig["configurable"])
---------------------------------------------------------
db : AsyncSession
    An already-open SQLAlchemy async session with SET LOCAL
    app.current_venture_id applied (provided by get_db() in the endpoint).
"""

import logging
import uuid

from langchain_core.runnables import RunnableConfig
from sqlalchemy.ext.asyncio import AsyncSession

from graph.state import ChatState
from models.hub import Organization

logger = logging.getLogger(__name__)

_FALLBACK_PERSONA = (
    "You are a helpful, professional AI assistant operating within a "
    "secure multi-venture platform. Answer concisely and accurately."
)


async def router_node(state: ChatState, config: RunnableConfig) -> dict:
    db: AsyncSession = config["configurable"]["db"]
    venture_id_str: str = state["venture_id"]

    try:
        org_uuid = uuid.UUID(venture_id_str)
    except ValueError:
        logger.warning("router_node: invalid venture_id format %r — using fallback persona", venture_id_str)
        return {"persona": _FALLBACK_PERSONA}

    org: Organization | None = await db.get(Organization, org_uuid)

    if org is None:
        logger.info("router_node: no organization found for id=%s — using fallback persona", venture_id_str)
        return {"persona": _FALLBACK_PERSONA}

    # Build a system persona from the org's name and description.
    description_clause = (
        f"  Context: {org.description.strip()}" if org.description else ""
    )
    persona = (
        f"You are the AI assistant for {org.name}, a venture on the Hub platform."
        f"{description_clause}\n"
        "Answer clearly, stay on topic for this venture, and never reveal "
        "information belonging to other ventures or organisations."
    )

    logger.info("router_node: resolved persona for org=%s (%s)", org.name, org_uuid)
    return {"persona": persona}
