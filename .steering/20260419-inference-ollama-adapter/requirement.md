# T11 inference-ollama-adapter — requirement

- 対象タスク: MASTER-PLAN §4.2 T11
- 担当機: **G-GEAR** (この作業ディレクトリ)
- 日付: 2026-04-19
- 依存完了: T08 (schemas 凍結) / T09 (qwen3:8b + nomic-embed-text pull 済)

## 1. 背景

ERRE-Sandbox の認知サイクル (T12) は「ローカル LLM への chat 形式リクエスト」を
10 秒 tick ごとに発行する。MVP (M2) ではクラウド API を**必須依存にしない**
制約から、開発環境の推論バックエンドとして **Ollama** (`http://localhost:11434`)
を採用する (architecture.md §2, §7 非採用表、architecture-rules Skill 禁止 2)。

T11 はその「推論バックエンドを叩く単一薄クライアント」を実装する。
SGLang 版 (M7+) は `sglang_adapter.py` として後続タスクで追加するため、
T11 は **SGLang に縛られない形で ERRE サンプリング合成** を提供するのが設計上
最重要の責務となる。

### 既存資産との接続

| コンポーネント | 状態 | 接続 |
|---|---|---|
| `schemas.SamplingBase` / `SamplingDelta` | T05 で凍結済 | 本タスクで合成 + クランプを実装 |
| `schemas.ERREMode` | T05 で凍結済 (`sampling_overrides: SamplingDelta`) | 本タスクで ERREMode → 具体的サンプリングに変換 |
| `schemas.PersonaSpec.default_sampling: SamplingBase` | T05 で凍結済 | 本タスクの基底パラメータ |
| `memory.embedding.EmbeddingClient` | T10 で実装済 | 本タスクで **パターンを踏襲** (httpx.AsyncClient + MockTransport テスト) |
| qwen3:8b (Ollama) | T09 で pull 済 (5.2 GB, 768d embedding 別途) | 本タスクで `/api/chat` を叩く |
| `cognition/cycle.py` | T12 で実装 (本タスクの利用者) | `generate_chat()` / `ChatResponse` を import |
| `inference/sglang_adapter.py` | M7 で追加予定 | T11 と同じ `ChatResponse` 型を返す (互換 API) |

## 2. ゴール (完了条件)

1. `src/erre_sandbox/inference/ollama_adapter.py` が存在し、以下の API を提供する:
   - `OllamaChatClient` クラス — `async def chat(messages, *, sampling, options) -> ChatResponse`
   - `ChatResponse` Pydantic モデル — `content: str` / `model: str` / `eval_count: int` / `total_duration_ms: float` / `finish_reason: Literal["stop", "length"]`
   - `OllamaUnavailableError(RuntimeError)` — `/api/chat` 到達不能/非 200/不正 JSON の 3 状態を正規化
2. ERRE モード別サンプリングを**純粋関数**として分離 (`inference/sampling.py`):
   - `compose_sampling(base: SamplingBase, delta: SamplingDelta) -> ResolvedSampling`
   - 加算後 `temperature ∈ [0.01, 2.0] / top_p ∈ [0.01, 1.0] / repeat_penalty ∈ [0.5, 2.0]` にクランプ (persona-erre Skill §ルール 2 + SamplingBase の range)
3. 依存方向を厳守: `inference/` から import してよいのは `schemas` と stdlib + `httpx` + `pydantic` のみ (architecture-rules Skill レイヤー表)
4. テスト: `tests/test_inference/test_ollama_adapter.py` / `test_sampling.py` が追加され、`uv run pytest` 全体緑 (134 baseline +α)
5. 静的解析: `uv run ruff check` / `ruff format --check` / `mypy src tests` 全緑
6. CI リグレッションなし: T10 の 134 passed / 16 skipped が維持される

## 3. スコープ内

- Ollama `/api/chat` エンドポイントへの単一 request/response (non-streaming)
- `OllamaChatClient.chat()` に **system + user messages** を渡せる API
- `SamplingBase` + `SamplingDelta` の合成関数 (分離ファイル)
- 到達不能・非 200・JSON 破損の 3 種エラー正規化
- タイムアウト (default 60s, error-handling Skill に準拠)
- httpx.AsyncClient 注入可能 (テストで MockTransport 差し込み可能)
- `OllamaChatClient` の **コンテキストマネージャ** 対応 (`async with`)
- Ollama `options` に `num_ctx` / `num_predict` / `stop` を透過的に渡せる拡張点
- 構造化レスポンスの Pydantic parse (LLM 出力の `content` 文字列の構造化は T12 の責務)

## 4. スコープ外

- **streaming 応答** (MVP は 10s tick なので完結 mode で十分、M5+ で必要になれば追加)
- **SGLang adapter** (M7+ で `sglang_adapter.py` を追加、本タスクでは **互換 API のみ定義**)
- **フォールバック** (`generate_with_fallback`) — これは `inference/server.py` (T14 前後) の責務
- **リトライ loop** (`retry_async`) — これも呼び出し側 (T12 cognition cycle) の責務
- **persona YAML → SamplingBase 読み込み** — persona loader 側の責務 (T12 以降)
- **system prompt 構築** (ペルソナ + AgentState → string) — persona-erre §ルール 3、T12 の責務
- **LLM 出力の構造化パース** (`AgentAction` 等) — T12 cognition cycle 側
- **Ollama サーバー起動スクリプト** — 運用手順は llm-inference Skill / operations.md に既存

