# AgentTaskContract

PaperPRISM uses a Codex-native multi-agent runtime. The main agent is the runtime manager and records task state here; Python scripts are optional consistency checks, not the normal user-facing workflow.

Every PaperPRISM agent task must be created before assignment with this contract shape.

```yaml
Task:
Input:
Expected Output:
Acceptance Criteria:
Failure Handling:
```

## Runtime Lifecycle

```text
Create Task
    ↓
Assign Agent
    ↓
Execute
    ↓
Review
    ↓
Retry or Merge
```

Allowed task states:

```yaml
created
assigned
executed
reviewed
retry
merged
failed
```

## Runtime State

| Task ID | Agent | Status | Retry Count | Max Retry | Reviewer | Merge Target | Last Issue Report |
|---|---|---|---:|---:|---|---|---|
|  |  | created / assigned / executed / reviewed / retry / merged / failed | 0 | 2 |  |  |  |

## Standard Agents

| Agent | Responsibility | Forbidden Output |
|---|---|---|
| trajectory-selector | retrieve, rank, and select trajectories | paper prose |
| trajectory-compiler | convert selected trajectory to `ClozeBlueprint` | final paper text |
| paper-writer | fill assigned sentence slots | new structure without blueprint revision |
| novelty-evaluator | evaluate novelty risk | manuscript review |
| review-simulator | reviewer-style critique and revision plan | unsupported evidence claims |
| evidence-mapper | claim and evidence status | invented results or citations |

## Agent Output Envelope

Agent output is not mergeable unless it includes:

```yaml
Task ID:
Agent:
Output:
Contract Compliance:
Acceptance Check:
Open Issues:
Merge Recommendation:
```

`Merge Recommendation` must be one of:

```yaml
merge
retry
fail
```

## Schema Validation Checklist

| Check | Required Condition | Status |
|---|---|---|
| contract_fields_present | `Task`, `Input`, `Expected Output`, `Acceptance Criteria`, `Failure Handling` are non-empty | pass / fail |
| output_envelope_present | output contains all required envelope fields | pass / fail |
| agent_identity_matches | output `Agent` matches assigned agent | pass / fail |
| forbidden_output_absent | output does not include forbidden agent behavior | pass / fail |
| acceptance_criteria_met | acceptance checks are explicit and satisfied | pass / fail |
| merge_recommendation_valid | `merge`, `retry`, or `fail` | pass / fail |

## Quality Scoring

| Dimension | Score | Notes |
|---|---:|---|
| completeness |  |  |
| consistency |  |  |
| citation coverage |  |  |
| trajectory adherence |  |  |

## Retry Loop

```text
Reviewer
    ↓
Issue Report
    ↓
Original Agent Retry
    ↓
Review
```

Stop at `max_retry`, then mark unresolved issues in `PaperState`. The orchestrator must not repair or merge failed output by writing the responsible agent's content itself.
