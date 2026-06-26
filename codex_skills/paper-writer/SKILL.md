---
name: paper-writer
description: Use when Codex needs to write, rewrite, or extend PaperPRISM paper prose or LaTeX while respecting claims, evidence, and WritingPlan constraints.
---

# Paper Writer

Read `../_shared/paperprism_codex_native.md` before acting.

## Goal

Fill sentence slots and write or revise paper text directly, preferably in `paper.tex`, using ResearchAsset, ClaimEvidenceMap, ClozeBlueprint, and PaperState as the contract.

## Workflow

1. Read the target slots from `ClozeBlueprint.md`.
2. Read the target section, current draft, or LaTeX file.
3. Check ClaimEvidenceMap before strong claims.
4. Fill only assigned slots unless broader edits are necessary and user-approved.
5. Keep unsupported claims out of assertive prose.
6. If a needed sentence slot is missing, stop and route to `logical-template-builder`.
7. Update sentence slot status from `planned` to `drafted`; do not mark it `supported` or `verified` yourself.
8. Route drafted slots to `claim-evidence-mapper` for support status.
9. Update PaperState with filled slots, changed prose, and open evidence gaps.
10. Compile or request compilation through tool calls when PDF delivery is part of the task only after export gates pass.

## Rules

- Do not invent citations, results, numbers, theorems, proof details, or related-work facts.
- Do not freely add, remove, or reorder sentence slots.
- Do not alter trajectory structure; request `trajectory-compiler` recompilation through `logical-template-builder` if structure is wrong.
- Do not present planned experiments as completed evidence.
- Keep partially supported claims qualified.
- Prefer clear LaTeX edits over generated intermediate JSON.
- Never set a sentence directly from `planned` to `verified`.
- Do not final-export if any sentence remains `planned` or evidence status remains `unsupported`.

## Expected Outputs

- Revised prose or LaTeX.
- Filled slot notes with slot ids and evidence status.
- Brief note on evidence constraints respected.
- Open questions or remaining unsupported claims.
