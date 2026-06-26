---
name: claim-evidence-mapper
description: Use when Codex needs to map, validate, weaken, or revise paper claims against available evidence before writing or review.
---

# Claim-Evidence Mapper

Read `../_shared/paperprism_codex_native.md` before acting.

## Goal

Maintain a readable `ClaimEvidenceMap` that controls claim strength.

## Workflow

1. Extract claims from the idea, draft, WritingPlan, ClozeBlueprint, LaTeX, or review issue.
2. For each claim, identify available evidence and missing evidence.
3. Assign status: `supported`, `partially_supported`, `planned`, or `unsupported`.
4. Assign allowed strength: `assertive`, `qualified`, `planned`, or `omit`.
5. Bind claim status to affected sentence slots when `ClozeBlueprint.md` exists.
6. Advance sentence slot status from `drafted` to `supported` only when the sentence has adequate evidence; do not mark it `verified`.
7. Update `ClaimEvidenceMap.md` or provide a concise equivalent.
8. Hand risky claims to `paper-writer`, `experiment-planner`, or `review-simulator`.

## Rules

- Supported claims may be assertive.
- Partially supported claims must be qualified.
- Planned evidence must be visibly planned.
- Unsupported claims must not enter paper prose as facts.
- Do not hide missing evidence with vague writing.
- Never advance a sentence from `planned` to `verified`.
- Before final export, report `unsupported_sentences` and block export if the count is nonzero.

## Expected Outputs

- Claim support table.
- Slot-level evidence bindings when a ClozeBlueprint exists.
- High-risk claims and required fixes.
- Writing policy for each risky claim.
