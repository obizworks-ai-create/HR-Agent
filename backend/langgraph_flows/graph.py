from langgraph.graph import StateGraph, END
from langgraph_flows.state import HRPipelineState
from langgraph_flows.nodes import (
    extract_jd_requirements_node,
    fetch_new_candidates_node,
    analyze_cv_node,
    generate_hr_questions_node,
    send_to_hr_node
)

def pass_fail_gate(state: HRPipelineState):
    verdict = state.get("verdict", "FAIL")
    if verdict == "PASS":
        return "pass"
    return "fail"

# Define the graph
workflow = StateGraph(HRPipelineState)

# Add Nodes
workflow.add_node("extract_jd_requirements_node", extract_jd_requirements_node)
workflow.add_node("fetch_new_candidates_node", fetch_new_candidates_node)

workflow.add_node("analyze_cv_node", analyze_cv_node)
workflow.add_node("generate_hr_questions_node", generate_hr_questions_node)
workflow.add_node("send_to_hr_node", send_to_hr_node)

# Define Logic
# This graph is multi-purpose. We can start at different points or have unconditional edges that skip if data missing.
# Standard Flow for Candidate: fetch -> download -> analyze -> gate -> generate -> send -> end
# JD Flow: extract_jd -> end (manually invoked or separate path)

# We set entry point to fetch.
workflow.set_entry_point("fetch_new_candidates_node")

workflow.add_edge("fetch_new_candidates_node", "analyze_cv_node")

workflow.add_conditional_edges(
    "analyze_cv_node",
    pass_fail_gate,
    {
        "pass": "generate_hr_questions_node",
        "fail": END
    }
)

workflow.add_edge("generate_hr_questions_node", "send_to_hr_node")
workflow.add_edge("send_to_hr_node", END)

# Compile
hr_pipeline_graph = workflow.compile()
