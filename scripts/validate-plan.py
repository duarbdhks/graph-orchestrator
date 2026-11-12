#!/usr/bin/env python3
"""Validate a graph-orchestrator machine-readable plan (stdlib only)."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from typing import Any


NODE_EXECUTORS = {"inline", "subagent"}
NODE_TIERS = {"fast", "standard", "strongest"}
NODE_RISKS = {"low", "medium", "high"}
CONSTRAINT_TYPES = {"concurrency", "write_lock"}
GATE_TYPES = {"verify", "approval"}


def node_id_from_ref(ref: Any) -> str | None:
    if not isinstance(ref, str) or not ref.strip():
        return None
    node, dot, suffix = ref.partition(".")
    if ref != ref.strip() or not node or (dot and suffix != "output"):
        return None
    return node


def load_plan(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("plan must be a JSON object")
    return data


def has_cycle(ids: set[str], edges: list[tuple[str, str]]) -> list[str]:
    """Find a directed cycle iteratively, even for graphs >1000 nodes."""
    graph: dict[str, list[str]] = defaultdict(list)
    for src, dst in edges:
        graph[src].append(dst)

    state = {node: 0 for node in ids}  # unseen, visiting, visited
    for root in sorted(ids):
        if state[root]:
            continue
        state[root] = 1
        stack = [(root, iter(graph[root]))]
        positions = {root: 0}
        while stack:
            current, neighbors = stack[-1]
            try:
                neighbor = next(neighbors)
            except StopIteration:
                state[current] = 2
                del positions[current]
                stack.pop()
                continue
            if neighbor not in state:
                continue
            if state[neighbor] == 1:
                path = [node for node, _ in stack]
                return [" -> ".join(path[positions[neighbor]:] + [neighbor])]
            if state[neighbor] == 0:
                state[neighbor] = 1
                positions[neighbor] = len(stack)
                stack.append((neighbor, iter(graph[neighbor])))
    return []

def validate(plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    nodes = plan.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        errors.append("nodes must be a non-empty array")
        return errors

    ids: list[str] = []
    id_set: set[str] = set()
    for i, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"nodes[{i}] must be an object")
            continue
        nid = node.get("id")
        if not isinstance(nid, str) or not nid.strip():
            errors.append(f"nodes[{i}] missing string id")
            continue
        if "." in nid or nid != nid.strip():
            errors.append(f"node {nid}: node id must not contain a dot")
            continue
        if nid in id_set:
            errors.append(f"duplicate node id: {nid}")
            continue
        ids.append(nid)
        id_set.add(nid)

        executor = node.get("executor")
        if executor is not None and (not isinstance(executor, str) or executor not in NODE_EXECUTORS):
            errors.append(f"node {nid}: executor must be inline|subagent, got {executor!r}")
        tier = node.get("tier")
        if tier is not None and (not isinstance(tier, str) or tier not in NODE_TIERS):
            errors.append(f"node {nid}: tier must be fast|standard|strongest, got {tier!r}")
        risk = node.get("risk")
        if risk is not None and (not isinstance(risk, str) or risk not in NODE_RISKS):
            errors.append(f"node {nid}: risk must be low|medium|high, got {risk!r}")

        cardinality = node.get("cardinality")
        if cardinality is not None and (
            not isinstance(cardinality, int) or isinstance(cardinality, bool) or cardinality < 1
        ):
            errors.append(f"node {nid}: cardinality must be a positive integer")

        requires = node.get("requires", [])
        if not isinstance(requires, list):
            errors.append(f"node {nid}: requires must be an array")
        else:
            for ref in requires:
                if node_id_from_ref(ref) is None:
                    errors.append(f"node {nid}: invalid requires entry {ref!r}")

    # second pass for requires now that all ids are known
    for node in nodes:
        if not isinstance(node, dict):
            continue
        nid = node.get("id")
        if not isinstance(nid, str) or nid not in id_set:
            continue
        requires = node.get("requires", [])
        if not isinstance(requires, list):
            continue
        for ref in requires:
            dep = node_id_from_ref(ref)
            if dep and dep not in id_set:
                errors.append(f"node {nid}: requires unknown node {dep}")

    edge_pairs: list[tuple[str, str]] = []
    edges = plan.get("edges", [])
    if edges is None:
        edges = []
    if not isinstance(edges, list):
        errors.append("edges must be an array")
    else:
        for i, edge in enumerate(edges):
            if not isinstance(edge, dict):
                errors.append(f"edges[{i}] must be an object")
                continue
            src, dst = edge.get("from"), edge.get("to")
            if not isinstance(src, str) or src not in id_set:
                errors.append(f"edges[{i}].from unknown node: {src!r}")
            if not isinstance(dst, str) or dst not in id_set:
                errors.append(f"edges[{i}].to unknown node: {dst!r}")
            reason = edge.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                errors.append(f"edges[{i}]: reason must be a non-empty string")
            if isinstance(src, str) and isinstance(dst, str) and src in id_set and dst in id_set:
                edge_pairs.append((src, dst))

    for node in nodes:
        if not isinstance(node, dict):
            continue
        nid = node.get("id")
        if not isinstance(nid, str) or nid not in id_set:
            continue
        requires = node.get("requires", [])
        if not isinstance(requires, list):
            continue
        for ref in requires:
            dep = node_id_from_ref(ref)
            if dep and dep in id_set:
                edge_pairs.append((dep, nid))

    constraints = plan.get("constraints", [])
    if constraints is None:
        constraints = []
    if not isinstance(constraints, list):
        errors.append("constraints must be an array")
    else:
        for i, c in enumerate(constraints):
            if not isinstance(c, dict):
                errors.append(f"constraints[{i}] must be an object")
                continue
            if not isinstance(c.get("type"), str) or c["type"] not in CONSTRAINT_TYPES:
                errors.append(f"constraints[{i}].type must be concurrency|write_lock")
            if not isinstance(c.get("resource"), str) or not c["resource"].strip():
                errors.append(f"constraints[{i}] missing resource")
            limit = c.get("limit")
            if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
                errors.append(f"constraints[{i}].limit must be a positive integer")
            elif c.get("type") == "write_lock" and limit != 1:
                errors.append(f"constraints[{i}]: write_lock limit must be 1")

    gates = plan.get("gates", [])
    if gates is None:
        gates = []
    if not isinstance(gates, list):
        errors.append("gates must be an array")
    else:
        for i, g in enumerate(gates):
            if not isinstance(g, dict):
                errors.append(f"gates[{i}] must be an object")
                continue
            if not isinstance(g.get("type"), str) or g["type"] not in GATE_TYPES:
                errors.append(f"gates[{i}].type must be verify|approval")
            before = g.get("before")
            if not isinstance(before, str) or before not in id_set:
                errors.append(f"gates[{i}].before unknown node: {before!r}")

    phases = plan.get("phases", [])
    if phases is None:
        phases = []
    phase_positions: dict[str, int] = {}
    phase_numbers: set[int] = set()
    if not isinstance(phases, list):
        errors.append("phases must be an array")
    else:
        for i, phase in enumerate(phases):
            if not isinstance(phase, dict):
                errors.append(f"phases[{i}] must be an object")
                continue
            number = phase.get("phase")
            if not isinstance(number, int) or isinstance(number, bool) or number < 0:
                errors.append(f"phases[{i}].phase must be a non-negative integer")
            elif number in phase_numbers:
                errors.append(f"phases[{i}]: duplicate phase number {number}")
            else:
                phase_numbers.add(number)

            if phase.get("mode") not in ("inline", "parallel"):
                errors.append(f"phases[{i}].mode must be inline|parallel")
            batch_size = phase.get("batch_size")
            if batch_size is not None and (
                not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size < 1
            ):
                errors.append(f"phases[{i}].batch_size must be a positive integer")

            raw_nodes = phase.get("nodes", [])
            if not isinstance(raw_nodes, list) or not all(isinstance(n, str) for n in raw_nodes):
                errors.append(f"phases[{i}].nodes must be an array of strings")
                continue
            for nid in raw_nodes:
                if nid not in id_set:
                    errors.append(f"phases[{i}] references unknown node: {nid}")
                elif nid in phase_positions:
                    errors.append(f"node {nid} appears in multiple phase entries")
                elif isinstance(number, int) and not isinstance(number, bool) and number >= 0:
                    phase_positions[nid] = number

        if phases:
            for nid in sorted(id_set - phase_positions.keys()):
                errors.append(f"node {nid} is missing from phases")
            for src, dst in sorted(set(edge_pairs)):
                if src in phase_positions and dst in phase_positions:
                    if phase_positions[src] >= phase_positions[dst]:
                        errors.append(
                            f"dependency {src} -> {dst} violates phase order "
                            f"({phase_positions[src]} >= {phase_positions[dst]})"
                        )

    cycles = has_cycle(id_set, edge_pairs)
    for cycle in cycles:
        errors.append(f"cycle detected: {cycle}")

    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: validate-plan.py <plan.json>", file=sys.stderr)
        return 2
    path = argv[1]
    try:
        plan = load_plan(path)
        errors = validate(plan)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        print(f"{len(errors)} error(s) in {path}", file=sys.stderr)
        return 1
    print(f"ok: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
