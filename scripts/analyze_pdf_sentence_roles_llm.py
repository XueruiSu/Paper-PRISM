from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any


"""
Usage:
  export OPENAI_API_KEY=...
  python tools/analyze_pdf_sentence_roles_llm.py paper.pdf -o report.html
  python tools/analyze_pdf_sentence_roles_llm.py --tex-source paper.tex -o report.html
  python tools/analyze_pdf_sentence_roles_llm.py paper.tex -o report.html
  python tools/analyze_pdf_sentence_roles_llm.py data/archetype_papers/pdfs/arxiv_downloads/sources --output-dir reports --workers 4

The API endpoint is OpenAI-compatible. By default the script uses:
  base_url = http://35.220.164.252:3888/v1
  model = glm-5.1

Before real API calls in this environment, api_info.md says to enable network with:
  source <(curl -sSL http://deploy.i.h.pjlab.org.cn/infra/scripts/setup_proxy.sh)

For parser/report validation without LLM calls:
  python tools/analyze_pdf_sentence_roles_llm.py paper.pdf -o report.html --dry-run
  python tools/analyze_pdf_sentence_roles_llm.py --tex-source paper.tex -o report.html --dry-run
  python tools/analyze_pdf_sentence_roles_llm.py data/archetype_papers/pdfs/arxiv_downloads/sources --output-dir reports --dry-run
"""


DEFAULT_BASE_URL = "http://35.220.164.252:3888/v1"
DEFAULT_MODEL = "glm-5.1"
LLM_REQUEST_RETRIES = 3
LLM_REQUEST_TIMEOUT_SECONDS = 240

ROLE_SCHEMA: dict[str, dict[str, str]] = {
    "Background": {
        "zh": "背景铺垫",
        "desc": "说明研究背景、领域进展或已有共识，为问题的重要性建立上下文。",
    },
    "Definition": {
        "zh": "概念/符号定义",
        "desc": "定义任务、符号、变量或基本设定，保证后续论证有清晰对象。",
    },
    "ProblemLimitation": {
        "zh": "问题/局限指出",
        "desc": "指出已有方法、当前设定或实验现象中的缺陷、风险或未解决问题。",
    },
    "Motivation": {
        "zh": "研究动机",
        "desc": "把前述背景或缺陷转化为本文需要解决的问题动因。",
    },
    "ResearchQuestion": {
        "zh": "研究问题提出",
        "desc": "把论文要回答的问题显式化，形成全文或章节的论证中心。",
    },
    "MainClaim": {
        "zh": "本文主张/方案",
        "desc": "陈述本文核心观点、方法框架、技术路线或设计选择。",
    },
    "MethodMechanism": {
        "zh": "方法机制说明",
        "desc": "说明算法、目标函数、训练过程、实验设置或设计细节如何工作。",
    },
    "TheoreticalResult": {
        "zh": "理论命题/推导",
        "desc": "给出命题、公式关系、推导结论或理论性质。",
    },
    "Evidence": {
        "zh": "证据/实验结果",
        "desc": "引用实验、图表、观察结果或事实来支撑前文主张。",
    },
    "Interpretation": {
        "zh": "结果解释",
        "desc": "解释理论或实验结果的含义，并把事实转化为论文论点。",
    },
    "Comparison": {
        "zh": "对比评估",
        "desc": "比较方法、设置或结果，突出差异、优势或改进幅度。",
    },
    "RelatedWorkPositioning": {
        "zh": "相关工作定位",
        "desc": "综述已有工作，并说明本文与它们的关系、差异或归属。",
    },
    "Contribution": {
        "zh": "贡献声明",
        "desc": "概括本文的具体贡献，帮助读者建立结果清单。",
    },
    "AssumptionScope": {
        "zh": "假设/范围限定",
        "desc": "限定分析条件、适用范围、实验边界或证明前提。",
    },
    "Transition": {
        "zh": "结构过渡",
        "desc": "提示章节安排、下一步内容或阅读指引。",
    },
    "LimitationFuture": {
        "zh": "局限/未来工作",
        "desc": "说明当前工作的边界，并指出可能的后续扩展方向。",
    },
    "Other": {
        "zh": "其他",
        "desc": "句子具有辅助说明功能，但不明显属于其他类型。",
    },
}

ABBR = {
    "i.e.": "i<prd>e<prd>",
    "e.g.": "e<prd>g<prd>",
    "cf.": "cf<prd>",
    "Dr.": "Dr<prd>",
    "Fig.": "Fig<prd>",
    "Eq.": "Eq<prd>",
    "Sec.": "Sec<prd>",
    "vs.": "vs<prd>",
    "et al.": "et al<prd>",
    "al.": "al<prd>",
}


@dataclass
class Sentence:
    sid: str
    section_id: str
    section_title: str
    text: str
    role: str = "Other"
    purpose: str = ""
    confidence: str = "medium"


@dataclass
class Section:
    section_id: str
    title: str
    paragraphs: list[str]
    sentences: list[Sentence]

    @property
    def context(self) -> str:
        return "\n\n".join(self.paragraphs)


def run_pdftotext(pdf: Path) -> str:
    print(f"[1/5] Extracting text from PDF: {pdf}", flush=True)
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        subprocess.run(["pdftotext", str(pdf), str(tmp_path)], check=True, capture_output=True, text=True)
        return tmp_path.read_text(errors="ignore")
    except FileNotFoundError as exc:
        raise SystemExit("pdftotext is required. Install poppler-utils first.") from exc
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"pdftotext failed:\n{exc.stderr}") from exc
    finally:
        tmp_path.unlink(missing_ok=True)


def is_tex_source_path(path: Path) -> bool:
    suffixes = path.suffixes
    return path.suffix == ".tex" or suffixes[-2:] == [".tar", ".gz"] or path.suffix == ".tgz"


def is_supported_input_path(path: Path) -> bool:
    return path.suffix.lower() == ".pdf" or is_tex_source_path(path)


def output_stem(path: Path) -> str:
    if path.suffixes[-2:] == [".tar", ".gz"]:
        return path.name[: -len(".tar.gz")]
    if path.suffix == ".tgz":
        return path.name[: -len(".tgz")]
    return path.stem


def output_paths_for_html(output_html: Path) -> dict[str, Path]:
    return {
        "html": output_html,
        "stats": output_html.with_suffix(".stats.json"),
        "annotations": output_html.with_suffix(".annotations.json"),
    }


def completed_output_exists(output_html: Path) -> bool:
    paths = output_paths_for_html(output_html)
    return all(path.exists() and path.stat().st_size > 0 for path in paths.values())


