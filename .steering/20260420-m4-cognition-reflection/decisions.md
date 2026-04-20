# Decisions — m4-cognition-reflection

## D1. `/reimagine` 適用
v1 (inline step 10 + ClassVar policy) → v2 (Reflector collaborator +
ReflectionPolicy pure dataclass + per-agent counter) を採用。
詳細は `design.md` 末尾 / `design-comparison.md`。

## D2. per-agent tick counter (not `tick % N`)
- **判断**: `Reflector._ticks_since_last: dict[agent_id, int]` で計数、
  発火時のみ 0 リセット
- **理由**: #6 multi-agent orchestrator で agent ごとに tick がずれる可能性
  (agent 追加・削除・再同期) に対し、`tick % N` は偽発火 / 発火漏れを
  生む。counter は "episodic experience の累積" という意味論に直結し、
  multi-agent でも単 agent でも同一コードで通用
- **トレードオフ**: Reflector が per-agent state を持つため "pure object"
  ではなくなる。policy は pure のまま分離

## D3. counter リセットは成功時のみ
- **判断**: `maybe_reflect` が `ReflectionEvent` を返した (persist 成功) 場合
  のみ counter = 0、それ以外 (policy decline / LLM outage / embedding
  outage / upsert 失敗) は counter 据え置き
- **理由**: outage 回復後に即座に次 tick で再試行してほしい。
  counter を失敗時もリセットすると N tick 待たねばならず reflection
  頻度が長期間落ちる
- **テスト**: `test_reflector_returns_none_on_ollama_unavailable` が
  `_ticks_since_last >= 1` を assert

## D4. CycleResult への反映は 1 field のみ
- **判断**: `reflection_event: ReflectionEvent | None = None` を追加、
  `reflection_outcome: ReflectionOutcome { event, fell_back }` のような
  sub-object は作らない
- **理由**: `reflection_triggered: bool` (既存) と `reflection_event is None`
  の組合せで "policy trigger しなかった / trigger したが失敗" を区別可能。
  YAGNI 原則で sub-object は必要になってから昇格
- **ロールバック契約**: `CycleResult` の既存 field は一切変更なし、
  default=None のため既存テストは無影響

## D5. reflection 専用 prompt (prompting.py は無編集)
- **判断**: `build_reflection_messages` を `reflection.py` 内に完結配置。
  既存 `build_system_prompt` / `build_user_prompt` は action 選択専用のまま
- **理由**: 責務分離。reflection は短い自然文 (<=200 chars) を要求し、
  action は JSON schema を強要するため、prompt 契約が根本的に異なる。
  混在させると prompting.py の読み手に誤解を与える
- **トレードオフ**: 一部の共通文字列 (ペルソナ block) は重複するが、
  フォーマットが違うため DRY よりクリアさを優先

## D6. summary は plain text、JSON 強要せず
- **判断**: LLM 応答を `.strip()` してそのまま `SemanticMemoryRecord.summary`
  に格納。JSON parsing / schema 検証はしない
- **理由**: 後段で使うのは embedding とプロンプト文字列のみ。JSON を
  強要すると失敗率が上がり reflection の主目的 (長期保存可能な自然文) から
  遠ざかる。空応答は弾く (`if not summary_text: return None`)

## D7. summary の長さ上限 = 500 chars (security review MEDIUM-1)
- **判断**: `resp.content.strip()[:_MAX_SUMMARY_CHARS]` でハード cap、
  `_MAX_SUMMARY_CHARS = 500`
- **理由**: prompt で "<=200 characters" と要求しているが LLM は守らない
  可能性がある (汚染モデル / prompt injection / 単純な応答逸脱)。
  truncate で SQLite row / embedding 入力の両方に bound をかける
- **テスト**: `test_reflector_truncates_oversized_llm_output` で 10000 文字
  入力に対し 500 文字以下に収まることを確認

## D8. upsert 失敗の catch 範囲 (security review MEDIUM-2)
- **判断**: `except (ValueError, sqlite3.OperationalError, OSError)` で
  3 種を catch、それ以外は伝播
- **理由**: `maybe_reflect` は "never raises" を契約している。実在する
  persistence 失敗 (embedding dim mismatch / DB lock / 権限エラー) を
  網羅する。`except Exception` は広すぎてバグを隠す

## D9. embedding 失敗時は row を作る / vec skip
- **判断**: `EmbeddingUnavailableError` 時に `embedding = []` で進み、
  `SemanticMemoryRecord` は作成して `upsert_semantic` を呼ぶ。
  store 側が `embedding == []` を vec_embeddings skip として処理
  (#3 D7 と整合)
- **理由**: reflection 自体は完了しており、後で埋め込みを別途 attach する
  余地を残す (同 id で再 upsert 可能)。完全破棄は情報損失
- **テスト**: `test_reflector_stores_row_without_embedding_on_embed_outage`

## D10. Reflector 構築時の infra 共有
- **判断**: `CognitionCycle.__init__(reflector=None)` の default path で
  `Reflector(store=store, embedding=embedding, llm=llm)` を構築。
  cycle と reflector が同じ MemoryStore / EmbeddingClient / OllamaChatClient
  インスタンスを共有
- **理由**: リソース (httpx client / sqlite 接続) の重複を避ける。
  ただし #6 で multi-agent 用に 1 つの Reflector を全 agent で共有したい
  場合は explicit inject できる (Reflector 内 dict が per-agent 分離)

## D11. 非 test 用の reflection は 10 tick default
- **判断**: `ReflectionPolicy.tick_interval: int = 10`
- **理由**: design.md に書いた通り、MVP の tick = 10s なので 10 tick =
  100 秒ごとに反省 = 人間の散歩休憩に近いリズム。tests は `tick_interval=1`
  を明示指定で override

## D12. handoff file の扱い
- **判断**: `.steering/_handoff-next-session-m4-5.md` は本タスクの
  完了を以て不要になるため、PR に含めて削除する
- **理由**: root 直下に残すと次 M4 #6 タスクが誤参照する可能性。
  git 履歴は残るので情報損失なし
