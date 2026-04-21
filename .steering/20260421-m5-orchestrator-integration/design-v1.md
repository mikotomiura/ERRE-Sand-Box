# 設計 — m5-orchestrator-integration (v1 初回案)

本文書は `/reimagine` の初回案 (v1) として記録する。採用案 (hybrid) は
`design.md` 末尾の「採用案」節で最終化する。v2 と比較するため最初の時点で
存在した設計を `design-v1.md` として退避する予定。

## 実装アプローチ

**3 軸の判断**:

### Axis 1 — feature flag の置き場: **`BootConfig` 拡張**

`BootConfig` に `disable_erre_fsm: bool = False` / `disable_dialog_turn: bool = False` /
`disable_mode_sampling: bool = False` の 3 フィールドを追加する。`__main__.py` の
argparse は `--disable-erre-fsm` 等の `store_true` フラグを追加し、`cli()` の
`BootConfig(...)` 呼び出しに 3 つの keyword を明示的に渡す。

**理由**:
- `BootConfig` は既に `check_ollama: bool` を持ち、このパターンと同形
- frozen dataclass の immutability が実行時改変を防ぎ、テストで
  `BootConfig(disable_dialog_turn=True)` と直接 construct できる
- 環境変数方式は発見性が低く、dev / CI / live 間で暗黙に挙動が変わる
- `BootConfig` の single source of truth を保つ (分散すると運用が混乱)

**リスク対策** (impact-analyzer 指摘):
- `cli()` の keyword mapping 漏れで silent no-op になるため、`tests/test_main.py`
  に `parse_args(["--disable-erre-fsm"])` → `cli()` → `BootConfig.disable_erre_fsm == True`
  の smoke test を 3 flag ぶん先行追加する

### Axis 2 — DialogTurnGenerator 注入点: **新規 `DialogOrchestrator` class**

`src/erre_sandbox/integration/dialog_orchestrator.py` に `DialogOrchestrator`
class を新設する。責務は "cognition tick ごとに open dialog を走査し、
budget 判定 + turn 生成 + record + emit を駆動する" の 1 点に集中。
`OllamaDialogTurnGenerator` (inference-backed) と `InMemoryDialogScheduler`
(state bookkeeping) を合成して cognition 層に提供する。

**理由**:
- `WorldRuntime` に async dialog generation を直接足すと、`_on_cognition_tick`
  の責務が肥大化し、既存 `_run_dialog_tick` テスト (`tests/test_world/test_tick.py`)
  の `_pump` 回数調整など波及修正が発生する
- `CognitionCycle` に入れるのは cross-agent な dialog が per-agent cycle の
  責務と不整合
- `Reflector` collaborator と同様、`DialogOrchestrator` は "コラボレータ 1 つ
  で 1 つの責務" という M4 以降のパターンに揃う
- `integration/` 層への新規配置は `integration/dialog_turn.py` 先例と同じ
  extension (inference import 許可、モジュール先頭に extension 宣言)

**layer 依存方向**:
- `DialogOrchestrator` は `inference/` (ChatClient 間接) + `schemas/` + 自身の
  package 内のみに依存
- `WorldRuntime` は orchestrator を Protocol 型で受け取る (新規 Protocol を
  schemas.py に追加するか、`Callable[[int, Sequence[AgentRuntime]], Awaitable[None]]`
  で duck type する) — **詳細は /reimagine v2 で検討**

### Axis 3 — open dialog iteration の所在: **`WorldRuntime._on_cognition_tick` で orchestrator を呼ぶ**

`WorldRuntime` に `attach_dialog_orchestrator(orchestrator)` を追加し、
`_on_cognition_tick` の末尾 (`_run_dialog_tick` の後) で
`await self._run_dialog_turns(world_tick, runtimes)` を呼ぶ。

**理由**:
- `scheduler.tick()` (proximity auto-fire + timeout close) は同期で済むが、
  turn generation は `await generator.generate_turn(...)` が必要 — そのため
  scheduler.tick() 内に混ぜるのは型が合わない
- 複数 open dialog の turn 生成は `asyncio.gather(..., return_exceptions=True)`
  で並列化 (cognition step と同じパターン)
- 既に `_on_cognition_tick` は async method なので新規 await を追加しても
  `_run_dialog_tick` と同様 test fixture は影響を受けない (ただし
  `_pump` 回数は `_pump_until_stable` 方式に差し替える必要がある)

**DialogOrchestrator の dialog_id 取得方法**:
- `DialogInitiateMsg` は `dialog_id` フィールドを持たない (initiator / target / zone のみ)
- `DialogOrchestrator` は `scheduler.envelope_sink` を横取りして
  `downstream_sink = runtime.inject_envelope` に forward するチェーン構造で構築