def discover_batch_inputs(batch_dir: Path) -> list[Path]:
    return sorted(path for path in batch_dir.rglob("*") if path.is_file() and is_supported_input_path(path))


def read_tex_project(source: Path) -> tuple[dict[str, str], str]:
    if source.suffix == ".tex":
        return {source.name: source.read_text(encoding="utf-8", errors="ignore")}, source.name
    if source.suffixes[-2:] == [".tar", ".gz"] or source.suffix == ".tgz":
        files: dict[str, str] = {}
        with tarfile.open(source, "r:*") as archive:
            for member in archive.getmembers():
                if not member.isfile() or not member.name.endswith(".tex"):
                    continue
                extracted = archive.extractfile(member)
                if extracted is None:
                    continue
                files[member.name] = extracted.read().decode("utf-8", errors="ignore")
        if not files:
            raise SystemExit(f"No .tex files found in source archive: {source}")
        return files, choose_main_tex(files)
    raise SystemExit(f"Unsupported TeX source path: {source}")


def choose_main_tex(files: dict[str, str]) -> str:
    candidates = [
        name
        for name, text in files.items()
        if r"\begin{document}" in text and "appendix" not in Path(name).name.lower()
    ]
    if not candidates:
        candidates = [name for name, text in files.items() if r"\begin{document}" in text]
    if not candidates:
        raise SystemExit("Could not find a main .tex file containing \\begin{document}.")
    return max(candidates, key=lambda name: len(files[name]))


def expand_tex_inputs(files: dict[str, str], main_name: str) -> str:
    seen: set[str] = set()

    def resolve_name(include_name: str, current_name: str) -> str | None:
        raw = include_name.strip()
        if not raw.endswith(".tex"):
            raw += ".tex"
        candidates = [
            raw,
            str(Path(current_name).parent / raw),
            Path(raw).name,
        ]
        return next((candidate for candidate in candidates if candidate in files), None)

    def expand(name: str) -> str:
        if name in seen:
            return ""
        seen.add(name)
        text = strip_tex_comments(files[name])

        def repl(match: re.Match[str]) -> str:
            command, include_name = match.group(1), match.group(2)
            if command == "include":
                replacement = r"\clearpage" + "\n"
            else:
                replacement = ""
            resolved = resolve_name(include_name, name)
            if resolved is None:
                return replacement
            return replacement + expand(resolved)

        return re.sub(r"\\(input|include)\{([^}]+)\}", repl, text)

    return expand(main_name)


def strip_tex_comments(text: str) -> str:
    stripped: list[str] = []
    for line in text.splitlines():
        match = re.search(r"(?<!\\)%", line)
        if match:
            line = line[: match.start()]
        stripped.append(line)
    return "\n".join(stripped)


def parse_tex_source(source: Path) -> list[Section]:
    files, main_name = read_tex_project(source)
    tex = expand_tex_inputs(files, main_name)
    tex = extract_tex_document_body(tex)
    tex = remove_tex_environment_blocks(tex)
    tex = tex_to_plain_text(tex)
    return assign_sentences(parse_tex_sections(tex))


def extract_tex_document_body(tex: str) -> str:
    match = re.search(r"\\begin\{document\}", tex)
    if match:
        tex = tex[match.end() :]
    end_markers = [
        r"\\appendix\b",
        r"\\bibliographystyle\b",
        r"\\bibliography\b",
        r"\\begin\{thebibliography\}",
        r"\\end\{document\}",
    ]
    positions = [m.start() for pattern in end_markers if (m := re.search(pattern, tex))]
    if positions:
        tex = tex[: min(positions)]
    return tex


def remove_tex_environment_blocks(tex: str) -> str:
    block_envs = [
        "abstract",
        "figure",
        "figure*",
        "wrapfigure",
        "table",
        "table*",
        "tabular",
        "tabularx",
        "algorithm",
        "algorithmic",
        "equation",
        "equation*",
        "align",
        "align*",
        "gather",
        "gather*",
        "multline",
        "multline*",
        "center",
    ]
    for env in block_envs:
        pattern = re.compile(rf"\\begin\{{{re.escape(env)}\}}.*?\\end\{{{re.escape(env)}\}}", re.S)
        tex = pattern.sub("\n\n", tex)
    return tex


def tex_to_plain_text(tex: str) -> str:
    tex = re.sub(r"\\(section|subsection|subsubsection)\*?\{([^{}]*)\}", lambda m: f"\n\n@@{m.group(1)}@@{m.group(2)}\n\n", tex)
    tex = re.sub(r"\\paragraph\*?\{([^{}]*)\}", lambda m: f"\n\n@@paragraph@@{m.group(1)}\n\n", tex)
    tex = re.sub(r"\\(cite|citep|citet|ref|eqref|label|url|href)\*?(?:\[[^\]]*\])*\{[^{}]*\}(?:\{[^{}]*\})?", "", tex)
    tex = re.sub(r"\\footnote\{[^{}]*\}", "", tex)
    tex = re.sub(r"\$[^\n$]*\$", " ", tex)
    tex = re.sub(r"\\\[(.*?)\\\]", " ", tex, flags=re.S)
    tex = re.sub(r"\\\((.*?)\\\)", " ", tex, flags=re.S)
    for _ in range(6):
        tex = re.sub(r"\\(?:textbf|textit|texttt|emph|m|mathbf|mathrm|mathit|textcolor)\*?(?:\[[^\]]*\])?\{([^{}]*)\}", r"\1", tex)
    tex = tex.replace("~", " ")
    tex = tex.replace("``", '"').replace("''", '"')
    tex = tex.replace("---", "-").replace("--", "-")
    tex = re.sub(r"\\item\b", "\n", tex)
    tex = re.sub(r"\\(begin|end)\{[^{}]+\}", "\n", tex)
    tex = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", " ", tex)
    tex = re.sub(r"\\.", " ", tex)
    tex = tex.replace("{", "").replace("}", "")
    tex = re.sub(r"[ \t]+", " ", tex)
    tex = re.sub(r"\n[ \t]+", "\n", tex)
    tex = re.sub(r"\n{3,}", "\n\n", tex)
    return tex.strip()


