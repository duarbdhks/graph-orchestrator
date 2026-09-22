# Execution Contract

Read this before a fan-out. The schemas here are the source of truth. `SKILL.md` states the rule; this file states the shape.

Context is not state. Shared state is these files, not the orchestrator's window.

## Terms

| Term | Meaning |
|---|---|
| recon | Bounded listing: items, shared resources, write locks, rubric, worker shape |
| cardinality | How many instances of a node run |
| ledger | The only runtime state for items. `ledger.jsonl` |
| parent return | `item_id`, `status`, `artifact_ref`, summary ≤ 3 lines |
| gate | `verify` or `approval`. A control stop, not data flow |
| write_lock | Single-writer bound on one path. Not an edge |
| fan-in | Join over a cardinality group. Ready when ledger expected vs received is honest |
| rubric | Shared success criteria for every item in the group |

`requires` is ready when the named outputs are ledger `done`. That is readiness. Completeness at fan-in is the join. Do not add fields for either.

## Artifact layout

Default root is workspace-relative. If the host already provides an artifact directory, use that as the root and keep the rest of the layout.

```text
artifacts/graph-orchestrator/<run-id>/
  ledger.jsonl
  items/<item-id>.json
  summaries/<batch-id>.json
```

`<run-id>` is a short timestamp, for example `20260826-1530`. Sanitize `<item-id>` for the filesystem: replace `/` with `__`.

Create the directories before the first dispatch. Do not invent a second store in chat, todos, or a planner database.

## Parent return

Each worker returns only:

```text
item_id
status          # ok | failed | blocked
artifact_ref    # path to the item file
summary         # at most 3 lines; keep paths, names, quantities
```

The item body stays in the file.

## Item file

Every item in a cardinality group uses the same keys. You may add fields the phase needs. Do not remove these:

```json
{
  "item_id": "src/auth/foo.ts",
  "status": "ok",
  "findings": [],
  "evidence": [
    {
      "source": "src/auth/foo.ts:41-58",
      "claim": "handler skips the shared auth middleware"
    }
  ],
  "confidence": "high",
  "errors": []
}
```

| Field | Rule |
|---|---|
| `item_id` | Stable id, unique in the run, because `ledger.jsonl` keeps one line per item. File path, URL, or ticket id. |
| `status` | `ok` \| `failed` \| `blocked` |
| `findings` | Array. Empty array if none. Each finding should carry a severity if the phase uses severity. |
| `evidence` | Array of `{source, claim}`. Claims without a source do not survive fan-in. |
| `confidence` | `high` \| `medium` \| `low` |
| `errors` | Array of strings. Empty on `ok`. |

`blocked` means a required input was missing, not that the worker crashed. `failed` means the worker ran and could not complete the item.

Batch summaries (`summaries/<batch-id>.json`) keep item ids, counts, and concrete findings. "Several files had issues" is not a summary.

## Ledger

`ledger.jsonl` is the only runtime state for items. One line per item.

```json
{
  "item_id": "src/auth/foo.ts",
  "status": "pending",
  "attempt": 0,
  "input_refs": [],
  "output_ref": null,
  "evidence_refs": [],
  "error": null
}
```

| Field | Rule |
|---|---|
| `item_id` | Same id as the item file. |
| `status` | `pending` \| `running` \| `done` \| `failed` \| `blocked` |
| `attempt` | Increment on each dispatch. Starts at 0. |
| `input_refs` | Artifact paths this item needs. |
| `output_ref` | Path to the item file once written. |
| `evidence_refs` | Source locators worth keeping (`path:line`, URL). |
| `error` | Short error on `failed` / `blocked`, else `null`. |

### Status mapping

Worker `status` and ledger `status` are different vocabularies. Map them; do not copy the worker value onto the ledger.

| Moment / worker `status` | Ledger `status` |
|---|---|
| before first dispatch | `pending` |
| dispatch | `running`, `attempt += 1` |
| `ok` | `done`, set `output_ref` |
| `failed` | `failed`, set `output_ref` and `error` |
| `blocked` | `blocked`, set `output_ref` and `error` |
| invalid spawn or missing item file | `failed`, set `error`, do not leave `running` |

Before every fan-in: expected ids vs ledger ids in `done` / `failed` / `blocked`. A line of `38/40` with two named missing ids is a valid ledger query and a valid join result. Do not invent the two missing bodies in prose. Do not start semantic verification until every expected id is `done`, `failed`, or `blocked`.

If `scripts/validate-results.py` exists, run it at fan-in with the expected id list and the **item** JSONL (or a JSONL of the item files). Do not pass `ledger.jsonl` to that script: ledger statuses are not `ok|failed|blocked`. If the script does not exist, do the same expected-vs-received check from the ledger by hand.

## What this file is not

This is not a scheduler. There is no timeout field, no runner-enforced retry, no queue. `attempt` is a counter the orchestrator writes. Caps and redo rules live in `SKILL.md` and `references/verification.md`.