- `DialogInitiateMsg` 観測時 → `scheduler.get_dialog_id(init, target)` で `dialog_id` を取得 → `_open[dialog_id] = (init, target, zone)` を保存
- `DialogCloseMsg` 観測時 → `_open.pop(dialog_id)` で除去
- PR #61 decisions.md §2「envelope sink 経由で orchestrator が state を保持する想定」に準拠

**budget / speaker 導出**:
- `transcript = scheduler.transcript_of(did)` / `turn_index = len(transcript)`
- `speaker_id = init if turn_index % 2 == 0 else target` (alternation)
- `speaker_state.cognitive.dialog_turn_budget` を per-agent runtime から取得
- `turn_index >= budget` → `scheduler.close_dialog(did, reason="exhausted")`
- `msg = await generator.generate_turn(...)`; `None` なら skip (timeout 経路で close)
- `msg` が返ったら `scheduler.record_turn(msg)` + `downstream_sink(msg)` で emit

## 変更対象

### 修正するファイル

- `src/erre_sandbox/bootstrap.py`
  - `DefaultERREModePolicy` を instantiate し、`cfg.disable_erre_fsm` が False の時に
    `CognitionCycle(erre_policy=...)` に渡す
  - `OllamaDialogTurnGenerator(llm=inference, personas={...})` を
    `cfg.disable_dialog_turn` が False の時に instantiate
  - `DialogOrchestrator(generator=..., scheduler=scheduler, downstream_sink=runtime.inject_envelope)` を構築
  - scheduler の `envelope_sink` を `orchestrator.intercept_sink` に差し替え
    (orchestrator が forward する)
  - `runtime.attach_dialog_orchestrator(orchestrator)` で wire
  - `personas_dir` → 全 persona YAML をまとめて load する helper を追加
    (既存の `_load_persona_yaml` を multi-persona 向けに dict 化)
  - `disable_mode_sampling=True` 時は `SAMPLING_DELTA_BY_MODE` を bypass する
    ラッパー policy を用意 (policy.next_mode() の結果を受けて zero-delta で
    ERREMode を組み立てる middleware、あるいは CognitionCycle に bypass フラグを
    通す) — **/reimagine v2 で詳細決定**

- `src/erre_sandbox/__main__.py`
  - argparse に `--disable-erre-fsm` / `--disable-dialog-turn` /
    `--disable-mode-sampling` を `store_true, default=False` で追加
  - `cli()` で `BootConfig(...)` に 3 キーワードを渡す
  - `--skip-health-check` と `--disable-dialog-turn` の組み合わせを
    `--help` 文字列で推奨する文言を追加

- `src/erre_sandbox/world/tick.py`
  - `attach_dialog_orchestrator(orchestrator)` method 追加
  - `_on_cognition_tick` 末尾で `await self._run_dialog_turns()` を呼ぶ
  - `_run_dialog_turns` method を新規実装 (async、`asyncio.gather` で
    open dialog を並列処理)
  - `orchestrator` が None の時は既存挙動 (dialog turn generation なし、
    timeout close のみ)

- `tests/test_bootstrap.py`
  - 既存 smoke test を壊さない (BootConfig default が維持される)
  - 新規: 3 flag OFF/ON 組み合わせで bootstrap が raise しないことを確認
    (4 ケース: baseline / --disable-erre-fsm / --disable-dialog-turn /
    --disable-mode-sampling)
  - 新規: DefaultERREModePolicy が `cycle._erre_policy` に設定されることを
    monkeypatch で検証
  - 新規: DialogOrchestrator が runtime にアタッチされることを smoke 検証

- `tests/test_main.py`
  - `parse_args(["--disable-erre-fsm"])` の argparse 解析と `cli()` →
    `BootConfig.disable_erre_fsm == True` の一致検証 (3 flag 分)

- `tests/test_world/test_tick.py`
  - `_pump` 回数を `_pump_until_stable` 方式に差し替え (async 化の副作用対策)
  - 新規: `attach_dialog_orchestrator` 経由で async turn generation が呼ばれる
    テスト (mock orchestrator で検証)

### 新規作成するファイル

- `src/erre_sandbox/integration/dialog_orchestrator.py` — `DialogOrchestrator`
  class (generator + scheduler 合成、envelope sink interception、per-tick
  iteration + turn generation)
- `tests/test_integration/test_dialog_orchestrator.py` — `DialogOrchestrator` 単体
  (mock generator / mock scheduler で budget 判定・alternation・exhausted
  close・LLM None 時の fallthrough を検証)

### 削除するファイル

なし。

## 影響範囲

impact-analyzer レポート要約:

