# ExecutableArchetype

Archetypes are executable writing knowledge, not only paper categories.

```yaml
Archetype:
  Categories:
  Exemplars:
  Section Trajectories:
  Sentence Trajectories:
  Adaptation Rules:
  Suitable Conditions:
  Avoid Conditions:
```

## Archetype Record

| Field | Required Content |
|---|---|
| Categories | Contribution and persuasion categories, such as Algorithm, Theory, Benchmark, Empirical Analysis |
| Exemplars | 10-20 exemplar papers when available; fewer only for seed-stage libraries |
| Section Trajectories | Section-level rhetorical path, such as background -> limitation -> gap -> idea -> contribution |
| Sentence Trajectories | Sentence-pattern library entries linked to trajectory IDs |
| Adaptation Rules | How to migrate the trajectory to a new paper without copying the exemplar |
| Suitable Conditions | Research situations where this archetype is appropriate |
| Avoid Conditions | Research situations where this archetype creates reviewer risk |

## Recommendation Contract

Input:

```yaml
paper_goal:
research_stage:
novelty_level:
```

Output:

```yaml
recommended_archetype:
confidence:
rationale:
```

Use `scripts/archetype_recommender.py` for deterministic internal support when a local archetype library is available.
