# M6-A-2b 繰越項目 (backend) の実装

## 背景

`.steering/20260421-m6-observatory/tasklist.md` の **Track M6-A-2b** には 5 件の繰越項目が残存している。M6 本体 PR (#75) では schema / envelope / 部分実装のみ着地し、firing logic や default handling が未達。M6 acceptance (90 秒 chashitsu demo) の前提として不足があるため、G-GEAR 側で backend 限定のまま追従実装する。

MacBook 側は同時並行で Godot 側 (M6-B の B-3 SynapseGraph / B-5 StateBar / Blender 検証) を進められる状態にしておきたい。

## ゴール

M6-A-2b の繰越 backend 項目 4 件 + 先頭 1 件 (cycle.py の埋め込み穴) を埋め、Observation stream の 4 新型 (Affordance/Proximity/Temporal/Biorhythm) を通じて完全に:

1. **Proximity**: agent ペアが 5m 閾値を跨いだら enter/leave event を発火
2. **prompt**: observation 窓を 5→10、Proximity 系は max 2 件/tick に clamp
3. **Stress Biorhythm**: Step 8 post-LLM の Cognitive 差分で mid-band (0.5) 跨ぎを検出、次 tick の observations に carry-forward
4. **default handling**: `cognition/state.py` の `_PHYSICAL_EVENT_IMPACT` と `cognition/importance.py` の `_BASE_IMPORTANCE` に 4 新型を登録
5. **bonus**: `cognition/cycle.py:_observation_content_for_embed()` が 4 新型で "[unknown] (unformatted)" を返す defect を修正 (Episodic memory に 4 新型が記録されない)

## 含まないもの

- **Affordance firing** — prop registry が不在のため M7 繰越 (tasklist.md:36 と decisions 一致)
- **Godot xAI 側 (M6-B-3/5)** — MacBook 担当
- **Blender headless export 検証 (M6-C-1)** — Blender 実機必要、Blender 所在確認後 (MacBook 側)

## 受け入れ条件

- [ ] Proximity 発火の unit test が 3 件以上 (enter / leave / 同 tick 内の複数 pair)
- [ ] Stress biorhythm crossing test が 2 件以上 (up / down)
- [ ] default handling を `estimate_importance` / `advance_physical` で exercise する test が追加
- [ ] prompt window 拡張 (5→10) と per-type limit の test
- [ ] 既存 730 PASS + 36 SKIP の regression ゼロ
- [ ] ruff check / format clean
- [ ] 実装後 `.steering/20260421-m6-observatory/tasklist.md` の該当 checkbox を cross-update