def parse_tex_sections(text: str) -> list[Section]:
    marker_re = re.compile(r"@@(section|subsection|subsubsection|paragraph)@@([^\n]+)")
    matches = list(marker_re.finditer(text))
    sections: list[Section] = []
    section_no = 0
    subsection_no = 0
    subsubsection_no = 0
    paragraph_no = 0
    current_id = ""
    current_title = ""
    current_start = 0

    def flush(end: int) -> None:
        if not current_id:
            return
        chunk = text[current_start:end]
        paragraphs = [
            normalize_paragraph(paragraph)
            for paragraph in re.split(r"\n\s*\n", chunk)
            if keep_tex_paragraph(normalize_paragraph(paragraph))
        ]
        sections.append(Section(current_id, current_title, paragraphs, []))

    for match in matches:
        flush(match.start())
        kind = match.group(1)
        title = normalize_paragraph(match.group(2))
        if kind == "section":
            section_no += 1
            subsection_no = 0
            subsubsection_no = 0
            paragraph_no = 0
            current_id = str(section_no)
        elif kind == "subsection":
            subsection_no += 1
            subsubsection_no = 0
            paragraph_no = 0
            current_id = f"{section_no}.{subsection_no}"
        elif kind == "subsubsection":
            subsubsection_no += 1
            paragraph_no = 0
            current_id = f"{section_no}.{subsection_no}.{subsubsection_no}"
        else:
            paragraph_no += 1
            if subsubsection_no:
                current_id = f"{section_no}.{subsection_no}.{subsubsection_no}.{paragraph_no}"
            elif subsection_no:
                current_id = f"{section_no}.{subsection_no}.{paragraph_no}"
            else:
                current_id = f"{section_no}.{paragraph_no}"
        current_title = title
        current_start = match.end()
    flush(len(text))
    return sections


def normalize_line(line: str) -> str:
    line = line.strip()
    line = line.replace("\u00a0", " ")
    line = re.sub(r"\s+", " ", line)
    return line


def is_probable_table_or_figure_line(line: str) -> bool:
    if not line:
        return False
    if is_standalone_section_number(line):
        return False
    if re.match(r"^(Figure|Fig\.|Table)\s+\d+[:.]", line, re.I):
        return True
    if re.match(r"^\(?[a-z]\)?$", line):
        return True
    if re.fullmatch(r"[\d.\-+×*/%=<>{}()[\],:; ]+", line) and not re.fullmatch(r"\d+", line):
        return True
    alpha = sum(ch.isalpha() for ch in line)
    digits = sum(ch.isdigit() for ch in line)
    tokens = line.split()
    if len(tokens) >= 4 and digits > alpha and alpha < 25:
        return True
    table_words = {
        "Model/Method",
        "AIME",
        "MATH",
        "Minerva",
        "Avg.",
        "Pass@1",
        "Accuracy",
        "Reward",
        "Entropy",
        "Dataset",
        "Baseline",
    }
    if any(word in line for word in table_words) and len(tokens) <= 12 and digits > 0:
        return True
    return False


def clean_pdf_text(raw: str) -> list[str]:
    raw = raw.replace("\x0c", "\n")
    lines: list[str] = []
    skip_caption_continuation = False
    for source_line in raw.splitlines():
        line = normalize_line(source_line)
        if not line:
            skip_caption_continuation = False
            lines.append("")
            continue
        # Keep standalone section-like numbers. In pdftotext output they can be
        # page numbers, figure ticks, or section numbers; parse_sections decides
        # which ones matter using neighboring title lines and monotonic order.
        if line.lower().startswith("arxiv:"):
            continue
        if is_probable_table_or_figure_line(line):
            skip_caption_continuation = line.lower().startswith(("figure", "fig.", "table"))
            continue
        if skip_caption_continuation:
            if re.fullmatch(r"\d+", line) or is_heading_title(line):
                skip_caption_continuation = False
            else:
                if re.search(r"[.!?]$", line):
                    skip_caption_continuation = False
                continue
        if sum(ch.isalpha() for ch in line) == 0 and not is_standalone_section_number(line):
            continue
        lines.append(line)
    return lines


def find_body_bounds(lines: list[str]) -> tuple[int, int]:
    start = 0
    for i, line in enumerate(lines):
        if re.fullmatch(r"(?:\d+\s+)?Introduction", line, re.I):
            start = i
            break
    end = len(lines)
    end_pat = re.compile(r"^(References|Bibliography|Acknowledg(e)?ments|Supplementary Material)$", re.I)
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if end_pat.match(line):
            end = i
            break
        if re.match(r"^Appendix(?:\s+[A-Z])?$", line, re.I):
            end = i
            break
    return start, end


def detect_section_heading(line: str, pending_number: str | None = None) -> tuple[str, str] | None:
    if pending_number:
        if is_heading_title(line, numbered=True):
            return pending_number, line
        return None
    match = re.match(r"^(\d+(?:\.\d+)*)\.?\s+(.{3,120})$", line)
    if match and is_heading_title(match.group(2), numbered=True):
        return match.group(1), match.group(2).strip()
    if re.fullmatch(r"(Introduction|Related Work|Background|Preliminaries|Experiments|Evaluation|Results|Discussion|Conclusion|Limitations)", line, re.I):
        return infer_section_number(line), line
    return None


def infer_section_number(title: str) -> str:
    order = {
        "introduction": "1",
        "related work": "2",
        "background": "2",
        "preliminaries": "3",
        "method": "4",
        "methods": "4",
        "approach": "4",
        "experiments": "5",
        "evaluation": "5",
        "results": "5",
        "discussion": "6",
        "conclusion": "7",
        "limitations": "7",
    }
    return order.get(title.lower(), "0")


def is_heading_title(line: str, numbered: bool = False) -> bool:
    if len(line) > 120 or len(line) < 3:
        return False
    if line.endswith("."):
        return False
    if not numbered and re.match(r"^(we|this|these|those|our|the|a|an)\s+", line, re.I):
        return False
    alpha = sum(ch.isalpha() for ch in line)
    if alpha < 3:
        return False
    words = line.split()
    if len(words) > 12:
        return False
    lower = line.lower()
    if any(token in lower for token in ["=", "http", "arxiv", "∑", "∈", "following baselines"]):
        return False
    if numbered:
        return True
    if re.search(r"[:()]", line):
        return False
    capitalized = sum(bool(re.match(r"[A-Z]", w)) for w in words)
    if capitalized >= max(1, len(words) // 2) or lower in {
        "introduction",
        "related work",
        "preliminaries",
        "experiments",
        "conclusion",
    }:
        return True
    return False


def is_standalone_section_number(line: str) -> bool:
    return bool(re.fullmatch(r"\d+(?:\.\d+)*", line))


def is_plausible_section_number(section_id: str, current_id: str) -> bool:
    parts = section_id.split(".")
    try:
        numbers = [int(part) for part in parts]
    except ValueError:
        return False
    if any(number < 0 or number > 20 for number in numbers):
        return False
    if len(numbers) == 1:
        if numbers[0] == 0:
            return False
        if not current_id:
            return True
        try:
            current_top = int(current_id.split(".", 1)[0])
        except ValueError:
            return True
        return numbers[0] > current_top and numbers[0] <= current_top + 1
    if len(numbers) > 3:
        return False
    if not current_id:
        return False
    try:
        current_parts = [int(part) for part in current_id.split(".")]
    except ValueError:
        return False
    if numbers[0] != current_parts[0]:
        return False
    if len(numbers) == len(current_parts):
        return numbers[:-1] == current_parts[:-1] and numbers[-1] > current_parts[-1]
    return numbers[:-1] == current_parts


