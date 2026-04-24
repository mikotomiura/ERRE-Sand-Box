# M7 — Slice γ (Dialogue & relationship loop)

## 背景

Slice α (PR #81) で observability overlay + camera hotkeys、Slice β (PR #83)
で behavioural differentiation (preferred_zones bias + 100m world + 3 new zone
scenes) を実装した。`.steering/20260424-m7-differentiation-observability/`
decisions.md D8 の β /reimagine で 4 項目を γ に明示延期した：

- **D1** 相互反省 prompt (`reflection.py` の system prompt に「直近 3 ターンの
  他 agent 発話」セクション)
- **D2** `record_dialog_interaction(agent_id, other_id, affinity_delta)`
  hook を relational_memory INSERT に配線、DialogTurnMsg 受信時に発火
- **D3** `ReasoningTrace.decision` に affinity 値と preferred_zones を
  根拠として埋める
- **D4** `ReasoningTrace` schema 拡張 (`observed_objects` /
  `nearby_agents` / `retrieved_memories`)
- **B3** Godot `ReasoningPanel.gd` に "Relationships" 折りたたみセクション
- **γ 送り負債 (D8 末尾)**: `WorldLayoutMsg` envelope、Zazen 石灯籠、
  slow probabilistic e2e、`Chashitsu.tscn` 座標 drift
- **C3 判定**: Relationships UI 実装後、agent anatomy visual がまだ必要か判定
  (decisions.md D7 参照)

MASTER-PLAN (`.steering/20260418-implementation-plan/MASTER-PLAN.md`) の
70/35/45 受入コアをまとめて埋める最大スライス。

## ゴール

1 PR (~11h 工数想定) で以下を同時達成し、live G-GEAR で「3 agent が別生物として
**関係性をもって** 振る舞う」を観察可能にする:

- agent 同士の対話 (DialogTurnMsg) が `relational_memory` に蓄積され、
  affinity が更新される
- 反省 (reflection) 時、他 agent の直近発話を prompt に注入
- Reasoning panel で agent 間の関係 (affinity 値 + 共有体験) が閲覧可能
- xAI trace (ReasoningTrace) が「何を観察し、誰が近くにいて、どの記憶を引いたか」
  を agent 視点で言語化

## スコープ

### 含むもの (次 PR)
- D1 / D2 / D3 / D4 / B3 の 5 項目縦切り
- `WorldLayoutMsg` envelope 配線 (BoundaryLayer.gd / zone_rects を Python から
  受領)
- Zazen 石灯籠 primitive
- `Chashitsu.tscn` scene root 座標の ZONE_CENTERS 一致化
- 受入 live run 追加項目 (affinity 3 行以上 / trace に affinity 文字列 /
  dialog_turn kind 出現)
- C3 (agent anatomy) 要否判定 → 必要なら /reimagine で 3 案比較、不要なら close

### 含まないもの (Slice δ 以降)
- LoRA による persona 分化 (L6 の scope、別 steering)
- 4 agent 目以降の追加 (user-dialogue IF 含む、L6)
- 長期記憶の decay 再設計
- Blender .glb 差し替え (backlog)

## 受け入れ条件

### Unit / integration
- [ ] `uv run pytest tests/` 全パス
- [ ] `uv run ruff check src/ tests/` pass
- [ ] D2 hook unit test: dialog_turn 受信で relational_memory INSERT
- [ ] D4 schema test: observed_objects / nearby_agents / retrieved_memories が
  ReasoningTrace に appear
- [ ] WorldLayoutMsg schema golden test

### Live G-GEAR
- [ ] 3 agent が互いに DialogTurnMsg を交換するシナリオを 90-120s run
- [ ] `evidence/<run>.summary.json` に `dialog_turn` kind が ≥3 行
- [ ] `relational_memory` に 3 行以上
- [ ] `ReasoningTrace.decision` に "affinity" または "関係" を示す文字列
- [ ] Godot `ReasoningPanel` で affinity 値 + 共有経験 UI が表示

## 関連ドキュメント

- Plan 本体: 次セッションで `/start-task` 不要、`design.md` を Plan mode で
  書き起こす (`/reimagine` 必須 — D2 の hook 位置 / D4 schema 拡張範囲 /
  WorldLayoutMsg 形式は複数案ありうる設計)
- design-final: `.steering/20260424-m7-differentiation-observability/design-final.md`
- β 完了記録: decisions D8 (同上)
- MASTER-PLAN: `.steering/20260418-implementation-plan/MASTER-PLAN.md`
