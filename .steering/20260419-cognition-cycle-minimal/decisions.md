# 設計判断 (Decisions)

## D1: /reimagine 適用、v2 (5 モジュール分離) を採用

- **判断**: 初回案 v1 (1 関数に全部詰める) を破棄、v2 (state/prompting/parse/
  importance/cycle の 5 モジュール分離) を採用
- **根拠**: v1 は致命 3 (テスト可能性破綻 / regex パース / except 握りつぶし)
  + 高 3 (ad-hoc state / tuple 戻り値 / RNG 非決定論) の合計 12 弱点
- **CSDG 参照**: T12 は CSDG の半数式 (MASTER-PLAN B.3) を直接移植する MVP 優先 #2
  タスクに該当。実装は `state.advance_physical` / `apply_llm_delta` に集約

## D2: LLM 出力は JSON + Pydantic `LLMPlan`、regex 禁止

- **判断**: Ollama プロンプトで JSON を要求、`parse_llm_plan` で抽出+検証。
  失敗 (missing JSON / malformed JSON / ValidationError) は `None` → fallback
- **根拠**: v1 は `SPEAK:` / `GO:` 正規表現で free-text から拾う方式だったが、
  LLM の多言語出力や行頭空白で容易に破綻する。構造化境界を Contract で閉じる
- **代替却下**: Ollama `format: "json"` adapter 拡張 — 将来実装可能だが MVP では
  プロンプト指示 + 寛容なパーサで十分 (BL-6 に記録)
- **境界**: code fence (` ```json ... ``` ` / ` ``` ... ``` `) も許容、引用内
  ブレースは brace balancer で正しく処理

## D3: `_build_body` 類似の "sampling 後勝ち" を `chat` API で再現

- **判断**: `cycle.py` は `compose_sampling(persona.default, agent.erre.overrides)`
  を呼んで `OllamaChatClient.chat` に渡す。クランプ忘れ不可能性は T11 側で担保
- **根拠**: T11 `OllamaChatClient.chat(sampling: ResolvedSampling)` が型で要求 →
  T12 は合成を忘れられない
- **CSDG と persona-erre Skill §ルール 2 の照合**: peripatetic の `temperature +0.3`
  を test_step_applies_erre_sampling_override で検証 (persona.base=0.6 +
  delta=0.3 = 0.9)

## D4: RNG を DI、ガウスノイズの決定論的テスト

- **判断**: `StateUpdateConfig` と `rng: Random | None` を `__init__` / 各関数に
  注入可能に。`None` 時は `_noise` が 0 を返す (テスト用)
- **根拠**: 半数式の `gauss(0, noise_scale)` をテストで再現できないと回帰防止が
  成立しない。`Random(42)` で 2 回呼んで同じ結果が得られる invariant を確立
  (test_advance_physical_rng_is_deterministic)

## D5: エラー 3 種のみ fallback、残りは crash-loud

- **判断**: `OllamaUnavailableError` / `EmbeddingUnavailableError` / `parse_llm_plan`
  が `None` の 3 経路のみ `CycleResult(llm_fell_back=True)` に畳む。
  `AttributeError` / `KeyError` 等は伝播 (`CognitionError` も用意しているが
  ここで raise する内部経路は MVP 範囲にはなし)
- **根拠**: v1 の `except Exception` は **バグ由来 Silent 化** を許す。error-handling
  Skill §ルール 5 (ValidationError 限定 fallback) に沿い、種類別 catch に徹底
- **効果**: Embedding 失敗は cycle 自体は継続 (memory を embedding なしで書く)、
  LLM 失敗は「現在の行動を継続」、parse 失敗は LLM 失敗と同じフォールバック経路

## D6: `CycleResult.llm_fell_back` を side-channel 化

- **判断**: fallback 発動時の `llm_fell_back: bool` フラグを `CycleResult` に明示
- **根拠**: v1 の tuple 戻り値では「LLM が fall back したかどうか」を caller が
  envelope 内容の diff から推測する必要があった。T14 gateway では metrics
  として集計したい情報なので、boolean を Contract に含める

## D7: 3-stage system prompt (共通 prefix → ペルソナ固有 → 動的 tail)

- **判断**: `build_system_prompt` は `_COMMON_PREFIX` (ERRE-Sandbox 世界観 / 5 ゾーン
  / JSON 出力指示) → `_format_persona_block` (habits fact/legend/speculative +
  preferred_zones) → `_format_state_tail` (tick / zone / ERRE mode / Physical /
  Cognitive) の 3 段
- **根拠**: persona-erre Skill §ルール 3 の RadixAttention 最適化 (SGLang M7+ で
  共通 prefix の KV 再利用) を MVP の段階で構造化しておく。MVP Ollama は
  活用しないが、リファクトなしで M7 に載る

## D8: `StateUpdateConfig` dataclass で CSDG 係数を外出し

- **判断**: `decay_rate / event_weight / max_llm_delta / llm_weight / noise_scale`
  の 5 パラメータを frozen dataclass に束ね、`CognitionCycle(update_config=...)`
  で差し替え可能に
- **根拠**: MVP の暫定値 (10 秒 tick 校正) は実測後に tune する必要がある。
  code change なしで M4 reflection 実装時 / 実データ観察後に調整できる
- **デフォルト値**: decay=0.05 (≈140 tick ≈ 23 分半減期) / event_weight=0.15 /
  max_llm_delta=0.3 / llm_weight=0.7 / noise_scale=0.02

## D9: Reflection はトリガーのみ、本体は M4+

- **判断**: `reflection_triggered: bool` を `CycleResult` に置き、ログだけ出す。
  実際の内省 LLM 呼び出しは M4 で追加
- **根拠**: MVP では peripatos/chashitsu 入室時の「トリガー検出パス」が成立して
  いることを証明すれば十分 (functional-design.md §2)。実行本体を MVP に入れる
  と cycle step が 2 回目の LLM 呼び出しを含み、tick 予算を超える
- **閾値**: `REFLECTION_IMPORTANCE_THRESHOLD = 1.5` (per-tick 内の累積 importance)。
  functional-design.md §2 の 150 は長期累積の値、per-tick では 1.5 (約 3 件の
  high-importance event) を採用

## D10: tests/ で `S311 Random` を許容 (pyproject.toml 変更)

- **判断**: `pyproject.toml` の `[tool.ruff.lint.per-file-ignores]` の `tests/**`
  に `S311` を追加
- **根拠**: `Random(seed)` はテストの決定論的再現のために必須。`S311` は暗号用途
  warning だが、テストの seed 用途は crypto と無関係
- **影響**: `src/` では引き続き S311 が適用される (非暗号用途で `random` を使う
  場合に警告される)

## 補足: CSDG との関係

T12 は MASTER-PLAN 付録 B.5 MVP 優先 #2「半数式状態遷移と HumanCondition 自動
導出の 4 要素ロジック移植」に完全対応。CSDG の `csdg/engine/state_transition.py`
の式 `base = prev * (1 - decay_rate) + event_impact * event_weight` と
`base + clip(llm_delta, ±max) * llm_weight + gauss(0, noise_scale)` は
`state.advance_physical` / `apply_llm_delta` にそのまま移植済。法的帰属義務なし
(CSDG MIT、ERRE-Sandbox Apache-2.0 OR MIT 互換)。
