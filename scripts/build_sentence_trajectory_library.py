from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.trajectory_library import validate_trajectory_library
from scripts.trajectory_miner import mine_trajectory_from_annotations


DEFAULT_REPORTS_DIR = (
    REPO_ROOT / "data" / "archetype_papers" / "pdfs" / "arxiv_downloads" / "sentence_role_reports"
)
DEFAULT_MANIFEST = REPO_ROOT / "data" / "archetype_papers" / "pdfs" / "arxiv_downloads" / "manifest.json"
DEFAULT_KB = REPO_ROOT / "data" / "research_archetype_knowledge_base.json"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "generated_sentence_trajectories.json"


def build_sentence_trajectory_library(
    *,
    reports_dir: Path,
    manifest: Path,
    kb: Path,
    output: Path,
    base_library: Path | None = None,
    metadata_overrides: Path | None = None,
) -> dict[str, Any]:
    manifest_records = _load_manifest_records(manifest)
    kb_payload = _load_json(kb)
    kb_index = _KnowledgeBaseIndex(kb_payload)
    override_index = _MetadataOverrideIndex.from_path(metadata_overrides)

    exemplar_trajectories: list[dict[str, Any]] = []
    sentence_type_trajectories: list[dict[str, Any]] = []

    for report_path in sorted(reports_dir.glob("*_sentence_roles.annotations.json")):
        manifest_record = _manifest_record_for_report(report_path, manifest_records)
        override_record = override_index.match(manifest_record, report_path)
        if override_record:
            manifest_record = _merge_manifest_override(manifest_record, override_record)
        kb_paper = override_record or kb_index.match(manifest_record)
        paper_metadata = _paper_metadata(manifest_record, kb_paper, report_path)
        classification = _classification(kb_paper, kb_index)
        mined = mine_trajectory_from_annotations(
            report_path,
            paper_metadata=paper_metadata,
            classification=classification,
        )
        exemplar_trajectories.append(mined["exemplar_trajectory"])
        sentence_type_trajectories.extend(mined["sentence_type_trajectories"])

    if base_library is not None and base_library.exists():
        base_payload = _load_json(base_library)
        exemplar_trajectories = _merge_by_id(
            base_payload.get("exemplar_trajectories", []),
            exemplar_trajectories,
            key="trajectory_id",
        )
        sentence_type_trajectories = _merge_by_id(
            base_payload.get("sentence_type_trajectories", []),
            sentence_type_trajectories,
            key="sentence_type_trajectory_id",
        )

    payload = {
        "version": "0.1.0-generated",
        "description": (
            "Generated sentence-type trajectory library mined from sentence role annotations. "
            "This file is an offline-generated PaperPRISM data product and is wired into the writing pipeline."
        ),
        "exemplar_trajectories": exemplar_trajectories,
        "sentence_type_trajectories": sentence_type_trajectories,
    }
    validate_trajectory_library(payload)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a draft sentence trajectory library from sentence role annotation reports."
    )
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--kb", type=Path, default=DEFAULT_KB)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--base-library",
        type=Path,
        help="Optional existing trajectory library to merge with newly mined trajectories.",
    )
    parser.add_argument(
        "--metadata-overrides",
        type=Path,
        help=(
            "Optional curated paper metadata records keyed by report_stem, arxiv_id, paper_id, "
            "or title. Override records take precedence over manifest and KB matches."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_sentence_trajectory_library(
        reports_dir=args.reports_dir,
        manifest=args.manifest,
        kb=args.kb,
        output=args.output,
        base_library=args.base_library,
        metadata_overrides=args.metadata_overrides,
    )
    print(
        "Wrote "
        f"{len(payload['exemplar_trajectories'])} exemplar trajectories and "
        f"{len(payload['sentence_type_trajectories'])} sentence trajectories to {args.output}"
    )
    return 0


class _KnowledgeBaseIndex:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.papers = [paper for paper in payload.get("papers", []) if isinstance(paper, dict)]
        self.archetypes = {
            archetype.get("id"): archetype
            for archetype in payload.get("archetype_library", [])
            if isinstance(archetype, dict)
        }
        self.by_title = {_normalize_title(paper.get("title", "")): paper for paper in self.papers}
        self.by_id = {str(paper.get("id", "")).lower(): paper for paper in self.papers}

    def match(self, manifest_record: dict[str, Any]) -> dict[str, Any] | None:
        title = manifest_record.get("arxiv_title") or manifest_record.get("inferred_title") or ""
        normalized_title = _normalize_title(title)
        if normalized_title in self.by_title:
            return self.by_title[normalized_title]

        paper_id = _paper_id_from_input_pdf(manifest_record.get("input_pdf", ""))
        if paper_id and paper_id in self.by_id:
            return self.by_id[paper_id]

        title_tokens = set(normalized_title.split())
        if not title_tokens:
            return None
        best_score = 0.0
        best_paper: dict[str, Any] | None = None
        for paper in self.papers:
            candidate_tokens = set(_normalize_title(paper.get("title", "")).split())
            if not candidate_tokens:
                continue
            overlap = len(title_tokens.intersection(candidate_tokens))
            score = overlap / max(len(title_tokens), len(candidate_tokens))
            if score > best_score:
                best_score = score
                best_paper = paper
        return best_paper if best_score >= 0.82 else None

    def archetype_name(self, archetype_id: str) -> str:
        archetype = self.archetypes.get(archetype_id, {})
        return str(archetype.get("name") or archetype_id or "Unknown")


class _MetadataOverrideIndex:
    def __init__(self, records: list[dict[str, Any]]) -> None:
        self.by_report_stem: dict[str, dict[str, Any]] = {}
        self.by_arxiv_id: dict[str, dict[str, Any]] = {}
        self.by_arxiv_id_without_version: dict[str, dict[str, Any]] = {}
        self.by_paper_id: dict[str, dict[str, Any]] = {}
        self.by_title: dict[str, dict[str, Any]] = {}
        for record in records:
            report_stem = str(record.get("report_stem") or "")
            if report_stem:
                self.by_report_stem[report_stem] = record
            arxiv_id = str(record.get("arxiv_id") or "")
            if arxiv_id:
                self.by_arxiv_id[arxiv_id.lower()] = record
                self.by_arxiv_id_without_version[_strip_arxiv_version(arxiv_id).lower()] = record
            paper_id = str(record.get("paper_id") or record.get("id") or "")
            if paper_id:
                self.by_paper_id[paper_id.lower()] = record
            normalized_title = _normalize_title(record.get("title", ""))
            if normalized_title:
                self.by_title[normalized_title] = record

    @classmethod
    def from_path(cls, path: Path | None) -> "_MetadataOverrideIndex":
        if path is None or not path.exists():
            return cls([])
        payload = _load_json(path)
        records = payload.get("records", payload.get("papers", []))
        return cls([record for record in records if isinstance(record, dict)])

    def match(self, manifest_record: dict[str, Any], report_path: Path) -> dict[str, Any] | None:
        report_stem = _report_input_stem(report_path)
        if report_stem in self.by_report_stem:
            return self.by_report_stem[report_stem]

        arxiv_id = str(manifest_record.get("arxiv_id") or _arxiv_id_from_report(report_path) or "")
        if arxiv_id:
            lowered = arxiv_id.lower()
            if lowered in self.by_arxiv_id:
                return self.by_arxiv_id[lowered]
            without_version = _strip_arxiv_version(arxiv_id).lower()
            if without_version in self.by_arxiv_id_without_version:
                return self.by_arxiv_id_without_version[without_version]

        paper_id = str(manifest_record.get("paper_id") or "").lower()
        if paper_id in self.by_paper_id:
            return self.by_paper_id[paper_id]

        normalized_title = _normalize_title(
            manifest_record.get("arxiv_title") or manifest_record.get("inferred_title") or ""
        )
        return self.by_title.get(normalized_title)


def _paper_metadata(
    manifest_record: dict[str, Any],
    kb_paper: dict[str, Any] | None,
    report_path: Path,
) -> dict[str, Any]:
    kb_paper = kb_paper or {}
    return {
        "title": manifest_record.get("arxiv_title")
        or kb_paper.get("title")
        or manifest_record.get("inferred_title")
        or report_path.stem,
        "arxiv_id": manifest_record.get("arxiv_id", _arxiv_id_from_report(report_path) or ""),
        "venue": kb_paper.get("venue", "unknown"),
        "year": kb_paper.get("year", "unknown"),
        "domain": kb_paper.get("domain", "unknown"),
        "task": kb_paper.get("research_problem", ""),
        "contribution_type": kb_paper.get("contribution_type", []),
    }


def _classification(kb_paper: dict[str, Any] | None, kb_index: _KnowledgeBaseIndex) -> dict[str, Any]:
    if not kb_paper:
        return {
            "primary_archetype_id": "unknown",
            "primary_archetype_name": "Unknown",
            "secondary_archetype_id": "unknown",
            "persuasion_path": "default",
            "evidence_pattern": [],
        }

    archetype_id = str(kb_paper.get("research_archetype") or "unknown")
    secondary = kb_paper.get("secondary_archetypes") or []
    secondary_id = secondary[0] if isinstance(secondary, list) and secondary else "unknown"
    return {
        "primary_archetype_id": archetype_id,
        "primary_archetype_name": kb_index.archetype_name(archetype_id),
        "secondary_archetype_id": secondary_id,
        "persuasion_path": archetype_id if archetype_id != "unknown" else "default",
        "evidence_pattern": _evidence_pattern(kb_paper.get("experiment_pattern")),
    }


def _merge_manifest_override(
    manifest_record: dict[str, Any],
    override_record: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(manifest_record)
    if override_record.get("title"):
        merged["arxiv_title"] = override_record["title"]
        merged["inferred_title"] = override_record["title"]
    for key in ("arxiv_id", "paper_id"):
        if override_record.get(key):
            merged[key] = override_record[key]
    return merged


def _evidence_pattern(experiment_pattern: Any) -> list[str]:
    if isinstance(experiment_pattern, dict):
        return sorted(str(key) for key, value in experiment_pattern.items() if value)
    if isinstance(experiment_pattern, list):
        return [str(item) for item in experiment_pattern]
    if isinstance(experiment_pattern, str) and experiment_pattern:
        return [experiment_pattern]
    return []


def _load_manifest_records(path: Path) -> list[dict[str, Any]]:
    payload = _load_json(path)
    records = payload.get("records", [])
    return [record for record in records if isinstance(record, dict)]


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _merge_by_id(base_items: Any, new_items: list[dict[str, Any]], *, key: str) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for item in base_items if isinstance(base_items, list) else []:
        if not isinstance(item, dict):
            continue
        item_id = item.get(key)
        if item_id:
            merged[str(item_id)] = item
    for item in new_items:
        item_id = item.get(key)
        if item_id:
            merged[str(item_id)] = item
    return list(merged.values())


def _manifest_record_for_report(
    report_path: Path,
    manifest_records: list[dict[str, Any]],
) -> dict[str, Any]:
    arxiv_id = _arxiv_id_from_report(report_path)
    if arxiv_id:
        for record in manifest_records:
            if record.get("arxiv_id") == arxiv_id:
                return record
    report_stem = _report_input_stem(report_path)
    if report_stem:
        for record in manifest_records:
            candidate_stems = {
                str(record.get("report_stem") or ""),
                Path(str(record.get("input_pdf") or "")).stem,
                Path(str(record.get("path") or "")).stem,
            }
            if report_stem in candidate_stems:
                return record
    return {"arxiv_id": arxiv_id or "", "arxiv_title": "", "inferred_title": report_path.stem}


def _arxiv_id_from_report(report_path: Path) -> str:
    match = re.match(r"arXiv-(.+?)_sentence_roles\.annotations\.json$", report_path.name)
    return match.group(1) if match else ""


def _report_input_stem(report_path: Path) -> str:
    return report_path.name.removesuffix("_sentence_roles.annotations.json")


def _paper_id_from_input_pdf(input_pdf: str) -> str:
    if not input_pdf:
        return ""
    stem = Path(input_pdf).stem.lower()
    return stem.split("__", 1)[0]


def _strip_arxiv_version(arxiv_id: str) -> str:
    return re.sub(r"v\d+$", "", arxiv_id)


def _normalize_title(title: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(title).lower()).strip()


if __name__ == "__main__":
    raise SystemExit(main())
