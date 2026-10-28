"""Tests for Directed Acyclic Thought Graph (DAG) and Cycle Detection."""

import pytest

from agent_system.core.contracts import ThoughtNode
from agent_system.reasoning.graph import ThoughtGraph


def test_thought_graph_basic_dag():
    graph = ThoughtGraph()

    root = ThoughtNode("root", "Initial problem statement")
    child1 = ThoughtNode("child1", "Branch 1: Heuristic approach", depth=1)
    child2 = ThoughtNode("child2", "Branch 2: Brute force", depth=1)

    graph.add_node(root)
    graph.add_node(child1)
    graph.add_node(child2)

    graph.add_edge("root", "child1")
    graph.add_edge("root", "child2")

    assert len(graph.get_roots()) == 1
    assert graph.get_roots()[0].node_id == "root"
    assert len(graph.get_children("root")) == 2


def test_graph_of_thoughts_fusion():
    """Test Multi-Parent Fusion (GoT) where a node combines ideas from 2 branches."""
    graph = ThoughtGraph()

    root = ThoughtNode("r", "Root")
    a = ThoughtNode("a", "Branch A")
    b = ThoughtNode("b", "Branch B")
    fused = ThoughtNode("fused", "Synthesized Plan (A + B)", is_terminal=True)

    graph.add_node(root)
    graph.add_node(a)
    graph.add_node(b)
    graph.add_node(fused)

    graph.add_edge("r", "a")
    graph.add_edge("r", "b")
    graph.add_edge("a", "fused")
    graph.add_edge("b", "fused")

    parents = [p.node_id for p in graph.get_parents("fused")]
    assert "a" in parents and "b" in parents
    assert len(graph.get_terminals()) == 1
    assert graph.get_terminals()[0].node_id == "fused"


def test_cycle_detection_rejected():
    graph = ThoughtGraph()

    n1 = ThoughtNode("n1", "Node 1")
    n2 = ThoughtNode("n2", "Node 2")
    n3 = ThoughtNode("n3", "Node 3")

    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_node(n3)

    graph.add_edge("n1", "n2")
    graph.add_edge("n2", "n3")

    # Attempting to add n3 -> n1 must trigger cycle detection!
    with pytest.raises(ValueError, match="Cycle detected"):
        graph.add_edge("n3", "n1")

    # Attempting self-loop
    with pytest.raises(ValueError, match="Self-loop"):
        graph.add_edge("n1", "n1")


def test_topological_sort():
    graph = ThoughtGraph()

    for nid in ["task1", "task2", "task3"]:
        graph.add_node(ThoughtNode(nid, f"Action {nid}"))

    graph.add_edge("task1", "task2")
    graph.add_edge("task2", "task3")

    ordered = [n.node_id for n in graph.topological_sort()]
    assert ordered == ["task1", "task2", "task3"]


def test_pruning():
    graph = ThoughtGraph()
    graph.add_node(ThoughtNode("r", "Root"))
    graph.add_node(ThoughtNode("bad_branch", "Failed approach"))
    graph.add_node(ThoughtNode("bad_child", "Sub-step of failed"))

    graph.add_edge("r", "bad_branch")
    graph.add_edge("bad_branch", "bad_child")

    assert len(graph.nodes) == 3
    graph.prune_subgraph("bad_branch")
    assert len(graph.nodes) == 1
    assert "bad_branch" not in graph.nodes
    assert "bad_child" not in graph.nodes


def test_serialization_roundtrip():
    graph = ThoughtGraph()
    graph.add_node(ThoughtNode("n1", "Root", score=1.0))
    graph.add_node(ThoughtNode("n2", "Child", score=0.8, is_terminal=True))
    graph.add_edge("n1", "n2")

    data = graph.to_dict()
    restored = ThoughtGraph.from_dict(data)

    assert len(restored.nodes) == 2
    assert restored.nodes["n2"].score == 0.8
    assert len(restored.get_children("n1")) == 1
