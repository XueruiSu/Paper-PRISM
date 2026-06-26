# PaperPRISM

PaperPRISM 是一个基于 Codex 的 Research-to-Paper Workflow System，面向 AI 领域研究者，帮助用户把已有研究资产组织、论证并写成可投稿论文。

科研论文写作的难点往往不只是把句子写出来，而是把已有 idea、方法、实验和 related works 组织成一条审稿人能接受的论证链。PaperPRISM 的定位是解决这个“最后一公里”：从研究资产出发，帮助用户完成论文 framing、结构规划、证据检查、正文写作、审稿模拟和修改。

PaperPRISM 适合以下使用场景：

- 已经有研究 idea、方法设计和部分实验结果，但不知道如何组织成一篇完整论文。
- 已经有论文初稿，希望检查 storyline、实验完整性、novelty 风险和 reviewer objections。
- 已经有 LaTeX 草稿，希望重写 introduction、method、experiments 或 related work。
- 准备投稿 CCF-A / 顶会 / SCI 一区，希望在投稿前做 reviewer-style revision。
- 希望把零散实验表格、ablation、analysis 和 limitations 整理成更有说服力的论文表达。

PaperPRISM 能帮助你完成：

- 梳理研究问题、核心 claim、贡献点和证据链。
- 判断研究更适合哪类 paper framing，例如 observation-to-method、model architecture、benchmark、empirical analysis 或 theory-to-algorithm。
- 对照标杆论文轨迹规划章节、段落和论证顺序。
- 检测缺失的 baseline、ablation、analysis、理论依据、motivation 或 limitations。
- 生成或修改论文正文和 LaTeX。
- 模拟审稿意见，并把意见转化为可执行 revision plan。

PaperPRISM 最终目标交付物是：

- `paper.tex`
- `paper.pdf`

使用者不需要手动运行代码，也不需要编辑中间 JSON。你只需要在 Codex 中描述自己的研究材料，并根据 Codex 的少量澄清问题补充关键信息。

## 需要准备什么

你提供的材料越完整，PaperPRISM 能产出的论文越接近可投稿状态。推荐准备：

- 研究 idea：研究问题、应用场景、为什么重要。
- 方法说明：核心 insight、模型/算法/框架设计、和已有方法的区别。
- 实验结果：主结果、baselines、ablation、analysis、效率或鲁棒性实验。
- 相关工作：最接近的论文、你和它们的差异。
- 理论或机制分析：如果论文需要理论保证、解释性分析或设计依据。
- 投稿目标：目标会议/期刊、页数限制、领域风格或模板要求。
- 已有材料：草稿、LaTeX、表格、图、review comments 或实验日志。

如果材料不完整，PaperPRISM 会指出缺口，并给出两类处理方式：要么建议补实验/补分析，要么在论文中降低 claim 强度，避免写出证据不足的结论。

## 快速开始

在本 repo 中与 Codex 交互，直接提供你的研究材料，例如：

- 研究 idea、目标问题和应用场景
- 方法摘要、核心 insight 和算法流程
- 实验结果、baselines、ablations 和 analysis experiments
- related works、理论分析、limitations 或已有论文初稿
- 目标投稿 venue 或写作风格要求

推荐安装方式：

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export PAPERPRISM_HOME="${CODEX_HOME}/paperprism"

