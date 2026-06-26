# PaperPRISM

PaperPRISM is a Codex-native Research-to-Paper Workflow System for AI researchers. It helps users organize existing research assets, build a defensible scientific argument, and turn the work into a submission-ready paper.

Writing a research paper is rarely just a matter of producing polished sentences. The hard part is turning ideas, methods, experiments, and related work into an argument chain that reviewers can accept. PaperPRISM targets this "last mile" of research writing: starting from research assets, it helps users complete paper framing, structure planning, evidence checking, manuscript writing, review simulation, and revision.

PaperPRISM is suitable when:

- You already have a research idea, method design, and partial experimental results, but need help organizing them into a complete paper.
- You already have a draft and want to check its storyline, experimental completeness, novelty risks, and likely reviewer objections.
- You already have a LaTeX draft and want to rewrite the introduction, method, experiments, or related work.
- You are preparing for a CCF-A, top-tier conference, or SCI Q1 journal submission and want reviewer-style revision before submission.
- You want to turn scattered experiment tables, ablations, analyses, and limitations into a more persuasive paper narrative.

PaperPRISM can help you:

- Clarify the research problem, core claims, contributions, and evidence chain.
- Identify the paper framing that best fits the work, such as observation-to-method, model architecture, benchmark, empirical analysis, or theory-to-algorithm.
- Plan sections, paragraphs, and argument order by comparing against exemplar paper trajectories.
- Detect missing baselines, ablations, analyses, theoretical justification, motivation, or limitations.
- Generate or revise paper prose and LaTeX.
- Simulate reviewer feedback and convert it into an executable revision plan.

The final target deliverables are:

- `paper.tex`
- `paper.pdf`

Users do not need to run code manually or edit intermediate JSON files. You only need to describe your research materials in Codex and answer a small number of high-value clarification questions when needed.

## What To Prepare

The more complete your materials are, the closer PaperPRISM can get to a submission-ready paper. Recommended inputs include:

- Research idea: the research problem, application scenario, and why it matters.
- Method description: the core insight, model, algorithm, framework design, and difference from prior methods.
- Experimental results: main results, baselines, ablations, analyses, efficiency, or robustness experiments.
- Related work: the closest papers and how your work differs from them.
- Theory or mechanism analysis: if the paper needs theoretical guarantees, interpretability analysis, or design justification.
- Submission target: target conference or journal, page limit, field style, or template requirements.
- Existing materials: draft, LaTeX, tables, figures, review comments, or experiment logs.

If the materials are incomplete, PaperPRISM should identify the gaps and suggest one of two paths: add experiments or analyses, or weaken the claims in the paper to avoid unsupported conclusions.

## Quick Start

Interact with Codex inside this repository and provide your research materials directly, for example:

- Research idea, target problem, and application scenario.
- Method summary, core insight, and algorithmic process.
- Experimental results, baselines, ablations, and analysis experiments.
- Related works, theoretical analysis, limitations, or an existing draft.
- Target venue or writing style requirements.

Example request:

```text
Use PaperPRISM to organize these research assets into a LaTeX paper, generate paper.tex / paper.pdf, and perform reviewer-style revision.
```

Codex will use your materials to proceed through research understanding, paper structure planning, writing, review, and revision. For missing information, Codex should ask a small number of high-value questions first. It must not fabricate experiments, citations, numbers, or theoretical conclusions when evidence is missing.

## For Developers

The current implementation uses a Codex-native sentence-slot workflow:

```text
Research Assets
    ↓
Research Understanding
    ↓
Archetype Identification
    ↓
Trajectory Retrieval and Selection
    ↓
Cloze Blueprint Generation
    ↓
Sentence Slot Filling
    ↓
Claim-Evidence Verification
    ↓
Review Simulation
    ↓
LaTeX / PDF Export
```

Trajectory selection must be completed before manuscript prose writing, and PaperPRISM must generate `TrajectorySelectionReport.md` and `ClozeBlueprint.md`. `ClozeBlueprint.md` uses the hierarchy `Section -> Paragraph -> Sentence`. Each sentence slot should include at least:

- `sentence_id`
- `sentence_type`
- `evidence_requirement`
- `assigned_agent`
- `status`

The sentence status lifecycle is fixed:

```text
planned -> drafted -> supported -> verified
```

Final export requires:

```text
unsupported_sentences == 0
planned_sentences == 0
```

### Codex Skills

