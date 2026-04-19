# ブロッカー / 保留懸案

本タスクで解消しなかった指摘と、後続タスクへ送る観察事項のメモ。

## BL-1: Observation テキスト化が 2 箇所に重複 (reviewer MEDIUM-3)

- **内容**: `cognition/cycle.py::_observation_content_for_embed` と
  `cognition/prompting.py::_observation_line` が event_type 別の 5 分岐 dispatch
  を持つ。将来 event_type を追加時に片方を更新し忘れる事故リスク
- **対処**: MVP では残す。M4 reflection 実装時に `cognition/_format.py` へ抽出
  する候補として記録
- **優先度**: LOW

## BL-2: AgentState 全公開が M4+ 複数エージェント時のリスク (security M2)

- **内容**: `_format_state_tail` が sleep_quality / fatigue / cognitive_load /
  valence / arousal / motivation / stress を LLM に渡す。M4+ で Agent A の
  speech を Agent B が観測 → B の LLM が A の状態をパラフレーズして漏洩する
  経路が理論上成立
- **対処**: MVP (単一エージェント) では実害なし。M4 着手時に
  `_format_state_tail` を "自覚できる情報のみ" にフィルタする関数を追加
- **優先度**: MEDIUM (M4 時に対応)

## BL-3: `done_reason` 未知値のサイレント正規化 (T11 BL-3 と同系列)

- **内容**: T11 `OllamaChatClient._parse` が `stop`/`length` 以外を `stop` に
  畳む。T12 では `ChatResponse.finish_reason` を直接消費しないので波及は軽微
- **対処**: T11 側の BL として継続管理
- **優先度**: LOW

## BL-4: ChatMessage.content / Observation.content の長さ制限なし (security L2)

- **内容**: 外部入力 (WebSocket 経由、M4+) で 巨大 content が渡される可能性。
  MVP はローカルのみなので実害なし
- **対処**: M4 で `Observation` validation に `max_length=512` 制約を schemas.py
  に追加検討
- **優先度**: LOW

## BL-5: `_FakeRanked` dataclass が `RankedMemory` の duck-type (reviewer LOW-10)

- **内容**: `tests/test_cognition/test_prompting.py::_FakeRanked` は `RankedMemory`
  の subset。`RankedMemory` にフィールド追加時に偽成功する可能性
- **対処**: M4 で `RankedMemory` に追加フィールドが載る場合に修正
- **優先度**: LOW

## BL-6: Ollama `format: "json"` 対応 (decisions.md D2 代替)

- **内容**: MVP はプロンプト指示 + 寛容パーサ。厳密 JSON 強制は `chat()` に
  `format="json"` オプションを追加することで可能だが、MVP では遅延
- **対処**: 実運用で JSON 以外が頻出する場合に adapter 拡張
- **優先度**: LOW

## BL-7: multi-byte 文字切断リスク (reviewer LOW-8)

- **内容**: `prompting._one_line` の `single[: limit - 1]` は Unicode codepoint
  単位で切る。サロゲートペアでは見た目の文字とずれる可能性
- **対処**: M4+ で `textwrap` / `grapheme` ベースに切替検討
- **優先度**: LOW

## BL-8: LLM 応答パフォーマンス観測が未実装

- **内容**: `ChatResponse.total_duration_ms` / `eval_count` は取得しているが、
  `CycleResult` には含めていない。T14 metrics 基盤の責務
- **対処**: T14 gateway で集計
- **優先度**: 管理対象外 (T14 に送る)

## BL-9: `estimate_importance` 未知 event_type フォールバックがテスト未検証 (reviewer LOW-11)

- **内容**: `_BASE_IMPORTANCE.get(event_type, _BASE_IMPORTANCE["perception"])` の
  フォールバック分岐に到達するテストがない
- **対処**: Observation が discriminated union なので到達不能経路。現状維持
- **優先度**: LOW

---

## 完全解消済み (参考)

| reviewer / security 指摘 | 優先度 | 対処 |
|---|---|---|
| HIGH-1 getattr ナローイング | HIGH | `obs.event_type == "..."` で discriminated union narrowing に変更、unused imports 削除 |
| HIGH-2 embedding=None 書き込み経路テスト欠落 | HIGH | `test_step_continues_on_embedding_unavailable` を追加 |
| MEDIUM-4 negative_speech narrowing | MEDIUM | for ループ + event_type narrowing に変更 |
| MEDIUM-5 embedding 失敗経路 | MEDIUM | 同上 (テスト追加) |
| MEDIUM-6 emotional_conflict docstring | MEDIUM | `advance_physical` docstring に 4 不変フィールド明記 |
| MEDIUM-7 `del tick_seconds` | MEDIUM | `_ = tick_seconds` + コメントに変更 |
| LOW-9 MoveMsg 座標補間コメント | LOW | "Godot side (T17) handles interpolation" コメント追加 |
| Security M1 巨大 JSON DoS | MEDIUM | `MAX_RAW_PLAN_BYTES = 64KB` ガード + test_parse_rejects_oversized_input |
