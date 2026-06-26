---
name: trajectory-selector
description: Use when Codex must select, compare, or adapt exemplar sentence-type trajectories from PaperPRISM's trajectory library before creating a ClozeBlueprint or writing a paper.
---

# Trajectory Selector

Read `../_shared/paperprism_codex_native.md` before acting.

## Goal

Select an exemplar paper trajectory as the logical skeleton for a target paper. This skill is required before creating a sentence-level ClozeBlueprint.

## Inputs

- ResearchAsset, ClaimEvidenceMap, draft, or user description.
- Target framing from `archetype-identifier`, if available.
- Trajectory library at `<PaperPRISM resource root>/data/generated_sentence_trajectories.json`.
- Executable archetype records at `<PaperPRISM resource root>/data/executable_archetypes.json`, when available.

## Workflow

1. Locate the PaperPRISM resource root using `../_shared/paperprism_codex_native.md`.
2. Identify target archetype/category, persuasion path, domain, venue level, evidence pattern, and section needs.
3. Retrieve top-k candidate trajectories from the trajectory library before any writing. Default `k = 5`.
   - Prefer `<resource root>/data/generated_sentence_trajectories.json`.
   - Use `<resource root>/scripts/trajectory_library.py` for deterministic retrieval when script execution is useful.
4. Inspect candidate trajectories under the same or nearest archetype/category.
5. Rank candidates by:
   - paper/task similarity
   - contribution type
   - section coverage
   - evidence pattern match
   - suitable/avoid conditions
   - unsupported moves that would need planned or qualified wording
6. Assign each candidate a selection score and concise rationale.
7. Select one primary trajectory and optional borrowed section trajectories.
8. Write a `TrajectorySelectionReport` in readable form:
   - candidate trajectories
   - selection score
   - selection rationale
   - rejected trajectories
   - selected trajectory id/title
   - matched criteria
   - adaptation notes
   - unsupported or planned moves
   - sections to include, drop, or qualify
9. Hand the report to `trajectory-compiler` through `logical-template-builder` to create `ClozeBlueprint.md`.

## Rules

- Do not write paper prose in this skill.
- Do not mechanically copy an exemplar paper's story.
- Do not select a trajectory whose core evidence moves cannot be supported, unless those moves are explicitly marked planned, qualified, or removed.
- If no suitable trajectory exists, create a minimal custom trajectory and explain why.
- Preserve traceability from selected trajectory to sections and sentence types.
- Do not hand off to writing without a ranked top-k report.

## Expected Outputs

- `TrajectorySelectionReport.md` or equivalent readable notes.
- Selected primary trajectory and any borrowed section trajectories.
- Adaptation notes and risk list for ClozeBlueprint construction.
