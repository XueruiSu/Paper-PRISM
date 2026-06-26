---
name: experiment-planner
description: Use when Codex needs to plan missing main experiments, baselines, ablations, robustness checks, efficiency analysis, statistics, or benchmark validation for a PaperPRISM paper.
---

# Experiment Planner

Read `../_shared/paperprism_codex_native.md` before acting.

## Goal

Convert evidence gaps into concrete experiments or planned placeholders without pretending the results exist.

## Workflow

1. Read the ClaimEvidenceMap, WritingPlan, and current draft or user request.
2. Identify which claim each missing experiment supports.
3. Propose experiment purpose, dataset/task, baselines, metrics, ablations, robustness checks, and expected reporting format.
4. Mark whether the experiment is must-fix, should-fix, or optional.
5. Update PaperState and WritingPlan with planned evidence.

## Rules

- Do not fabricate results or expected numbers.
- Planned experiments may appear in drafts only as explicitly planned content.
- Prioritize experiments that unblock central claims.

## Expected Outputs

- Experiment plan tied to claims.
- Required inputs from the user.
- Safe wording until results are available.
