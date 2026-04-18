# タスクリスト

## 準備 (本セッション完了分)
- [x] docs/architecture.md §Memory Layer / §Memory Stream を読む
- [x] docs/repository-structure.md §1 / §4 で memory/ 配置と依存方向を確認
- [x] src/erre_sandbox/schemas.py §6 MemoryEntry / MemoryKind を確認 (埋め込み非含有・Contract 凍結済み)
- [x] .claude/skills/architecture-rules/SKILL.md で依存禁止リストを確認
- [x] .steering/20260418-implementation-plan/MASTER-PLAN.md §4.2 T10 / 付録 B.2 B.5 を読む
- [x] /reimagine 適用: v1 (単一テーブル) vs v2 (kind 別 + vec0) を比較、v2 採用 (decisions.md D1)
- [x] `git checkout -b feature/memory-store`

## 実装 (次セッション)

### store.py
- [ ] `MemoryStore.__init__` で sqlite-vec ロード、connection 確立
- [ ] `create_schema()`: 4 kind content テーブル + vec0 virtual table を atomically 作成
- [ ] `add(entry, embedding)`: 対応 kind テーブル insert + vec0 insert (embedding が None なら vec0 skip)
- [ ] `get_by_id(id)`: 4 kind テーブルを UNION ALL で探索、最初のヒットを MemoryEntry に復元
- [ ] `list_by_agent(agent_id, kind, limit)`: kind テーブルから agent_id フィルタ、created_at DESC で返却
- [ ] `mark_recalled(ids)`: recall_count++ & last_recalled_at=now (4 テーブル横断)
- [ ] `evict_episodic_before(agent_id, tick_cutoff)`: episodic_memory から抽出 (source_observation_id 経由、または created_at に変換)
- [ ] `close()`: connection 終了

### embedding.py
- [ ] `EmbeddingClient.__init__`: httpx.AsyncClient、endpoint / model デフォルト
- [ ] `embed(text)`: POST `/api/embed`、`{"model":..., "input":text}` → response の `embeddings[0]` を返す
- [ ] `embed_many(texts)`: 入力が list の場合の一括 embed (Ollama は list input 対応)
- [ ] `EmbeddingUnavailableError` と httpx 例外の wrap
- [ ] `close()`: client.aclose()

### retrieval.py
- [ ] `score()`: `importance * exp(-λ*age_days) * (1 + β*recall_count) * cosine_sim`
- [ ] `cosine_similarity(a, b)`: numpy で dot / (norm*norm)
- [ ] `Retriever.retrieve()`:
  - クエリを embed
  - 指定 kinds 分だけ store.list_by_agent で agent_id 候補取得
  - world-scope は agent_id != 自分の entries (別 API 追加が必要)
  - 全候補を cosine 計算 + score()
  - 上位 k_agent + k_world を返却
  - retrieve の最後に store.mark_recalled(返却 id 群)

### __init__.py
- [ ] public re-export: MemoryStore, EmbeddingClient, EmbeddingUnavailableError, Retriever, score

## テスト (次セッション)

- [ ] `tests/test_memory/__init__.py` 空ファイル作成
- [ ] `tests/test_memory/conftest.py`: `in_memory_store`, `fake_embedding_client` fixture
- [ ] test_store.py 5 ケース実装
- [ ] test_embedding.py 2 ケース実装 (httpx mock)
- [ ] test_retrieval.py 3 ケース実装
- [ ] `uv run pytest tests/test_memory/` でローカル緑
- [ ] `uv run pytest` 全体で 96 + 10 前後 = ~106 passed を確認

## レビュー (次セッション)
- [ ] code-reviewer エージェントで store.py の SQL injection 有無、async の正しさをレビュー
- [ ] security-checker で embedding のネットワーク呼び出しに credential 漏れがないか確認
- [ ] architecture-rules 遵守確認 (`grep "from erre_sandbox\." src/erre_sandbox/memory/`)

## ドキュメント (次セッション)
- [ ] 必要なら docs/architecture.md §Memory Layer に「nomic-embed-text 768 次元」「kind 別テーブル + vec0」を追記
- [ ] glossary 追加は不要 (新用語なし)

## 完了処理 (次セッション)
- [ ] `.steering/_setup-progress.md` の T10 を `[x]` 更新、採用スキーマ / 行数 / テスト数 を記録
- [ ] `decisions.md` の D2 (λ・β 初期値) と D3 (将来マイグレーション方針) を記入
- [ ] `git add` → `git commit -m "feat(memory): T10 memory-store — sqlite-vec + 2-scope retrieval"`
- [ ] `git push -u origin feature/memory-store`
- [ ] PR 作成 (GitHub Web UI)
