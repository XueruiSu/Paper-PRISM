---
name: review-simulator
description: Use when Codex needs to simulate reviewer feedback, explain reviewer risks, and turn critique into a PaperPRISM revision plan.
---

# Review Simulator

Read `../_shared/paperprism_codex_native.md` before acting.

## Goal

Review the current paper or section as a skeptical reviewer and convert feedback into actionable revisions.

## Workflow

1. Read the draft, paper.tex, ClaimEvidenceMap, WritingPlan, and PaperState if available.
2. Evaluate novelty, technical quality, evidence rigor, clarity, significance, and limitations.
3. Group issues as must-fix, should-fix, and writing-only.
4. Map each issue to a claim, section, paragraph, sentence slot, or missing evidence item.
5. Route evidence gaps to `experiment-planner`, novelty risks to `novelty-evaluator`, and prose fixes to `paper-writer`.
6. Mark sentence slots `verified` only after they are already `supported` and pass review.
7. Update PaperState with revision tasks.

## Rules

- Do not hide missing evidence as a prose issue.
- Do not claim reviewer risk decreased unless the underlying evidence or text changed.
- Keep reviewer comments concrete and actionable.
- If a review issue requires adding, deleting, or reordering sentences, route to `logical-template-builder` to revise the ClozeBlueprint before prose repair.
- Never mark a sentence `verified` directly from `planned`.
- Before final export, report `planned_sentences` and `unsupported_sentences`; block export unless both are zero.

## Expected Outputs

- Reviewer-style critique.
- Prioritized revision plan.
- Slot-level or claim-level revision targets when possible.
- Minimal user questions for blocked revisions.
