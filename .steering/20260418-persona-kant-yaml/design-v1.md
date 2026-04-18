# 設計 — T06 persona-kant-yaml (初回案 v1)

## 実装アプローチ

**「biographical data → YAML の直接アダプタ」**として設計する。
Kuehn 2001 を中心に Kant の伝記事実を 6 件の `cognitive_habit` として列挙し、
各項目に (description / source / flag / mechanism) を記入する。
persona-erre Skill の雛形をそのまま踏襲し、`PersonaSpec` の各フィールドに
保守的に値を埋める。実運用よりも「伝記資料の再現性」を優先する documentary な姿勢。

方針の要点:
1. cognitive_habit は観察可能な行動述語として書く (「散歩する」ではなく
   「15:30±5 分に 60-75 分歩行、帰路に会話なし」)
2. flag は fact / legend / speculative の 3 種を意識的に混ぜる
3. mechanism は認知神経科学の一次論文への簡潔な参照を付す
4. Big Five は Kant 伝記研究での通説的プロフィール
5. `default_sampling` は Kant 的精密さを反映して温度を base より下げる
6. `trigger_zone` は明らかなもの (walk → peripatos) のみ設定、他は None

## 変更対象

### 修正するファイル
- なし

### 新規作成するファイル
- `personas/kant.yaml` — Immanuel Kant のペルソナ YAML
- `tests/test_personas.py` — YAML ロード + `PersonaSpec` 検証 + Kant 固有不変条件

### 削除するファイル
- なし

## YAML 内容 (v1)

```yaml
schema_version: "0.1.0-m2"
persona_id: kant
display_name: Immanuel Kant
era: "1724-1804"

primary_corpus_refs:
  - kuehn2001                               # Kuehn, Kant: A Biography (Cambridge UP)
  - kant_kritik_reine_vernunft_1787
  - kant_kritik_praktischen_vernunft_1788
  - kant_kritik_urteilskraft_1790
  - kant_anthropologie_1798

personality:
  openness: 0.85
  conscientiousness: 0.95
  extraversion: 0.40
  agreeableness: 0.55
  neuroticism: 0.25
  wabi: 0.30
  ma_sense: 0.65

cognitive_habits:
  - description: "15:30±5min, 60-75min walk on the Linden-Allee; no return-conversation"
    source: kuehn2001
    flag: fact
    mechanism: "DMN activation via rhythmic locomotion (Oppezzo & Schwartz 2014); +60% divergent thinking"
    trigger_zone: peripatos

  - description: "Wake at 04:55 by servant Lampe; coffee before any work"
    source: kuehn2001
    flag: fact
    mechanism: "Circadian alignment; protected prefrontal morning window"
    trigger_zone: null

  - description: "Writing window 05:00-07:00; lectures 07:00-09:00; private study 10:00-12:45"
    source: kuehn2001
    flag: fact
    mechanism: "Chronotype discipline; write-first-read-later scheduling"
    trigger_zone: study

  - description: "Midday dinner 13:00-16:00 with 4-9 guests, topic-driven conversation"
    source: kuehn2001
    flag: fact
    mechanism: "Social cognition + postprandial discourse; minimum 'Graces' maximum 'Muses'"
    trigger_zone: agora

  - description: "Never traveled more than ~10 miles from Königsberg in entire life"
    source: kuehn2001
    flag: fact
    mechanism: "Radical local embeddedness; knowledge of the world via reading and correspondence"
    trigger_zone: null

  - description: "Nasal-only breathing during walks to maintain speech silence"
    source: kant_anthropologie_1798
    flag: legend
    mechanism: "Vagal tone modulation via nasal breathing (speculative)"
    trigger_zone: peripatos

preferred_zones:
  - study
  - peripatos
  - agora

default_sampling:
  temperature: 0.65
  top_p: 0.88
  repeat_penalty: 1.10
```

## 既存パターンとの整合性

- persona-erre Skill のルール 1-5 に厳密準拠
- architecture-rules: `schemas.py` 以外の Python コードを追加しない
- python-standards: テストコードで型ヒント・`from __future__ import annotations` 使用
- glossary: agora を Kant の dinner に mapping する (functional equivalent of social discourse)

## テスト戦略

`tests/test_personas.py` に以下を追加:

1. **ロード成功**: `yaml.safe_load("personas/kant.yaml")` → `PersonaSpec.model_validate(...)` が成功
2. **persona_id / display_name**: "kant" / "Immanuel Kant" と一致
3. **schema_version**: `SCHEMA_VERSION` と一致
4. **habits の完全性**: 全 cognitive_habits に description / source / flag / mechanism が揃っている
5. **epistemic 多様性**: flag に `fact` と `legend` が少なくとも 1 件ずつ含まれる
6. **zone の妥当性**: preferred_zones が Zone enum のサブセット、peripatos が含まれる
7. **Kant 固有不変条件**: `conscientiousness >= 0.85`, `openness >= 0.8`
8. **サンプリング妥当性**: temperature ≤ 0.7 (Kant の精密さ)
9. **walk habit の存在**: 少なくとも 1 件の habit に "walk" が含まれる
10. **extra="forbid"**: 未知フィールドが入っていたら ValidationError

## ロールバック計画

- 新規ファイル 2 件のみ。問題があれば `git revert` で単純に戻せる
- 後続 T11 (inference-ollama-adapter) で YAML の読み取りが失敗した場合、
  schema の問題なら T05 を修正、値の問題なら kant.yaml を修正

## v1 の自覚している懸念点

| 懸念 | 内容 |
|---|---|
| documentary 寄り | habit が「伝記事実の列挙」になっており、T11/T12 で LLM が使う時の操作性が低い |
| trigger_zone の活用不足 | 6 habit のうち 3 つが null。せっかくのスキーマ機能を使い切れていない |
| mechanism の粒度が不均一 | 歩行は一次論文付きだが、夕食は薄い |
| legend が 1 件のみ | 時計合わせ逸話 (Heine) 等の有名 legend を落としている |
| サンプリングが保守的 | (0.65, 0.88, 1.10) は Nietzsche や Rikyu と差をつけるには弱い |
| Biography 欠損 | `schemas.py` の `PersonaSpec` には biography サブモデルがないが、YAML に履歴的背景が全く入らず、system prompt 組み立て時に情報不足になる可能性 |

これらを踏まえず、`/reimagine` でゼロから再設計し比較する。
