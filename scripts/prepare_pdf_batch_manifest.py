from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any


DEFAULT_PDF_DIR = Path("data/archetype_papers/pdfs_0618")
DEFAULT_OUTPUT = Path("data/archetype_papers/pdfs_0618_manifest.json")


def prepare_manifest(
    *,
    pdf_dir: Path,
    output: Path,
    infer_titles: bool = False,
) -> dict[str, Any]:
    pdfs = sorted(path for path in pdf_dir.rglob("*.pdf") if path.is_file())
    records = [_record_for_pdf(path, infer_titles=infer_titles) for path in pdfs]
    manifest = {
        "source": str(pdf_dir),
        "total": len(records),
        "records": records,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a PaperPRISM-compatible manifest for a local PDF batch.")
    parser.add_argument("--pdf-dir", type=Path, default=DEFAULT_PDF_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--infer-titles",
        action="store_true",
        help="Use pdftotext on the first page to infer a better title when possible.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = prepare_manifest(pdf_dir=args.pdf_dir, output=args.output, infer_titles=args.infer_titles)
    print(f"Wrote {manifest['total']} PDF manifest records to {args.output}")
    return 0


def _record_for_pdf(path: Path, *, infer_titles: bool) -> dict[str, Any]:
    arxiv_id = _arxiv_id_from_name(path.name)
    inferred_title = _infer_title_from_pdf(path) if infer_titles else ""
    if not inferred_title:
        inferred_title = _title_from_filename(path.stem)
    return {
        "input_pdf": str(path),
        "path": str(path),
        "report_stem": path.stem,
        "status": "local_pdf",
        "arxiv_id": arxiv_id,
        "arxiv_title": inferred_title,
        "inferred_title": inferred_title,
        "paper_id": _paper_id(path.stem, arxiv_id),
    }


def _arxiv_id_from_name(name: str) -> str:
    match = re.search(r"(?<!\d)(\d{4}\.\d{4,5})(v\d+)?", name)
    if not match:
        return ""
    return f"{match.group(1)}{match.group(2) or ''}"


def _paper_id(stem: str, arxiv_id: str) -> str:
    source = arxiv_id or stem
    return re.sub(r"[^a-z0-9]+", "_", source.lower()).strip("_")


def _title_from_filename(stem: str) -> str:
    text = re.sub(r"(?<!\d)(\d{4}\.\d{4,5})(v\d+)?", "", stem)
    text = re.sub(r"^\d{4}\.(acl|findings-acl|emnlp|naacl|coling|aaai)[-_.a-z0-9]*", "", text, flags=re.I)
    text = text.replace("_", " ").replace("-", " ")
    text = re.sub(r"\s+", " ", text).strip(" ._-")
    return text or stem


def _infer_title_from_pdf(path: Path) -> str:
    try:
        result = subprocess.run(
            ["pdftotext", "-f", "1", "-l", "1", str(path), "-"],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return ""
    lines = [_clean_line(line) for line in result.stdout.splitlines()]
    lines = [line for line in lines if _looks_like_title_line(line)]
    if not lines:
        return ""
    title_lines = []
    for line in lines[:4]:
        if _looks_like_author_line(line):
            break
        title_lines.append(line)
    title = " ".join(title_lines).strip()
    return title if 8 <= len(title) <= 220 else ""


def _clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.replace("\x0c", " ")).strip()


def _looks_like_title_line(line: str) -> bool:
    if len(line) < 4 or len(line) > 180:
        return False
    lowered = line.lower()
    if lowered.startswith(("abstract", "introduction", "proceedings", "arxiv:")):
        return False
    if re.fullmatch(r"[\d\s.:-]+", line):
        return False
    return sum(ch.isalpha() for ch in line) >= 4


def _looks_like_author_line(line: str) -> bool:
    lowered = line.lower()
    return bool(
        re.search(r"\b(university|institute|laboratory|department|school|college|email|@)\b", lowered)
        or re.search(r"\band\b", lowered)
    )


if __name__ == "__main__":
    raise SystemExit(main())
