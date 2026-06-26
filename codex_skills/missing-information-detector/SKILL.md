---
name: missing-information-detector
description: Use when Codex needs to identify missing motivation, experiments, baselines, theory, novelty, scope, limitations, or writing inputs for a PaperPRISM project.
---

# Missing Information Detector

Read `../_shared/paperprism_codex_native.md` before acting.

## Goal

Find the missing information that blocks credible paper claims or high-quality writing.

## Workflow

1. Inspect the ResearchAsset, ClaimEvidenceMap, WritingPlan, draft, or review issue.
2. Group gaps by motivation, task definition, method, baselines, experiments, ablations, theory, novelty, related work, limitations, and LaTeX/deliverable needs.
3. Mark severity: must-fix, should-fix, or writing-only.
4. Ask at most three high-value questions when user input is required.
5. Update PaperState or provide a concise missing-information report.

## Rules

- Do not block progress for non-critical gaps.
- Do not treat missing experiments as writing-only problems.
- If evidence is missing, recommend qualify, planned, omit, or ask user.

## Expected Outputs

- Missing components grouped by severity.
- Minimal user questions.
- Recommended next skill or action.