| リスク | 対象 | 対策 |
|---|---|---|
| BootConfig 新 field の silent no-op | `cli()` keyword 漏れ | `test_main.py` に 3 flag の parse+cli smoke test 追加 |
| `_run_dialog_tick` async 化の flaky | `test_world/test_tick.py` `_pump` 依存 | `_pump_until_stable` へ差し替え |
| `--skip-health-check` + dialog_turn | Ollama 停止時の tick ごとエラーログ | 運用ガイドに `--disable-dialog-turn` 併用を明記 |
| layer 依存方向 | `world/ → integration/` を避ける | orchestrator は Protocol 型で受取 / `attach_*` で注入 |

## 既存パターンとの整合性

- `attach_dialog_scheduler` (`world/tick.py:276`) をそのまま兄弟化する形で
  `attach_dialog_orchestrator` を追加
- `Reflector` collaborator (`cognition/reflection.py`) の "注入可能・失敗時
  None 返し・絶対に例外を漏らさない" 契約を `DialogOrchestrator` も踏襲
- `CognitionCycle(erre_policy=None)` の optional DI パターンを
  `WorldRuntime(dialog_orchestrator=None)` で踏襲
- `OllamaDialogTurnGenerator` 同様、`DialogOrchestrator` も integration 層の
  extension (inference import) をモジュール先頭で明示
- `BootConfig` への flag 追加は `check_ollama: bool` と同形
- bootstrap の resource lifecycle は `AsyncExitStack` で管理 (新規 orchestrator
  は state だけなので close callback 不要)

## テスト戦略

- **単体テスト** (TDD 順序で先行作成):
  - `test_dialog_orchestrator.py`:
    - budget = 6、`len(transcript) == 5` 時は turn 生成、== 6 時は
      `close_dialog(reason="exhausted")` になる
    - turn_index % 2 == 0 → initiator、else target の speaker alternation
    - generator が `None` を返した場合、`record_turn` も emit も呼ばれない
      (timeout 経路に任せる)
    - open dialog 複数時に `asyncio.gather` で並列 generate
    - envelope sink interception: DialogInitiateMsg / DialogCloseMsg が
      downstream に forward される (bypass しない)
  - `test_main.py`: 3 flag の argparse → BootConfig mapping 検証
  - `test_bootstrap.py`: 3 flag 組み合わせで bootstrap が完走
- **統合テスト**:
  - `test_integration/test_dialog_orchestrator.py` 末尾に "fake LLM + real
    scheduler + real orchestrator で initiate → 6 turn → exhausted close"
    end-to-end を配置
- **回帰テスト**:
  - `uv run pytest -q` で既存 549 passed (PR #61 時点) に 0 failure
  - `uv run ruff check` / `ruff format --check` / `mypy` いずれも PASS
- **live acceptance は次タスク** `m5-acceptance-live` の責務 (本 task では
  行わない)

## 関連する Skill

- `implementation-workflow` — 共通骨格 (Step A-J)
- `error-handling` — orchestrator の async + graceful None path (Reflector
  / dialog_turn_generator と同パターン)
- `python-standards` — snake_case, 型ヒント, from __future__ import annotations
- `test-standards` — pytest-asyncio, mock 戦略
- `architecture-rules` — `world/ → integration/` を避ける設計判断 (本案では
  Protocol / attach_* で回避している)

## ロールバック計画

- feature flag 3 軸で OFF すれば M4 相当の挙動に帰着
- `--disable-erre-fsm` → FSM no-op (pre-M5 挙動)
- `--disable-dialog-turn` → dialog generator 不動 (initiate + timeout close のみ、M4 相当)
- `--disable-mode-sampling` → sampling override bypass (persona YAML default sampling のみ)
- 3 flag 全 ON でも schema 0.3.0-m5 wire 互換 (additive default のため)
- 緊急時は `git revert` で本 PR 全体を M4 状態に戻せる (単独 PR で merge する)

---

## 運用メモ

本案は **v1 (初回案)**。`/reimagine` で v2 を生成し、以下 3 点を再検討する予定:

1. Axis 1 (flag 置き場): `BootConfig` vs 環境変数 vs CLI のみ
2. Axis 2 (generator 注入点): `DialogOrchestrator` 新設 vs 既存 scheduler への
   拡張 (PR #61 decisions §2 拒否済だが再確認) vs WorldRuntime 直接注入
3. Axis 3 (iteration 所在): WorldRuntime._on_cognition_tick vs scheduler.tick()
   内包 vs 専用 tick method
4. feature flag `--disable-mode-sampling` の実装経路 (policy wrapper vs
   CognitionCycle bypass flag vs `SAMPLING_DELTA_BY_MODE` 差し替え)
5. `DialogOrchestrator` の dialog_id 取得: envelope sink interception vs
   scheduler minimal accessor 追加
