---
name: archetype-identifier
description: Use when Codex needs to explain, validate, or revise PaperPRISM research archetype and paper framing choices.
---

# Archetype Identifier

Read `../_shared/paperprism_codex_native.md` before acting.

## Goal

Choose the most useful paper framing for the current research asset. This is a Codex judgment task, not a Python classifier.

## Resources

- Locate the PaperPRISM resource root using `../_shared/paperprism_codex_native.md`.
- Use `<resource root>/data/archetypes.json` for supported archetype definitions.
- Use `<resource root>/data/executable_archetypes.json` for available exemplar coverage and adaptation patterns.
- Use `<resource root>/data/research_archetype_knowledge_base.json` when broader archetype background is useful.

## Workflow

1. Read the ResearchAsset, draft, evidence, and user goals.
2. Identify primary and secondary archetypes, such as observation-to-method, theory-to-algorithm, benchmark, framework, empirical analysis, or comparative analysis.
3. Explain how the framing changes the WritingPlan: introduction burden, method detail, theory closure, experiments, and related work.
4. If multiple framings are plausible, compare tradeoffs and recommend one.
5. Update WritingPlan or PaperState with the selected framing.

## Rules

- Do not force a predefined archetype when the asset does not fit.
- Do not claim novelty from framing alone.
- Ask the user before overriding an already chosen framing if the change affects the paper story.

## Expected Outputs

- Recommended framing.
- Alternative framings and risks.
- Concrete implications for structure and evidence.