mkdir -p "$CODEX_HOME/skills" "$PAPERPRISM_HOME"
cp -R codex_skills/* "$CODEX_HOME/skills/"
cp -R data scripts paperprism_state_templates "$PAPERPRISM_HOME/"
```

示例请求：

```text
使用 PaperPRISM 将这些研究资产整理成一篇 LaTeX 论文，生成 paper.tex / paper.pdf，并进行 reviewer-style revision。
```

Codex 会根据你的材料推进研究理解、论文结构规划、写作、审稿和修改。对于缺失信息，Codex 应优先问少量高价值问题；对于没有证据支持的结果，不应伪造实验、引用、数字或理论结论。

## To 开发者

当前实现采用 Codex-native sentence-slot workflow：

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

正文写作前必须完成 trajectory selection，并生成 `TrajectorySelectionReport.md` 和 `ClozeBlueprint.md`。`ClozeBlueprint.md` 使用 `Section -> Paragraph -> Sentence` 层级，每个 sentence slot 至少包含：

- `sentence_id`
- `sentence_type`
- `evidence_requirement`
- `assigned_agent`
- `status`

sentence status 生命周期固定为：

```text
planned -> drafted -> supported -> verified
```

最终导出前必须满足：

```text
unsupported_sentences == 0
planned_sentences == 0
```

### Codex Skills

PaperPRISM 的主要执行逻辑拆分在 `codex_skills/`。这些 skills 是用户和 PaperPRISM 知识库之间的 Codex-native 执行层：

- `paperprism-orchestrator`：组织完整 PaperPRISM workflow。
- `research-understanding`：访谈用户并整理 ResearchAsset。
- `archetype-identifier`：识别 research archetype 和 framing。
- `trajectory-selector`：检索、排序和选择 exemplar trajectories。
- `logical-template-builder`：把 selected trajectory 转换为 WritingPlan / ClozeBlueprint。
- `claim-evidence-mapper`：维护 claim support status 和 evidence gaps。
- `missing-information-detector`：发现缺失 baseline、ablation、理论依据、动机或 limitation。
- `novelty-evaluator`：评估 closest works、创新性风险和可区分点。
- `experiment-planner`：把 evidence gaps 转换为实验计划，不伪造结果。
- `paper-writer`：根据 ClozeBlueprint 填充 sentence slots 并写 LaTeX。
- `review-simulator`：模拟审稿并生成 revision plan。

这些 skills 依赖 PaperPRISM 的资源库，不只是 `SKILL.md` 文件。安装时需要同时复制：

- `codex_skills/`：Codex 可发现的 skills。
- `data/`：trajectory library、executable archetypes、archetype definitions 和 persuasion strategy library。
- `scripts/`：trajectory 检索、编译、导出和验证辅助脚本。
- `paperprism_state_templates/`：ResearchAsset、ClaimEvidenceMap、ClozeBlueprint 等工作状态模板。

推荐安装方式：

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export PAPERPRISM_HOME="${CODEX_HOME}/paperprism"

mkdir -p "$CODEX_HOME/skills" "$PAPERPRISM_HOME"
cp -R codex_skills/* "$CODEX_HOME/skills/"
cp -R data scripts paperprism_state_templates "$PAPERPRISM_HOME/"
```

安装后重启 Codex。skills 会优先在当前 repo 读取 PaperPRISM 资源；如果当前工作目录不是 PaperPRISM repo，则应从 `$PAPERPRISM_HOME` 读取：

- `$PAPERPRISM_HOME/data/generated_sentence_trajectories.json`
- `$PAPERPRISM_HOME/data/executable_archetypes.json`
- `$PAPERPRISM_HOME/data/archetypes.json`
- `$PAPERPRISM_HOME/data/research_archetype_knowledge_base.json`
- `$PAPERPRISM_HOME/data/persuasion_strategy_library.json`
- `$PAPERPRISM_HOME/scripts/`
- `$PAPERPRISM_HOME/paperprism_state_templates/`

如果使用软链接开发安装，也要同时链接资源目录：

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

### 知识库状态

当前 repo 已包含可执行的论文轨迹基础库：

- `data/generated_sentence_trajectories.json`
  - 107 篇 exemplar paper trajectories
  - 1999 条 section / sentence-type trajectories
- `data/executable_archetypes.json`
  - 9 个 executable research archetypes
  - 7 个 archetype 已达到 complete 覆盖
  - 2 个 archetype 仍为 partial 覆盖
- `data/archetypes.json`
  - archetype 定义、适用条件和写作结构
- `data/research_archetype_knowledge_base.json`
  - research archetype 调研知识库
- `data/persuasion_strategy_library.json`
  - persuasion strategy / subtype 支持库

当前 executable archetype 覆盖情况：

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

### 工作状态文件

PaperPRISM 可在项目目录中维护少量人类可读的工作文件。这些文件是 Codex 的内部状态，不是最终交付物：

- `ResearchAsset.md`：研究资产整理。
- `ClaimEvidenceMap.md`：claim、证据、缺口和降级策略。
- `WritingPlan.md`：章节计划、写作顺序和补充材料。
- `TrajectorySelectionReport.md`：trajectory top-k 检索、排序、选择和拒绝理由。
- `ClozeBlueprint.md`：章节、段落和 sentence slots。
- `AgentTaskContract.md`：delegated task 的输入、输出和验收标准。
- `AgentRuntimeLedger.md`：agent 输出、retry、merge 和 issue 记录。
- `PaperState.md`：稿件状态、review issues、LaTeX 编译状态和下一步动作。

模板位于 `paperprism_state_templates/`。

### 离线脚本

`scripts/` 中的脚本用于离线资料建设、检索和验证：

- `analyze_pdf_sentence_roles_llm.py`：分析论文 sentence roles。
- `build_sentence_trajectory_library.py`：从 annotation reports 构建 trajectory library。
- `export_executable_archetypes.py`：从 trajectory library 导出 executable archetypes。
- `trajectory_library.py`：加载、校验和检索 trajectory library。
- `trajectory_compiler.py`：将 selected trajectory 编译为 ClozeBlueprint payload。
- `archetype_recommender.py`：确定性 archetype 推荐辅助。
- `agent_runtime.py` / `workflow_validator.py`：检查 agent contract、runtime state 和 final export gate。

这些脚本服务于 PaperPRISM 内部，不要求最终用户直接调用。

### 构建专属 PaperPRISM

开发者可以用 `scripts/` 中的离线脚本构建自己的论文库，让 PaperPRISM 更贴合特定领域、课题组方向或目标 venue。推荐思路是：收集一批你认可的 exemplar papers，抽取 sentence roles，挖掘 trajectory library，然后把生成的 `data/` 资源安装到 `$PAPERPRISM_HOME`。

适合构建专属库的场景：

- 你的研究领域和默认 AI exemplar library 差异较大。
- 你希望 PaperPRISM 模仿某个会议、期刊、课题组或导师偏好的论文结构。
- 你希望把内部高质量论文、accepted papers 或特定 benchmark 论文沉淀成可复用写作轨迹。
- 你希望为某个 research archetype 补足 exemplar coverage，例如 `new_task_formulation` 或 `comparative_analysis`。

推荐数据量：

- 小规模定制：10-20 篇高质量论文，适合单一方向或单一 archetype。
- 中等规模定制：30-60 篇论文，适合覆盖一个子领域的多种写作范式。
- 完整领域库：100 篇左右论文，适合构建稳定的多 archetype trajectory library。

本地 PDF 路径：

```bash
mkdir -p data/custom_papers/pdfs
# 将你的 PDF 放入 data/custom_papers/pdfs/

python -m scripts.prepare_pdf_batch_manifest \
  --pdf-dir data/custom_papers/pdfs \
  --output data/custom_papers/manifest.json \
  --infer-titles
```

如果你有 arXiv metadata seed，可以先批量下载 PDF 和 TeX source。seed JSON 可参考 `data/metadata_overrides/pdfs_0624_seed_metadata.json`：

```bash
python -m scripts.download_arxiv_batch \
  --metadata data/metadata_overrides/my_seed_metadata.json \
  --output-dir data/custom_papers/arxiv_downloads \
  --manifest data/custom_papers/arxiv_downloads/manifest.json
```

对 PDF 或 TeX source 做 sentence role annotation：

```bash
python -m scripts.analyze_pdf_sentence_roles_llm \
  data/custom_papers/pdfs \
  --output-dir data/custom_papers/sentence_role_reports \
  --workers 4
```

如果只想验证解析和报告生成，不调用 LLM：

```bash
python -m scripts.analyze_pdf_sentence_roles_llm \
  data/custom_papers/pdfs \
  --output-dir data/custom_papers/sentence_role_reports \
  --dry-run
```

建议为自定义论文准备 metadata overrides，用来补充 title、venue、year、domain、contribution_type、research_archetype 和 secondary_archetypes。这样生成的 trajectory 更容易被 `trajectory-selector` 正确检索和排序：

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

构建或合并 trajectory library：

```bash
python -m scripts.build_sentence_trajectory_library \
  --reports-dir data/custom_papers/sentence_role_reports \
  --manifest data/custom_papers/manifest.json \
  --metadata-overrides data/metadata_overrides/my_seed_metadata.json \
  --base-library data/generated_sentence_trajectories.json \
  --output data/generated_sentence_trajectories.json
```

如果你想生成完全独立的专属库，而不是合并默认库，可以去掉 `--base-library`，并把输出写到新的资源目录：

```bash
python -m scripts.build_sentence_trajectory_library \
  --reports-dir data/custom_papers/sentence_role_reports \
  --manifest data/custom_papers/manifest.json \
  --metadata-overrides data/metadata_overrides/my_seed_metadata.json \
  --output data/my_paperprism/generated_sentence_trajectories.json
```

同步 executable archetypes：

```bash
python -m scripts.export_executable_archetypes \
  --archetypes data/archetypes.json \
  --trajectories data/generated_sentence_trajectories.json \
  --output data/executable_archetypes.json
```

最后，把定制后的资源安装到 PaperPRISM resource root：

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export PAPERPRISM_HOME="${CODEX_HOME}/paperprism"

mkdir -p "$PAPERPRISM_HOME"
cp -R data scripts paperprism_state_templates "$PAPERPRISM_HOME/"
```

安装后，PaperPRISM skills 会从当前 repo 或 `$PAPERPRISM_HOME` 读取你的自定义 trajectory library。对于团队内部版本，建议把定制后的 `data/`、`scripts/` 和 `paperprism_state_templates/` 固化到单独分支或内部仓库中，形成专属 PaperPRISM。

### 更新轨迹库

新增 sentence role annotation reports 后，可以把它们合并进主轨迹库：

```bash
python -m scripts.build_sentence_trajectory_library \
  --reports-dir data/archetype_papers/pdfs_0624_sentence_role_reports \
  --manifest data/archetype_papers/pdfs_0624_sentence_role_reports/batch_manifest.json \
  --metadata-overrides data/metadata_overrides/pdfs_0624_seed_metadata.json \
  --base-library data/generated_sentence_trajectories.json \
  --output data/generated_sentence_trajectories.json
```

然后同步 executable archetypes：

```bash
python -m scripts.export_executable_archetypes
```

### 测试

开发者可运行：

```bash
python -m unittest discover -s tests
```

当前测试覆盖：

- trajectory library validation 和 top-k retrieval；
- trajectory-to-ClozeBlueprint compilation；
- sentence status lifecycle；
- agent task contract、output envelope、runtime transition、retry / merge gate 和 quality scoring；
- orchestrator boundary / final export gate；
- archetype recommendation engine。

## Citation

如果 PaperPRISM 对你的研究写作、论文结构设计或实验论证有帮助，请引用本项目：

```bibtex
@software{paperprism2026,
  title        = {PaperPRISM: A Codex-Native Research-to-Paper Workflow System},
  author       = {Xuerui Su, Zonglin Li and Zun Wang},
  year         = {2026},
  url          = {https://github.com/XueruiSu/PaperPRISM},
  note         = {Codex-native workflow system for research asset understanding, sentence-level trajectory planning, paper writing, and review simulation}
}
```



