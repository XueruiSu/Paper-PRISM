---
name: logical-template-builder
description: Use when Codex needs to convert selected exemplar trajectories into a sentence-level PaperPRISM ClozeBlueprint before paper writing, or revise an existing WritingPlan/ClozeBlueprint.
---

# Logical Template Builder

Read `../_shared/paperprism_codex_native.md` before acting.

## Goal

Create a sentence-level ClozeBlueprint that tells Codex exactly how many sections, paragraphs, and sentence slots the paper has, and what each slot must accomplish.

## Resources

- Locate the PaperPRISM resource root using `../_shared/paperprism_codex_native.md`.
- Use `<resource root>/data/generated_sentence_trajectories.json` for selected trajectory details.
- Use `<resource root>/data/executable_archetypes.json` for archetype-level section and sentence trajectory variants.
- Use `<resource root>/scripts/trajectory_compiler.py` when deterministic trajectory-to-blueprint compilation is useful.
- Use `<resource root>/paperprism_state_templates/ClozeBlueprint.md` as the readable blueprint template when creating a project-local file.

## Workflow

1. Read ResearchAsset, ClaimEvidenceMap, framing notes, and the TrajectorySelectionReport from `trajectory-selector`.
2. If no trajectory has been selected, stop and route to `trajectory-selector`.
3. Use `trajectory-compiler` to convert the selected trajectory into sentence skeletons and then a `ClozeBlueprint.md`.
4. For every section, define section title, rhetorical goal, source trajectory, and paragraph count.
5. For every paragraph, define purpose, sentence count, and sentence slot ids.
6. For every sentence slot, define:
   - sentence id
   - sentence type
   - logical role
   - content to fill
   - evidence requirement
   - linked claim ids
   - evidence status: supported, partially supported, planned, or unsupported
   - allowed strength: assertive, qualified, planned, or omit
   - assigned agent, usually `paper-writer`
   - status: planned, drafted, supported, or verified
7. Route missing evidence to `experiment-planner` and risky claims to `claim-evidence-mapper`.

## Rules

- Do not add conventional sections without a claim or evidence purpose.
- Do not decide a paper story by Python templates.
- Do not make sentence slots optional for a normal writing task.
- Do not allow `paper-writer` to freely add or delete sentence slots; blueprint revision must happen here first.
- Do not modify trajectory structure during writing; structural changes require recompilation by `trajectory-compiler`.
- Keep the plan editable by Codex and understandable by the user.
- If structure changes would alter framing, route to `archetype-identifier`.
- Initial sentence status must be `planned`.
- Enforce sentence status lifecycle `planned -> drafted -> supported -> verified`.

## Expected Outputs

- Sentence-level `ClozeBlueprint.md`.
- Section and paragraph counts.
- Complete sentence slot table.
- Evidence and claim risks that must be handled before prose.
