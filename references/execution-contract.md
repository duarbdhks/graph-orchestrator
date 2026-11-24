# Execution Contract

Read this before fan-out or routing. Use these shapes for worker output and state.

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
| fan-in | Join planned IDs with current ledger rows and item files |
| rubric | Shared success criteria for every item in the group |

For a `requires` entry, check for ledger `done` and a valid current `output_ref`. A terminal failure is enough to report the outcome at fan-in. Consumers of the required output remain `blocked`.

## Routing

Declare the classifier, the exact string values it can return as `route`, the continuation for each value, and the check the paths share. Keep the classifier inline when it is a small lookup. Put `route` and its supporting evidence in the classifier's item file.

The parent validates the classifier's item file, requires `ok`, and looks up its `route` in the declared table. A missing, ambiguous, or unlisted value fails the classifier item. Record the reason in the ledger and leave its `output_ref` empty.

Expand only the selected continuation. Bind the common join's `requires` to the selected outputs it reads. An explicitly empty continuation passes the classifier's evidence to the join. Derive phases and fix the expected IDs for the active phase before dispatch. Inactive paths stay outside its expected IDs. Apply the same gates to the selected path.

## Artifact layout

Default root is workspace-relative. If the host already provides an artifact directory, use that as the root and keep the rest of the layout.

```text
artifacts/graph-orchestrator/<run-id>/
  ledger.jsonl
  items/<item-id>.json
  summaries/<batch-id>.json
```

`<run-id>` is a short timestamp, for example `20260826-1530`. Sanitize `<item-id>` for the filesystem: replace `/` with `__`.

Create the directories before the first dispatch. Assign a new path under `items/` for a retry, such as `items/attempt-2/<item-id>.json`. Read only the current `output_ref` when joining results.

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

The parent maintains `ledger.jsonl` with one current row per item. Workers write their assigned item files.

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
| dispatch | `running`, `attempt += 1`, clear stale output and evidence refs and error |
| `ok` | `done`, set `output_ref` |
| `failed` | `failed`, set `output_ref` and `error` |
| `blocked` | `blocked`, set `output_ref` and `error` |
| invalid spawn or invalid or missing item file | `failed`, set `error`, clear `output_ref` |
| required input cannot be used | `blocked`, record the dependency and reason, leave `attempt` unchanged if undispatched |

At fan-in, use the expected IDs from the active plan and the ledger rows for that scope. Check each `output_ref` for an item file with the matching `item_id` and mapped `status`. Count valid item files as received. Count valid files with `ok` and ledger `done` as successful. Name missing, invalid, failed, and blocked IDs. An error row can explain a missing file. Record a verification verdict separately from these counts.

If `scripts/validate-results.py` is available, validate the expected IDs and JSONL built from the current item files. Otherwise, verify those IDs and item shapes directly. For required scopes, use the success check in `references/verification.md`.

## What this file is not

This is not a scheduler. There is no timeout field, no runner-enforced retry, no queue. `attempt` is a counter the orchestrator writes. Caps and redo rules live in `SKILL.md` and `references/verification.md`.
