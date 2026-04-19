# design-comparison — v1 (素直案) vs v2 (Contract-First)

## サマリ

- **採用**: v2 (Contract-First OllamaChatClient + 分離 sampling)
- **破棄**: v1 (error-handling Skill example の直移植)
- **判断根拠**: v1 は致命弱点 2 件と高弱点 4 件を構造的に抱え、T12+ で波及する

## 比較表

| 観点 | v1 (素直案) | v2 (Contract-First) | 勝者 |
|---|---|---|---|
| **API 形式** | module-level `generate(prompt, temperature, top_p, **kwargs)` | `OllamaChatClient.chat(messages, *, sampling, options)` | **v2** |
| **Ollama endpoint** | `/api/generate` (prompt 完結) | `/api/chat` (system + user messages) | **v2** (RadixAttention 前向き) |
| **Response 型** | `dict[str, Any]` 生 | `ChatResponse(BaseModel, frozen=True)` | **v2** |
| **サンプリング合成** | **呼び出し側の責務** (T12, T14 で重複) | `compose_sampling()` 純粋関数で一元化 | **v2** |
| **サンプリングクランプ** | 呼び出し側に散在、忘れると VRAM overflow | `ResolvedSampling` の Field range で静的担保 | **v2** |
| **ERRE mode `SamplingDelta` 型** | 使わない (float をバラで渡す) | T05 で凍結済の型をそのまま受ける | **v2** |
| **エラー表現** | httpx の 4 種例外が漏れる | `OllamaUnavailableError` 1 つに正規化 (T10 と統一) | **v2** |
| **httpx.AsyncClient の扱い** | 毎回 `async with` で新規生成 | DI 可能 + 所有権管理 (T10 と同形) | **v2** |
| **テスト容易性** | MockTransport 差し込み不可 (毎回 new) | `httpx.MockTransport` を直接注入 | **v2** |
| **SGLang (M7+) への互換性** | `dict[str, Any]` で差分吸収を後回し | `ChatResponse` を共通型として確立、`SGLangChatClient` は drop-in | **v2** |
| **実装行数** | ~60 行 | ~320 行 | v1 |
| **学習コスト (新規参加者)** | 1 関数で完結、読みやすい | 3 ファイル + Pydantic 型、最初に 15 分かかる | v1 |
| **既存パターン整合 (T10)** | 乖離 (module-level vs class) | 完全対称 (EmbeddingClient と同形) | **v2** |
| **依存方向違反リスク** | 低 (schemas を使わないので) | 低 (schemas のみを使う) | 同等 |

## v1 弱点の v2 解消マッピング

| v1 弱点 | 深刻度 | v2 での解消方法 | 完全解消? |
|---|---|---|---|
| V1-W1 クランプ漏れ波及 | 致命 | `ResolvedSampling` Field range + `compose_sampling()` 一元化 | **完全** |
| V1-W2 生 dict 漏洩 | 致命 | `ChatResponse(BaseModel, frozen=True)` で境界を閉じる | **完全** |
| V1-W3 `/api/generate` 依存 | 高 | `/api/chat` に切替、messages 配列 API | **完全** |
| V1-W4 `SamplingBase/Delta` スキップ | 高 | `compose_sampling()` が `SamplingBase + SamplingDelta` を型で要求 | **完全** |
| V1-W5 例外非正規化 | 中 | `OllamaUnavailableError` 1 つに畳む | **完全** |
| V1-W6 定数ハードコード | 中 | `ClassVar` (T10 と同形) で DI 可 | **完全** |
| V1-W7 client 毎回 new | 中 | コンストラクタで DI、所有権フラグ管理 | **完全** |
| V1-W8 SGLang 互換差分 | 高 | `ChatResponse` を共通型として宣言、`SGLangChatClient` は同型を返す | **完全** (契約のみ、実装は M7) |
| V1-W9 責務境界曖昧 | 中 | T11 = 1 backend + sampling compose、T12 = retry + 構造化 parse、T14 = fallback、と明示 | **完全** |
| V1-W10 log context 欠落 | 低 | T14 で logger を集約する方針に統一 | 部分的 (T11 では未対応) |

## v2 が背負うトレードオフと mitigation

### T1: 実装行数の増加 (60 → 320 行)

- mitigation: そのうち ~180 行は Pydantic/docstring/型ヒントで可視的に機能する
  「自己文書化」に近い。T10 EmbeddingClient (150 行) と同等の密度
- 新規参加者の初回コストは ~15 分増だが、**毎 tick 呼び出しの cognition 実装
  コスト** が劇的に下がる (sampling を忘れられない、error catch を忘れられない)

### T2: 3 ファイル構成

- mitigation: `inference/__init__.py` で 7 シンボル re-export。呼び出し側は
  `from erre_sandbox.inference import OllamaChatClient, compose_sampling, ChatMessage`
  で完結、内部 module path を気にしない

### T3: `ChatResponse` が Ollama 固有フィールドを削ぎ落とす

- `prompt_eval_count` / `eval_count` / `total_duration_ms` だけ保持、
  `total_duration` (ns) / `load_duration` / `eval_duration` は捨てる
- mitigation: パフォーマンス監視が必要になれば `diagnostics: dict | None`
  フィールドを後から足せる (Pydantic `extra="forbid"` のまま `diagnostics` 追加
  は schema_version bump 1 回で対応可能)

### T4: `compose_sampling` が `inference/` に置かれる

- 責務論としては `schemas.py` か `inference/` かで悩む
- 採用理由: `ResolvedSampling` は**ワイヤー契約ではなく内部戻り値型**なので、
  schemas.py (ワイヤーの唯一の正) には置かない
- 代替案 (mitigation): `erre/sampling.py` も考えたが、MVP では `erre/` 自体が
  存在しない (M5+)。`inference/` が最も自然な居場所

## 判定

**v2 を採用** (decisions.md D1 に記録)。

- v1 の致命 2 弱点は呼び出し側コードベースで波及する (cognition/cycle.py、
  gateway/server.py、ui/dashboard.py のそれぞれで sampling 合成 + dict key 参照
  が重複) → MVP 完了時点で 3+ 箇所の手戻りコストが v2 実装時間を超える試算
- v1 の利点 (行数) は**密度の低さ** (docstring と型定義で占められる)、実機能
  差ではない
- T10 embedding.py が v2 相当の構造で実装済み → v1 を採ると対称性を壊し、
  レビュー時の混乱を生む
