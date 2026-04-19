# 設計 (v2 採用版) — Contract-First OllamaChatClient + 分離 sampling

> **採用確定**: v1 の 10 弱点中、致命 2 / 高 4 を構造で解消
> 比較根拠: `design-comparison.md`
> 破棄案: `design-v1.md`

## 1. 実装アプローチ

Ollama `/api/chat` を叩く **クラスベースの薄クライアント** + **Pydantic 正規化された
`ChatResponse`** + **純粋関数としての `compose_sampling()`** の 3 ブロック。

- T10 の `EmbeddingClient` と同一パターン (ClassVar defaults / httpx.AsyncClient
  注入 / `async with` / エラー正規化) で**対称性**を確保
- サンプリング合成は `sampling.py` に **純粋関数**として分離
- `ChatResponse` は schemas.py には置かない (ワイヤー契約ではなく内部戻り値型)

## 2. モジュール構成

```
src/erre_sandbox/inference/
├── __init__.py               # 7 シンボルを re-export
├── sampling.py               # compose_sampling + ResolvedSampling (純粋)
└── ollama_adapter.py         # OllamaChatClient + ChatMessage + ChatResponse + OllamaUnavailableError
```

### 2.1 `inference/sampling.py` — 純粋関数 (新規 ~80 行)

- `ResolvedSampling(BaseModel, frozen=True)` — `temperature: [0.01, 2.0]` /
  `top_p: [0.01, 1.0]` / `repeat_penalty: [0.5, 2.0]` を Field range で担保
- `compose_sampling(base: SamplingBase, delta: SamplingDelta) -> ResolvedSampling` —
  加算 → `_clamp` → `ResolvedSampling` 生成
- 定数 `_TEMPERATURE_MIN/MAX` 等を module 先頭に `Final` で置く
- **I/O 無し、schemas のみ依存**

### 2.2 `inference/ollama_adapter.py` — クライアント (新規 ~240 行)

主要シンボル:

- `DEFAULT_CHAT_MODEL: Final[str] = "qwen3:8b"` (T09 D1 fallback 反映)
- `ChatMessage(BaseModel, frozen=True)` — `role: Literal["system","user","assistant"]`,
  `content: str`
- `ChatResponse(BaseModel, frozen=True)` — `content / model / eval_count /
  prompt_eval_count / total_duration_ms / finish_reason`
- `OllamaUnavailableError(RuntimeError)` — 4 種の httpx/JSON エラーを 1 つに正規化
- `OllamaChatClient`:
  - `ClassVar`: `DEFAULT_MODEL` / `DEFAULT_ENDPOINT` / `DEFAULT_TIMEOUT_SECONDS`
    / `CHAT_PATH`
  - `__init__(*, model, endpoint, timeout, client)` — httpx.AsyncClient DI
  - `async __aenter__ / __aexit__ / close` — コンテキストマネージャ
  - `async chat(messages, *, sampling, model=None, options=None) -> ChatResponse`
  - `_build_body()` — sampling は options の後に上書きで入れ、**呼び出し側が
    sampling を事故で override できないように**防御
  - `_post()` — httpx エラー → `OllamaUnavailableError` 正規化
  - `_parse()` staticmethod — payload → `ChatResponse`、validation 失敗も正規化

### 2.3 `inference/__init__.py` (差し替え)

```python
from erre_sandbox.inference.ollama_adapter import (
    DEFAULT_CHAT_MODEL, ChatMessage, ChatResponse,
    OllamaChatClient, OllamaUnavailableError,
)
from erre_sandbox.inference.sampling import ResolvedSampling, compose_sampling
__all__ = [7 シンボル]
```

## 3. 呼び出し側 (T12) での想定使用パターン

```python
from erre_sandbox.inference import (
    ChatMessage, OllamaChatClient, compose_sampling,
)

async def cognition_step(persona: PersonaSpec, agent: AgentState, observation: str):
    sampling = compose_sampling(persona.default_sampling, agent.erre.sampling_overrides)
    async with OllamaChatClient() as llm:
        resp = await llm.chat(
            messages=[
                ChatMessage(role="system", content=build_system_prompt(persona, agent)),
                ChatMessage(role="user",   content=observation),
            ],
            sampling=sampling,
            options={"num_predict": 256},
        )
    return resp.content  # structured parsing は T12 の責務
```

この API により、**ERRE mode のクランプ忘れ**も **sampling の事故 override** も
静的型 + body builder で構造的に防がれる (V1-W1 / V1-W4 の構造的解消)。

## 4. 依存方向の確認

```
inference/sampling.py        → schemas (SamplingBase, SamplingDelta) + pydantic ✓
inference/ollama_adapter.py  → inference.sampling (ResolvedSampling) + httpx + pydantic ✓
inference/__init__.py        → 上記 2 つのみ ✓
```

- schemas → 無し (最下層)
- memory / cognition / world / ui を import しない (architecture-rules 準拠)
- クラウド LLM API (openai / anthropic) を import しない (禁止 2 準拠)
- GPL 依存なし (禁止 1 準拠)

grep で検証:
```
grep -r "from erre_sandbox" src/erre_sandbox/inference/
# → erre_sandbox.schemas と erre_sandbox.inference.sampling のみ
```

## 5. 変更対象

### 5.1 新規作成

| ファイル | 想定行数 | 役割 |
|---|---|---|
| `src/erre_sandbox/inference/sampling.py` | ~80 | 純粋合成関数 + ResolvedSampling |
| `src/erre_sandbox/inference/ollama_adapter.py` | ~240 | Client + ChatMessage/Response + Error |
| `tests/test_inference/__init__.py` | 0 | package marker |
| `tests/test_inference/test_ollama_adapter.py` | ~220 | httpx MockTransport で 10 ケース |
| `tests/test_inference/test_sampling.py` | ~90 | 純粋関数 6 ケース |

