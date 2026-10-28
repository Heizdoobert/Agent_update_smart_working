"""Directed Acyclic Thought Graph (DAG) with cycle detection for ToT/GoT reasoning."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from agent_system.core.contracts import ThoughtNode


class ThoughtGraph:
    """Manages Tree and Graph of Thoughts (ToT/GoT) enforcing DAG invariants."""

    def __init__(self):
        self.nodes: Dict[str, ThoughtNode] = {}
        self._adj: Dict[str, Set[str]] = {}  # parent -> set of children
        self._rev_adj: Dict[str, Set[str]] = {}  # child -> set of parents

    def add_node(self, node: ThoughtNode) -> None:
        """Add a thought node to the graph."""
        if node.node_id in self.nodes:
            raise ValueError(f"Node '{node.node_id}' already exists in graph.")
        self.nodes[node.node_id] = node
        self._adj[node.node_id] = set()
        self._rev_adj[node.node_id] = set()

        # Connect initial parents
        for pid in list(node.parent_ids):
            if pid in self.nodes:
                self.add_edge(pid, node.node_id)

    def add_edge(self, parent_id: str, child_id: str) -> None:
        """Add directed edge parent -> child. Validates DAG cycle constraints."""
        if parent_id not in self.nodes:
            raise KeyError(f"Parent node '{parent_id}' not found.")
        if child_id not in self.nodes:
            raise KeyError(f"Child node '{child_id}' not found.")

        if parent_id == child_id:
            raise ValueError(f"Self-loop cycle detected on node '{parent_id}'.")

        # Check if parent is reachable from child (which would cause a cycle)
        if self._is_reachable(source=child_id, target=parent_id):
            raise ValueError(
                f"Cycle detected: edge '{parent_id}' -> '{child_id}' would create a cycle."
            )

        self._adj[parent_id].add(child_id)
        self._rev_adj[child_id].add(parent_id)

        # Update node contracts
        p_node = self.nodes[parent_id]
        c_node = self.nodes[child_id]
        if child_id not in p_node.children_ids:
            p_node.children_ids.append(child_id)
        if parent_id not in c_node.parent_ids:
            c_node.parent_ids.append(parent_id)

    def _is_reachable(self, source: str, target: str) -> bool:
        """DFS check if target is reachable from source."""
        visited: Set[str] = set()
        stack = [source]

        while stack:
            curr = stack.pop()
            if curr == target:
                return True
            if curr not in visited:
                visited.add(curr)
                stack.extend(self._adj.get(curr, set()) - visited)

        return False

    def get_roots(self) -> List[ThoughtNode]:
        """Return nodes that have no parents."""
        return [self.nodes[nid] for nid, parents in self._rev_adj.items() if not parents]

    def get_terminals(self) -> List[ThoughtNode]:
        """Return nodes marked as terminal or having no children."""
        return [
            self.nodes[nid]
            for nid, children in self._adj.items()
            if not children or self.nodes[nid].is_terminal
        ]

    def get_children(self, node_id: str) -> List[ThoughtNode]:
        """Return direct child nodes."""
        return [self.nodes[cid] for cid in self._adj.get(node_id, set())]

    def get_parents(self, node_id: str) -> List[ThoughtNode]:
        """Return direct parent nodes."""
        return [self.nodes[pid] for pid in self._rev_adj.get(node_id, set())]

    def topological_sort(self) -> List[ThoughtNode]:
        """Return nodes in topological order."""
        in_degree = {nid: len(parents) for nid, parents in self._rev_adj.items()}
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        sorted_nodes: List[ThoughtNode] = []

        while queue:
            curr = queue.pop(0)
            sorted_nodes.append(self.nodes[curr])
            for child in self._adj.get(curr, set()):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        if len(sorted_nodes) != len(self.nodes):
            raise RuntimeError("Topological sort failed: graph contains unhandled cycle.")

        return sorted_nodes

    def prune_subgraph(self, node_id: str) -> None:
        """Remove a node and all of its descendants."""
        to_remove: Set[str] = set()
        stack = [node_id]

        while stack:
            curr = stack.pop()
            if curr not in to_remove:
                to_remove.add(curr)
                stack.extend(self._adj.get(curr, set()) - to_remove)

        for nid in to_remove:
            # Clean up parent references
            for pid in self._rev_adj.get(nid, set()):
                self._adj[pid].discard(nid)
                if nid in self.nodes[pid].children_ids:
                    self.nodes[pid].children_ids.remove(nid)
            # Remove node
            del self.nodes[nid]
            del self._adj[nid]
            del self._rev_adj[nid]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize graph to dictionary."""
        return {
            "nodes": [
                {
                    "node_id": n.node_id,
                    "thought": n.thought,
                    "parent_ids": list(n.parent_ids),
                    "children_ids": list(n.children_ids),
                    "score": n.score,
                    "depth": n.depth,
                    "visits": n.visits,
                    "is_terminal": n.is_terminal,
                    "metadata": n.metadata,
                }
                for n in self.nodes.values()
            ]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ThoughtGraph:
        """Reconstruct ThoughtGraph from dictionary."""
        graph = cls()
        nodes_data = data.get("nodes", [])

        # Add all nodes first
        for nd in nodes_data:
            node = ThoughtNode(
                node_id=nd["node_id"],
                thought=nd["thought"],
                parent_ids=[],  # Connect via edges
                children_ids=[],
                score=nd.get("score", 0.0),
                depth=nd.get("depth", 0),
                visits=nd.get("visits", 0),
                is_terminal=nd.get("is_terminal", False),
                metadata=nd.get("metadata", {}),
            )
            graph.add_node(node)

        # Add edges
        for nd in nodes_data:
            nid = nd["node_id"]
            for pid in nd.get("parent_ids", []):
                if pid in graph.nodes:
                    graph.add_edge(pid, nid)

        return graph
