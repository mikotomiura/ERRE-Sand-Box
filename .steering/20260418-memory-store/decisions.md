# Decisions

## D1. kind 別テーブル + 共有 vec0 + 関数 decay (v2) を採用

- **日付**: 2026-04-18 (設計段階)
- **判断**: memory/ のストレージ構造は「4 kind 分のコンテンツテーブル + `vec_embeddings` vec0 virtual table + 関数としての strength 算出」を採用。単一 `memory_entries` テーブル案 (v1) は不採用。
- **背景**: `/reimagine` で初回案 (v1: 単一テーブル + embedding BLOB 同居 + strength カラム) を破壊し、v2 を再生成。5 項目 (W1-W5) で v1 が v2 に劣る (design.md §2.1 参照)。特に:
  - `strength` を DB カラムにすると更新漏れで rot する (CSDG 半数式と同じ罠)
  - BLOB embedding では sqlite-vec の `vec_distance_l2` KNN が使えない → 強みを捨てる
  - Semantic は short text + struct、Procedural は zone key lookup と、kind ごとに自然な schema が違う
  - Relational memory は AgentState.relationships と SoT 分離が必要 (Park et al. 2023 整合)
- **採用理由**:
  1. sqlite-vec の `vec0` virtual table を正しく使える (KNN primitive)
  2. kind ごとに最小固有スキーマ → 将来の拡張 (belief struct 化、zone FK) が breaking change にならない
  3. strength が関数であれば単体テストで純粋関数として検証可能 (`score()`)
  4. Qdrant 等への段階的移行 (Episodic だけ先) が後から可能
- **トレードオフ**: 4 テーブル + 1 vec0 の初期 DDL が長い。`create_schema()` を atomically 実行する 1 関数に閉じ込めることで可読性を確保。
- **ロールバックトリガー**: M4 reflection 実装時に「kind 別で UNION ALL が多発して boilerplate 増」「Semantic テーブルが実運用で belief struct を持てずに rot」などが発生したら、`MemoryStore` を再設計 (v3: belief/theme を独立ドメイン型として schemas.py に追加)。
- **反映先**: `design.md §1 / §3`, `tasklist.md` の実装節、`src/erre_sandbox/memory/__init__.py` の docstring、テスト 4 kind 分離ケース

## D2. decay / recall のハイパラ初期値 (λ=0.1, β=0.2)

- **日付**: 2026-04-18
- **判断**: `score()` の初期値を `decay_lambda = 0.1` (半減期 ≈ 7 日) と `recall_boost = 0.2` に設定。将来は tick 単位に再校正する。
- **背景**: architecture.md §Memory Layer で `strength = importance * exp(-λ*days) * (1 + recall_count*0.2)` が明記されており、`recall_count` 係数は 0.2 が正典。`λ` は文書未指定のため、Park et al. (2023) の Generative Agents が「半減期 1 日」前後を採用している範囲と、ERRE-Sandbox が「10 秒 tick × 数日運用」を想定していることから、**半減期 7 日** を採用 (λ ≈ ln(2)/7 ≈ 0.099 → 0.1 に丸め)。
- **採用理由**:
  1. docs/architecture.md の `recall_count*0.2` が唯一明示されている係数 → そのまま β=0.2
  2. λ=0.1 は M4 (3 体対話・反省) の数日運用で、直近 1-2 日の記憶が支配的になりつつ、過去の重要イベントを完全に消さない曲線
  3. 実データで再校正する場合は `score()` 引数で差し替え可能 (ハードコード不要)
- **トレードオフ**: 10 秒 tick 単位の実サイクルでは 1 日 = 8640 tick のため、長期運用で λ*days の days 側を「tick 基準」に置き換える版が必要になる可能性あり。T13 world-tick-zones で tick ↔ wall-clock の対応が固まった段階で再評価。
- **反映先**: `retrieval.py` の `Retriever.__init__` デフォルト、`score()` 関数の kwargs

## D3. Procedural / Relational は最小テーブルのみ、rich 実装は後回し

- **日付**: 2026-04-18
- **判断**: T10 のスコープ内で Procedural / Relational memory はテーブル DDL と `add/get/list_by_agent` のみを実装する。以下は後続タスクに回す:
  - Procedural の trigger detection (zone 入室で発火、手順実行で重要度昇格) → M5 `erre-mode-fsm`
  - Relational と `AgentState.relationships` の双方向同期 → T12 `cognition-cycle-minimal`
