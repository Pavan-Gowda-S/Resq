"""
LangGraph Orchestrator - State Graph Definition.
Unified multi-agent workflow with conditional routing and human checkpoints.
"""
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from agents.core.state import AgentState
from agents.core.client import ResqApiClient

# Import all agent nodes
from agents.incident_intelligence.agent import run_incident_intelligence
from agents.risk_decision.agent import run_risk_decision
from agents.rescue_matching.agent import run_rescue_matching
from agents.hospital_matching.agent import run_hospital_matching
from agents.route_mobility.agent import run_route_mobility
from agents.resource_marketplace.agent import run_resource_marketplace
from agents.verification_audit.agent import run_verification_audit


def should_run_rescue_matching(state: AgentState) -> bool:
    """Check if rescue matching should run."""
    task_proposals = state.get("task_proposals", [])
    return any(t.get("task_type") == "RESCUE_EXTRACTION" for t in task_proposals)


def should_run_hospital_matching(state: AgentState) -> bool:
    """Check if hospital matching should run."""
    task_proposals = state.get("task_proposals", [])
    return any(
        t.get("task_type") in ["HOSPITAL_ADMISSION", "AMBULANCE_TRANSPORT"]
        for t in task_proposals
    )


def should_run_resource_marketplace(state: AgentState) -> bool:
    """Check if resource marketplace should run."""
    task_proposals = state.get("task_proposals", [])
    return any(t.get("task_type") == "SUPPLY_DELIVERY" for t in task_proposals)


def route_after_risk_decision(state: AgentState) -> Literal["rescue_matching", "hospital_matching", "resource_marketplace", "route_mobility"]:
    """
    Conditional routing after risk decision based on task types.
    Routes to first matching agent in priority order.
    """
    if should_run_rescue_matching(state):
        return "rescue_matching"
    elif should_run_hospital_matching(state):
        return "hospital_matching"
    elif should_run_resource_marketplace(state):
        return "resource_marketplace"
    else:
        return "route_mobility"


def route_after_rescue(state: AgentState) -> Literal["hospital_matching", "resource_marketplace", "route_mobility"]:
    """Route after rescue matching."""
    if should_run_hospital_matching(state):
        return "hospital_matching"
    elif should_run_resource_marketplace(state):
        return "resource_marketplace"
    else:
        return "route_mobility"


def route_after_hospital(state: AgentState) -> Literal["resource_marketplace", "route_mobility"]:
    """Route after hospital matching."""
    if should_run_resource_marketplace(state):
        return "resource_marketplace"
    else:
        return "route_mobility"


def build_orchestrator_graph(client: ResqApiClient) -> StateGraph:
    """
    Build the complete LangGraph StateGraph for incident lifecycle orchestration.

    Graph flow:
    1. Incident Intelligence (entity extraction, duplicate detection)
    2. Risk Decision (triage, task pathway generation)
    3. [CONDITIONAL ROUTING based on task types]
       - Rescue Matching (if RESCUE_EXTRACTION tasks exist)
       - Hospital Matching (if HOSPITAL_ADMISSION or AMBULANCE_TRANSPORT tasks exist)
       - Resource Marketplace (if SUPPLY_DELIVERY tasks exist)
    4. Route Mobility (assess transport routes for matched resources)
    5. Verification Audit (validate completeness, generate audit summary)
    6. END

    Human-in-the-loop checkpoint:
    - If triage.requires_human_review == True, state["human_review_required"] is set
    - Control room must authorize before automated dispatch

    Args:
        client: RESQ API client for all agents

    Returns:
        Compiled StateGraph ready for execution
    """

    # Create graph
    workflow = StateGraph(AgentState)

    # Add agent nodes with client binding (must be async-compatible)
    async def intelligence_node(state):
        return await run_incident_intelligence(state, client)

    async def risk_decision_node(state):
        return await run_risk_decision(state, client)

    async def rescue_matching_node(state):
        return await run_rescue_matching(state, client)

    async def hospital_matching_node(state):
        return await run_hospital_matching(state, client)

    async def resource_marketplace_node(state):
        return await run_resource_marketplace(state, client)

    async def route_mobility_node(state):
        return await run_route_mobility(state)

    async def verification_audit_node(state):
        return await run_verification_audit(state, client)

    workflow.add_node("intelligence", intelligence_node)
    workflow.add_node("risk_decision", risk_decision_node)
    workflow.add_node("rescue_matching", rescue_matching_node)
    workflow.add_node("hospital_matching", hospital_matching_node)
    workflow.add_node("resource_marketplace", resource_marketplace_node)
    workflow.add_node("route_mobility", route_mobility_node)
    workflow.add_node("verification_audit", verification_audit_node)

    # Set entry point
    workflow.set_entry_point("intelligence")

    # Intelligence -> Risk Decision (always)
    workflow.add_edge("intelligence", "risk_decision")

    # Risk Decision -> Conditional routing based on task types
    workflow.add_conditional_edges(
        "risk_decision",
        route_after_risk_decision,
        {
            "rescue_matching": "rescue_matching",
            "hospital_matching": "hospital_matching",
            "resource_marketplace": "resource_marketplace",
            "route_mobility": "route_mobility"
        }
    )

    # Rescue Matching -> Next conditional
    workflow.add_conditional_edges(
        "rescue_matching",
        route_after_rescue,
        {
            "hospital_matching": "hospital_matching",
            "resource_marketplace": "resource_marketplace",
            "route_mobility": "route_mobility"
        }
    )

    # Hospital Matching -> Next conditional
    workflow.add_conditional_edges(
        "hospital_matching",
        route_after_hospital,
        {
            "resource_marketplace": "resource_marketplace",
            "route_mobility": "route_mobility"
        }
    )

    # Resource Marketplace -> Route Mobility (always)
    workflow.add_edge("resource_marketplace", "route_mobility")

    # Route Mobility -> Verification Audit (always)
    workflow.add_edge("route_mobility", "verification_audit")

    # Verification Audit -> END (always)
    workflow.add_edge("verification_audit", END)

    # Compile graph
    return workflow.compile()
