"""The workflow as a graph:

  research -> plan -> [write_blog | write_video | make_images] -> write_posts -> approve -> publish

The three content steps run in parallel because none of them depends on the others.
"""
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agent import nodes
from agent.state import AgentState


def build_graph(checkpointer=None):
    g = StateGraph(AgentState)
    g.add_node("research", nodes.research)
    g.add_node("plan", nodes.plan)
    g.add_node("write_blog", nodes.write_blog)
    g.add_node("write_video", nodes.write_video)
    g.add_node("make_images", nodes.make_images)
    g.add_node("write_posts", nodes.write_posts)
    g.add_node("approve", nodes.approve)
    g.add_node("publish", nodes.publish)

    g.add_edge(START, "research")
    g.add_edge("research", "plan")
    for step in ("write_blog", "write_video", "make_images"):  # fan out: run in parallel
        g.add_edge("plan", step)
    g.add_edge(["write_blog", "write_video", "make_images"], "write_posts")  # join: wait for all three
    g.add_edge("write_posts", "approve")
    g.add_conditional_edges("approve", nodes.route_after_approval, {"publish": "publish", "end": END})
    g.add_edge("publish", END)

    # The checkpointer lets the graph pause at "approve" and resume later.
    return g.compile(checkpointer=checkpointer or MemorySaver())