- **採用理由**:
  1. MVP (M2) では Kant 1 体歩行で他者がいない → Relational memory の実データが存在しない
  2. Procedural の trigger は ERRE モード FSM (M5) 側の責務が大きく、T10 で先取りすると over-engineering
  3. スキーマ DDL だけ先に固めておけば、T11 / T12 で使い始める段階で breaking change なく参照できる
- **トレードオフ**: 2 テーブルが空のまま M4 まで残る。データベースサイズは無視できる (~0 MB)。
- **反映先**: `store.py` で 4 テーブルすべてを `create_schema()` に含める、`__init__.py` の re-export は全 kind 共通 API、テストは Episodic/Semantic を厚めに、Procedural/Relational は 1 ケースずつ round-trip のみ

## D5. 埋め込みはプレフィックス付与を強制 (QUERY / DOC 区別)

- **日付**: 2026-04-18 (T09 nomic-embed-text pull 完了後のアメンド)
- **判断**: `EmbeddingClient` は `embed_query(text)` と `embed_document(text)` を第一級 API として公開し、それぞれ `"search_query: "` と `"search_document: "` プレフィックスを自動付与する。低レベル `embed(text)` は明示利用のみ (Retriever からは呼ばない)。
- **背景**: nomic-embed-text-v1.5 は Contrastive Learning で訓練されており、検索用クエリと保存用ドキュメントは異なるプレフィックスを付与することで学習時分布に合わせる設計になっている。プレフィックスミスマッチは recall で 5-15 ポイント劣化することが CSDG 実装でも観測されている (test-standards Skill §ルール 6 の警告と整合)。
- **採用理由**:
  1. test-standards Skill §ルール 6 で `tests/test_memory/test_embedding_prefix.py` が **CI 必須、削除禁止** と明記されている
  2. 呼び出し側 (`Retriever.retrieve()` がクエリ、`MemoryStore.add()` 経由でドキュメント) の意図が型レベルで分離できる
  3. 将来 multilingual-e5 や bge-m3 等に切替える際も、プレフィックス定数を 1 行書き換えるだけで済む
- **プレフィックス仕様**:
  - `QUERY_PREFIX = "search_query: "` (nomic-embed-text-v1.5 規約)
  - `DOC_PREFIX   = "search_document: "`
  - 将来モデル切替時: multilingual-e5 → `"query: "` / `"passage: "`、bge-m3 → プレフィックス不要 (空文字列)
- **トレードオフ**: `embed()` 低レベル API も残すため API 面積が 3 メソッドに増える。明確に「高レベル優先、低レベルは明示利用」のドキュメントで混乱を防ぐ。
- **反映先**: `design.md §3.2 / §7`, `tasklist.md` embedding.py 実装節、`test_embedding_prefix.py` の新規追加

## D4. 本セッションのスコープは設計確定まで (実装は次セッション)

- **日付**: 2026-04-18
- **判断**: 本セッション (T09 と並行稼働中) では T10 の **requirement / design / tasklist / decisions のみ** を確定し、`src/erre_sandbox/memory/*.py` の実装コードは次セッションに回す。
- **採用理由**:
  1. T10 は 1.5d のタスク (MASTER-PLAN §4.2) で、実装・テスト・レビューまで含めると 1 セッションに収まらない
  2. T09 の BG pull (qwen3:8b 5.2 GB) が完了するまで待つ時間を、設計品質の向上に充てるのが合理的
  3. 設計確定まで push できれば MacBook 側からもレビュー可能
  4. 実装段階で /add-feature コマンド + `implementation-workflow` Skill + code-reviewer / test-runner エージェントを本格投入する流れが、CLAUDE.md 推奨の順序 (Plan → Execute) に整合
- **トレードオフ**: Critical Path 上の T10 → T11 → T12 の実装スタートが 1 セッション分遅れる。ただし T09 pull の 20-30 分は実装タイムラインに組み込まれる想定 (MASTER-PLAN R1 想定値内)。
- **反映先**: tasklist.md の「実装 (次セッション)」明記、git commit は設計成果物のみ (v0.1 ではない、まだ実装は ∅)
