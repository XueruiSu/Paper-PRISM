---
name: research-understanding
description: Use when Codex needs to interview the user or normalize research notes, experiments, theory, related works, LaTeX, tables, or a draft into a PaperPRISM ResearchAsset.
---

# Research Understanding

Read `../_shared/paperprism_codex_native.md` before acting.

## Goal

Turn messy research material into a readable `ResearchAsset` without requiring fixed JSON or Python execution.

## Inputs

- Idea, draft, LaTeX, table, experiment logs, related-work notes, review comments, or conversation.
- Optional existing `ResearchAsset.md` or paper draft.

## Workflow

1. Extract task, method, insight, evidence, baselines, related works, theory, limitations, and target venue.
2. If the user provides a draft, extract assets before rewriting.
3. Update `ResearchAsset.md` or provide an equivalent concise working summary.
4. Identify the top missing inputs that block claims or writing.
5. Ask at most three high-value questions; otherwise continue with caveats.

## Rules

- Do not invent results, baselines, citations, theory, or related-work facts.
- Do not ask the user to fill a schema.
- Preserve uncertainty and source provenance.
- Treat incomplete material as usable but risky, not as a reason to stop.

## Expected Outputs

- Updated or proposed `ResearchAsset`.
- Top missing information.
- Handoff recommendation to framing, claim-evidence mapping, or writing.