def parse_sections(lines: list[str]) -> list[Section]:
    start, end = find_body_bounds(lines)
    body = lines[start:end]
    sections: list[Section] = []
    current_id = ""
    current_title = "Body"
    current_paragraph_lines: list[str] = []
    current_paragraphs: list[str] = []
    pending_number: str | None = None

    def flush_paragraph() -> None:
        nonlocal current_paragraph_lines
        if current_paragraph_lines:
            paragraph = normalize_paragraph(" ".join(current_paragraph_lines))
            if keep_paragraph(paragraph):
                current_paragraphs.append(paragraph)
            current_paragraph_lines = []

    def flush_section() -> None:
        flush_paragraph()
        if current_paragraphs:
            sections.append(Section(current_id or "0", current_title, current_paragraphs.copy(), []))
            current_paragraphs.clear()

    i = 0
    while i < len(body):
        line = body[i]
        if not line:
            flush_paragraph()
            i += 1
            continue
        if is_standalone_section_number(line):
            next_line, after_next = next_non_empty_lines(body, i + 1, limit=2)
            if (
                next_line
                and is_plausible_section_number(line, current_id)
                and is_heading_title(next_line, numbered=True)
                and not is_table_context_heading(next_line, after_next)
            ):
                pending_number = line
            else:
                pending_number = None
            i += 1
            continue
        heading = detect_section_heading(line, pending_number)
        if heading and is_plausible_section_number(heading[0], current_id):
            flush_section()
            current_id, current_title = heading
            pending_number = None
            i += 1
            continue
        pending_number = None
        current_paragraph_lines.append(line)
        i += 1
    flush_section()
    return assign_sentences(sections)


def next_non_empty_lines(lines: list[str], start: int, limit: int) -> tuple[str | None, str | None]:
    found: list[str] = []
    for line in lines[start:]:
        if line:
            found.append(line)
            if len(found) >= limit:
                break
    while len(found) < limit:
        found.append(None)  # type: ignore[arg-type]
    return found[0], found[1]


def is_table_context_heading(candidate: str, following: str | None) -> bool:
    if candidate in {"Step", "Method", "Model/Method", "Generation Entropy", "Pass@1", "Reward"}:
        return True
    if following and re.fullmatch(r"0(?:\.\d+)+", following):
        return True
    if candidate in {"Dr. GRPO", "DAPO", "TRPA", "GRPO-ER", "DisCO", "DisCO DisCO-b w/"}:
        return True
    if "DisCO DisCO-b" in candidate or "p(1 p)" in candidate:
        return True
    if is_table_fragment_text(candidate):
        return True
    if following and is_table_fragment_text(following):
        return True
    return False


def is_table_fragment_text(text: str) -> bool:
    table_tokens = {
        "Difficulty Bias",
        "Clipping",
        "KL Divergence",
        "Score Function",
        "AIME 2024",
        "AIME 2025",
        "MATH 500",
        "AMC 2023",
        "Minerva",
        "O-Bench",
        "Avg.",
        "OpenAI-o1-Preview",
        "Model/Method",
        "Generation Entropy",
        "Pass@1",
        "KL Reg.",
        "Clipped L-ratio",
    }
    return any(token in text for token in table_tokens)


def normalize_paragraph(paragraph: str) -> str:
    paragraph = paragraph.replace("- ", "")
    paragraph = re.sub(r"\s+([,.;:])", r"\1", paragraph)
    paragraph = re.sub(r"\s+", " ", paragraph)
    return paragraph.strip()


def keep_paragraph(paragraph: str) -> bool:
    if not paragraph:
        return False
    if paragraph.startswith(("Figure ", "Fig. ", "Table ")):
        return False
    alpha = sum(ch.isalpha() for ch in paragraph)
    alnum = sum(ch.isalnum() for ch in paragraph)
    if alpha < 20:
        return False
    if alpha / max(alnum, 1) < 0.42:
        return False
    if paragraph.count("=") >= 4 and alpha < 180:
        return False
    return True


def keep_tex_paragraph(paragraph: str) -> bool:
    if not paragraph:
        return False
    alpha = sum(ch.isalpha() for ch in paragraph)
    alnum = sum(ch.isalnum() for ch in paragraph)
    if alpha < 20:
        return False
    if alpha / max(alnum, 1) < 0.42:
        return False
    if paragraph.count("=") >= 4 and alpha < 180:
        return False
    return True


def split_sentences(paragraph: str) -> list[str]:
    text = paragraph
    for src, dst in ABBR.items():
        text = text.replace(src, dst)
    text = re.sub(r"(•)\s*", r"\n\1 ", text)
    text = re.sub(r"(?<=[.!?])\s+(?=(?:[A-Z]|[“(]|•))", "\n", text)
    sentences: list[str] = []
    for sent in text.split("\n"):
        sent = sent.strip()
        for src, dst in ABBR.items():
            sent = sent.replace(dst, src)
        if keep_sentence(sent):
            sentences.append(sent)
    return sentences


def keep_sentence(sentence: str) -> bool:
    if len(sentence) < 18:
        return False
    alpha = sum(ch.isalpha() for ch in sentence)
    if alpha < 12:
        return False
    if sentence.startswith(("Figure ", "Fig. ", "Table ")):
        return False
    if sentence.count("=") >= 4 and alpha < 120:
        return False
    return True


def assign_sentences(sections: list[Section]) -> list[Section]:
    serial = 1
    for section in sections:
        for paragraph in section.paragraphs:
            for text in split_sentences(paragraph):
                section.sentences.append(
                    Sentence(
                        sid=f"S{serial:04d}",
                        section_id=section.section_id,
                        section_title=section.title,
                        text=text,
                    )
                )
                serial += 1
    return sections


