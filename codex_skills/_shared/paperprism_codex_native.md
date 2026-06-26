# PaperPRISM Codex-Native Protocol

PaperPRISM is a Codex-native writing workflow. Normal use does not require Python, CLI commands, fixed JSON schemas, or generated stage artifacts.

## Resource Root

PaperPRISM skills depend on the PaperPRISM resource library, not only on skill prompt files. Before using trajectory selection, archetype selection, blueprint construction, or validation helpers, locate the PaperPRISM resource root in this order:

1. The current working repository, if it contains `data/generated_sentence_trajectories.json`.
2. `$PAPERPRISM_HOME`, if set.
3. `$CODEX_HOME/paperprism`, if `CODEX_HOME` is set.
4. `~/.codex/paperprism`.

The resource root should contain:

- `data/generated_sentence_trajectories.json`
- `data/executable_archetypes.json`
- `data/archetypes.json`
- `data/research_archetype_knowledge_base.json`
- `data/persuasion_strategy_library.json`
- `scripts/`
- `paperprism_state_templates/`

When running helper scripts, run them from the resource root or pass paths relative to that root. Do not assume `codex_skills/` alone contains the trajectory library.

## Core Objects

Maintain these as human-readable working files when useful:

- `ResearchAsset.md`: what the user has provided, normalized by Codex.
- `ClaimEvidenceMap.md`: claims, available evidence, missing evidence, risk, and allowed strength.
- `WritingPlan.md`: framing, section order, and high-level writing tasks.
- `TrajectorySelectionReport.md`: mandatory top-k trajectory retrieval, ranking, selection, and rejection rationale.
- `ClozeBlueprint.md`: mandatory sentence-level fill-in-the-blank blueprint for normal paper writing.
- `AgentTaskContract.md`: task contracts, runtime ledger, output envelope checks, retry state, and merge decisions.
- `PaperState.md`: current draft status, open questions, review issues, LaTeX/PDF status, and next actions.

These files may also be embedded in notes, LaTeX comments, or another user-approved location. Do not require the user to edit them.

## Rules

- Do not run or depend on `python -m paperprism.cli`.
- Do not require fixed input JSON before helping the user.
- Do not ask the user to inspect internal JSON/YAML artifacts.
- Do not start normal paper prose writing before a `ClozeBlueprint.md` exists.
- Treat trajectory selection as the mandatory writing entry point:
  `Research Goal -> Trajectory Retrieval -> Trajectory Ranking -> Trajectory Selection -> Cloze Blueprint Generation -> Slot Filling`.
- Retrieve top-k candidate trajectories before any blueprint generation. Default `k = 5`.
- Produce a `TrajectorySelectionReport.md` or equivalent readable notes with candidate trajectories, selection scores, selection rationale, and rejected trajectories.
- Convert the selected trajectory into sentence skeletons through `trajectory-compiler`; do not let writers invent the structure.
- `ClozeBlueprint.md` must use the hierarchy `Section -> Paragraph -> Sentence`.
- Every sentence slot must include `sentence_id`, `sentence_type`, `evidence_requirement`, `assigned_agent`, and `status`.
- Sentence slot status must follow `planned -> drafted -> supported -> verified`; never jump from `planned` to `verified`.
- Do not export final `paper.tex` / `paper.pdf` until `unsupported_sentences == 0` and `planned_sentences == 0`.
- Use `paper-writer` to fill slots; use `claim-evidence-mapper` to judge evidence; use `review-simulator` for review.
- Use Codex reasoning and skills for evidence judgment, novelty judgment, writing, review, and LaTeX repair.
- Use scripts only for offline data construction, such as trajectory library mining.
- Treat `paper.tex` and `paper.pdf` as the final user-facing deliverables.
- If evidence is missing, ask a small number of high-value questions, weaken the claim, mark it as planned, or move it to a revision plan.
- Never invent experiments, citations, numeric results, theorems, proofs, or related-work facts.
- Orchestrator is a manager only. It may plan, decompose tasks, assign agents, control workflow, and enforce quality gates.
- Orchestrator must not write paper text, evaluate novelty, review manuscripts, or verify evidence.
- If `orchestrator_wrote_text`, `orchestrator_reviewed_paper`, or `orchestrator_did_novelty_eval` becomes true, treat it as a workflow violation and stop until rerouted to the correct agent.

## Agent Contract

PaperPRISM uses Codex-native multi-agent orchestration. The main agent is the runtime manager; Python helpers are optional validation aids, not the normal execution path.

For every delegated task, the main agent must perform this lifecycle explicitly:

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

Every agent task must be framed before assignment as:

```yaml
Task:
Input:
Expected Output:
Acceptance Criteria:
Failure Handling:
```

Every agent response must use this output envelope before it can be merged:

```yaml
Task ID:
Agent:
Output:
Contract Compliance:
Acceptance Check:
Open Issues:
Merge Recommendation:
```

The main agent must validate the output envelope by checking required fields, agent identity, acceptance criteria, forbidden outputs, trajectory adherence, evidence status, and merge recommendation. Free-form agent output is not mergeable.

If validation fails, the reviewing agent or main agent writes an Issue Report and routes the task back to the original agent until `max_retry`. When `max_retry` is exhausted, the task is marked failed and unresolved issues are recorded in `PaperState`; the main agent must not silently merge failed output.

## Recommended Workflow

1. Understand the user's material in its current form: idea, draft, results, LaTeX, tables, or conversation.
2. Update or create the four core working objects only when they help the task.
3. Use `trajectory-selector` to retrieve top-k trajectories, rank candidates, and select a trajectory.
4. Use `trajectory-compiler` through `logical-template-builder` to create `ClozeBlueprint.md`.
5. Assign sentence filling tasks to `paper-writer`.
6. Route filled slots through `claim-evidence-mapper` until support status is explicit.
7. Use `review-simulator` before final assembly when the paper or major section is complete.
8. Assemble or revise `paper.tex` from filled and supported slots.
9. Compile PDF through Codex tool calls when needed.
10. Keep the final response focused on paper progress, open evidence gaps, and deliverables.
