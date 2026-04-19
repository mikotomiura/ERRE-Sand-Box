# T11 inference-ollama-adapter — タスクリスト

採用設計 (v2) に基づく。各タスクは **30 分以内** を目安に粒度分割。

## Step A/B/C ✓ (完了)
- [x] llm-inference / error-handling / architecture-rules / persona-erre Skill Read
- [x] docs/architecture.md / pyproject.toml / schemas.py / T10 embedding.py の参照
- [x] MASTER-PLAN T11 スコープと依存 (T08/T09) 確認
- [x] requirement.md 記述
- [x] design-v1.md (素直案 + 10 弱点列挙)
- [x] /reimagine → v2 再生成 → design-comparison.md → **v2 採用**
- [x] design.md に v2 を記録

## Step D ✓
- [x] tasklist.md を v2 設計に即して分解 (本ファイル)

## Step E: 実装

### E-1: sampling.py 新規作成
- [ ] `src/erre_sandbox/inference/sampling.py` 作成 (~80 行)
      - [ ] module docstring (pure composition, no I/O)
      - [ ] `Final` 定数 6 個 (_TEMPERATURE_MIN/MAX, _TOP_P_MIN/MAX, _REPEAT_PENALTY_MIN/MAX)
      - [ ] `ResolvedSampling(BaseModel, frozen=True)` (extra=forbid, Field range)
      - [ ] `_clamp(value, lo, hi) -> float`
      - [ ] `compose_sampling(base, delta) -> ResolvedSampling`
      - [ ] `__all__ = ["ResolvedSampling", "compose_sampling"]`

### E-2: ollama_adapter.py 新規作成
- [ ] `src/erre_sandbox/inference/ollama_adapter.py` 作成 (~240 行)
      - [ ] module docstring (T09 D1 モデル, Contract-First)
      - [ ] `DEFAULT_CHAT_MODEL: Final[str] = "qwen3:8b"`
      - [ ] `ChatMessage(BaseModel, frozen=True)` role/content
      - [ ] `ChatResponse(BaseModel, frozen=True)` content/model/eval_count/
            prompt_eval_count/total_duration_ms/finish_reason
      - [ ] `OllamaUnavailableError(RuntimeError)`
      - [ ] `OllamaChatClient` クラス
            - [ ] ClassVar: `DEFAULT_MODEL`, `DEFAULT_ENDPOINT`, `DEFAULT_TIMEOUT_SECONDS`, `CHAT_PATH`
            - [ ] `__init__(*, model, endpoint, timeout, client)` + `_owns_client` flag
            - [ ] `__aenter__ / __aexit__ / close`
            - [ ] `async chat(messages, *, sampling, model, options) -> ChatResponse`
            - [ ] `_build_body(messages, sampling, model, options)` — sampling を options の後に上書き (事故 override 防止)
            - [ ] `_post(body)` — httpx エラー → `OllamaUnavailableError` 正規化 (TimeoutException → HTTPError の順)
            - [ ] `_parse(payload)` @staticmethod — `message.content` 抽出、ChatResponse 組立、ValidationError 正規化
      - [ ] `__all__ = [5 シンボル]`

### E-3: __init__.py 差し替え
- [ ] `src/erre_sandbox/inference/__init__.py`
      - [ ] docstring 更新 (公開サーフェス明記)
      - [ ] 7 シンボル re-export
      - [ ] `__all__` 完備

### E-4: テスト package 準備
- [ ] `tests/test_inference/__init__.py` (空)

### E-5: test_sampling.py 新規作成
- [ ] `tests/test_inference/test_sampling.py` (~90 行)
      - [ ] 6 テスト (v2 design.md §7.2 のリスト順)
      - [ ] pytest.approx で float 比較

### E-6: test_ollama_adapter.py 新規作成
- [ ] `tests/test_inference/test_ollama_adapter.py` (~220 行)
      - [ ] helpers: `_ok_handler` / `_err_handler` / `_make_client` (T10 と同形)
      - [ ] 10 テスト (v2 design.md §7.1 のリスト順)
      - [ ] captured request body を list に詰めて後から検証

### E-7: tasklist 更新
- [ ] 実装完了タスクを順次チェック

## Step F: テストと検証
- [ ] `uv run pytest tests/test_inference -v` (新規 16 件、全 pass)
- [ ] `uv run pytest tests/` 全体緑 (134 → ~150 passed、skip 16 維持)
- [ ] `uv run ruff check .` 緑
- [ ] `uv run ruff format --check .` 緑
- [ ] `uv run mypy src tests` 緑
- [ ] 依存方向確認: `grep -r "from erre_sandbox" src/erre_sandbox/inference/` で
      schemas と inference.sampling のみ

## Step G: code-reviewer
- [ ] `code-reviewer` サブエージェント起動 (Opus)
- [ ] HIGH → 必ず修正 / MEDIUM → ユーザー/decisions 判断 / LOW → blockers.md

## Step H: security-checker (軽量)
- [ ] Ollama への任意 URL (endpoint 注入) が呼び出し側で制御可能か確認
- [ ] 空メッセージ配列 / 巨大 content サイズの DoS 可能性
- [ ] `security-checker` 起動 (200 行以内のレポート依頼)

## Step I: ドキュメント更新
- [ ] `.steering/_setup-progress.md` Phase 8 に T11 エントリ追加
      (採用スキーマ、行数、設計判断件数を記録)
- [ ] `docs/functional-design.md` / `docs/glossary.md` 更新判断 (不要なら省略)
- [ ] `.steering/20260419-inference-ollama-adapter/decisions.md` 作成

## Step J: コミットと PR
- [ ] `git checkout -b feature/inference-ollama-adapter`
- [ ] 単一 feat コミット: `feat(inference): T11 inference-ollama-adapter —
      Ollama /api/chat + ERRE sampling compose`
- [ ] `Co-Authored-By: Claude Opus 4.7 (1M context)` + `Refs:` 付与
- [ ] `git push -u origin feature/inference-ollama-adapter`
- [ ] `gh pr create` で PR 作成

## 完了処理
- [ ] decisions.md 作成 (設計判断 5+ 件)
- [ ] blockers.md 作成 (LOW 懸案のみ必要時)
- [ ] `/finish-task` で最終化

## ブロッカー候補 (発生時に blockers.md へ)
- Ollama `/api/chat` の実応答フォーマットが想定と異なる (実サーバーで wire
  ログ 1 回確認)
- httpx `TimeoutException` / `HTTPError` の継承関係で catch 順が逆転する
- pydantic v2 `model_config = ConfigDict(frozen=True)` と `extra="forbid"` の
  同時指定時の既知 issue
- mypy strict で `Sequence[ChatMessage]` を `list[dict]` に変換する dump
  結果の型推論が厳しすぎる