PaperPRISM's main execution logic is split across `codex_skills/`. These skills are the Codex-native execution layer between users and the PaperPRISM knowledge base:

- `paperprism-orchestrator`: coordinates the full PaperPRISM workflow.
- `research-understanding`: interviews the user and normalizes the ResearchAsset.
- `archetype-identifier`: identifies the research archetype and paper framing.
- `trajectory-selector`: retrieves, ranks, and selects exemplar trajectories.
- `logical-template-builder`: converts the selected trajectory into a WritingPlan / ClozeBlueprint.
- `claim-evidence-mapper`: maintains claim support status and evidence gaps.
- `missing-information-detector`: finds missing baselines, ablations, theory, motivation, or limitations.
- `novelty-evaluator`: evaluates closest works, novelty risks, and differentiators.
- `experiment-planner`: converts evidence gaps into experiment plans without fabricating results.
- `paper-writer`: fills sentence slots and writes LaTeX according to the ClozeBlueprint.
- `review-simulator`: simulates peer review and produces a revision plan.

These skills depend on the PaperPRISM resource library, not only the `SKILL.md` files. Installation should copy:

- `codex_skills/`: skills discoverable by Codex.
- `data/`: trajectory library, executable archetypes, archetype definitions, and persuasion strategy library.
- `scripts/`: helper scripts for trajectory retrieval, compilation, export, and validation.
- `paperprism_state_templates/`: working-state templates such as ResearchAsset, ClaimEvidenceMap, and ClozeBlueprint.

Recommended installation:

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export PAPERPRISM_HOME="${CODEX_HOME}/paperprism"

