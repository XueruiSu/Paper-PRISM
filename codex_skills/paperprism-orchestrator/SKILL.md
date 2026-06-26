---
name: paperprism-orchestrator
description: Use when the user wants to turn a research idea, experiment results, related works, or draft into a paper through the Codex-native PaperPRISM workflow.
---

# PaperPRISM Orchestrator

Use this skill to coordinate PaperPRISM through Codex conversation. Read `../_shared/paperprism_codex_native.md` before acting.

## Role

The orchestrator routes work across specialized skills. It should not become a monolithic writer, reviewer, or evidence judge.

Allowed responsibilities:

- planning
- task decomposition
- agent assignment
- workflow control
- quality gate enforcement

Forbidden responsibilities:

- write paper text
- evaluate novelty
- review manuscript
- verify evidence

## Workflow

1. Understand what the user provided: idea, draft, experimental result, related work notes, LaTeX, review comments, or mixed conversation.
2. Create or update the readable working objects needed for the task:
   - `ResearchAsset.md`
   - `ClaimEvidenceMap.md`
   - `TrajectorySelectionReport.md`
   - `WritingPlan.md`
   - `ClozeBlueprint.md`
   - `AgentTaskContract.md`
   - `PaperState.md`
3. Enforce the mandatory writing entry path:
   `Research Goal -> Trajectory Selection -> Blueprint Generation -> Task Assignment -> Sentence Filling -> Evidence Mapping -> Review Simulation -> Final Assembly`.
4. Route to the smallest relevant skill:
   - `research-understanding` for messy input or draft extraction.
   - `missing-information-detector` for missing motivation, experiment, theory, or scope.
   - `archetype-identifier` for paper framing.
   - `trajectory-selector` before any ClozeBlueprint is created; it must retrieve top-k candidates with default `k = 5`.
   - `novelty-evaluator` for closest-work and differentiation risk.
   - `claim-evidence-mapper` before strong claims or review.
   - `logical-template-builder` and `trajectory-compiler` for ClozeBlueprint and structure.
   - `experiment-planner` for missing experiments.
   - `paper-writer` for prose and LaTeX.
   - `review-simulator` for reviewer-style critique and revision planning.
5. Validate agent outputs against the contract:
   `Task`, `Input`, `Expected Output`, `Acceptance Criteria`, `Failure Handling`.
6. Run the Codex-native agent runtime for delegated work:
   `Create Task -> Assign Agent -> Execute -> Review -> Retry or Merge`.
7. Require every agent output to include:
   `Task ID`, `Agent`, `Output`, `Contract Compliance`, `Acceptance Check`, `Open Issues`, `Merge Recommendation`.
8. If the output fails review, create an Issue Report and retry with the same agent until `max_retry`; unresolved issues must remain in `PaperState`.
9. Ask at most three high-value questions when information is missing.
10. Keep `paper.tex` and `paper.pdf` as the final deliverables.

## Rules

- Do not make helper scripts a user-facing writing entry point.
- Do not require the user to provide or edit JSON.
- Do not enter paper writing without a `ClozeBlueprint.md` or an explicit user-approved emergency exception.
- Do not create a ClozeBlueprint without first using `trajectory-selector` and producing a `TrajectorySelectionReport`, unless no suitable trajectory exists and that exception is recorded.
- Delegate slot filling to `paper-writer`; do not write paper prose in the orchestrator.
- Delegate evidence judgment to `claim-evidence-mapper`; do not silently strengthen claims.
- Delegate review to `review-simulator`; do not perform final review inline.
- Delegate novelty evaluation to `novelty-evaluator`; do not perform novelty evaluation inline.
- Do not invent experiments, citations, numeric results, theorem statements, or related-work facts.
- Keep planned evidence visibly planned.
- Maintain evidence status in readable working notes when claims are risky.
- Do not merge free-form agent output. Merge only output that satisfies the task contract and output envelope.
- Do not bypass retry by rewriting failed agent output in the orchestrator; reroute to the responsible agent.
- Do not exceed `max_retry`; failed tasks must be recorded with unresolved issues and a blocking or downgraded next action.
- Run or emulate workflow validation before final assembly:
  `orchestrator_wrote_text?`, `orchestrator_reviewed_paper?`, `orchestrator_did_novelty_eval?`.
- If any workflow validation flag is true, record a workflow violation and reroute the work to the correct agent.
- Block final export unless `unsupported_sentences == 0` and `planned_sentences == 0`.

## Expected Outputs

- A clear next action or routed skill decision.
- Updated readable working files when needed.
- User-facing questions only when they unblock the paper.
- `paper.tex` and `paper.pdf` when the writing task reaches final delivery.
