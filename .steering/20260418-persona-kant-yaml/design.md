# 設計 — T06 persona-kant-yaml (再生成案 v2)

## 実装アプローチ

YAML を「Kant の伝記を整理した書類」ではなく、
**「Kant を演じる LLM + 状態機械に渡す操作的仕様」** として設計する。
要件の背景にある「M2 E2E = peripatos 散歩 → 認知サイクル → Godot 可視化」を
直接駆動できるよう、各 `cognitive_habit` を

> **observable trigger → behavior → mechanism → cognitive consequence**

の 4 要素で読める operational な記述に揃える。
v2 の核心は 4 点:

1. **trigger_zone 活用率を最大化する** — 5/6 の habit にゾーンを紐付け、
   スキーマの機能を使い切る。全 null 回避
2. **Epistemic 3-tier を見本化する** — fact / legend / speculative を
   それぞれ最低 1 件含め、後続ペルソナ YAML の参考例として機能させる
3. **`primary_corpus_refs` を実 source に絞る** — `cognitive_habits.source` で
   実際に使うキーのみ列挙し、YAML を lean に保つ
4. **Sampling fingerprint を distinctive にする** — (0.60, 0.85, 1.12) で
   Kant 的精密さを後続 persona (Nietzsche / Rikyu / Dogen) と明確に分ける

## 変更対象

### 修正するファイル
- なし

### 新規作成するファイル
- `personas/kant.yaml` — 本体 YAML
- `tests/test_personas.py` — 6 種の smoke + invariant テスト

### 削除するファイル
- なし

## cognitive_habits の設計 (6 件)

| # | habit | trigger_zone | flag | source | mechanism の骨子 |
|---|---|---|---|---|---|
| 1 | 15:30±5min / 60-75min walk on Linden-Allee, no return conversation | peripatos | fact | kuehn2001 | DMN activation via rhythmic locomotion (Oppezzo & Schwartz 2014) — +60% divergent thinking |
| 2 | Nasal-only breathing during walks, enforcing speech silence | peripatos | legend | kant_anthropologie_1798 | Vagal tone modulation via nasal respiration (mechanism speculative, behaviour claimed by Kant in §44) |
| 3 | Daily walk punctuality; Königsberg townspeople reportedly set clocks by him | peripatos | legend | heine1834 | Community-level temporal anchor; ritualised predictability (PDF §3.1 flags this as legend) |
| 4 | Midday dinner 13:00-16:00 with 4-9 guests; topic-driven, "minimum Graces, maximum Muses" | agora | fact | jachmann1804 | Social cognition + postprandial discourse; limited group size preserves deep conversation |
| 5 | Morning writing window 05:00-07:00 for long-form critique drafting | study | fact | kuehn2001 | Chronotype-aligned prefrontal window for multi-step deductive reasoning |
| 6 | Never travelled >10 miles from Königsberg in his entire life | null (persona-global) | speculative | kuehn2001 | Local embedded spatial memory becomes scaffold for abstract conceptual navigation (Constantinescu et al. 2016, grid-code-on-concept hypothesis) |

