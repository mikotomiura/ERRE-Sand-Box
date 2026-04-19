# 設計 v1 (初回案) — 素直に error-handling Skill の例を採用

> **状態**: 破棄 (reimagine 後)
> この v1 を破壊して v2 を再生成した結果 `design-comparison.md` で比較し、
> `design.md` に採用版 (v2) を記録する。

## 1. 全体構造

```
src/erre_sandbox/inference/
├── __init__.py               # re-export
├── ollama_adapter.py         # module-level `generate()` 関数
└── sglang_adapter.py         # M7+ で追加、同じ形の `generate()` を提供
```

error-handling Skill の `examples.md` §例 1 をほぼコピーし、Ollama 版だけ
実装する。SGLang と `generate_with_fallback()` は後続タスクで追加する。

## 2. モジュール API

### 2.1 `inference/ollama_adapter.py`

```python
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen3:8b"
OLLAMA_TIMEOUT = 60.0


async def generate(
    prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7,
    top_p: float = 0.9,
    **kwargs: Any,
) -> dict[str, Any]:
    """Generate via Ollama with timeout."""
    async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature, "top_p": top_p, **kwargs},
            },
        )
        response.raise_for_status()
        return response.json()
```

### 2.2 `inference/__init__.py`

```python
"""LLM inference adapters (SGLang / Ollama) — depends on ``schemas`` only."""
from erre_sandbox.inference.ollama_adapter import generate as ollama_generate

__all__ = ["ollama_generate"]
```

### 2.3 サンプリング合成

**v1 では分離せず**、`generate()` の引数 (temperature / top_p / **kwargs) に
ERRE モードの加算済み値を「呼び出し側で計算して」渡す。

```python
# v1 での想定呼び出し側 (cognition/cycle.py)
temperature = base_temperature + erre_mode.sampling_overrides.temperature
top_p = base_top_p + erre_mode.sampling_overrides.top_p
temperature = max(0.01, min(2.0, temperature))  # クランプもここ
top_p = max(0.01, min(1.0, top_p))

result = await ollama_generate(prompt, temperature=temperature, top_p=top_p)
content = result["response"]  # Ollama /api/generate の生 JSON キー
```

## 3. エラーハンドリング

`response.raise_for_status()` に任せ、`TimeoutError` / `ConnectionRefusedError` /
`OSError` は呼び出し側で catch する前提 (error-handling Skill の例どおり)。

```python
# 呼び出し側で
try:
    result = await ollama_generate(prompt, ...)
except (TimeoutError, ConnectionRefusedError, OSError, httpx.HTTPStatusError) as e:
    logger.warning("Ollama failed: %s", e)
    # ... fallback or skip
```

## 4. テスト戦略

`tests/test_inference/test_ollama_adapter.py`:
- `test_generate_returns_dict` — httpx.MockTransport で 200 応答、`response` キー抽出
- `test_generate_sends_options` — captured payload の `options.temperature` 確認
- `test_generate_5xx_raises_httpstatus_error` — 500 → `httpx.HTTPStatusError`
- `test_generate_connect_error_propagates` — ConnectError → そのまま propagate

## 5. 弱点 (v1 を破壊する理由)

| # | 弱点 | 深刻度 | 破壊の必要性 |
|---|---|---|---|
| V1-W1 | サンプリング合成とクランプを**呼び出し側** (cognition/cycle.py、T12) にぶら下げる → ERRE モード N 種 × 呼び出し箇所 M 箇所で重複発生、忘れた箇所でクランプ漏れ = VRAM overflow や temperature 2.1 の致命事故 | 致命 | Yes |
| V1-W2 | **Contract の欠落**: 呼び出し側は `result["response"]` のような生辞書 key を直接触る。Ollama 側 API 仕様変更 (`/api/chat` に移行したい等) で全呼び出し箇所が壊れる | 致命 | Yes |
| V1-W3 | `/api/generate` は単純 prompt 完結 mode。ペルソナ (system) + 観察 (user) の 2 メッセージ構造は `/api/chat` が本来の場所。system prompt を prompt 先頭に連結する ad-hoc 解では RadixAttention の prefix 共有 (llm-inference Skill) の恩恵を捨てる | 高 | Yes |
| V1-W4 | `SamplingBase` / `SamplingDelta` (T05 で凍結済) を完全スキップ。代わりに float 4 個をバラで渡す → 型安全性が消え、`repeat_penalty` を忘れるバグが起きやすい | 高 | Yes |
| V1-W5 | エラーを正規化しない (httpx.HTTPStatusError / ConnectError / TimeoutException / ValueError(JSON) が全て違う例外型で漏れる) → 呼び出し側で 4 種の except を書く必要があり忘れる | 中 | Yes |
| V1-W6 | `OLLAMA_BASE_URL` / `DEFAULT_MODEL` / `OLLAMA_TIMEOUT` を **module-level 定数**で直に書いている → テストで差し替えるには `monkeypatch` 必要 (T10 の EmbeddingClient は ClassVar + コンストラクタ注入で解決済み、こちらだけ乖離) | 中 | Yes |
| V1-W7 | `httpx.AsyncClient` を `async with` で毎回生成 → 高頻度呼び出し時にコネクション張り直しコスト。テストでも MockTransport を差し込めない (T10 は client 注入可能) | 中 | Yes |
| V1-W8 | SGLang adapter を追加する時、共通 `ChatResponse` 型がないため `generate_with_fallback()` が `dict[str, Any]` レベルで合成 → type 安全性なし、SGLang と Ollama の JSON 差分の吸収が散在 | 高 | Yes |
| V1-W9 | **タスクとの責務境界が曖昧**: "ペルソナ sampling の合成" は T11 / T12 / persona-erre のどこで行うのかが決まらない → ユニットテストを書く場所が決まらない | 中 | Yes |
| V1-W10 | logger 設定が module-level `logger = logging.getLogger(__name__)` のみで、ログに含めるべき context (agent_id / model / eval_count) が抜けやすい | 低 | 部分的 Yes |

### 弱点サマリ

致命: **V1-W1, V1-W2** (Contract 破綻)
高: V1-W3, V1-W4, V1-W5, V1-W8 (型安全性と Ollama/SGLang 互換)
中: V1-W6, V1-W7, V1-W9, V1-W10

→ **v1 をそのまま採用すると、T12 以降で呼び出し側に同じ変換ロジックが
4-6 箇所ばらまかれる**。Contract-First 原則 (MASTER-PLAN §2.2) の失効。

## 6. v1 を破棄して v2 を再生成する

/reimagine でゼロから再設計。観点:

1. サンプリング合成を **T11 の中** に閉じ込める (クラス or 純粋関数)
2. Ollama 生辞書を Pydantic `ChatResponse` で正規化 (Contract)
3. `/api/chat` (messages) API に揃え、M7 SGLang へのスムーズな移植
4. エラーを `OllamaUnavailableError` 一種に正規化 (T10 `EmbeddingUnavailableError` と統一)
5. `httpx.AsyncClient` を DI、コンテキストマネージャ、ClassVar defaults (T10 と整合)

再生成結果は `design.md` (本採用版) と `design-comparison.md` (比較表) を参照。