### 5.2 修正

| ファイル | 変更内容 |
|---|---|
| `src/erre_sandbox/inference/__init__.py` | docstring のみ → 7 シンボル re-export |
| `.steering/_setup-progress.md` | Phase 8 の T11 を `[x]` 追加 |

### 5.3 削除

なし。

## 6. エラーハンドリング方針 (error-handling Skill 準拠)

### 6.1 正規化対象 (httpx の多種例外 → 1 例外)

| httpx 由来 | 正規化後 |
|---|---|
| `httpx.TimeoutException` (ConnectTimeout / ReadTimeout 等) | `OllamaUnavailableError("timeout after ...s")` |
| `httpx.HTTPError` (ConnectError / NetworkError / ReadError 等) | `OllamaUnavailableError("unreachable at ...")` |
| 非 200 ステータス | `OllamaUnavailableError("HTTP 5xx: <body[:200]>")` |
| 非 JSON (`response.json()` ValueError) | `OllamaUnavailableError("non-JSON payload")` |
| JSON が dict 以外 | `OllamaUnavailableError("non-object JSON")` |
| `message.content` 欠落 | `OllamaUnavailableError("missing 'message.content'")` |
| `ChatResponse` validation 失敗 | `OllamaUnavailableError("failed to parse")` |

`httpx.TimeoutException` は `httpx.HTTPError` のサブクラスなので、
`try: ... except TimeoutException: ... except HTTPError: ...` の順で catch する。

### 6.2 呼び出し側の契約

**T11 は正規化のみ。リトライ / フォールバック / ログ出力は呼び出し側**。
error-handling Skill ルール 1 (SGLang→Ollama) とルール 2 (retry_async) は
`inference/server.py` (T14) で `OllamaUnavailableError` を catch して実装する。

## 7. テスト戦略

### 7.1 `tests/test_inference/test_ollama_adapter.py`

T10 `test_embedding.py` の `_ok_handler` / `_err_handler` / `_make_client` ヘルパ
パターンを踏襲。

| # | テスト | 目的 |
|---|---|---|
| 1 | `test_chat_returns_chat_response` | 正常 `message.content` 抽出 + 型 + model |
| 2 | `test_chat_sends_sampling_and_messages` | captured body の options 3 値 + messages 配列 |
| 3 | `test_chat_merges_extra_options` | `options={"num_predict": 256}` 透過、sampling は保護 (上書き不可) |
| 4 | `test_chat_respects_model_override` | `chat(..., model="foo:tiny")` が payload.model に反映 |
| 5 | `test_chat_unreachable_raises` | ConnectError → `OllamaUnavailableError("unreachable")` |
| 6 | `test_chat_timeout_raises` | TimeoutException → `OllamaUnavailableError("timeout")` |
| 7 | `test_chat_non_200_raises` | 500 → `OllamaUnavailableError("HTTP 500")` |
| 8 | `test_chat_missing_message_raises` | `message` キーなし → `OllamaUnavailableError` |
| 9 | `test_chat_malformed_json_raises` | 非 JSON → `OllamaUnavailableError("non-JSON")` |
| 10 | `test_async_with_closes_owned_client` | `async with` 出口で internal client `aclose` |

### 7.2 `tests/test_inference/test_sampling.py`

純粋関数なので mock 不要、Pydantic 型の入出力のみ。

| # | テスト | 目的 |
|---|---|---|
| 1 | `test_compose_applies_additive_delta` | base=0.6 + delta=+0.3 → resolved=0.9 (temp) |
| 2 | `test_compose_clamps_temperature_upper` | 1.5 + 1.0 → 2.0 |
| 3 | `test_compose_clamps_temperature_lower` | 0.0 + (-0.5) → 0.01 |
| 4 | `test_compose_clamps_top_p_upper` | 0.95 + 0.1 → 1.0 |
| 5 | `test_compose_clamps_repeat_penalty_upper` | 1.9 + 0.2 → 2.0 |
| 6 | `test_compose_peripatetic_greater_than_zazen` | persona-erre §ルール 2 の peripatetic (+0.3) > zazen (-0.3) monotonicity |

### 7.3 回帰確認

- baseline: 134 passed / 16 skipped (T10 完了時)
- 期待: +16 前後 = **~150 passed**
- skip は 16 のまま (新規 skip なし)

## 8. 既存パターンとの整合性

- **T10 embedding.py と対称**: ClassVar / client DI / `async with` / `Unavailable` エラー
- **python-standards**: `from __future__ import annotations` / 型ヒント / google docstring / snake_case
- **test-standards**: `tests/test_inference/` ミラー構造、httpx MockTransport、
  `asyncio_mode=auto` なので `async def test_*` で OK
- **error-handling**: 例外正規化のみ実装 (retry/fallback は呼び出し側)
- **git-workflow**: `feat(inference): ...` Conventional Commits、`Refs: .steering/...`

## 9. ロールバック計画

- 3 ファイル + 3 テストファイルの新規追加のみ。`git revert` 1 コミットで完全復元
- Ollama API の将来的な変更 (`/api/chat` v2 等) には `CHAT_PATH: ClassVar[str]`
  と `_parse` static method を差し替えるだけで済む
- SGLang 追加 (M7) 時は `sglang_adapter.py` に **同じ `ChatResponse` を返す
  `SGLangChatClient`** を実装し、`inference/server.py` で選択する設計
