# AgentRuntimeLedger

Use this ledger when a PaperPRISM session delegates work across multiple Codex skills. The main agent owns the ledger and updates it before merge.

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

## Task Ledger

| Task ID | Agent | Contract Summary | Status | Retry Count | Max Retry | Reviewer | Merge Target | Last Issue Report |
|---|---|---|---|---:|---:|---|---|---|
|  |  |  | created / assigned / executed / reviewed / retry / merged / failed | 0 | 2 |  |  |  |

## Output Envelope Gate

Agent output must include:

```yaml
Task ID:
Agent:
Output:
Contract Compliance:
Acceptance Check:
Open Issues:
Merge Recommendation:
```

`Merge Recommendation` must be `merge`, `retry`, or `fail`.

## Merge Rule

Merge only when:

```yaml
contract_fields_present: true
output_envelope_present: true
agent_identity_matches: true
acceptance_criteria_met: true
merge_recommendation: merge
retry_count_within_limit: true
```

If any gate fails, create an Issue Report and retry with the original agent until `max_retry`. Record unresolved issues in `PaperState`.
