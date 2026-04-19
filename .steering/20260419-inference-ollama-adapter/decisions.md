# 設計判断 (Decisions)

## D1: /reimagine 適用、v2 (Contract-First) を採用

- **判断**: 初回案 v1 を破棄し、再生成案 v2 を採用
- **根拠**:
  - v1 は「error-handling Skill examples.md を直移植」するだけで、**致命 2 件**
    (クランプ漏れ波及 / 生 dict 漏洩) と **高 4 件** の弱点を抱えた
  - v2 は T10 `EmbeddingClient` と完全対称、ClassVar defaults + DI client +
    `async with` + `*Unavailable` error を踏襲
  - 比較表は `design-comparison.md` に 14 観点で記録
- **代替**: v1 を採用した場合、T12 / T14 / ui/dashboard でサンプリング合成と
  dict key 参照が 3+ 箇所で重複 → MVP 完了時点で v2 実装時間を超える手戻り
- **CSDG 参照**: なし (T10 と違い CSDG は LLM クライアント側を直接参照しない)

## D2: `/api/generate` ではなく `/api/chat` エンドポイントを採用

- **判断**: Ollama の `/api/chat` (messages 配列) を使う。`/api/generate`
  (prompt 文字列完結) は採用しない
- **根拠**:
  - ERRE-Sandbox は **system prompt (ペルソナ + AgentState) + user (観察)**
    の 2 メッセージ構造が本来の形 (persona-erre Skill §ルール 3)
  - `/api/chat` は将来の assistant history 追加 (M4+ 複数ターン会話) に自然に
    拡張できる
  - SGLang / vLLM も chat 形式を第一級でサポート → M7+ 移行時に wire 互換
  - RadixAttention の prefix KV 共有 (llm-inference Skill §ルール 2) は
    chat 形式で message prefix を共有する前提で設計されている
- **代替案却下**: `/api/generate` を採用すると `/api/chat` へのマイグレーションは
  T12 書き換え + プロンプト合成の再設計を伴う大工事になる

## D3: `ChatResponse` を Pydantic `frozen=True` 正規化、Ollama 生フィールドは破棄

- **判断**: `ChatResponse` は
  `content / model / eval_count / prompt_eval_count / total_duration_ms /
  finish_reason` の 6 フィールドのみ。Ollama の `load_duration` / `eval_duration`
  / `context` / `done` 等は捨てる
- **根拠**:
  - 「adapter 間で共通の Contract」を **最小サーフェス** で確立することで、
    SGLang / vLLM 追加時の差分吸収コストを 0 に近づける
  - `total_duration` (ns) → `total_duration_ms` に単位統一し、呼び出し側の
    単位変換ミス (ns vs ms で 1e6 倍外す) を防ぐ
  - `frozen=True` により「response を受け取った側が in-place 改変して
    次の call に渡す」悪用パターンを静的に封じる
- **代替案却下**: `diagnostics: dict | None` で全 raw キーを保持する案 →
  「最初から拡張性のためだけに重い」、M9 まで未使用のフィールドを持つのは
  YAGNI 違反。必要になれば `schema_version` bump と同時に追加
- **拡張点**: 将来 `diagnostics` フィールドを追加する際は
  `.steering/YYYYMMDD-inference-diagnostics/` で別タスク化

## D4: サンプリング合成を `inference/sampling.py` に純粋関数として分離

- **判断**: `compose_sampling(base, delta) -> ResolvedSampling` を
  `inference/sampling.py` (I/O 無し、schemas のみ依存) に置く
- **根拠**:
  - **責務境界**: `OllamaChatClient.chat(sampling: ResolvedSampling)` が
    signature で `ResolvedSampling` を要求することで、**クランプ忘れ**を
    静的型で構造的に防ぐ (V1-W1 を完全解消)
  - adapter 内に置くと SGLang adapter 追加時に重複、または `inference/` 直下の
    共通関数に refactor するコストが発生
  - schemas.py (ワイヤー契約) には置かない: `ResolvedSampling` は wire 型で
    なく内部戻り値 → schemas の「唯一の正」性を保つ
- **代替案却下**:
  - `cognition/sampling.py` に置く → MVP 時点で cognition は空、先に作ると
    architecture-rules の依存方向 (`cognition → inference`) に合わない
  - `erre/sampling.py` → `erre/` は M5+ に登場。MVP で前倒し配置するなら
    `inference/` が最も自然