def build_prompt(section: Section) -> list[dict[str, str]]:
    roles = "\n".join(f"- {name}: {data['zh']}。{data['desc']}" for name, data in ROLE_SCHEMA.items())
    sentence_lines = "\n".join(f"{s.sid}: {s.text}" for s in section.sentences)
    system = (
        "You are an expert scientific-writing analyst. "
        "Classify each sentence by its rhetorical/logical role in the paper. "
        "Use the section context, not the isolated sentence. "
        "Return strict JSON only."
    )
    user = f"""请基于整个章节上下文，判断该章节内每个句子的主要作用类型。

章节：{section.section_id} {section.title}

可选类型：
{roles}

章节全文：
<<<SECTION_CONTEXT
{section.context}
SECTION_CONTEXT>>>

待标注句子：
<<<SENTENCES
{sentence_lines}
SENTENCES>>>

输出要求：
1. 只输出 JSON，不要 Markdown。
2. JSON 顶层格式为 {{"annotations": [...]}}。
3. annotations 中每个对象必须包含：
   - "sid": 句子 ID，必须来自待标注句子。
   - "role": 只能使用上面列出的英文类型名。
   - "purpose": 用中文一句话说明该句在本章节论证链中的具体作用。
   - "confidence": "high"、"medium" 或 "low"。
4. 必须覆盖所有句子，每个 sid 恰好出现一次。
5. 如果一句话有多个功能，选择它在当前章节论证链中的主功能。
"""
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def call_llm(messages: list[dict[str, str]], model: str, base_url: str, temperature: float) -> dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is not set. Export it before running this script.")
    last_error: Exception | None = None
    for attempt in range(1, LLM_REQUEST_RETRIES + 1):
        try:
            try:
                from openai import OpenAI

                client = OpenAI(api_key=api_key, base_url=base_url)
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    response_format={"type": "json_object"},
                    timeout=LLM_REQUEST_TIMEOUT_SECONDS,
                )
                content = response.choices[0].message.content or ""
            except ImportError:
                content = call_llm_with_urllib(messages, model, base_url, temperature, api_key)
            return parse_json_response(content)
        except Exception as exc:
            last_error = exc
            if attempt >= LLM_REQUEST_RETRIES:
                break
            time.sleep(2 * attempt)
    assert last_error is not None
    raise last_error


