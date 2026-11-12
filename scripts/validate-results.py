#!/usr/bin/env python3
"""Validate worker item JSONL against expected ids (stdlib only)."""

from __future__ import annotations

import json
import sys
from typing import Any


STATUSES = {"ok", "failed", "blocked"}
CONFIDENCES = {"high", "medium", "low"}
REQUIRED = ("item_id", "status", "findings", "evidence", "confidence", "errors")


def load_expected(path: str) -> list[str]:
    with open(path, encoding="utf-8") as fh:
        stripped = fh.read().strip()
    if stripped.startswith("[") or stripped.startswith("{"):
        data = json.loads(stripped)
        if isinstance(data, dict) and "ids" in data:
            data = data["ids"]
    else:
        data = [
            line.strip() for line in stripped.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    if not isinstance(data, list) or not data or not all(
        isinstance(value, str) and value.strip() and value == value.strip()
        for value in data
    ):
        raise ValueError("expected ids must be a non-empty array of non-blank strings")
    if len(data) != len(set(data)):
        raise ValueError("expected ids contain duplicates")
    return data

def load_results(path: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            text = line.strip()
            if not text:
                continue
            try:
                row = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSON ({exc})") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{lineno}: each line must be a JSON object")
            items.append(row)
    return items


def validate(expected: list[str], items: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen: dict[str, int] = {}
    received: list[str] = []

    for i, item in enumerate(items):
        loc = f"item[{i}]"
        for key in REQUIRED:
            if key not in item:
                errors.append(f"{loc} missing field {key}")
        item_id = item.get("item_id")
        if not isinstance(item_id, str) or not item_id.strip():
            errors.append(f"{loc} item_id must be a non-empty string")
            continue
        received.append(item_id)
        if item_id in seen:
            errors.append(f"duplicate item_id: {item_id} (rows {seen[item_id]} and {i})")
        else:
            seen[item_id] = i

        status = item.get("status")
        if not isinstance(status, str) or status not in STATUSES:
            errors.append(f"{item_id}: status must be ok|failed|blocked, got {status!r}")
        confidence = item.get("confidence")
        if "confidence" in item and (not isinstance(confidence, str) or confidence not in CONFIDENCES):
            errors.append(f"{item_id}: confidence must be high|medium|low, got {confidence!r}")
        for field in ("findings", "evidence", "errors"):
            if field in item and not isinstance(item[field], list):
                errors.append(f"{item_id}: {field} must be an array")
        if isinstance(item.get("evidence"), list):
            for j, ev in enumerate(item["evidence"]):
                if not isinstance(ev, dict) or any(
                    not isinstance(ev.get(key), str) or not ev[key].strip()
                    for key in ("source", "claim")
                ):
                    errors.append(f"{item_id}: evidence[{j}] must have non-blank source and claim")
        item_errors = item.get("errors")
        if isinstance(item_errors, list):
            for j, error in enumerate(item_errors):
                if not isinstance(error, str) or not error.strip():
                    errors.append(f"{item_id}: errors[{j}] must be a non-blank string")
            if status == "ok" and item_errors:
                errors.append(f"{item_id}: ok status must have no errors")
            elif status in ("failed", "blocked") and not item_errors:
                errors.append(f"{item_id}: {status} status must include an error")

    expected_set = list(dict.fromkeys(expected))
    received_set = set(received)
    missing = [eid for eid in expected_set if eid not in received_set]
    extra = [rid for rid in received if rid not in set(expected_set)]
    if missing:
        errors.append("missing ids: " + ", ".join(missing))
    if extra:
        errors.append("unexpected ids: " + ", ".join(extra))

    print(
        f"expected={len(expected_set)} received={len(received)} "
        f"missing={len(missing)} extra={len(extra)}"
    )
    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "usage: validate-results.py <expected-ids.json|txt> <results.jsonl>",
            file=sys.stderr,
        )
        return 2
    expected_path, results_path = argv[1], argv[2]
    try:
        expected = load_expected(expected_path)
        items = load_results(results_path)
        errors = validate(expected, items)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        print(f"{len(errors)} error(s)", file=sys.stderr)
        return 1
    print(f"ok: {results_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
