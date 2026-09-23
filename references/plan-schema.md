# Machine-Readable Plan Format

The markdown `## Graph` in `SKILL.md` and this JSON are the same model. Phases in either format are a derived schedule of that graph, not a second source of truth.

Emit this JSON **only** when the plan is being handed to an external runner: a scheduler, a CI job, another agent. For a human reader it's noise; use the markdown graph in `SKILL.md` instead.

Important: nothing in this schema executes on its own. Fields like `max_concurrency` are instructions *to a runner you have written*. If no such runner exists, omit runner-enforced fields rather than emitting values that imply a scheduler is enforcing them.

Worker item shape, parent return, and ledger fields live in `references/execution-contract.md`. Do not duplicate them here.

If `scripts/validate-plan.py` exists, run it on this JSON before handing it over.

## Schema

```json
{
  "goal": "One-sentence statement of what done looks like",
  "nodes": [
    {
      "id": "classify_endpoint",
      "description": "Classify one endpoint's auth posture",
      "requires": ["read_handler.output", "read_middleware.output"],
      "reads": ["src/api/handlers", "src/auth/middleware.ts"],
      "writes": [],
      "output_schema": ["item_id", "status", "findings", "evidence", "confidence", "errors"],
      "risk": "low",
      "cardinality": 60,
      "executor": "subagent",
      "tier": "standard"
    }
  ],
  "edges": [
    {
      "from": "read_middleware",
      "to": "classify_endpoint",
      "reason": "Classification is relative to middleware defaults"
    }
  ],
  "constraints": [
    {
      "type": "concurrency",
      "resource": "github_api",
      "limit": 5
    },
    {
      "type": "write_lock",
      "resource": "src/auth/middleware.ts",
      "limit": 1
    }
  ],
  "gates": [
    {
      "type": "verify",
      "before": "draft_email"
    },
    {
      "type": "approval",
      "before": "send_email"
    }
  ],
  "phases": [
    {
      "phase": 0,
      "mode": "inline",
      "nodes": ["recon"]
    },
    {
      "phase": 1,
      "mode": "parallel",
      "nodes": ["read_handler", "read_middleware"],
      "batch_size": 20
    }
  ],
  "artifacts": {
    "root": "artifacts/graph-orchestrator/<run-id>",
    "ledger": "artifacts/graph-orchestrator/<run-id>/ledger.jsonl"
  },
  "consolidation": {
    "layers": [
      { "inputs": 60, "batch_size": 20, "outputs": 3 },
      { "inputs": 3, "batch_size": 3, "outputs": 1 }
    ],
    "completeness_check": "ledger expected ids vs received ids; list any missing by id"
  },
  "verification": {
    "stages": ["deterministic", "semantic", "sampling"],
    "method": "re-derive from source",
    "scope": "all Critical findings, every High finding that would change the recommendation, and at least one item stage 2 did not re-derive"
  }
}
```

## Field notes

**`requires`**: previous outputs this node consumes, as `node_id.output` or `node_id`. This is the data dependency. If you cannot name what flows, there is no edge.

**`reads` / `writes`**: resources, not other nodes. Two nodes that write the same path need a `write_lock` constraint, not a fake sequencing edge, unless one consumes the other's output.

**`output_schema`**: names the item file keys. It does not name the parent return. Uniform shape across a cardinality group is what makes fan-in cheap. Keep the keys in `references/execution-contract.md`.

**`risk`**: `low` \| `medium` \| `high`. High-risk nodes sit behind verification and, if irreversible, an approval gate.

**`cardinality`**: how many instances of this node run. Lets a runner size batches without inspecting inputs.

**`edges`**: data dependencies only. `from` / `to` must be node ids. `reason` is required. Writing the reason is what catches phantom edges.

**`constraints`**: scheduler bounds, not edges. `type` is `concurrency` or `write_lock`. A rate limit of 5 is `concurrency` on that API, not `A → B`.

**`gates`**: control stops. `type` is `verify` or `approval`. `before` is the node that must not run until the gate passes. A runner that cannot pause for approval must not be handed a plan containing one.

**`artifacts`**: where workers write. Layout is in `references/execution-contract.md`.

**`batch_size`**: cap it at the binding constraint, not at an aspirational number.

**`executor`**: `"inline"` or `"subagent"`. Irreversible nodes, recon, and final synthesis are always `"inline"`; high-cardinality independent nodes are usually `"subagent"`.

**`tier`**: `"fast"`, `"standard"`, or `"strongest"`. A tier name, never a model ID. Use `fast` for independent verification and `strongest` for final judgment after verification.

On Codex, `tier` stays in the plan. Spawn still uses `agent_type="default"` plus explicit `model` and `reasoning_effort`. Do not put a semantic agent type in the plan. Mapping: `references/codex-spawn.md`.

**`verification.stages`**: the three-stage procedure in `references/verification.md`. Do not replace it with "top 5 findings" unless that is only the semantic budget inside that procedure.

**Omit rather than fabricate.** No `timeout_seconds` unless something enforces timeouts. No runner `retry` field unless something retries. Ledger `attempt` is file state, not a promise that a scheduler will retry. A spec that describes infrastructure you don't have is worse than a shorter honest one.