## 5. 受け入れ条件

### 5.1 コード

- [ ] `src/erre_sandbox/inference/ollama_adapter.py` が `OllamaChatClient` / `ChatResponse` / `OllamaUnavailableError` を提供
- [ ] `src/erre_sandbox/inference/sampling.py` が `ResolvedSampling` / `compose_sampling()` を提供
- [ ] `src/erre_sandbox/inference/__init__.py` が 5 つを公開 re-export
- [ ] 3 つの import が `schemas` のみを対象 (grep で確認)
- [ ] `from __future__ import annotations` / docstring / 型ヒント完備 (python-standards)
- [ ] マジックナンバーなし (`DEFAULT_TIMEOUT_SECONDS` 等の `ClassVar[float]` 定数)

### 5.2 テスト

- [ ] `tests/test_inference/__init__.py` + `conftest.py` (必要なら)
- [ ] `test_ollama_adapter.py`:
  - [ ] `test_chat_returns_content` — 正常系、`message.content` 抽出
  - [ ] `test_chat_sends_sampling_options` — captured payload の `options` に `temperature` 等が入る
  - [ ] `test_chat_unreachable_raises` — httpx.ConnectError → `OllamaUnavailableError("unreachable")`
  - [ ] `test_chat_non_200_raises` — HTTP 500 → `OllamaUnavailableError("HTTP 500")`
  - [ ] `test_chat_malformed_payload_raises` — `message` キー欠落 → `OllamaUnavailableError`
  - [ ] `test_chat_timeout_propagates` — httpx.TimeoutException → `OllamaUnavailableError("timeout")`
  - [ ] `test_chat_async_with_closes_client` — owns client の場合に `aclose` される
- [ ] `test_sampling.py`:
  - [ ] `test_compose_applies_delta_additively` — base + delta = resolved
  - [ ] `test_compose_clamps_temperature_upper` — `1.5 + 1.0 → 2.0`
  - [ ] `test_compose_clamps_temperature_lower` — `0.0 + (-0.5) → 0.01`
  - [ ] `test_compose_clamps_top_p` — `0.95 + 0.1 → 1.0`
  - [ ] `test_compose_clamps_repeat_penalty` — `1.9 + 0.2 → 2.0`
  - [ ] `test_compose_peripatetic_vs_zazen_monotonic` — persona-erre §ルール 2 表の peripatetic と zazen で temperature の大小関係が正しい
- [ ] `uv run pytest` 全体緑、追加件数 +12 前後 (134 → ~146)

### 5.3 ドキュメント

- [ ] `.steering/20260419-inference-ollama-adapter/design.md` (v2 採用後)
- [ ] `.steering/20260419-inference-ollama-adapter/design-v1.md` (素直な案)
- [ ] `.steering/20260419-inference-ollama-adapter/design-comparison.md` (/reimagine 比較)
- [ ] `.steering/20260419-inference-ollama-adapter/decisions.md` (設計判断 5 件以上)
- [ ] `.steering/20260419-inference-ollama-adapter/blockers.md` (LOW 懸案のみ必要時)
- [ ] `.steering/_setup-progress.md` Phase 8 に T11 エントリ追加

### 5.4 CI / コミット

- [ ] `uv run ruff check .` / `ruff format --check .` 緑
- [ ] `uv run mypy src tests` 緑
- [ ] `uv run pytest tests/` 緑、skip は baseline 16 のまま
- [ ] `feat(inference): T11 inference-ollama-adapter — Ollama /api/chat + ERRE sampling compose` 1 コミット
- [ ] `Co-Authored-By: Claude Opus 4.7 (1M context)` + `Refs: .steering/20260419-inference-ollama-adapter/`
- [ ] `feature/inference-ollama-adapter` ブランチ → PR 作成

## 6. 想定工数

MASTER-PLAN 見積 1.0d。実装 (~450 行) + テスト (~300 行) + .steering 文書 (~800 行)
の新規作成が中心で、既存資産の改変は `inference/__init__.py` 1 ファイル。
Reimagine + code-reviewer 対応込みで 3-4h を想定。

## 運用メモ

- 破壊と構築 (/reimagine) 適用: **Yes**
- 理由:
  - (a) 外部インターフェース (`ChatResponse`, `OllamaChatClient.chat()` の signature)
    を公開するため、決定後の手戻りコストが高い
  - (b) エラーハンドリング/サンプリング合成/response 構造化の **責務境界** に
    複数のもっともらしい配置案が存在する (module-level fn vs class, raw dict
    vs Pydantic model, sampling compose の配置先)
  - (c) SGLang (M7+) を見越した API 互換性を T11 時点で確定させる必要がある
