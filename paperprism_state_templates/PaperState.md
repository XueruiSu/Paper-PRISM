# PaperState

## Current Status

- Current phase:
- Active files:
- Active TrajectorySelectionReport:
- Active ClozeBlueprint:
- Latest completed section:
- PDF status:

## Workflow Gates

| Gate | Required Condition | Current Value | Status |
|---|---|---|---|
| trajectory_selection | `TrajectorySelectionReport` exists before blueprint |  | pass / blocked |
| blueprint_generation | `ClozeBlueprint` has Section -> Paragraph -> Sentence slots |  | pass / blocked |
| agent_contract | all delegated tasks have complete `AgentTaskContract` entries |  | pass / blocked |
| agent_output_schema | agent outputs include required output envelope before merge |  | pass / blocked |
| retry_resolution | failed reviews were retried until pass or `max_retry` |  | pass / blocked |
| sentence_lifecycle | no `planned -> verified` transition |  | pass / blocked |
| evidence_support | `unsupported_sentences == 0` |  | pass / blocked |
| writing_progress | `planned_sentences == 0` |  | pass / blocked |
| final_export | evidence_support and writing_progress pass |  | pass / blocked |

## Agent Runtime Ledger

| Task ID | Agent | Status | Retry Count | Max Retry | Reviewer | Merge Target | Open Issue |
|---|---|---|---:|---:|---|---|---|
|  |  | created / assigned / executed / reviewed / retry / merged / failed | 0 | 2 |  |  |  |

## Orchestrator Boundary Check

| Check | Value | Action If True |
|---|---|---|
| orchestrator_wrote_text | false | workflow violation; reroute to `paper-writer` |
| orchestrator_reviewed_paper | false | workflow violation; reroute to `review-simulator` |
| orchestrator_did_novelty_eval | false | workflow violation; reroute to `novelty-evaluator` |

## Open Tasks

| Priority | Task | Owner | Blocking Evidence |
|---|---|---|---|
| must-fix |  | Codex / user |  |

## Review Issues

- Must fix:
- Should fix:
- Writing-only:

## Next Actions

1.
2.
3.
