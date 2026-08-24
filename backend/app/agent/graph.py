"""LangGraph StateGraph Builder and Workflow Engine (TRD Section 11.1, Table 28, Table 30, ADR-005)."""

from typing import Literal
from langgraph.graph import StateGraph, START, END

from backend.app.agent.state import AgentState
from backend.app.agent.nodes import (
    task_understanding_node,
    planning_node,
    model_selection_node,
    tool_selection_node,
    execution_node,
    observation_node,
    validation_node,
    final_deliverable_node,
)


def should_continue_or_finalize(state: AgentState) -> Literal["planning", "model_selection", "final_deliverable"]:
    """Conditional edge from Validation (TRD Table 30):
    - If passed & steps remain in plan -> model_selection (next plan step)
    - If passed & plan exhausted -> final_deliverable (succeeded)
    - If failed & iteration < max_iterations -> planning (re-plan loop)
    - If failed & iteration >= max_iterations -> final_deliverable (failed_bounded)
    """
    validation_passed = state.get("validation_passed", False)
    iteration = state.get("iteration", 1)
    max_iterations = state.get("max_iterations", 4)
    current_step_index = state.get("current_step_index", 0)
    plan = state.get("plan", [])

    if not validation_passed:
        if iteration < max_iterations:
            return "planning"
        return "final_deliverable"

    # Validation passed: check if there are more steps in current plan
    if current_step_index < len(plan):
        return "model_selection"

    return "final_deliverable"


def build_agent_graph() -> StateGraph:
    """Build and compile the fixed 7 operational stages + 1 terminal node LangGraph state machine."""
    builder = StateGraph(AgentState)

    # 1. Add all 8 nodes
    builder.add_node("task_understanding", task_understanding_node)
    builder.add_node("planning", planning_node)
    builder.add_node("model_selection", model_selection_node)
    builder.add_node("tool_selection", tool_selection_node)
    builder.add_node("execution", execution_node)
    builder.add_node("observation", observation_node)
    builder.add_node("validation", validation_node)
    builder.add_node("final_deliverable", final_deliverable_node)

    # 2. Add sequential edges
    builder.add_edge(START, "task_understanding")
    builder.add_edge("task_understanding", "planning")
    builder.add_edge("planning", "model_selection")
    builder.add_edge("model_selection", "tool_selection")
    builder.add_edge("tool_selection", "execution")
    builder.add_edge("execution", "observation")
    builder.add_edge("observation", "validation")

    # 3. Add conditional edge from validation
    builder.add_conditional_edges(
        "validation",
        should_continue_or_finalize,
        {
            "planning": "planning",
            "model_selection": "model_selection",
            "final_deliverable": "final_deliverable",
        },
    )

    # 4. Terminal edge
    builder.add_edge("final_deliverable", END)

    return builder.compile()


# Compiled agent graph singleton
agent_graph = build_agent_graph()
