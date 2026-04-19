# design-comparison — v1 (単一関数) vs v2 (5 モジュール分離)

## サマリ

- **採用**: v2 (5 モジュール pure function + orchestrator + LLMPlan 構造化パース)
- **破棄**: v1 (1 ファイル 1 関数、regex パース、全例外握りつぶし)
- **判断根拠**: v1 は致命 3 / 高 3 / 中 5 / 低 1 の計 12 弱点。特にテスト可能性 (W1)、
  構造化パース (W2)、例外種別分岐 (W6) はプロジェクト原則に反する

## 比較表

| 観点 | v1 (単一関数) | v2 (5 モジュール分離) | 勝者 |
|---|---|---|---|
| **API 構造** | 1 関数 `run_cognition_cycle(...)` | `CognitionCycle.step(...)` + 4 pure モジュール | **v2** |
| **LLM 出力パース** | free text + regex `SPEAK:` `GO:` | JSON + Pydantic `LLMPlan` + `parse_llm_plan` | **v2** |
| **状態遷移** | `prev * 0.95 + gauss(0, 0.02)` べた書き | CSDG 半数式 `advance_physical` (4 要素導出完全実装) | **v2** |
| **戻り値型** | `tuple[AgentState, list[Envelope]]` | `CycleResult(BaseModel, frozen)` with `llm_fell_back` 明示 | **v2** |
| **RNG 決定論性** | `random.gauss(0, ...)` global | `Random` 注入 + seed 固定可能 | **v2** |
| **例外ハンドリング** | `except Exception as e:` 握りつぶし | Unavailable + Parse 失敗のみ fallback、それ以外 crash-loud | **v2** |
| **importance 計算** | `return 0.5` プレースホルダ | event_type lookup + intensity 補正 | **v2** |
| **system prompt** | 1 f-string に全部 | 共通 prefix + ペルソナ固有 + 動的 tail の 3 段 (RadixAttention 最適化) | **v2** |
| **fallback 可視性** | 側チャネルなし | `CycleResult.llm_fell_back: bool` | **v2** |
| **ChatMessage 型安全** | `{"role":..., "content":...}` dict | `ChatMessage(role=..., content=...)` Pydantic | **v2** |
| **Reflection trigger** | 未実装 | 閾値 + zone 入室検出 (実行は M4+) | **v2** |
| **多エージェント拡張 (M4+)** | 全関数書き直し | per-agent `CognitionCycle` インスタンス化 | **v2** |
| **ユニットテスト可能性** | LLM + DB 全 mock 必須 | pure 関数を直接テスト可能 (state/prompting/parse/importance) | **v2** |
| **総実装行数** | ~200 行 | ~710 行 (src) + ~780 行 (tests) | v1 |
| **総学習コスト (新規参加者)** | 5 分 (1 関数読むだけ) | 30 分 (5 ファイル構造理解) | v1 |
| **既存パターン整合 (T10/T11)** | 乖離 (関数型 vs クラス型 adapter) | 完全対称 (DI コンストラクタ、frozen Pydantic、ClassVar defaults) | **v2** |

## v1 弱点の v2 解消マッピング

| v1 弱点 | 深刻度 | v2 での解消方法 | 完全解消? |
|---|---|---|---|
| V1-W1 巨大関数 | 致命 | 5 モジュール分離、各 pure 関数を直接テスト | **完全** |
| V1-W2 regex パース | 致命 | JSON + Pydantic `LLMPlan`、parse 失敗は明示的 None | **完全** |
| V1-W3 ad-hoc state 更新 | 高 | `advance_physical` (CSDG 半数式 4 要素導出を正式実装) | **完全** |
| V1-W4 tuple 戻り値 | 高 | `CycleResult(BaseModel, frozen)` で構造化 + flag | **完全** |
| V1-W5 RNG 決定論性 | 高 | `Random` 注入、テストで seed 固定 | **完全** |
| V1-W6 except 握りつぶし | 致命 | `OllamaUnavailableError` / `EmbeddingUnavailableError` / parse None のみ fallback。それ以外は伝播 | **完全** |
| V1-W7 importance plate-holder | 中 | `estimate_importance` event_type lookup | **完全** |
| V1-W8 prompt f-string | 中 | 3 段構造 (共通 prefix / ペルソナ固有 / 動的 tail) | **完全** |
| V1-W9 llm_fell_back 不可視 | 中 | `CycleResult.llm_fell_back: bool` | **完全** |
| V1-W10 ChatMessage dict | 低 | T11 Pydantic `ChatMessage` を型で使用 | **完全** |
| V1-W11 importance/prompt 埋没 | 中 | 独立モジュール化、M4+ で差し替え容易 | **完全** |
| V1-W12 reflection 未実装 | 中 | トリガー検出実装 (実行は M4+) | **構造は完全、実行は保留** |

## v2 が背負うトレードオフと mitigation

### T1: 実装行数の大幅増加 (200 → 710 行)

- mitigation: 実装の 40% (~280 行) は純粋関数の **自己文書化コード** (型ヒント、
  docstring、Pydantic Field)。機能行は ~430 行で v1 (200 行) の 2.1 倍だが、
  追加機能 (RNG 注入、Reflection trigger、RadixAttention prompt、event_type
  importance、CycleResult flag、CSDG 半数式) が加わる
- 実装難易度は v1 より**低い** (各モジュールが小さく責務が明確なため)

### T2: 6 モジュール構成

- mitigation: `cognition/__init__.py` で 12 シンボル re-export。呼び出し側
  (T13 world tick) は `from erre_sandbox.cognition import CognitionCycle,
  CycleResult` で完結
- T11 inference/ と同じ「top-level 公開 / 内部 module は見えない」パターン

### T3: LLM に JSON 出力を要求する

- リスク: LLM が JSON を返さないケース (日本語で散文を返す等)
- mitigation:
  - プロンプトで JSON スキーマを明示 (`RESPONSE_SCHEMA_HINT` 定数)
  - `parse_llm_plan` は JSON が取れなければ None 返却、cycle は fallback
  - 将来 Ollama の `format: "json"` を adapter に追加 (別 PR、BL に記録)

### T4: `CognitionCycle` が per-agent 単位 (thread-safe でない)

- MVP は 1 エージェント固定なので問題なし
- M4+ 複数エージェント時: factory で per-agent インスタンスを作る (既存の
  store / embedding / llm は共有可)

### T5: `ChatMessage` を `Sequence[ChatMessage]` で渡す必要

- v1 (dict 直渡し) より冗長だが、T11 が型で要求しているので従うのみ
- mitigation: `cycle.py` 内で `[ChatMessage(role="system", content=s),
  ChatMessage(role="user", content=u)]` と明示的に書く。2 行増えるのみ

## 判定

**v2 を採用** (decisions.md D1 に記録)。

致命弱点 3 件 (テスト可能性 / 構造化パース / 例外握りつぶし) のうちどれか
1 つでも採用後に顕在化すると MVP E2E テストが fail する可能性が高い:
- W1: state テスト 1 件書くのに LLM モック + DB モックが必要
- W2: Kant が日本語で散文返答すると `SPEAK:` regex が空振り → UI に何も出ない
- W6: AttributeError がサイレント → Godot 側はダッシュに気付かず走り続け
  (「継続フォールバック」として正しく見えてしまう)

v1 の利点は**学習コスト**と**行数**のみで、機能的・構造的利点は一つもない。
