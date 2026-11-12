# Machine-Readable Plan Format

The markdown `## Graph` in `SKILL.md` and this JSON are the same model. Phases in either format are a derived schedule of that graph, not a second source of truth.

Emit this JSON **only** when the plan is being handed to an external runner: a scheduler, a CI job, another agent. For a human reader it's noise; use the markdown graph in `SKILL.md` instead.

Important: nothing in this schema executes on its own. Fields like `max_concurrency` are instructions *to a runner you have written*. If no such runner exists, omit runner-enforced fields rather than emitting values that imply a scheduler is enforcing them.

Worker item shape, parent return, and ledger fields live in `references/execution-contract.md`. Do not duplicate them here.

If `scripts/validate-plan.py` exists, run it on this JSON before handing it over.

## Schema

The example below is a complete, validator-accepted graph with a derived phase schedule. The approval gate is a control stop, not a data dependency.

```json
{
  "goal": "Audit 60 handlers, draft an email, then send only after approval",
  "nodes": [
    {
      "id": "recon",
      "description": "List targets and shared resources",
      "requires": [],
      "cardinality": 1,
      "executor": "inline",
      "tier": "fast"
    },
    {
      "id": "read_handler",
      "description": "Read one handler",
      "requires": [
        "recon.output"
      ],
      "cardinality": 60,
      "executor": "subagent",
      "tier": "standard"
    },
    {
      "id": "read_middleware",
      "description": "Read shared middleware",
      "requires": [
        "recon.output"
      ],
      "cardinality": 1,
      "executor": "subagent",
      "tier": "standard"
    },
    {
      "id": "classify_endpoint",
      "description": "Classify one endpoint's auth posture",
      "requires": [
        "read_handler.output",
        "read_middleware.output"
      ],
      "reads": [
        "src/api/handlers",
        "src/auth/middleware.ts"
      ],
      "writes": [],
      "output_schema": [
        "item_id",
        "status",
        "findings",
        "evidence",
        "confidence",
        "errors"
      ],
      "risk": "low",
      "cardinality": 60,
      "executor": "subagent",
      "tier": "standard"
    },
    {
      "id": "draft_email",
      "description": "Consolidate verified findings into an email",
      "requires": [
        "classify_endpoint.output"
      ],
      "cardinality": 1,
      "executor": "inline",
      "tier": "standard"
    },
    {
      "id": "send_email",
      "description": "Send only after human approval",
      "requires": [
        "draft_email.output"
      ],
      "cardinality": 1,
      "executor": "inline",
      "tier": "strongest",
      "risk": "high"
    }
  ],
  "edges": [
    {
      "from": "recon",
      "to": "read_handler",
      "reason": "Read only the identified target handlers"
    },
    {
      "from": "recon",
      "to": "read_middleware",
      "reason": "Read the shared resource discovered in recon"
    },
    {
      "from": "read_handler",
      "to": "classify_endpoint",
      "reason": "Classification consumes each handler"
    },
    {
      "from": "read_middleware",
      "to": "classify_endpoint",
      "reason": "Classification consumes middleware defaults"
    },
    {
      "from": "classify_endpoint",
      "to": "draft_email",
      "reason": "Email summarizes the verified findings"
    },
    {
      "from": "draft_email",
      "to": "send_email",
      "reason": "Send consumes the approved draft"
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
      "nodes": [
        "recon"
      ]
    },
    {
      "phase": 1,
      "mode": "parallel",
      "nodes": [
        "read_handler",
        "read_middleware"
      ],
      "batch_size": 20
    },
    {
      "phase": 2,
      "mode": "parallel",
      "nodes": [
        "classify_endpoint"
      ],
      "batch_size": 20
    },
    {
      "phase": 3,
      "mode": "inline",
      "nodes": [
        "draft_email"
      ]
    },
    {
      "phase": 4,
      "mode": "inline",
      "nodes": [
        "send_email"
      ]
    }
  ],
  "artifacts": {
    "root": "artifacts/graph-orchestrator/<run-id>",
    "ledger": "artifacts/graph-orchestrator/<run-id>/ledger.jsonl"
  },
  "consolidation": {
    "layers": [
      {
        "inputs": 60,
        "batch_size": 20,
        "outputs": 3
      },
      {
        "inputs": 3,
        "batch_size": 3,
        "outputs": 1
      }
    ],
    "completeness_check": "ledger expected ids vs received ids; list any missing by id"
  },
  "verification": {
    "stages": [
      "deterministic",
      "semantic",
      "sampling"
    ],
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
