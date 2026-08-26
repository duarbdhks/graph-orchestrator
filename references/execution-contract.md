# Execution Contract

Read this before a fan-out. The schemas here are the source of truth. `SKILL.md` states the rule; this file states the shape.

Workers write files. The parent keeps an artifact ref and a short summary, not the item body. Fan-in reduces records of the same shape. Completeness is a ledger aggregate, not a mental count.

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

The item body stays in the file. Returning the full analysis to the parent is how this skill loses its reason to exist.

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
| `item_id` | Stable id, unique in the group. File path, URL, ticket id. |
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

Update points:

- before dispatch: `running`, `attempt += 1`
- on worker return: `done` or `failed`, set `output_ref`
- missing dependency: `blocked`, set `error`
- before every fan-in: expected ids vs ledger ids in `done` / `failed` / `blocked`

A line of `38/40` with two named missing ids is a ledger query. Do not synthesize over unnamed gaps.

If `scripts/validate-results.py` exists, run it at fan-in with the expected id list and the item JSONL (or a JSONL of the item files). If it does not exist, do the same check by hand.

## What this file is not

This is not a scheduler. There is no timeout field, no runner-enforced retry, no queue. `attempt` is a counter the orchestrator writes. Caps and redo rules live in `SKILL.md` and `references/verification.md`.
