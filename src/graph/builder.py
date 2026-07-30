from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from src.graph.edges import route_after_validation
from src.graph.nodes.aggregator import aggregator_node
from src.graph.nodes.formatter import formatter_node
from src.graph.nodes.mindmap import mindmap_generator
from src.graph.nodes.pdf_exporter import pdf_exporter_node
from src.graph.nodes.planner import planner_node
from src.graph.nodes.pyq_agent import pyq_agent_node
from src.graph.nodes.research import research_node
from src.graph.nodes.synthesizer import synthesizer_node
from src.graph.nodes.validator import validator_node
from src.graph.state import NotesState


def build_graph() -> StateGraph:
    workflow = StateGraph(NotesState)

    workflow.add_node("planner", planner_node)
    workflow.add_node("mindmap_generator", mindmap_generator)
    workflow.add_node("research", research_node)
    workflow.add_node("aggregator", aggregator_node)
    workflow.add_node("synthesizer", synthesizer_node)
    workflow.add_node("validator", validator_node)
    workflow.add_node("formatter", formatter_node)
    workflow.add_node("pyq_agent", pyq_agent_node)
    workflow.add_node("pdf_exporter", pdf_exporter_node)

    workflow.set_entry_point("planner")

    workflow.add_edge("planner", "mindmap_generator")
    workflow.add_edge("planner", "research")
    workflow.add_edge("mindmap_generator", "aggregator")
    workflow.add_edge("research", "aggregator")
    workflow.add_edge("aggregator", "synthesizer")
    workflow.add_edge("synthesizer", "validator")

    workflow.add_conditional_edges(
        "validator",
        route_after_validation,
        {
            "synthesizer": "synthesizer",
            "format_pyq": "formatter",
        },
    )

    workflow.add_edge("formatter", "pyq_agent")
    workflow.add_edge("pyq_agent", "pdf_exporter")
    workflow.add_edge("pdf_exporter", END)

    checkpointer = MemorySaver()

    return workflow.compile(checkpointer=checkpointer)


graph = build_graph()