- **クランプ範囲**: `[0.01, 2.0] / [0.01, 1.0] / [0.5, 2.0]` は
  `SamplingBase` の Field range と persona-erre Skill §ルール 2 に一致

## D5: `_build_body()` で sampling を options の後に上書き (事故 override 防止)

- **判断**: `merged_options = dict(options or {})` 後に `sampling.temperature /
  top_p / repeat_penalty` を代入する順序を厳格に守る
- **根拠**:
  - 呼び出し側が `options={"temperature": 1.99}` を渡しても**必ず上書きされる**
  - クランプ済み `ResolvedSampling` が最終権威 (authoritative) であることを
    コード順序で保証 (テスト `test_chat_merges_extra_options_but_sampling_wins`
    で検証)
  - 「options でサンプリングを上書きできる」仕様にするなら後から追加できるが、
    逆 (許容 → 厳格) は breaking change になる → 最初から厳格に倒す
- **代替案却下**: 呼び出し側の `options` を尊重する案 → クランプの意味が消失、
  V1-W1 の弱点が復活

## D6: エラー正規化を `OllamaUnavailableError` 1 種に畳む

- **判断**: httpx の 4 種例外 (TimeoutException / HTTPError / ValueError /
  ValidationError) を全て `OllamaUnavailableError` に再送出
- **根拠**:
  - T10 `EmbeddingUnavailableError` と**命名対称**、呼び出し側 (T12) は
    `except (OllamaUnavailableError, EmbeddingUnavailableError)` の 2 行で
    「外部 Ollama 起因の不安定性」全般を受け取れる
  - `args[0]` / `str(exc)` の substring (`'timeout'` / `'unreachable'` /
    `'HTTP 5xx'` / `'non-JSON'` / `"missing 'message.content'"` /
    `'failed to parse'`) で具体原因を識別可能
  - error-handling Skill §ルール 5 (Pydantic ValidationError の扱い) に
    従い、validation 失敗もサイレント破棄せず正規化 raise
- **代替案却下**: 個別例外型 `OllamaTimeoutError` / `OllamaHTTPError` 等 →
  呼び出し側の except 行が増える、対称性も崩れる

## D7: `DEFAULT_CHAT_MODEL = "qwen3:8b"` (T09 D1 fallback を継承)

- **判断**: デフォルトモデル tag は T09 で実際に pull した `qwen3:8b`
  (not `qwen3:8b-q5_K_M`)
- **根拠**:
  - MASTER-PLAN §6.3 は `qwen3:8b-q5_K_M` を指定していたが、T09 D1 で Ollama
    registry 未登録のため `qwen3:8b` fallback 採用済
  - T09 decisions.md で実測 VRAM 6.2 GB delta、日本語応答確認済
  - M7 で SGLang + GGUF 直接ロード (`/models/Qwen3-8B-Q5_K_M.gguf`) に切替時、
    `DEFAULT_CHAT_MODEL` を指す箇所は `OllamaChatClient.DEFAULT_MODEL` のみ
    → 1 行変更で移行可能
- **拡張点**: `llm-inference` Skill の `DEFAULT_MODEL` 推奨値と整合性を確認する
  役割は `llm-inference` Skill / `operations.md` の責務

## D8: `inference/__init__.py` で 7 シンボルを top-level re-export

- **判断**: `OllamaChatClient` / `ChatMessage` / `ChatResponse` /
  `OllamaUnavailableError` / `compose_sampling` / `ResolvedSampling` /
  `DEFAULT_CHAT_MODEL` を `erre_sandbox.inference` から直接 import 可能に
- **根拠**:
  - 呼び出し側 (T12) は内部 module path (`ollama_adapter` / `sampling`) を
    知る必要がない → リファクタリング耐性が高い
  - T10 `memory/__init__.py` が 14 シンボル re-export している前例と対称
  - 将来 SGLang adapter 追加時、`from erre_sandbox.inference import SGLangChatClient`
    で自然に公開できる (`inference/server.py` の `generate_with_fallback` も
    同じ top-level で公開予定)
- **`__all__`**: 定義済、ruff F401 の `**/__init__.py` ignore で noqa 不要

## 補足: CSDG との関係

T11 は CSDG (`csdg/llm_client.py`) の「プロバイダー抽象化パターン」の精神を
参考にしつつ、API は Ollama 向けに完全書き直し (MASTER-PLAN 付録 B.4
「LLM 呼び出しコード」取り込まない項に対応)。法的帰属義務はない。
