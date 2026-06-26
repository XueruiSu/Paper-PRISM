from __future__ import annotations

import argparse
import gzip
import io
import json
import re
import sys
import tarfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_METADATA = ROOT / "data" / "metadata_overrides" / "pdfs_0624_seed_metadata.json"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "archetype_papers" / "pdfs_0624"
USER_AGENT = "paperprism-arxiv-batch-downloader/0.1 (research use; contact: local)"


def request_bytes(url: str, timeout: int) -> tuple[bytes, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(), response.headers.get("Content-Type", "")


def normalize_arxiv_id(arxiv_id: str) -> str:
    return arxiv_id.strip().removeprefix("arXiv:")


def safe_name(arxiv_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", normalize_arxiv_id(arxiv_id))


def is_pdf(data: bytes, content_type: str) -> bool:
    return data.startswith(b"%PDF") or "application/pdf" in content_type.lower()


def has_tex_members(data: bytes) -> bool:
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
            return any(member.isfile() and member.name.endswith(".tex") for member in archive.getmembers())
    except tarfile.TarError:
        return False


def normalize_source_archive(raw: bytes, arxiv_id: str) -> tuple[bytes | None, str]:
    if has_tex_members(raw):
        return raw, "tar"

    try:
        decompressed = gzip.decompress(raw)
    except OSError:
        decompressed = b""

    if decompressed.lstrip().startswith(b"\\") or b"\\documentclass" in decompressed[:5000]:
        output = io.BytesIO()
        tex_name = f"arXiv-{safe_name(arxiv_id)}.tex"
        with tarfile.open(fileobj=output, mode="w:gz") as archive:
            info = tarfile.TarInfo(tex_name)
            info.size = len(decompressed)
            archive.addfile(info, io.BytesIO(decompressed))
        return output.getvalue(), "gzipped_tex_wrapped"

    if raw.lstrip().startswith(b"\\") or b"\\documentclass" in raw[:5000]:
        output = io.BytesIO()
        tex_name = f"arXiv-{safe_name(arxiv_id)}.tex"
        with tarfile.open(fileobj=output, mode="w:gz") as archive:
            info = tarfile.TarInfo(tex_name)
            info.size = len(raw)
            archive.addfile(info, io.BytesIO(raw))
        return output.getvalue(), "plain_tex_wrapped"

    return None, "no_tex_source"


def download_pdf(arxiv_id: str, output: Path, timeout: int, overwrite: bool) -> tuple[str, str]:
    if output.exists() and output.stat().st_size > 0 and not overwrite:
        return "exists", ""
    try:
        data, content_type = request_bytes(f"https://arxiv.org/pdf/{arxiv_id}", timeout)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        return "failed", str(exc)
    if not is_pdf(data, content_type):
        return "failed", f"downloaded content is not a PDF; content_type={content_type!r}"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    return "downloaded", ""


def download_source(arxiv_id: str, output: Path, timeout: int, overwrite: bool) -> tuple[str, str, str]:
    if output.exists() and output.stat().st_size > 0 and not overwrite:
        return "exists", "", "existing"
    try:
        raw, _ = request_bytes(f"https://arxiv.org/e-print/{arxiv_id}", timeout)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        return "failed", str(exc), ""
    normalized, mode = normalize_source_archive(raw, arxiv_id)
    if normalized is None:
        return "failed", mode, ""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(normalized)
    return "downloaded", "", mode


def download_record(record: dict[str, Any], output_dir: Path, timeout: int, overwrite: bool) -> dict[str, Any]:
    arxiv_id = normalize_arxiv_id(str(record.get("arxiv_id") or ""))
    if not arxiv_id:
        return {"id": record.get("id", ""), "status": "failed", "error": "missing arxiv_id"}

    filename_id = safe_name(arxiv_id)
    pdf_path = output_dir / "pdfs" / f"arXiv-{filename_id}.pdf"
    source_path = output_dir / "sources" / f"arXiv-{filename_id}.tar.gz"
    pdf_status, pdf_error = download_pdf(arxiv_id, pdf_path, timeout, overwrite)
    source_status, source_error, source_mode = download_source(arxiv_id, source_path, timeout, overwrite)

    return {
        "id": record.get("id", ""),
        "arxiv_id": arxiv_id,
        "title": record.get("title", ""),
        "research_archetype": record.get("research_archetype", ""),
        "pdf": str(pdf_path),
        "source": str(source_path),
        "pdf_status": pdf_status,
        "pdf_error": pdf_error,
        "source_status": source_status,
        "source_error": source_error,
        "source_mode": source_mode,
        "usable_for_tex_analysis": source_status in {"downloaded", "exists"},
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download arXiv PDFs and normalized TeX source archives from a metadata seed list.")
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--manifest", type=Path, help="Output manifest path. Default: <output-dir>/manifest.json")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--sleep", type=float, default=3.0)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata_path = args.metadata.resolve()
    output_dir = args.output_dir.resolve()
    manifest_path = (args.manifest or output_dir / "manifest.json").resolve()

    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    records = [record for record in payload.get("records", []) if isinstance(record, dict)]
    if args.limit is not None:
        records = records[: args.limit]
    if not records:
        raise SystemExit(f"No records found in {metadata_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for index, record in enumerate(records, start=1):
        arxiv_id = record.get("arxiv_id", "")
        print(f"[{index}/{len(records)}] {arxiv_id} {record.get('title', '')}", flush=True)
        result = download_record(record, output_dir, args.timeout, args.overwrite)
        results.append(result)
        print(
            "  "
            f"pdf={result.get('pdf_status')} "
            f"source={result.get('source_status')} "
            f"mode={result.get('source_mode')} "
            f"usable={result.get('usable_for_tex_analysis')}",
            flush=True,
        )
        if index < len(records) and args.sleep:
            time.sleep(args.sleep)

    manifest = {
        "metadata": str(metadata_path),
        "output_dir": str(output_dir),
        "total": len(results),
        "pdf_ok": sum(item["pdf_status"] in {"downloaded", "exists"} for item in results),
        "source_ok": sum(item["source_status"] in {"downloaded", "exists"} for item in results),
        "usable_for_tex_analysis": sum(bool(item["usable_for_tex_analysis"]) for item in results),
        "records": results,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: manifest[key] for key in ["total", "pdf_ok", "source_ok", "usable_for_tex_analysis"]}, indent=2))
    print(f"manifest: {manifest_path}")
    return 0 if manifest["source_ok"] == manifest["total"] and manifest["pdf_ok"] == manifest["total"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        sys.exit(130)
