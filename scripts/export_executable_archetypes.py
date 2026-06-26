from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_ARCHETYPES = Path("data/archetypes.json")
DEFAULT_TRAJECTORIES = Path("data/generated_sentence_trajectories.json")
DEFAULT_OUTPUT = Path("data/executable_archetypes.json")


def export_executable_archetypes(
    *,
    archetypes_path: Path,
    trajectories_path: Path,
    output: Path,
) -> dict[str, Any]:
    archetypes_payload = _load_json(archetypes_path)
    trajectories_payload = _load_json(trajectories_path)
    sentence_index = {
        item.get("sentence_type_trajectory_id"): item
        for item in trajectories_payload.get("sentence_type_trajectories", [])
        if isinstance(item, dict)
    }
    exemplars_by_archetype: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for trajectory in trajectories_payload.get("exemplar_trajectories", []):
        if not isinstance(trajectory, dict):
            continue
        archetype_id = str(trajectory.get("classification", {}).get("primary_archetype_id") or "unknown")
        exemplars_by_archetype[archetype_id].append(trajectory)

    records = []
    for archetype in archetypes_payload.get("archetypes", []):
        if not isinstance(archetype, dict):
            continue
        archetype_id = str(archetype.get("id") or "")
        exemplars = exemplars_by_archetype.get(archetype_id, [])
        records.append(_executable_record(archetype, exemplars, sentence_index))

    payload = {
        "version": "0.2.0",
        "description": "Executable PaperPRISM archetype knowledge base generated from archetype definitions and mined trajectories.",
        "minimum_exemplars_per_archetype": 10,
        "target_exemplars_per_archetype": 20,
        "archetypes": records,
        "coverage": _coverage(records),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export executable PaperPRISM archetype records.")
    parser.add_argument("--archetypes", type=Path, default=DEFAULT_ARCHETYPES)
    parser.add_argument("--trajectories", type=Path, default=DEFAULT_TRAJECTORIES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = export_executable_archetypes(
        archetypes_path=args.archetypes,
        trajectories_path=args.trajectories,
        output=args.output,
    )
    print(f"Wrote {len(payload['archetypes'])} executable archetype records to {args.output}")
    for item in payload["coverage"]["by_archetype"]:
        print(
            f"{item['archetype_id']}: exemplars={item['exemplar_count']} "
            f"status={item['coverage_status']}"
        )
    return 0


def _executable_record(
    archetype: dict[str, Any],
    exemplars: list[dict[str, Any]],
    sentence_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    archetype_id = str(archetype.get("id") or "")
    section_trajectories = []
    sentence_trajectories = []
    for exemplar in exemplars[:20]:
        paper = exemplar.get("paper", {})
        for section in exemplar.get("sections", []):
            if not isinstance(section, dict):
                continue
            stt_id = section.get("sentence_type_trajectory_id", "")
            sentence_trajectory = sentence_index.get(stt_id, {})
            section_trajectories.append(
                {
                    "trajectory_id": exemplar.get("trajectory_id", ""),
                    "paper_title": paper.get("title", ""),
                    "section": section.get("section_title", ""),
                    "path": _compressed_path(sentence_trajectory),
                    "rhetorical_goal": section.get("rhetorical_goal", ""),
                }
            )
            sentence_trajectories.append(
                {
                    "sentence_type_trajectory_id": stt_id,
                    "trajectory_id": exemplar.get("trajectory_id", ""),
                    "paper_title": paper.get("title", ""),
                    "section": section.get("section_title", ""),
                    "compressed_path": sentence_trajectory.get("compressed_path", []),
                    "required_assets": sentence_trajectory.get("reuse_constraints", {}).get("required_assets", []),
                }
            )

    return {
        "id": archetype_id,
        "name": archetype.get("name", archetype_id),
        "categories": _as_list(archetype.get("categories") or archetype.get("name")),
        "exemplars": [_exemplar_summary(item) for item in exemplars[:20]],
        "section_trajectories": section_trajectories,
        "sentence_trajectories": sentence_trajectories,
        "adaptation_rules": _adaptation_rules(archetype, exemplars),
        "suitable_conditions": archetype.get("suitable_conditions", archetype.get("signals", [])),
        "avoid_conditions": archetype.get("avoid_conditions", _default_avoid_conditions(archetype)),
        "variant_templates": _variant_templates(archetype, section_trajectories),
        "coverage_status": _coverage_status(len(exemplars)),
    }


def _exemplar_summary(trajectory: dict[str, Any]) -> dict[str, Any]:
    paper = trajectory.get("paper", {})
    return {
        "trajectory_id": trajectory.get("trajectory_id", ""),
        "title": paper.get("title", ""),
        "venue": paper.get("venue", ""),
        "year": paper.get("year", ""),
        "domain": paper.get("domain", ""),
        "contribution_type": paper.get("contribution_type", []),
    }


def _adaptation_rules(archetype: dict[str, Any], exemplars: list[dict[str, Any]]) -> list[str]:
    rules = list(_as_list(archetype.get("adaptation_rules")))
    rules.extend(
        [
            "Reuse role order and evidence burden, not exemplar wording.",
            "Drop or qualify trajectory moves whose required assets are unavailable.",
            "Route structural changes back to trajectory-compiler before slot filling.",
        ]
    )
    evidence_counter: Counter[str] = Counter()
    for exemplar in exemplars:
        evidence_counter.update(_as_list(exemplar.get("classification", {}).get("evidence_pattern")))
    if evidence_counter:
        common = ", ".join(item for item, _ in evidence_counter.most_common(4))
        rules.append(f"Expect evidence patterns common to this archetype: {common}.")
    return _dedupe(rules)


def _variant_templates(archetype: dict[str, Any], section_trajectories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    template_sections = archetype.get("logical_template", {}).get("sections", [])
    variants = []
    if isinstance(template_sections, list) and template_sections:
        variants.append(
            {
                "name": "logical_template_default",
                "sections": [
                    {
                        "section": section.get("name", ""),
                        "paragraph_path": [paragraph.get("purpose", "") for paragraph in section.get("paragraphs", [])],
                    }
                    for section in template_sections
                    if isinstance(section, dict)
                ],
            }
        )
    mined_intro_paths = [
        item for item in section_trajectories if str(item.get("section", "")).lower() == "introduction"
    ][:3]
    if mined_intro_paths:
        variants.append({"name": "mined_introduction_variants", "sections": mined_intro_paths})
    return variants


def _coverage(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_archetype = [
        {
            "archetype_id": record["id"],
            "exemplar_count": len(record["exemplars"]),
            "section_trajectory_count": len(record["section_trajectories"]),
            "sentence_trajectory_count": len(record["sentence_trajectories"]),
            "coverage_status": record["coverage_status"],
        }
        for record in records
    ]
    return {
        "total_archetypes": len(records),
        "complete_archetypes": sum(1 for item in by_archetype if item["coverage_status"] == "complete"),
        "seed_or_partial_archetypes": sum(1 for item in by_archetype if item["coverage_status"] != "complete"),
        "by_archetype": by_archetype,
    }


def _coverage_status(exemplar_count: int) -> str:
    if exemplar_count >= 10:
        return "complete"
    if exemplar_count > 0:
        return "partial"
    return "missing"


def _compressed_path(sentence_trajectory: dict[str, Any]) -> list[str]:
    return [str(item.get("sentence_type", "")) for item in sentence_trajectory.get("compressed_path", [])]


def _default_avoid_conditions(archetype: dict[str, Any]) -> list[str]:
    name = str(archetype.get("name") or archetype.get("id") or "this archetype")
    return [
        f"Avoid {name} when the target paper lacks the evidence pattern required by its selected trajectory.",
        "Avoid when the selected exemplar's central persuasion move would force invented results or citations.",
    ]


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if str(value):
        return [str(value)]
    return []


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


if __name__ == "__main__":
    raise SystemExit(main())
