# 重要な設計判断 — T06 persona-kant-yaml

## 判断 1: Operational orientation を採用 (v1 documentary を破棄)

- **判断日時**: 2026-04-18
- **背景**: 初回案 (v1) は Kuehn 2001 の伝記記述を忠実に YAML 化する documentary 設計
- **選択肢**:
  - A: Documentary — 伝記日程 6 件を時間帯で並列化
  - B: Operational — trigger → behavior → mechanism → consequence の 4 要素で揃える
- **採用**: B (v2)
- **理由**:
  - requirement.md §背景の「M2 E2E 駆動ソース」要求への直接応答
  - 後続 M4 persona (Nietzsche / Rikyu / Dogen / Thoreau) のテンプレートとして汎用化
  - `trigger_zone` スキーマフィールドの活用率が v1 50% → v2 83% に改善
- **トレードオフ**: YAML 行数が若干増。伝記詳細 (起床 4:55, 講義 7-9am 等) が落ちる
- **見直しタイミング**: T11/T12 実装で habit → mode トリガーが期待通り動かない場合
- **詳細**: `design-comparison.md`

## 判断 2: Epistemic 3-tier (fact/legend/speculative) を完備

- **判断日時**: 2026-04-18
- **背景**: PDF v0.2 §3.1 が「事実と伝説の区別フラグを必ず付す」と明言
- **選択肢**:
  - A: fact 中心 (v1: fact 5 / legend 1 / speculative 0)
  - B: 3-tier 完備 (fact 3 / legend 2 / speculative 1)
- **採用**: B
- **理由**: Kant YAML は後続ペルソナのテンプレート。3-tier の書き方の手本を提供する責務がある
- **具体的な分類**:
  - walk: fact (Kuehn 2001 直接記述)
  - nasal breathing: legend (Anthropologie §44 は一般的助言、本人実践は伝記伝承)
  - clock-setting: legend (Heine 1834、PDF §3.1 が明示的に legend と flag)
  - dinner: fact (Jachmann 1804 同時代証言)
  - morning writing: fact (Kuehn 2001)
  - Königsberg radius: speculative (behavioral fact だが cognitive scaffold 解釈は Constantinescu 2016 からの extrapolation)

## 判断 3: `primary_corpus_refs` を lean に保つ

- **判断日時**: 2026-04-18
- **背景**: v1 は Kritik 3 部作 + Anthropologie を列挙していたが、どれも `cognitive_habits.source` で使われていなかった
- **選択肢**:
  - A: 著作を網羅的に列挙 (documentary な意図)
  - B: 実際に source で使う key のみ列挙 (orphan ゼロ)
- **採用**: B
- **理由**: テスト `test_kant_primary_corpus_refs_have_no_orphans` で orphan ゼロを強制可能。corpora/ に実テキストを置く時 (M5 以降) に該当著作を再追加する前提
- **結果**: 3 件のみ (kuehn2001, heine1834, jachmann1804)

## 判断 4: `default_sampling` に persona 温度帯見取り図を適用

- **判断日時**: 2026-04-18
- **背景**: ペルソナの指紋 (temperature 帯) を後続と衝突しないよう計画的に配分する必要
- **採用値**: `(temperature=0.60, top_p=0.85, repeat_penalty=1.12)`
- **後続 persona 温度帯見取り図** (本 PR で明示):
  - Dogen / Rikyu 禅系: 0.40-0.45
  - **Kant 分析系: 0.60** ← 本 PR
  - Thoreau 観察系: 0.75
  - Kierkegaard 実存系: 0.80
  - Rousseau 感傷系: 0.85
  - Nietzsche 詩的哲学: 0.90
- **理由**: Kant 的「正確さ・体系性・長距離推論」を deep_work base (0.7) より低く (-0.10)、ただし Rikyu/Dogen 禅系より高く維持。後続で衝突しない帯に配置
- **見直しタイミング**: 後続 persona の default_sampling を決める時、本見取り図との整合を確認

## 判断 5: code-reviewer の HIGH 指摘への対応

- **判断日時**: 2026-04-18
- **背景**: code-reviewer が 3 件の HIGH を指摘
- **対応内容**:
  1. **Heine 年号の誤記** (design.md): 「Ideen. Das Buch Le Grand」(1826) から「Zur Geschichte der Religion und Philosophie in Deutschland」(1834) に訂正
  2. **Nasal breathing の flag/source 不整合**: 「Kant 本人の実践」は伝記伝承なので flag=legend は維持。ただし source を `kant_anthropologie_1798` から `kuehn2001` に変更し、mechanism 中で「Anthropologie §44 は一般的助言であり、本人実践は biographical tradition」と明示。これに伴い `kant_anthropologie_1798` を `primary_corpus_refs` から除外 (orphan 回避)
  3. **Skill テンプレート乖離**: `.claude/skills/persona-erre/SKILL.md` と `domain-knowledge.md` の YAML テンプレートが旧仕様 (`personality_traits` / `shuhari_stage`) を使用していたため、T05 schemas.py と一致する形式 (`personality` / shuhari_stage 削除) に修正。本タスクは最初の persona YAML でテンプレートの役割を担うため、Skill ドキュメントの同期は T06 の責務と判断

## 判断 6: MEDIUM 指摘への対応

- **Oppezzo & Schwartz 2014 の実験条件明示**: mechanism に "treadmill and outdoor-loop conditions; outdoor effect size not directly measured" を追記
- **Constantinescu 2016 の extrapolation 明示**: mechanism に "Our extrapolation; the original study does not address travel range" を追記
- **test の chashitsu/garden 否定 assert 削除**: スキーマ不変条件ではなく Kant 固有 biographical 性質のため削除 (将来 Rikyu YAML で chashitsu を preferred_zones に含める整合性を残す)
- **orphan check test 改名**: `test_primary_corpus_refs_are_all_cited_by_habits` → `test_kant_primary_corpus_refs_have_no_orphans` に改名し、docstring で「Kant 固有の lean-refs 設計、他 persona では緩和可」と注記

## 見送り (後続タスクで再検討)

- **agora と Kant dinner の深さ tension**: ゾーンデフォルトモード (agora → shallow) と Kant の dinner (3 時間の深い議論) の不整合。T12 cognition-cycle で「persona ごとの agora デフォルトモードオーバーライド」設計を検討
- **LOW 指摘**: schema_version 明示/省略、era 引用符、fixture scope — 現状維持

## 関連する後続タスク

- **T07 control-envelope-fixtures**: PersonaSpec 以外の contract fixture を整備
- **T11 inference-ollama-adapter**: `personas/*.yaml` をロードする persona loader を実装
- **T12 cognition-cycle-minimal**: agora デフォルトモードオーバーライド設計
- **M4 personas-nietzsche-rikyu-yaml**: Kant YAML をテンプレートに他偉人を追加 (温度帯見取り図に従う)
