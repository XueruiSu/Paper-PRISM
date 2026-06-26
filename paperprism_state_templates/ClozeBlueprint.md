# ClozeBlueprint

## Blueprint Metadata

- Blueprint ID:
- Source ResearchAsset:
- Source ClaimEvidenceMap:
- Source TrajectorySelectionReport:
- Primary archetype/category:
- Primary exemplar trajectory:
- Compiled by: `trajectory-compiler`
- Created/updated by:

## Global Writing Contract

- Required hierarchy: `Section -> Paragraph -> Sentence`
- Total sections:
- Total paragraphs:
- Total sentence slots:
- Default slot-filling agent: `paper-writer`
- Evidence-checking agent: `claim-evidence-mapper`
- Review agent: `review-simulator`
- Allowed sentence status lifecycle: `planned -> drafted -> supported -> verified`
- Forbidden status transition: `planned -> verified`
- Export gate: `unsupported_sentences == 0` and `planned_sentences == 0`

## Section Blueprint

| Section ID | Title | Rhetorical Goal | Source Trajectory | Paragraph Count | Sentence Slot Count | Status |
|---|---|---|---|---:|---:|---|
| sec.01 | Introduction |  |  |  |  | planned |

## Paragraph Blueprint

| Paragraph ID | Section ID | Purpose | Sentence Count | Linked Claims | Required Evidence | Status |
|---|---|---|---:|---|---|---|
| sec.01.p01 | sec.01 |  |  |  |  | planned |

## Sentence Slots

| Sentence ID | Section | Paragraph | Order | Sentence Type | Logical Role | Content To Fill | Evidence Requirement | Linked Claims | Evidence Status | Allowed Strength | Assigned Agent | Status |
|---|---|---|---:|---|---|---|---|---|---|---|---|---|
| S01.P01.S01 | Introduction | S01.P01 | 1 | background_context | Broad Context |  | literature_or_common_problem |  | supported / partial / planned / unsupported | assertive / qualified / planned / omit | paper-writer | planned |

Each sentence must include:

```yaml
sentence_id:
sentence_type:
evidence_requirement:
assigned_agent:
status:
```

## Unsupported Or Planned Moves

| Slot ID | Issue | Required User Evidence | Temporary Action |
|---|---|---|---|
|  |  |  | qualify / mark planned / omit |

## Completion Gate

Before final LaTeX/PDF export, compute:

```yaml
planned_sentences:
unsupported_sentences:
drafted_but_not_supported:
supported_but_not_verified:
```

Final export is blocked unless:

```yaml
planned_sentences: 0
unsupported_sentences: 0
```

## Blueprint Revision Rules

- `paper-writer` may fill slots but must not freely add or delete slots.
- If writing requires new sentence slots, return to `trajectory-compiler` through `logical-template-builder`.
- If evidence status changes, return to `claim-evidence-mapper`.
- If reviewer feedback requires structural change, revise this blueprint before rewriting prose.
- Sentence status must move one step at a time: `planned -> drafted -> supported -> verified`.
