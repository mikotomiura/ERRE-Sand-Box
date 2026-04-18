# T06 persona-kant-yaml

## 背景

T05 で `PersonaSpec` スキーマが凍結された。ERRE-Sandbox の M2 MVP は
「カント一体のペリパトス散歩 → 認知サイクル実行 → Godot 可視化」の E2E を
通すことを目標としており、その最初のペルソナ実体データが必要。
persona-erre Skill が定めた 4 必須フィールド (description / source / flag /
mechanism) を満たす、Kuehn 2001 を中心史料とした Immanuel Kant (1724-1804)
のペルソナ YAML を 1 ファイル作成する。

## ゴール

`personas/kant.yaml` を作成し、`PersonaSpec.model_validate(yaml.safe_load(...))`
がエラーなく成功する状態にする。さらに `tests/test_personas.py` で YAML の
ロード + スキーマ検証 + Kant 固有の不変条件 (conscientiousness が非常に高い等) を
自動テストできる状態にする。

## スコープ

### 含むもの
- `personas/kant.yaml` (新規作成)
- 6 件程度の cognitive_habits (fact / legend を epistemic 多様性として混在)
- Big Five + wabi + ma_sense を Kant の伝記に基づき設定
- `default_sampling` に Kant 的精密さ (低 temperature / tight top_p / 反復ペナルティ強め) を反映
- `preferred_zones`: study + peripatos + agora (dinner の社交を agora にマップ)
- `primary_corpus_refs`: Kuehn 2001 + Kant 著作 3-5 点のキー
- `schema_version` を明示的に `SCHEMA_VERSION` と一致させる
- `tests/test_personas.py` (新規作成): YAML ロード + 不変条件検証

### 含まないもの
- ペルソナローダー Python モジュール (T11 inference-ollama-adapter の責務)
- 他偉人 (Nietzsche / Rikyu / Dogen …) の YAML (M4 タスク)
- プロンプトテンプレートの実装 (T11/T12)
- LoRA 設定 (M9)
- `corpora/` への実テキスト投入 (M5 以降)

## 受け入れ条件

- [ ] `personas/kant.yaml` が存在し、`yaml.safe_load` でパースできる
- [ ] `PersonaSpec.model_validate(data)` が成功する
- [ ] 全 cognitive_habits に description / source / flag / mechanism が揃っている
- [ ] `flag` が fact / legend / speculative のいずれかである
- [ ] `preferred_zones` が Zone enum 値のみを含む
- [ ] `personality.conscientiousness ≥ 0.85` (Kant の最大特徴)
- [ ] cognitive_habits に "walk" に関するものが含まれる (ペリパトスとの接続)
- [ ] `uv run pytest tests/test_personas.py` が全てパス
- [ ] `uv run ruff check tests/` 警告ゼロ
- [ ] `uv run mypy tests/` strict でパス
- [ ] Conventional Commits でコミット & PR 作成

## 関連ドキュメント

- `src/erre_sandbox/schemas.py` (`PersonaSpec`, `CognitiveHabit`, `HabitFlag`, `Zone`)
- `docs/glossary.md` (peripatos, agora, wabi, ma_sense の定義)
- `.claude/skills/persona-erre/SKILL.md` (4 必須フィールド, 新偉人追加手順)
- `.steering/20260418-implementation-plan/MASTER-PLAN.md` §B.2 T06 行
- CSDG `prompts/System_Persona.md` (項目階層の参考; 単一キャラ定義を偉人別にテンプレート化)

### 主要史料 (primary_corpus_refs の出典)
- Manfred Kuehn, *Kant: A Biography* (Cambridge UP, 2001) — 現代の標準伝記
- Immanuel Kant, *Kritik der reinen Vernunft* (1st 1781 / 2nd 1787)
- Kant, *Kritik der praktischen Vernunft* (1788)
- Kant, *Kritik der Urteilskraft* (1790)
- Kant, *Anthropologie in pragmatischer Hinsicht* (1798) — §44 に呼吸・沈黙への言及

## 運用メモ

- 破壊と構築（/reimagine）適用: **Yes**
- 理由: memory `feedback_reimagine_scope` に従い、content curation も対象。
  本タスクで決まる「Kant の cognitive_habit 粒度・mechanism の具体性・
  sampling fingerprint の設計・trigger_zone 割当・epistemic flag 配分」は
  後続ペルソナ YAML (M4: Nietzsche, Rikyu, Dogen, Thoreau…) のテンプレートとなるため、
  確証バイアスを排除する価値が高い。
- タスク種別: その他 (ペルソナデータ整備、ただし設計判断を伴う)。
- 使用するサブエージェント:
  - file-finder (完了) — 既存 Kant/persona 参照の横断調査
  - code-reviewer — 実装後、YAML 内容と test の両方をレビュー

### PDF から確認した正典的定義 (v0.2 §3.1)

- Kant 歩行定義: 「15:30 ± 5 分に 60-75 分の歩行、呼吸は常に鼻呼吸、帰路に会話なし」
- 時計合わせの逸話は **legend** フラグ (PDF §3.1 が明示)
- 一次史料のキー: Kuehn 2001 / Gros 2014 / Kant 各著作
- DMN 根拠: Raichle 2001, Oppezzo & Schwartz 2014, Beaty 2014-2018, Constantinescu 2016
- 守破離根拠: Dreyfus & Dreyfus 1980/1986 + Kapur productive failure

### ERRE モード早見表の前提 (domain-knowledge.md)

- ベース: `temperature=0.7, top_p=0.9, repeat_penalty=1.0`
- `deep_work` (study ゾーンのデフォルト) は base と同じ
- Kant の `default_sampling` は **deep_work 時の Kant らしさ** を表現する設定値