mkdir -p "$CODEX_HOME/skills" "$PAPERPRISM_HOME"
cp -R codex_skills/* "$CODEX_HOME/skills/"
cp -R data scripts paperprism_state_templates "$PAPERPRISM_HOME/"
```

Restart Codex after installation. Skills first read PaperPRISM resources from the current repository. If the current working directory is not the PaperPRISM repository, they should read from `$PAPERPRISM_HOME`:

- `$PAPERPRISM_HOME/data/generated_sentence_trajectories.json`
- `$PAPERPRISM_HOME/data/executable_archetypes.json`
- `$PAPERPRISM_HOME/data/archetypes.json`
- `$PAPERPRISM_HOME/data/research_archetype_knowledge_base.json`
- `$PAPERPRISM_HOME/data/persuasion_strategy_library.json`
- `$PAPERPRISM_HOME/scripts/`
- `$PAPERPRISM_HOME/paperprism_state_templates/`

For symlink-based development installation, link both skills and resource directories:

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export PAPERPRISM_HOME="${CODEX_HOME}/paperprism"

mkdir -p "$CODEX_HOME/skills" "$PAPERPRISM_HOME"
ln -s "$PWD/codex_skills/paperprism-orchestrator" "$CODEX_HOME/skills/paperprism-orchestrator"
ln -s "$PWD/codex_skills/research-understanding" "$CODEX_HOME/skills/research-understanding"
ln -s "$PWD/codex_skills/archetype-identifier" "$CODEX_HOME/skills/archetype-identifier"
ln -s "$PWD/codex_skills/trajectory-selector" "$CODEX_HOME/skills/trajectory-selector"
ln -s "$PWD/codex_skills/logical-template-builder" "$CODEX_HOME/skills/logical-template-builder"
ln -s "$PWD/codex_skills/claim-evidence-mapper" "$CODEX_HOME/skills/claim-evidence-mapper"
ln -s "$PWD/codex_skills/missing-information-detector" "$CODEX_HOME/skills/missing-information-detector"
ln -s "$PWD/codex_skills/novelty-evaluator" "$CODEX_HOME/skills/novelty-evaluator"
ln -s "$PWD/codex_skills/experiment-planner" "$CODEX_HOME/skills/experiment-planner"
ln -s "$PWD/codex_skills/paper-writer" "$CODEX_HOME/skills/paper-writer"
ln -s "$PWD/codex_skills/review-simulator" "$CODEX_HOME/skills/review-simulator"
ln -s "$PWD/codex_skills/_shared" "$CODEX_HOME/skills/_shared"
ln -s "$PWD/data" "$PAPERPRISM_HOME/data"
ln -s "$PWD/scripts" "$PAPERPRISM_HOME/scripts"
ln -s "$PWD/paperprism_state_templates" "$PAPERPRISM_HOME/paperprism_state_templates"
```

### Knowledge Base Status

This repository already contains an executable paper trajectory base:

- `data/generated_sentence_trajectories.json`
  - 107 exemplar paper trajectories.
  - 1999 section / sentence-type trajectories.
- `data/executable_archetypes.json`
  - 9 executable research archetypes.
  - 7 archetypes with complete coverage.
  - 2 archetypes with partial coverage.
- `data/archetypes.json`
  - Archetype definitions, applicability conditions, and writing structures.
- `data/research_archetype_knowledge_base.json`
  - Research archetype investigation knowledge base.
- `data/persuasion_strategy_library.json`
  - Persuasion strategy / subtype support library.

Current executable archetype coverage:

| Archetype | Exemplars | Status |
| --- | ---: | --- |
| `observation_to_method` | 16 | complete |
| `theory_to_algorithm` | 11 | complete |
| `algorithm_theoretical_analysis` | 10 | complete |
| `framework_unification` | 17 | complete |
| `benchmark_dataset` | 19 | complete |
| `empirical_analysis` | 11 | complete |
| `model_architecture_design` | 15 | complete |
| `new_task_formulation` | 5 | partial |
| `comparative_analysis` | 3 | partial |

### Working State Files

PaperPRISM may maintain a small number of human-readable working files in a project directory. These files are Codex internal state, not final deliverables:

- `ResearchAsset.md`: normalized research assets.
- `ClaimEvidenceMap.md`: claims, evidence, gaps, and claim weakening strategy.
- `WritingPlan.md`: section plan, writing order, and additional materials.
- `TrajectorySelectionReport.md`: top-k trajectory retrieval, ranking, selection, and rejection rationale.
- `ClozeBlueprint.md`: sections, paragraphs, and sentence slots.
- `AgentTaskContract.md`: delegated task inputs, outputs, and acceptance criteria.
- `AgentRuntimeLedger.md`: agent outputs, retries, merges, and issue records.
- `PaperState.md`: manuscript status, review issues, LaTeX compilation status, and next actions.

Templates are stored in `paperprism_state_templates/`.

### Offline Scripts

Scripts under `scripts/` are used for offline data construction, retrieval, and validation:

- `analyze_pdf_sentence_roles_llm.py`: analyzes sentence roles in papers.
- `build_sentence_trajectory_library.py`: builds the trajectory library from annotation reports.
- `export_executable_archetypes.py`: exports executable archetypes from the trajectory library.
- `trajectory_library.py`: loads, validates, and retrieves trajectories.
- `trajectory_compiler.py`: compiles a selected trajectory into a ClozeBlueprint payload.
- `archetype_recommender.py`: deterministic archetype recommendation helper.
- `agent_runtime.py` / `workflow_validator.py`: check agent contracts, runtime state, and final export gates.

These scripts serve PaperPRISM internally and are not required for normal end-user use.

### Building A Custom PaperPRISM

Developers can use the offline scripts in `scripts/` to build a custom paper library, making PaperPRISM better aligned with a specific field, research group, or target venue. The recommended process is to collect high-quality exemplar papers, annotate sentence roles, mine a trajectory library, and install the generated `data/` resources into `$PAPERPRISM_HOME`.

Good use cases for a custom library include:

- Your research area differs substantially from the default AI exemplar library.
- You want PaperPRISM to emulate the structure preferred by a specific conference, journal, research group, or advisor.
- You want to turn internal high-quality papers, accepted papers, or benchmark papers into reusable writing trajectories.
- You want to improve exemplar coverage for a specific research archetype, such as `new_task_formulation` or `comparative_analysis`.

Recommended data volume:

- Small customization: 10-20 high-quality papers, suitable for one direction or one archetype.
- Medium customization: 30-60 papers, suitable for covering multiple writing paradigms in a subfield.
- Full field library: around 100 papers, suitable for a stable multi-archetype trajectory library.

Local PDF path:

```bash
mkdir -p data/custom_papers/pdfs
# Put your PDFs under data/custom_papers/pdfs/

python -m scripts.prepare_pdf_batch_manifest \
  --pdf-dir data/custom_papers/pdfs \
  --output data/custom_papers/manifest.json \
  --infer-titles
```

If you have an arXiv metadata seed, you can first download PDFs and TeX sources in batch. See `data/metadata_overrides/pdfs_0624_seed_metadata.json` for a seed JSON example:

```bash
python -m scripts.download_arxiv_batch \
  --metadata data/metadata_overrides/my_seed_metadata.json \
  --output-dir data/custom_papers/arxiv_downloads \
  --manifest data/custom_papers/arxiv_downloads/manifest.json
```

Run sentence role annotation on PDFs or TeX sources:

```bash
python -m scripts.analyze_pdf_sentence_roles_llm \
  data/custom_papers/pdfs \
  --output-dir data/custom_papers/sentence_role_reports \
  --workers 4
```

To only verify parsing and report generation without calling an LLM:

```bash
python -m scripts.analyze_pdf_sentence_roles_llm \
  data/custom_papers/pdfs \
  --output-dir data/custom_papers/sentence_role_reports \
  --dry-run
```

Prepare metadata overrides for custom papers to provide title, venue, year, domain, contribution_type, research_archetype, and secondary_archetypes. This helps `trajectory-selector` retrieve and rank trajectories correctly:

```json
{
  "records": [
    {
      "report_stem": "my_paper_stem",
      "title": "Paper Title",
      "venue": "NeurIPS",
      "year": 2025,
      "domain": "Large Language Models",
      "contribution_type": "Architecture",
      "research_archetype": "model_architecture_design",
      "secondary_archetypes": ["empirical_analysis"]
    }
  ]
}
```

Build or merge a trajectory library:

```bash
python -m scripts.build_sentence_trajectory_library \
  --reports-dir data/custom_papers/sentence_role_reports \
  --manifest data/custom_papers/manifest.json \
  --metadata-overrides data/metadata_overrides/my_seed_metadata.json \
  --base-library data/generated_sentence_trajectories.json \
  --output data/generated_sentence_trajectories.json
```

If you want to generate a fully independent custom library instead of merging with the default library, remove `--base-library` and write the output to a new resource directory:

```bash
python -m scripts.build_sentence_trajectory_library \
  --reports-dir data/custom_papers/sentence_role_reports \
  --manifest data/custom_papers/manifest.json \
  --metadata-overrides data/metadata_overrides/my_seed_metadata.json \
  --output data/my_paperprism/generated_sentence_trajectories.json
```

Synchronize executable archetypes:

```bash
python -m scripts.export_executable_archetypes \
  --archetypes data/archetypes.json \
  --trajectories data/generated_sentence_trajectories.json \
  --output data/executable_archetypes.json
```

Finally, install the customized resources into the PaperPRISM resource root:

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export PAPERPRISM_HOME="${CODEX_HOME}/paperprism"

mkdir -p "$PAPERPRISM_HOME"
cp -R data scripts paperprism_state_templates "$PAPERPRISM_HOME/"
```

After installation, PaperPRISM skills read the custom trajectory library from the current repository or `$PAPERPRISM_HOME`. For internal team versions, consider preserving customized `data/`, `scripts/`, and `paperprism_state_templates/` in a separate branch or internal repository.

### Updating The Trajectory Library

After adding new sentence role annotation reports, merge them into the main trajectory library:

```bash
python -m scripts.build_sentence_trajectory_library \
  --reports-dir data/archetype_papers/pdfs_0624_sentence_role_reports \
  --manifest data/archetype_papers/pdfs_0624_sentence_role_reports/batch_manifest.json \
  --metadata-overrides data/metadata_overrides/pdfs_0624_seed_metadata.json \
  --base-library data/generated_sentence_trajectories.json \
  --output data/generated_sentence_trajectories.json
```

Then synchronize executable archetypes:

```bash
python -m scripts.export_executable_archetypes
```

### Tests

Developers can run:

```bash
python -m unittest discover -s tests
```

Current tests cover:

- trajectory library validation and top-k retrieval;
- trajectory-to-ClozeBlueprint compilation;
- sentence status lifecycle;
- agent task contract, output envelope, runtime transition, retry / merge gate, and quality scoring;
- orchestrator boundary / final export gate;
- archetype recommendation engine.

## Citation

If PaperPRISM helps with your research writing, paper structure design, or experimental argumentation, please cite this project:

```bibtex
@software{paperprism2026,
  title        = {PaperPRISM: A Codex-Native Research-to-Paper Workflow System},
  author       = {Xuerui Su, Zonglin Li and Zun Wang},
  year         = {2026},
  url          = {https://github.com/XueruiSu/PaperPRISM},
  note         = {Codex-native workflow system for research asset understanding, sentence-level trajectory planning, paper writing, and review simulation}
}
```
