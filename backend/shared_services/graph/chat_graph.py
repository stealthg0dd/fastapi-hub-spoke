"""
Chat graph — the top-level LangGraph state machine for the Hub.

Graph topology (linear, no branches)
--------------------------------------

    START
      │
      ▼
   router          Fetches the venture's System Persona from hub.organizations.
      │             Requires: state.venture_id, config["configurable"]["db"]
      ▼
   agent           Calls claude-sonnet-4-6 with the persona + user prompt.
      │             Requires: state.persona, state.prompt
      ▼
   security        PII-scrubs the raw LLM response.
      │             Requires: state.raw_response
      ▼
    END

Usage
-----
    from graph.chat_graph import compiled_graph
    from langchain_core.runnables import RunnableConfig

    result: ChatState = await compiled_graph.ainvoke(
        {
            "venture_id": "...",
            "prompt": "Hello!",
            "persona": "",
            "raw_response": "",
            "safe_response": "",
            "pii_detected": [],
        },
        config=RunnableConfig(configurable={"db": db_session}),
    )
"""

from langgraph.graph import END, START, StateGraph

from graph.nodes.agent_node import agent_node
from graph.nodes.router_node import router_node
from graph.nodes.security_node import security_node
from graph.state import ChatState

# ── Build the graph ─────────────────────────────────────────────────────────

_builder = StateGraph(ChatState)

_builder.add_node("router", router_node)
_builder.add_node("agent", agent_node)
_builder.add_node("security", security_node)

_builder.add_edge(START, "router")
_builder.add_edge("router", "agent")
_builder.add_edge("agent", "security")
_builder.add_edge("security", END)

# Compile once at import time; the compiled graph is thread- and task-safe.
compiled_graph = _builder.compile()