- **trigger_zone null 件数**: 1/6 (#6 のみ — persona-global 属性のため)
- **flag 分布**: fact 3 / legend 2 / speculative 1 — 3-tier の見本として均衡

## `personality` の設計

Kant の伝記心理学的プロフィール (Kuehn 2001 に基づく一般的合意):

| 特性 | 値 | 根拠 |
|---|---|---|
| openness | 0.85 | 形而上学・倫理・美学・自然地理・人間学すべて講義、知的広範 |
| conscientiousness | 0.98 | punctuality の逸話化、『純粋理性批判』の 10 年以上の持続プロジェクト |
| extraversion | 0.35 | 親密な 4-9 名 dinner を好む。大人数のパーティーは避ける |
| agreeableness | 0.50 | polite だが principled — 第 2 版への批判に対しても信念を曲げない |
| neuroticism | 0.20 | Kuehn 2001 が "imperturbable" と形容。情緒安定 |
| wabi | 0.25 | Sublime/Beautiful は grandeur の美学、wabi-sabi とは対照的 |
| ma_sense | 0.70 | 帰路の沈黙ルール、nasal breathing による発声抑制 |

## `default_sampling` の設計

**基本方針**: deep_work モードの base (0.7 / 0.9 / 1.0) を Kant 個性で修正。
後続 persona との差別化を **温度帯** で行う。

| 値 | 採用理由 |
|---|---|
| temperature = 0.60 | base より -0.10。Kant 的「正確さ・体系性・長距離推論」を反映。ただし単調にならないよう Rikyu/Dogen (禅系 0.40-0.45) ほどは下げない |
| top_p = 0.85 | base より -0.05。語彙の逸脱を抑える (専門用語の安定) |
| repeat_penalty = 1.12 | base より +0.12。反復を軽く抑制しつつ、用語の一貫性は壊さない |

**後続 persona 温度帯の見取り図 (参考、本タスクのスコープ外)**:
- Dogen / Rikyu 禅系: 0.40-0.45
- Kant 分析系: **0.60** ← 本タスク
- Thoreau 観察系: 0.75
- Kierkegaard 実存系: 0.80
- Nietzsche 詩的哲学: 0.90
- Rousseau 感傷系: 0.85

## `primary_corpus_refs` の設計

`cognitive_habits.source` で実際に参照される 4 キーのみを列挙:

```yaml
primary_corpus_refs:
  - kuehn2001                      # Kuehn, Kant: A Biography (Cambridge UP)
  - kant_anthropologie_1798        # Anthropologie in pragmatischer Hinsicht §44
  - heine1834                      # Heine, "Zur Geschichte der Religion und Philosophie in Deutschland" (1834) — clock-setting legend 源
  - jachmann1804                   # Jachmann, Kant's contemporary biographer
```

Kritik 三部作は本 YAML では source として使われないため除外。corpora/ に実テキストを
入れる時に本 YAML にも追加する方針 (M5 以降)。

## `preferred_zones` の設計

Kant の日常活動が実際に行われる 3 ゾーン:

```yaml
preferred_zones:
  - study       # 執筆・講義準備・読書
  - peripatos   # 15:30 の散歩 (ペルソナの象徴行動)
  - agora       # dinner の discourse
```

`chashitsu` (茶道) と `garden` (庭園創作) は Kant の伝記にマッピングできない。

## 全体 YAML 構造プレビュー

```yaml
schema_version: "0.1.0-m2"
persona_id: kant
display_name: Immanuel Kant
era: "1724-1804"
primary_corpus_refs: [kuehn2001, kant_anthropologie_1798, heine1834, jachmann1804]
personality: { openness: 0.85, conscientiousness: 0.98, ... ma_sense: 0.70 }
cognitive_habits:
  - { description: ..., source: kuehn2001, flag: fact, mechanism: ..., trigger_zone: peripatos }
  - ... (計 6 件)
preferred_zones: [study, peripatos, agora]
default_sampling: { temperature: 0.60, top_p: 0.85, repeat_penalty: 1.12 }
```

## テスト戦略 (`tests/test_personas.py`)

1. **YAML ロード**: `yaml.safe_load` → `PersonaSpec.model_validate` 成功
2. **schema_version 整合**: `SCHEMA_VERSION == "0.1.0-m2"` と一致
3. **Kant 固有 invariant**:
   - persona_id == "kant"
   - display_name == "Immanuel Kant"
   - conscientiousness >= 0.85 (受け入れ条件)
   - openness >= 0.80
4. **cognitive_habits の invariants**:
   - ≥ 5 件
   - 全件で source / flag / mechanism / description が truthy
   - "walk" が description に含まれる habit が ≥ 1 (受け入れ条件)
5. **Epistemic 3-tier 見本**: flag の集合が fact と legend を含む
   (speculative は本 YAML にあるが、将来ペルソナで無い場合を許容する緩い assert)
6. **trigger_zone の健全性**: null でないものは Zone enum の値
7. **preferred_zones**: peripatos が含まれる、全てが Zone enum
8. **default_sampling**: temperature ≤ 0.70 (Kant 精密性を数値で担保)
9. **extra="forbid" の効き**: YAML に未知キーを足した dict で reject される

## 既存パターンとの整合性

- persona-erre Skill ルール 1-5 に準拠 (description / source / flag / mechanism 必須)
- architecture-rules: `schemas.py` 以外に Python コード追加せず、YAML データのみ
- python-standards: `tests/test_personas.py` は `from __future__ import annotations` + 型ヒント + f-string
- glossary: agora を Kant の dinner に functional mapping (文書化済み)
- repository-structure §1: YAML は `personas/` 配下、テストは `tests/` 配下

## 既存コードへの影響範囲

- `src/erre_sandbox/` 下のコードへの変更は **ゼロ**
- `pyproject.toml` の依存 (pyyaml) は T04 で既に入っている (確認済み)
- `tests/conftest.py` への変更は不要 (直接ファイルパスを使う)

## ロールバック計画

- 新規ファイル 2 件のみ。問題があれば `git revert` 単発で完全に戻せる
- YAML の値に誤りが見つかった場合、followup PR で修正 (T06 自体のロールバックは不要)

## 懸念とその対処

| 懸念 | 対処 |
|---|---|
| heine1834 / jachmann1804 は実際の史料キーとしては未確定 | 将来 corpora/ に実テキスト配置時に命名規約を整備。本 PR は「このキーが後続で参照される」という表明 |
| speculative #6 の mechanism (Constantinescu 2016) は Kant に対する仮説 | description 末尾に "(interpretation)" を添えず、mechanism 側で "hypothesis" と明示する |
| `default_sampling.temperature = 0.60` が deep_work base 0.7 から離れ過ぎていないか | persona の指紋として base ± 0.10 は許容範囲。domain-knowledge の deep_work 既定との関係は T11 で再校正可能 |
| 将来 persona が増えた時に温度帯が衝突 | 本 PR で "persona 温度帯見取り図" を design.md に明記しておく (既記) |
| agora デフォルトモード (shallow) と Kant の dinner (3 時間の深い議論) の tension | `domain-knowledge.md` のゾーン早見表では agora → shallow だが、Kant の midday dinner は "minimum Graces, maximum Muses" で深い議論。T12 cognition-cycle で「persona ごとに agora のデフォルトモードをオーバーライド可能」な設計が必要。本 PR ではフラグとして記録のみ |
| Oppezzo & Schwartz 2014 の実験条件 | +60% の divergent thinking は treadmill + outdoor-loop 条件。屋外での 60 分歩行に対する効果量は同論文では直接測定されていないため、YAML の mechanism にその旨を明記 |
| Constantinescu 2016 の適用範囲 | 同論文は「概念空間のグリッドコード」を示したが、「旅行しないこと」が「概念推論の scaffold」になるとは論文は主張していない。YAML で "our extrapolation" と明記 |

## 設計判断の履歴

- 初回案（design-v1.md）と再生成案（v2）を `design-comparison.md` で比較
- 採用: **v2（再生成案）**
- 根拠: requirement.md §背景の「M2 E2E 駆動ソース」要求への直接応答、後続 M4
  persona (Nietzsche / Rikyu / Dogen) のテンプレート効果、PDF §3.1 の 3-tier
  epistemic flag 要求に対する見本化、`trigger_zone` スキーマ意図の尊重。
  ハイブリッドは v1 の「Kritik 全列挙」と v2 の lean 原則が相反するため不採用。
