# m5-llm-spike — dialog_turn LLM プロンプト品質の実機探索

## 背景

M5 では M4 で deferred された `dialog_turn` を LLM で生成する仕組みを正式実装する。
計画策定時点 (`.steering/20260420-m5-planning/decisions.md` 判断 4) で、プロンプト
設計の不確実性 (utterance 長・停止語彙・温度帯・幻覚パターン) を contract freeze より
先に経験的に確定する方針が採られた。

Contract-First で schema を凍結した後にプロンプト不具合が判明すると、`DialogTurnMsg`
の field 追加や `reason` literal 拡張など再度の schema bump が必要になる。そのリスクを
回避するため、throwaway spike として G-GEAR 実機で qwen3:8b に対し Kant ↔ Rikyū の
1-on-1 対話を走らせ、schema 前提となる数値・語彙を事前に確定する。

本タスクは **コード commit しない** (判断 4)。知見のみ `decisions.md` に残す。

## ゴール

`.steering/20260420-m5-llm-spike/decisions.md` に以下 4 項目の経験的判断が
記録されている状態。後続 `m5-contracts-freeze` / `m5-dialog-turn-generator` が
この判断を参照して schema / プロンプトを決定できる:

1. **utterance 長の経験値** — `num_predict=80` で 160 chars 以内に収まるか
2. **停止語彙 (stop tokens)** — stage direction / JSON wrapping / 名前混入を防ぐ tokens
3. **適切な温度帯** — persona.default + ERRE delta が幻覚破綻しない範囲
4. **turn_index 上限** — `dialog_turn_budget=6` が適切か、長すぎ/短すぎ

加えて副次的に:

5. **幻覚パターン** — 相手名の誤生成、無限繰返し、stage direction 混入、言語崩壊
   などの出現頻度と対策

## スコープ

### 含むもの

- G-GEAR (qwen3:8b, localhost:11434) 上での ad-hoc スクリプト実行
- `_ad_hoc/` または `%TEMP%` 配下の throwaway Python スクリプト (commit しない)
- Kant ↔ Rikyū の 1-on-1 対話 (3 mode × 2-3 run の subjective 評価)
- `decisions.md` への知見の文字化 + スコア記録

### 含まないもの

- 正式な `DialogTurnGenerator` 実装 (→ `m5-dialog-turn-generator` に委譲)
- schema 変更 (→ `m5-contracts-freeze` に委譲)
- Nietzsche persona 検証 (spike は Kant/Rikyū の 2 軸で足りる、3 軸は live acceptance で)
- テスト追加・CI 変更
- pytest 実行 (spike コードは既存 test に触れない)

## 受け入れ条件

- [ ] `.steering/20260420-m5-llm-spike/decisions.md` に 5 項目の判断が記載されている
- [ ] 各項目に「なぜその値/語彙を選んだか」の経験的根拠 (実測値 or 観察ログ) が紐付く
- [ ] spike スクリプト自体はリポジトリに commit されていない (git status clean)
- [ ] 幻覚パターン 3 種以上の具体例が `decisions.md` に引用されている
- [ ] 後続 `m5-contracts-freeze` が参照すべき field / default 値が明示されている

## 関連ドキュメント

- `.steering/20260420-m5-planning/design.md` §LLM プロンプト設計方針
- `.steering/20260420-m5-planning/decisions.md` 判断 4 (throwaway 方針)
- `src/erre_sandbox/cognition/prompting.py` (既存 `build_system_prompt` / `build_user_prompt`)
- `src/erre_sandbox/cognition/reflection.py` (OllamaUnavailableError fallback パターン)
- `src/erre_sandbox/inference/sampling.py` (`compose_sampling` + persona.default + ERRE delta)
- `persona-erre` Skill §ルール 2 (ERRE mode ごとの delta 表)
- `src/erre_sandbox/config/personas/{kant,rikyu}.yaml` (persona spec)

## 運用メモ

- 破壊と構築 (/reimagine) 適用: **No**
- 理由: spike は探索そのものが目的で「2 案比較」にそぐわない。設計判断は成果物
  (`decisions.md`) として後続タスクに渡り、そこで reimagine が必要なら適用される。
  判断 3 (M5 planning 全体に reimagine 適用済) により、spike の位置付けは既に
  hybrid 案の一部として確定している。
