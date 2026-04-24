# Decisions — M7 First PR

このファイルは設計判断を記録する。**First PR** 期間中に出た判断のみ。
Follow-up track (A2/A3/B3/C/D) の判断は別タスク or 本ファイルの末尾セクション。

## D1. First PR を「優先 3」に絞る

- **選択肢**: (a) 4-track 全部同時, (b) Track A 全部, (c) 優先 3 のみ
- **採用**: (c) 優先 3 (V + A1 + B1 + B2)
- **理由**: 体感デルタ/工数比最大。`~8h` で 1 PR。残り track は merge 後に判断。
- **源**: AskUserQuestion 回答 2 (2026-04-24 plan 承認時)

## D2. L6 (LoRA / scaling / user-dialogue IF) は別 steering で並行起票

- **選択肢**: (a) 同タスクの decisions.md に書く, (b) 別 steering, (c) MASTER-PLAN 追記
- **採用**: (b) `.steering/20260424-steering-scaling-lora/`
- **理由**: コード作業と戦略文書を混ぜない。Track D4 の成長メトリクス実装後に
  閾値を確定する前提で初稿は定性記述。
- **源**: AskUserQuestion 回答 3

## D3. AffordanceEvent MVP は chashitsu 1 zone の 1-2 prop のみ

- **選択肢**: (a) 全 5 zone に prop 配置, (b) chashitsu のみ
- **採用**: (b)
- **理由**: PR 肥大化防止。schema/発火機構ができれば他 zone は機械的追加。
  アンチパターン回避 (plan file 末尾)。

## D4. A1 の prompt 追加は 2 行以内に抑制

- **選択肢**: (a) 全 personality field を形容詞化して文章で渡す,
  (b) 数値 1 行 + Wabi/Ma 1 行で計 2 行, (c) JSON object を dump
- **採用**: (b)
- **理由**: context 窓圧迫回避。形容詞化は LLM に委ねる（"openness=0.8 →
  好奇心旺盛" という解釈は LLM の役割）。
- **源**: plan file "アンチパターン回避メモ"

## D5. V は reflection.py を大改造しない (dialog_turn パターンの流用)

- **選択肢**: (a) language manager を新設, (b) system prompt tail +1 行のみ
- **採用**: (b)
- **理由**: PR #68 で dialog_turn.py が同パターンで成功している。First PR 範囲では
  同じ最小改修で十分。manager 抽出は languages が 2 箇所を超えた時に検討。

## D6. B2 の overlay は hardcode 座標で先行、WebSocket 配線は次 PR

- **選択肢**: (a) schema に PropSpec を足し、WebSocket で座標を送る,
  (b) Godot 側に同 prop 座標を hardcode し、後で配線
- **採用**: (b)
- **理由**: B1 と B2 の結合度を下げて並列開発しやすくする。prop 座標は M7 期間中に
  2-3 箇所しか動かない想定。schema 変更は B3 (ReasoningTrace 拡張) とまとめて
  次 PR で。

## 本 PR 外だが記録すべき判断 (deferred)

### C3 (agent anatomy visual) は着手前 `/reimagine` 必須

- 3 案候補: (i) 粒子/tree 抽象, (ii) UI オーバーレイでメモリカード, (iii)
  shader-based synapse 発火
- 実装着手前に /reimagine で比較、採用案を本ファイルに追記
- **本 First PR には含めない**
