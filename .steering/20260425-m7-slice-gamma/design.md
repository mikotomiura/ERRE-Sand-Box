# Design — Slice γ

> **次セッション開始時に Plan mode + Opus + /reimagine で書き起こす。**
> 現時点は骨格のみ。/reimagine 発動必須の理由は「hook 挿入位置 /
> schema 拡張範囲 / envelope 形式」が複数案ありうる設計判断だから
> (CLAUDE.md 99 行 Plan mode + /reimagine ルール)。

## スケルトン (5 commit 想定)

1. **`refactor(schemas)` — ReasoningTrace 拡張 + WorldLayoutMsg 定義**
   - `ReasoningTrace` に `observed_objects: list[...]` /
     `nearby_agents: list[AgentId]` / `retrieved_memories: list[MemoryId]`
     を追加 (D4)
   - `WorldLayoutMsg(ControlEnvelope)` 追加、`zone_centers: dict[Zone, Position]`
     / `zone_props: list[PropSpec]` (γ 負債)
   - schema_version bump、golden JSON fixture 追加
   - 1.5h

2. **`feat(cognition)` — affinity hook + 相互反省 prompt**
   - `memory/store.py` の relational_memory INSERT 経路に
     `record_dialog_interaction(agent_id, other_id, affinity_delta=0.02)`
     追加 (D2、固定値 MVP)
   - `cognition/cycle.py` DialogTurnMsg 受信時に hook 発火
   - `cognition/reflection.py` system prompt に「直近 3 ターンの他 agent 発話」
     セクション (`MemoryStore.transcript_of` 経由) (D1)
   - `cognition/cycle.py` ReasoningTrace 生成時に affinity 値と preferred_zones
     を `decision` に埋め込み (D3)
   - 4h

3. **`feat(gateway)` — WorldLayoutMsg の on-connect 送信**
   - gateway / godot_bridge で WS connect 時に現在の ZONE_CENTERS / ZONE_PROPS
     を WorldLayoutMsg として送信
   - 1h

4. **`feat(godot)` — Relationships UI + WorldLayoutMsg consumer**
   - `ReasoningPanel.gd` に "Relationships" 折りたたみ section (B3)
   - `BoundaryLayer.gd` が WorldLayoutMsg を受信して zone_rects / prop_coords
     を更新 (β の TODO(slice-γ) コメント解消)
   - `Chashitsu.tscn` scene root を (33.33, 0, -33.33) に修正 (β 送り負債)
   - Zazen に 石灯籠 primitive 追加 (β 送り負債)
   - 3h

5. **`feat(cognition/tests)` — γ 受入テスト + C3 判定**
   - D4 schema test、D2 hook unit test
   - C3 (agent anatomy) 要否判定 (Relationships UI 実装後に行う)
   - 不要なら `decisions.md` に "C3 deprecated" を追記し close
   - 必要なら新 task dir に 3 案 /reimagine を発動
   - 1.5h

合計 ~11h。context 30% 超えたら `/clear` して plan file + design-final を
re-read してから実装継続 (CLAUDE.md Plan → Clear → Execute ハンドオフ)。

## /reimagine で確認する軸 (次セッションで Plan agent に渡す)

1. **affinity_delta の配線位置**: (a) DialogTurnMsg 受信時 / (b) reflection
   ループ内 / (c) LLM による動的判定
2. **ReasoningTrace の observed_objects 粒度**: (a) 全 prop / (b) 半径内のみ /
   (c) LLM が salient とした物のみ
3. **WorldLayoutMsg の送信タイミング**: (a) on-connect のみ / (b) tick 0 /
   (c) zone_centers 変化時にも差分送信
4. **Relationships UI の情報密度**: (a) affinity 数値のみ / (b) 共有経験ログ /
   (c) 相手の persona 情報も含む
5. **C3 (anatomy) の判定基準**: Relationships UI で何が足りなければ anatomy が
   必要と判断するか、先に明文化する
