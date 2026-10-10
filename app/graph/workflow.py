"""
LangGraph StateGraph Workflow Assembly for RideWise Assist
"""

from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END

from app.graph.state import RideWiseState
from app.graph.nodes import (
    router_node,
    rbac_guard_node,
    db_execution_node,
    rag_retrieval_node,
    synthesizer_node,
    verifier_node
)

def check_after_router(state: RideWiseState) -> Literal["verifier", "rbac_guard"]:
    if state.get("final_response"):
        return "verifier"
    return "rbac_guard"

def check_after_rbac(state: RideWiseState) -> Literal["verifier", "db_execution"]:
    if state.get("final_response"):
        return "verifier"
    return "db_execution"

def check_after_db(state: RideWiseState) -> Literal["verifier", "rag_retrieval"]:
    if state.get("final_response"):
        return "verifier"
    return "rag_retrieval"

def build_ridewise_graph():
    """Builds and compiles the RideWise LangGraph workflow."""
    workflow = StateGraph(RideWiseState)

    # Add Nodes
    workflow.add_node("router", router_node)
    workflow.add_node("rbac_guard", rbac_guard_node)
    workflow.add_node("db_execution", db_execution_node)
    workflow.add_node("rag_retrieval", rag_retrieval_node)
    workflow.add_node("synthesizer", synthesizer_node)
    workflow.add_node("verifier", verifier_node)

    # Set Entry Point
    workflow.set_entry_point("router")

    # Add Conditional Edges
    workflow.add_conditional_edges("router", check_after_router)
    workflow.add_conditional_edges("rbac_guard", check_after_rbac)
    workflow.add_conditional_edges("db_execution", check_after_db)
    
    # Direct Edges
    workflow.add_edge("rag_retrieval", "synthesizer")
    workflow.add_edge("synthesizer", "verifier")
    workflow.add_edge("verifier", END)

    return workflow.compile()

# Compiled graph singleton
ridewise_app = build_ridewise_graph()
