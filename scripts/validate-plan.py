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
    return ref.split(".", 1)[0]


def load_plan(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("plan must be a JSON object")
    return data


def has_cycle(ids: set[str], edges: list[tuple[str, str]]) -> list[str]:
    graph: dict[str, list[str]] = defaultdict(list)
    for src, dst in edges:
        graph[src].append(dst)
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in ids}
    found: list[str] = []

    def dfs(u: str, stack: list[str]) -> None:
        color[u] = GRAY
        stack.append(u)
        for v in graph[u]:
            if v not in color:
                continue
            if color[v] == GRAY:
                cycle_start = stack.index(v)
                found.append(" -> ".join(stack[cycle_start:] + [v]))
                return
            if color[v] == WHITE:
                dfs(v, stack)
                if found:
                    return
        stack.pop()
        color[u] = BLACK

    for n in ids:
        if color[n] == WHITE:
            dfs(n, [])
            if found:
                return found
    return found


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
        if not isinstance(nid, str) or not nid:
            errors.append(f"nodes[{i}] missing string id")
            continue
        if nid in id_set:
            errors.append(f"duplicate node id: {nid}")
            continue
        ids.append(nid)
        id_set.add(nid)

        executor = node.get("executor")
        if executor is not None and executor not in NODE_EXECUTORS:
            errors.append(f"node {nid}: executor must be inline|subagent, got {executor!r}")
        tier = node.get("tier")
        if tier is not None and tier not in NODE_TIERS:
            errors.append(f"node {nid}: tier must be fast|standard|strongest, got {tier!r}")
        risk = node.get("risk")
        if risk is not None and risk not in NODE_RISKS:
            errors.append(f"node {nid}: risk must be low|medium|high, got {risk!r}")

        requires = node.get("requires") or []
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
        if nid not in id_set:
            continue
        for ref in node.get("requires") or []:
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
            if src not in id_set:
                errors.append(f"edges[{i}].from unknown node: {src!r}")
            if dst not in id_set:
                errors.append(f"edges[{i}].to unknown node: {dst!r}")
            if not edge.get("reason"):
                errors.append(f"edges[{i}] missing reason")
            if src in id_set and dst in id_set:
                edge_pairs.append((src, dst))

    for node in nodes:
        if not isinstance(node, dict):
            continue
        nid = node.get("id")
        if nid not in id_set:
            continue
        for ref in node.get("requires") or []:
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
            if c.get("type") not in CONSTRAINT_TYPES:
                errors.append(f"constraints[{i}].type must be concurrency|write_lock")
            if not c.get("resource"):
                errors.append(f"constraints[{i}] missing resource")
            limit = c.get("limit")
            if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
                errors.append(f"constraints[{i}].limit must be a positive integer")

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
            if g.get("type") not in GATE_TYPES:
                errors.append(f"gates[{i}].type must be verify|approval")
            before = g.get("before")
            if before not in id_set:
                errors.append(f"gates[{i}].before unknown node: {before!r}")

    phases = plan.get("phases", [])
    if phases is None:
        phases = []
    if not isinstance(phases, list):
        errors.append("phases must be an array")
    else:
        for i, phase in enumerate(phases):
            if not isinstance(phase, dict):
                errors.append(f"phases[{i}] must be an object")
                continue
            for nid in phase.get("nodes") or []:
                if nid not in id_set:
                    errors.append(f"phases[{i}] references unknown node: {nid}")

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
