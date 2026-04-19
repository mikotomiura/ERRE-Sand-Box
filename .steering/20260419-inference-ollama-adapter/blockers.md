# ブロッカー / 保留懸案

本タスクで解消しなかった LOW 指摘と、後続タスクへ送る観察事項のメモ。

## BL-1: T10 `EmbeddingClient` の timeout 分岐が未分離 (code-reviewer HIGH-1)

- **内容**: T11 は `httpx.TimeoutException` と `httpx.HTTPError` を別メッセージに
  分岐するが、T10 `memory/embedding.py` は `httpx.HTTPError` 一本で catch し、
  timeout も "unreachable" として扱われる
- **影響**: T14 (gateway / server.py) で 2 つのアダプタを統合する際、timeout と
  接続断の区別が片側 (Ollama chat) にしかない。フォールバック判定の粒度が非対称
- **優先度**: LOW (T11 スコープ外、reviewer も "T11 側は変更不要" と明言)
- **対処**: **T11 では対応しない**。後続で `.steering/YYYYMMDD-embedding-timeout-branch/`
  として T10 改修タスクを切る候補として記録のみ

## BL-2: `response.text[:200]` のエラーボディ漏洩 (security MEDIUM-1)

- **内容**: HTTP 非 200 時に `response.text[:200]` をそのまま `OllamaUnavailableError`
  メッセージに載せる (`_post` 内)。将来 Ollama がリクエストボディをエコーバックする
  ケースで ペルソナプロンプト断片が漏れる可能性
- **影響**: LAN 内個人研究ツール前提では実害なし。T14 が例外メッセージを外部
  HTTP レスポンスにそのまま返す実装にしたらリスク顕在化
- **優先度**: LOW (LAN 個人利用 + reviewer/security-checker ともに "T14 設計時に
  対処" を推奨)
- **対処**: T14 `.steering/YYYYMMDD-gateway-fastapi-ws/design.md` で「adapter 例外
  は外部 HTTP レスポンスに透過しない」旨を明文化する

## BL-3: `done_reason` 未知値のサイレントフォールバック (code-reviewer LOW-8)

- **内容**: `_parse()` は `"length"` 以外を `"stop"` に正規化する。将来 Ollama が
  `"error"` / `"cancelled"` / `"tool_calls"` を返した場合、静かに `"stop"` に
  化ける
- **影響**: diagnostics の精度低下。M5+ で streaming / tool_calls を扱う段階で
  見直しが必要
- **優先度**: LOW
- **対処**: MVP では現状維持。streaming 対応タスク (M5+) で `ChatResponse.finish_reason`
  を `Literal["stop", "length", "tool_calls", "cancelled", "unknown"]` に拡張し、
  `_parse` で未知値を `"unknown"` に正規化 + DEBUG ログを出す方針

## BL-4: `ChatMessage.content` に長さ制限がない (security LOW-6)

- **内容**: 巨大 content (数 MB) を渡すと httpx 側で POST される。ローカルでは
  Ollama が応答不能になる程度、実害なし
- **影響**: LAN 個人利用では自己 DoS のみ成立
- **優先度**: LOW
- **対処**: M4+ で WebSocket 経由の外部入力が始まる場合に `ChatMessage` に
  `max_length` バリデーションを追加検討。T11 では対応しない

## BL-5: `options` dict の allowlist 化 (security LOW-4)

- **内容**: `options` の任意キーが透過で Ollama に渡る (`num_gpu` / `numa` /
  `mmap` などリソース制御パラメータも通る)。sampling 3 値は上書き保護されている
- **影響**: LAN 個人利用では呼び出し元が自身のコードのみなので実害なし
- **優先度**: LOW
- **対処**: MVP では現状維持。将来外部入力を受ける場合は `_build_body()` で
  allowlist (`num_ctx`, `num_predict`, `stop`, `seed`, `num_keep`) を実装

---

## 完全解消済み (参考)

| reviewer / security 指摘 | 優先度 | 対処 |
|---|---|---|
| HIGH-2 `close()` idempotency | HIGH | `is_closed` ガード追加、`test_close_is_idempotent` 追加 |
| MEDIUM-4 / security-2 `payload!r` 漏洩 | MEDIUM | `sorted(payload.keys())` に切り詰め |
| MEDIUM-3 `total_duration_ms=0.0` の曖昧性 | MEDIUM | docstring 追記 (best-effort 明記) |
| MEDIUM-5 `close()` idempotent test 欠落 | MEDIUM | test 追加 |
| MEDIUM-6 `repeat_penalty` 下限テスト欠落 | MEDIUM | test 追加 |
| MEDIUM-7 `top_p` 下限テスト欠落 | MEDIUM | test 追加 |
| LOW-10 `ResolvedSampling` 直接構築誘惑 | LOW | docstring に "Construct via compose_sampling" 追記 |
| LOW-11 `_make_client` が `async def` | LOW | `def` に変更 + `await` 除去 |