def call_llm_with_urllib(
    messages: list[dict[str, str]],
    model: str,
    base_url: str,
    temperature: float,
    api_key: str,
) -> str:
    endpoint = base_url.rstrip("/") + "/chat/completions"
    payload = json.dumps(
        {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=LLM_REQUEST_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"LLM API HTTP error {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"LLM API connection error: {exc}") from exc
    except TimeoutError as exc:
        raise RuntimeError(f"LLM API request timed out after {LLM_REQUEST_TIMEOUT_SECONDS} seconds.") from exc
    data = json.loads(raw)
    return data["choices"][0]["message"]["content"] or ""


def parse_json_response(content: str) -> dict[str, Any]:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?", "", content).strip()
        content = re.sub(r"```$", "", content).strip()
    decoder = json.JSONDecoder()
    try:
        payload, _ = decoder.raw_decode(content)
    except json.JSONDecodeError:
        match = re.search(r"[\[{]", content)
        if not match:
            raise
        payload, _ = decoder.raw_decode(content[match.start() :])
    if isinstance(payload, list):
        return {"annotations": payload}
    if isinstance(payload, dict) and "annotations" not in payload and {"sid", "role"} & set(payload):
        return {"annotations": [payload]}
    if not isinstance(payload, dict):
        raise ValueError(f"LLM response JSON must be an object or annotation list, got {type(payload).__name__}.")
    return payload


def annotate_sections(
    sections: list[Section],
    *,
    model: str,
    base_url: str,
    temperature: float,
    dry_run: bool,
    workers: int,
) -> None:
    total_sections = len(sections)
    workers = max(1, workers)
    print(f"[3/5] Annotating {total_sections} section(s) with {workers} worker(s).", flush=True)
    if not dry_run and workers > 1:
        annotate_sections_concurrently(
            sections,
            model=model,
            base_url=base_url,
            temperature=temperature,
            workers=workers,
        )
        return
    for index, section in enumerate(sections, start=1):
        print(
            f"  - Section {index}/{total_sections}: {section.section_id} {section.title} "
            f"({len(section.sentences)} sentences)",
            flush=True,
        )
        if not section.sentences:
            print("    skipped: no analyzable sentences in this structural section.", flush=True)
            continue
        if dry_run:
            for sentence in section.sentences:
                sentence.role = "Other"
                sentence.purpose = "dry-run 模式未调用 LLM；这里只验证 PDF 解析、切句、统计和 HTML 渲染流程。"
                sentence.confidence = "low"
            print("    dry-run: skipped LLM call.", flush=True)
            continue
        payload = call_llm(build_prompt(section), model, base_url, temperature)
        apply_annotations(section, payload)
        print("    done.", flush=True)


def annotate_sections_concurrently(
    sections: list[Section],
    *,
    model: str,
    base_url: str,
    temperature: float,
    workers: int,
) -> None:
    sections_to_annotate = [section for section in sections if section.sentences]
    empty_sections = len(sections) - len(sections_to_annotate)
    if empty_sections:
        print(f"  - Skipping {empty_sections} structural section(s) with no analyzable sentences.", flush=True)
    if not sections_to_annotate:
        return

    workers = min(workers, len(sections_to_annotate))

    def request(section: Section) -> tuple[Section, dict[str, Any]]:
        return section, call_llm(build_prompt(section), model, base_url, temperature)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(request, section): section for section in sections_to_annotate}
        completed = 0
        for future in as_completed(futures):
            section = futures[future]
            try:
                annotated_section, payload = future.result()
                apply_annotations(annotated_section, payload)
            except Exception as exc:
                raise RuntimeError(f"LLM annotation failed for section {section.section_id} {section.title}: {exc}") from exc
            completed += 1
            print(
                f"  - Done {completed}/{len(sections_to_annotate)}: {section.section_id} {section.title} "
                f"({len(section.sentences)} sentences)",
                flush=True,
            )


def apply_annotations(section: Section, payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise TypeError(
            f"LLM response for section {section.section_id} must be a JSON object, "
            f"got {type(payload).__name__}."
        )
    annotations = payload.get("annotations")
    if not isinstance(annotations, list):
        raise ValueError(f"LLM response for section {section.section_id} does not contain annotations list.")
    by_sid = {s.sid: s for s in section.sentences}
    seen: set[str] = set()
    for item in annotations:
        if not isinstance(item, dict):
            continue
        sid = str(item.get("sid", "")).strip()
        if sid not in by_sid:
            continue
        role = str(item.get("role", "Other")).strip()
        if role not in ROLE_SCHEMA:
            role = "Other"
        confidence = str(item.get("confidence", "medium")).strip().lower()
        if confidence not in {"high", "medium", "low"}:
            confidence = "medium"
        purpose = str(item.get("purpose", "")).strip()
        by_sid[sid].role = role
        by_sid[sid].purpose = purpose or ROLE_SCHEMA[role]["desc"]
        by_sid[sid].confidence = confidence
        seen.add(sid)
    missing = set(by_sid) - seen
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(f"LLM response for section {section.section_id} missed sentence IDs: {missing_list}")


def make_stats(sections: list[Section]) -> dict[str, Any]:
    total = Counter()
    by_section: dict[str, Counter[str]] = {}
    section_labels = top_level_section_labels(sections)
    for section in sections:
        counter = Counter(s.role for s in section.sentences)
        section_key = section_labels.get(section.section_id, f"{top_level_section_id(section.section_id)} {section.title}".strip())
        by_section.setdefault(section_key, Counter()).update(counter)
        total.update(counter)
    return {
        "total_sentences": sum(total.values()),
        "total_histogram": dict(total),
        "section_histograms": {section: dict(counter) for section, counter in by_section.items()},
    }


def top_level_section_id(section_id: str) -> str:
    return section_id.split(".", 1)[0] if section_id else "0"


def top_level_section_labels(sections: list[Section]) -> dict[str, str]:
    top_titles: dict[str, str] = {}
    for section in sections:
        top_id = top_level_section_id(section.section_id)
        if "." not in section.section_id and top_id not in top_titles:
            top_titles[top_id] = section.title

    labels: dict[str, str] = {}
    for section in sections:
        top_id = top_level_section_id(section.section_id)
        title = top_titles.get(top_id, section.title)
        labels[section.section_id] = f"{top_id} {title}".strip()
    return labels


def render_bar_histogram(counter: Counter[str], max_count: int | None = None) -> str:
    if not counter:
        return ""
    max_count = max_count or max(counter.values())
    rows = []
    for role, count in counter.most_common():
        width = 100 * count / max_count if max_count else 0
        rows.append(
            f'<div class="bar-row"><span class="bar-label">{html.escape(ROLE_SCHEMA[role]["zh"])}</span>'
            f'<div class="bar-track"><div class="bar" style="width:{width:.1f}%"></div></div>'
            f'<span class="bar-count">{count}</span></div>'
        )
    return "\n".join(rows)


def render_html(sections: list[Section], stats: dict[str, Any], source_pdf: Path, model: str) -> str:
    all_sentences = [s for section in sections for s in section.sentences]
    total_counter = Counter(stats["total_histogram"])
    max_total = max(total_counter.values()) if total_counter else 1
    toc = "\n".join(
        f'<a href="#section-{html.escape(section.section_id)}">{html.escape(section.section_id)} {html.escape(section.title)}</a>'
        for section in sections
    )
    role_buttons = "\n".join(
        f'<button data-filter="{html.escape(role)}"><span>{html.escape(ROLE_SCHEMA[role]["zh"])}</span><small>{count}</small></button>'
        for role, count in total_counter.most_common()
    )
    section_histograms = []
    for key in stats["section_histograms"]:
        counter = Counter(stats["section_histograms"].get(key, {}))
        section_histograms.append(
            f'<details><summary>{html.escape(key)} <span>{sum(counter.values())}</span></summary>'
            f'{render_bar_histogram(counter)}</details>'
        )

    content = []
    for section in sections:
        content.append(f'<h2 id="section-{html.escape(section.section_id)}">{html.escape(section.section_id)} {html.escape(section.title)}</h2>')
        for sentence in section.sentences:
            role_meta = ROLE_SCHEMA[sentence.role]
            content.append(
                f'<article class="sentence" data-role="{html.escape(sentence.role)}">'
                f'<div class="meta"><span class="sid">{html.escape(sentence.sid)}</span>'
                f'<span class="tag">{html.escape(role_meta["zh"])}</span>'
                f'<span class="confidence">{html.escape(sentence.confidence)}</span></div>'
                f'<p class="original">{html.escape(sentence.text)}</p>'
                f'<p class="purpose"><strong>目的：</strong>{html.escape(sentence.purpose)}</p>'
                f'<p class="role-note"><strong>类型说明：</strong>{html.escape(role_meta["desc"])}</p>'
                f'</article>'
            )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Sentence Role Analysis</title>
  <style>
    :root {{
      --bg: #f5f7fa;
      --panel: #ffffff;
      --text: #202a36;
      --muted: #68788d;
      --line: #dbe2eb;
      --accent: #116a63;
      --accent-soft: #e6f2ef;
      --warn: #8a5a13;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.55;
    }}
    header {{
      background: var(--panel);
      border-bottom: 1px solid var(--line);
      padding: 26px 32px 18px;
    }}
    h1 {{ margin: 0 0 8px; font-size: 28px; line-height: 1.2; letter-spacing: 0; }}
    .subtitle {{ margin: 0; color: var(--muted); max-width: 1100px; }}
    .layout {{
      display: grid;
      grid-template-columns: 330px minmax(0, 1fr);
      gap: 22px;
      padding: 22px 32px 44px;
    }}
    aside {{
      position: sticky;
      top: 16px;
      align-self: start;
      max-height: calc(100vh - 32px);
      overflow: auto;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
    }}
    aside h2 {{ font-size: 15px; margin: 18px 0 10px; }}
    aside h2:first-child {{ margin-top: 0; }}
    .stats {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
    .stat {{ border: 1px solid var(--line); border-radius: 6px; background: #fbfcfd; padding: 10px; }}
    .stat strong {{ display: block; color: var(--accent); font-size: 22px; }}
    .stat span {{ color: var(--muted); font-size: 12px; }}
    nav a {{
      display: block;
      color: var(--text);
      text-decoration: none;
      border-bottom: 1px solid #eef1f5;
      padding: 5px 0;
      font-size: 13px;
    }}
    .filters button {{
      width: 100%;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      margin: 0 0 7px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      padding: 7px 9px;
      cursor: pointer;
      color: var(--text);
    }}
    .filters button:hover, .filters button.active {{ border-color: var(--accent); color: var(--accent); }}
    .bar-row {{ display: grid; grid-template-columns: 96px 1fr 34px; align-items: center; gap: 8px; margin: 7px 0; font-size: 12px; }}
    .bar-label {{ color: var(--muted); }}
    .bar-track {{ height: 9px; background: #edf1f5; border-radius: 999px; overflow: hidden; }}
    .bar {{ height: 100%; background: var(--accent); }}
    .bar-count {{ color: var(--muted); text-align: right; font-variant-numeric: tabular-nums; }}
    details {{ border-top: 1px solid #eef1f5; padding: 7px 0; }}
    summary {{ cursor: pointer; font-size: 13px; }}
    summary span {{ color: var(--muted); float: right; }}
    main {{
      min-width: 0;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 22px 24px;
    }}
    main h2 {{
      margin: 28px 0 14px;
      padding-top: 8px;
      border-top: 1px solid var(--line);
      font-size: 22px;
      letter-spacing: 0;
    }}
    main h2:first-child {{ margin-top: 0; border-top: 0; }}
    .sentence {{
      border: 1px solid var(--line);
      border-left: 4px solid var(--accent);
      border-radius: 8px;
      background: #fff;
      padding: 14px 16px;
      margin: 12px 0;
    }}
    .sentence.hidden {{ display: none; }}
    .meta {{ display: flex; gap: 8px; align-items: center; margin-bottom: 7px; }}
    .sid, .confidence {{ color: var(--muted); font-size: 12px; font-variant-numeric: tabular-nums; }}
    .tag {{
      border: 1px solid #c6e1dc;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      padding: 2px 8px;
      font-size: 12px;
      white-space: nowrap;
    }}
    .original {{ margin: 0 0 9px; font-size: 15px; }}
    .purpose, .role-note {{ margin: 5px 0 0; color: #3d4a5c; font-size: 14px; }}
    .role-note {{ color: var(--muted); }}
    .note {{
      margin-top: 12px;
      border: 1px solid #edd5a8;
      border-radius: 6px;
      background: #fff8ea;
      color: var(--warn);
      padding: 10px 12px;
      font-size: 13px;
    }}
    @media (max-width: 900px) {{
      header {{ padding: 22px 18px 14px; }}
      .layout {{ display: block; padding: 16px; }}
      aside {{ position: static; max-height: none; margin-bottom: 16px; }}
      main {{ padding: 18px 14px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>论文正文句子级作用分析报告</h1>
    <p class="subtitle">源文件：{html.escape(str(source_pdf))}；模型：{html.escape(model)}。正文按 section 划分；表格、图片标题和明显图表内容已在解析阶段移除。</p>
    <p class="note">LLM 每次接收一个完整 section 的上下文，并一次性标注该 section 内所有句子，避免孤立句子分类。</p>
  </header>
  <div class="layout">
    <aside>
      <h2>统计</h2>
      <div class="stats">
        <div class="stat"><strong>{len(all_sentences)}</strong><span>句子数</span></div>
        <div class="stat"><strong>{len(sections)}</strong><span>sections</span></div>
      </div>
      <h2>章节导航</h2>
      <nav>{toc}</nav>
      <h2>总直方图</h2>
      {render_bar_histogram(total_counter, max_total)}
      <h2>按类型筛选</h2>
      <div class="filters">
        <button data-filter="ALL" class="active"><span>显示全部</span><small>{len(all_sentences)}</small></button>
        {role_buttons}
      </div>
      <h2>分章节直方图</h2>
      {''.join(section_histograms)}
    </aside>
    <main>
      {''.join(content)}
    </main>
  </div>
  <script>
    const buttons = [...document.querySelectorAll('[data-filter]')];
    const cards = [...document.querySelectorAll('.sentence')];
    buttons.forEach(button => {{
      button.addEventListener('click', () => {{
        const filter = button.dataset.filter;
        buttons.forEach(b => b.classList.remove('active'));
        button.classList.add('active');
        cards.forEach(card => {{
          card.classList.toggle('hidden', filter !== 'ALL' && card.dataset.role !== filter);
        }});
      }});
    }});
  </script>
</body>
</html>
"""


def write_outputs(sections: list[Section], output_html: Path, source_path: Path, model: str) -> None:
    print(f"[4/5] Rendering report and statistics.", flush=True)
    stats = make_stats(sections)
    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text(render_html(sections, stats, source_path, model), encoding="utf-8")
    stats_path = output_html.with_suffix(".stats.json")
    stats_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    annotations_path = output_html.with_suffix(".annotations.json")
    annotations = [
        {
            "sid": sentence.sid,
            "section_id": sentence.section_id,
            "section_title": sentence.section_title,
            "sentence": sentence.text,
            "role": sentence.role,
            "role_zh": ROLE_SCHEMA[sentence.role]["zh"],
            "purpose": sentence.purpose,
            "confidence": sentence.confidence,
        }
        for section in sections
        for sentence in section.sentences
    ]
    annotations_path.write_text(json.dumps({"annotations": annotations}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[5/5] Wrote outputs.", flush=True)


def analyze_one(
    *,
    input_path: Path | None,
    tex_source: Path | None,
    output_html: Path,
    model: str,
    base_url: str,
    temperature: float,
    dry_run: bool,
    workers: int,
) -> dict[str, str]:
    pdf: Path | None = None

    if input_path and not input_path.exists():
        raise SystemExit(f"Input not found: {input_path}")
    if tex_source and not tex_source.exists():
        raise SystemExit(f"TeX source not found: {tex_source}")
    if tex_source and not is_tex_source_path(tex_source):
        raise SystemExit(f"Unsupported TeX source path: {tex_source}")

    if tex_source:
        pdf = input_path
    elif input_path and is_tex_source_path(input_path):
        tex_source = input_path
    elif input_path:
        pdf = input_path
    else:
        raise SystemExit("Provide either an input PDF, an input TeX source, or --tex-source.")

    if pdf and is_tex_source_path(pdf):
        raise SystemExit(f"Expected a PDF input, got TeX source path: {pdf}")
    if pdf and pdf.suffix.lower() != ".pdf":
        raise SystemExit(f"Expected a PDF input path or TeX source path, got: {pdf}")

    parse_mode = "TeX source" if tex_source else "PDF"
    if pdf:
        print(f"Input PDF: {pdf}", flush=True)
    else:
        print("Input PDF: not provided", flush=True)
    if tex_source:
        print(f"Parse source: {tex_source.resolve()} (TeX priority)", flush=True)
    print(f"Output HTML: {output_html.resolve()}", flush=True)
    print(f"Model: {model}", flush=True)
    print(f"Base URL: {base_url}", flush=True)
    if dry_run:
        print("Mode: dry-run (LLM calls disabled)", flush=True)
    if tex_source:
        print(f"[1/5] Reading LaTeX source: {tex_source.resolve()}", flush=True)
        print("[2/5] Parsing TeX sections and splitting sentences.", flush=True)
        sections = parse_tex_source(tex_source.resolve())
        source_for_report = tex_source.resolve()
    else:
        assert pdf is not None
        raw_text = run_pdftotext(pdf)
        print("[2/5] Parsing body sections and splitting sentences.", flush=True)
        sections = parse_sections(clean_pdf_text(raw_text))
        source_for_report = pdf
    if not sections:
        raise SystemExit("No analyzable body sections were detected.")
    total_sentences = sum(len(section.sentences) for section in sections)
    print(f"Detected {len(sections)} section(s), {total_sentences} sentence(s) from {parse_mode}.", flush=True)
    for section in sections:
        print(f"  * {section.section_id} {section.title}: {len(section.sentences)} sentences", flush=True)
    annotate_sections(
        sections,
        model=model,
        base_url=base_url,
        temperature=temperature,
        dry_run=dry_run,
        workers=workers,
    )
    write_outputs(sections, output_html.resolve(), source_for_report, model)
    print(f"HTML: {output_html.resolve()}")
    print(f"Stats: {output_html.resolve().with_suffix('.stats.json')}")
    print(f"Annotations: {output_html.resolve().with_suffix('.annotations.json')}")
    return {
        "html": str(output_html.resolve()),
        "stats": str(output_html.resolve().with_suffix(".stats.json")),
        "annotations": str(output_html.resolve().with_suffix(".annotations.json")),
        "parse_mode": parse_mode,
        "sections": str(len(sections)),
        "sentences": str(total_sentences),
    }


def run_batch(args: argparse.Namespace, batch_dir: Path) -> None:
    if not batch_dir.exists() or not batch_dir.is_dir():
        raise SystemExit(f"Batch directory not found: {batch_dir}")
    output_dir = (args.output_dir or batch_dir / "sentence_role_reports").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    inputs = discover_batch_inputs(batch_dir.resolve())
    if not inputs:
        raise SystemExit(f"No supported inputs found under batch directory: {batch_dir}")

    print(f"Batch directory: {batch_dir.resolve()}", flush=True)
    print(f"Batch outputs: {output_dir}", flush=True)
    print(f"Batch discovered inputs: {len(inputs)}", flush=True)
    if args.limit is not None:
        print(f"Batch run limit: {args.limit} unfinished input(s)", flush=True)
    if args.dry_run:
        print("Mode: dry-run (LLM calls disabled)", flush=True)

    records: list[dict[str, str]] = []
    submitted = 0
    for index, source in enumerate(inputs, start=1):
        output_html = output_dir / f"{output_stem(source)}_sentence_roles.html"
        print(f"\n=== [{index}/{len(inputs)}] {source} ===", flush=True)
        if not args.rerun_existing and completed_output_exists(output_html):
            output_paths = output_paths_for_html(output_html)
            print(f"Skipping completed output: {output_html}", flush=True)
            records.append(
                {
                    "source": str(source),
                    "status": "skipped_completed",
                    "html": str(output_paths["html"]),
                    "stats": str(output_paths["stats"]),
                    "annotations": str(output_paths["annotations"]),
                }
            )
            continue
        if args.skip_existing and output_html.exists():
            print(f"Skipping existing HTML output: {output_html}", flush=True)
            records.append({"source": str(source), "status": "skipped_existing_html", "html": str(output_html)})
            continue
        if args.limit is not None and submitted >= args.limit:
            print(f"Reached --limit {args.limit}; stopping before next unfinished input.", flush=True)
            break
        try:
            submitted += 1
            source_is_tex = is_tex_source_path(source)
            result = analyze_one(
                input_path=None if source_is_tex else source,
                tex_source=source if source_is_tex else None,
                output_html=output_html,
                model=args.model,
                base_url=args.base_url,
                temperature=args.temperature,
                dry_run=args.dry_run,
                workers=args.workers,
            )
            records.append({"source": str(source), "status": "ok", **result})
        except SystemExit as exc:
            print(f"Failed: {exc}", flush=True)
            records.append({"source": str(source), "status": "failed", "error": str(exc)})
        except Exception as exc:
            print(f"Failed: {exc}", flush=True)
            records.append({"source": str(source), "status": "failed", "error": str(exc)})

    manifest = {
        "batch_dir": str(batch_dir.resolve()),
        "output_dir": str(output_dir),
        "total": len(records),
        "ok": sum(record["status"] == "ok" for record in records),
        "failed": sum(record["status"] == "failed" for record in records),
        "skipped": sum(record["status"].startswith("skipped") for record in records),
        "records": records,
    }
    manifest_path = output_dir / "batch_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nBatch manifest: {manifest_path}", flush=True)
    if manifest["failed"]:
        print(f"Batch completed with {manifest['failed']} failed input(s).", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze sentence-level rhetorical roles in a paper PDF or LaTeX source using one LLM call per section."
    )
    parser.add_argument("input", type=Path, nargs="?", help="Input PDF path, LaTeX source path, or a directory for batch mode.")
    parser.add_argument("-o", "--output-html", type=Path, help="Output HTML report path.")
    parser.add_argument("--batch-dir", type=Path, help="Directory containing PDFs or LaTeX sources to analyze sequentially.")
    parser.add_argument("--output-dir", type=Path, help="Output directory for batch reports. Default: <batch-dir>/sentence_role_reports.")
    parser.add_argument("--limit", type=int, help="Analyze only the first N discovered inputs/papers in batch mode.")
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="In batch mode, skip inputs whose HTML report exists even if stats/annotations are missing.",
    )
    parser.add_argument(
        "--rerun-existing",
        action="store_true",
        help="In batch mode, rerun inputs even when complete outputs already exist.",
    )
    parser.add_argument(
        "--tex-source",
        type=Path,
        help="Optional LaTeX source path (.tex, .tar.gz, or .tgz). If set, parse this source instead of extracting text from the PDF.",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"LLM model name. Default: {DEFAULT_MODEL}.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"OpenAI-compatible API base URL. Default: {DEFAULT_BASE_URL}.")
    parser.add_argument("--temperature", type=float, default=0.0, help="LLM temperature. Default: 0.")
    parser.add_argument("--workers", type=int, default=4, help="Concurrent LLM calls per paper. Use 1 for serial annotation. Default: 4.")
    parser.add_argument("--dry-run", action="store_true", help="Do not call LLM; only test parsing and rendering.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = args.input.resolve() if args.input else None
    tex_source = args.tex_source.resolve() if args.tex_source else None

    batch_dir = args.batch_dir.resolve() if args.batch_dir else None
    if batch_dir or (input_path and input_path.is_dir()):
        if args.output_html:
            raise SystemExit("Use --output-dir instead of --output-html in batch mode.")
        if tex_source:
            raise SystemExit("--tex-source is only supported for single-paper mode.")
        run_batch(args, batch_dir or input_path)
        return

    source_for_default_output = tex_source or input_path
    assert source_for_default_output is not None
    output_html = args.output_html
    if output_html is None:
        output_html = source_for_default_output.with_name(f"{output_stem(source_for_default_output)}_sentence_roles.html")
    analyze_one(
        input_path=input_path,
        tex_source=tex_source,
        output_html=output_html,
        model=args.model,
        base_url=args.base_url,
        temperature=args.temperature,
        dry_run=args.dry_run,
        workers=args.workers,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
