# 設計 — m5-orchestrator-integration (v2 再生成案)

本文書は `/reimagine` の再生成案 (v2)。初回案 `design-v1.md` を意図的に
見ずに、`requirement.md` のみに立脚してゼロから最小差分を設計した。

## 実装アプローチ

**根底の設計判断**: 新しい抽象を導入するより、既存の構造 (WorldRuntime が
物理・認知・heartbeat・dialog scheduler を 1 coroutine で順次まわす) に
dialog turn driving を同化させる。orchestration の責務はすでに
WorldRuntime が負っているので、新しい class・新しい Protocol を導入せずに
済むなら導入しない。

### 3 軸の判断

#### Axis 1: feature flag の置き場 — **`bootstrap()` 関数の kwargs**

`__main__.py` argparse で 3 フラグを受け取り、`bootstrap(cfg, *, enable_erre_fsm, enable_dialog_turn, enable_mode_sampling)` の keyword-only 引数として渡す。`BootConfig` には**追加しない**。

**理由**:
- `BootConfig` は live 運用で永続する設定 (host, port, db_path, ollama_url
  等) の契約。feature flag は M5 acceptance までの transient rollback knob で、
  M6 で削除される想定 — 永続 config と同じ名前空間に混ぜると契約が汚れる
- `check_ollama` は CI / offline の恒常的ニーズがあるので BootConfig に残すが、
  M5 rollback 用 3 flag は過渡期のもので性質が違う
- bootstrap の signature を直接読むだけで「この関数はどの機能を ON/OFF できるか」
  が分かる (BootConfig にまぎれないため発見性が高い)
- テストでは `bootstrap(cfg, enable_dialog_turn=False)` と直接書ける

**flag default**: すべて `True` (= 本番挙動)。OFF = rollback。

#### Axis 2: dialog turn orchestration の所在 — **`WorldRuntime` 内部に同化**

新規 class / 新規 Protocol / 新規ファイルを作らない。`WorldRuntime` に以下 2 つの
method を足すだけ:

```python
def attach_dialog_generator(self, generator: DialogTurnGenerator) -> None: ...
async def _drive_dialog_turns(self, world_tick: int) -> None: ...
```

**理由**:
- `WorldRuntime` は既に physics + cognition + heartbeat + dialog scheduler tick
  の 4 系統を 1 min-heap で回している coordinator。dialog turn driving は
  5 系統目として自然に収まる
- `attach_dialog_scheduler` と同形の `attach_dialog_generator` になるので、
  既存の読者が 1 秒で理解できる
- `DialogOrchestrator` のような中間 class を挟むと、"scheduler と generator を
  糊付けするだけの単純 class" が test で mock する対象になり間接性が増す
- state (`_open` map) を複製して保持する必要がない: scheduler が真実の source
  なので直接問い合わせる

#### Axis 3: open dialog iteration の tick 上の位置 — **`_on_cognition_tick` 末尾で `_drive_dialog_turns` を await**

`_on_cognition_tick` の呼び出し順:

```
cognition gather (per-agent)
  ↓
_consume_result (per-agent)
  ↓
_run_dialog_tick (sync: 既存 proximity auto-fire + timeout close)
  ↓
await self._drive_dialog_turns(world_tick)  ← 新規、async
```

**理由**:
- turn 生成 は `_run_dialog_tick` で新規 admit された dialog も即応するよう、
  admit より後に置く
- timeout close は `_run_dialog_tick` 内で既に走るので、expired dialog に
  無駄 turn を生成しない
- 並列化: 複数 open dialog の `generator.generate_turn(...)` を
  `asyncio.gather(..., return_exceptions=True)` で並列実行 — cognition step と
  同じパターン

### 4 つの補助決定

#### D1: scheduler に `iter_open_dialogs()` を 1 本だけ追加

`InMemoryDialogScheduler` に以下を追加:

```python
def iter_open_dialogs(self) -> Iterator[tuple[str, str, str, Zone]]:
    """Yield (dialog_id, initiator_id, target_id, zone) for each open dialog."""
    for did, d in self._open.items():
        yield did, d.initiator, d.target, d.zone
```

**理由**: orchestration には `dialog_id + pair` の enumerate が必要。PR #61
decisions §2 は *dialog_turn_generator の拡張として* scheduler helper 追加を
拒否した — 本 task (orchestrator integration) は別コンテキストで、1 本の
minimal accessor を足すのが envelope sink interception より圧倒的に単純。

**代替案との比較**:
- envelope sink chain で init/close を観測して自力マップを持つ → state 二重化、
  bug-prone、dialog_id は DialogInitiateMsg に含まれないため
  `scheduler.get_dialog_id(init, target)` を結局呼ぶ必要がある
- pair で iterate して `get_dialog_id` を呼ぶ → open でない pair 全てを
  問い合わせる O(N^2) で無駄
- `iter_open_dialogs` → O(open) で、追加 4 行、read-only

PR #61 §2 が拒否した `participants_of` / `should_take_turn` / `turn_index_of`
のいずれとも重ならない (あれは "pair → dialog_id" or "dialog_id → participants"
や turn 判定の helper、こちらは "全 open の enumerate")。

#### D2: `disable_mode_sampling` の実装経路

`CognitionCycle.__init__` に `erre_sampling_deltas: Mapping[ERREModeName, SamplingDelta] | None = None` の optional 注入点を追加。default は `SAMPLING_DELTA_BY_MODE`、disable 時は bootstrap が全ゼロの `_ZERO_MODE_DELTAS` table を注入。

`_maybe_apply_erre_fsm` の line 383 が `self._erre_sampling_deltas[candidate]` を参照するように 1 行置き換え。

**理由**:
- `disable_mode_sampling` の意味: FSM 遷移 (mode name 変更) は動く、delta 適用だけ止める — mode 遷移そのものは記録したい (live acceptance 項目 3 の一部)
- policy wrapper で返り値を None にする案は FSM 自体を止めてしまうので disable_erre_fsm と区別できなくなる
- `compose_sampling` 側に bypass flag を入れるのは関数の純粋性を損なう
- CognitionCycle の DI スロット 1 個追加は最小侵襲

#### D3: persona registry の構築

bootstrap.py に `_load_persona_registry(cfg) -> dict[str, PersonaSpec]` を追加。既存の agent 登録ループで使われる `_load_persona_yaml` を先頭でまとめて呼び、dict を構築して `OllamaDialogTurnGenerator(personas=...)` に渡す。

**理由**: generator は「persona_id → display_name で呼びかけ」のために persona
registry が必要 (PR #61 decisions §4)。bootstrap は既に各 persona YAML を個別に
load しているので、dict にまとめるだけ (重複 load なし)。

#### D4: `__main__.py` の 3 flag mapping 漏れ対策

`cli()` で `BootConfig(...)` 生成後、`bootstrap(cfg, enable_erre_fsm=args.enable_erre_fsm, ...)` を明示的に渡す。`tests/test_main.py` に 3 flag の argparse → bootstrap kwargs mapping を検証する smoke test (3 件) を先行追加。

**理由**: impact-analyzer が指摘した silent no-op (argparse パースされるが
bootstrap に渡らない) を CI で検出可能にする。

## 変更対象

### 修正するファイル

- **`src/erre_sandbox/bootstrap.py`**
  - `bootstrap()` に keyword-only `enable_erre_fsm: bool = True` /
    `enable_dialog_turn: bool = True` / `enable_mode_sampling: bool = True` 追加
  - `_load_persona_registry(cfg) -> dict[str, PersonaSpec]` helper 追加
  - `CognitionCycle(...)` 呼び出しに `erre_policy=DefaultERREModePolicy() if enable_erre_fsm else None` / `erre_sampling_deltas=_ZERO_MODE_DELTAS if not enable_mode_sampling else None` を追加
  - `enable_dialog_turn` が True の時のみ `OllamaDialogTurnGenerator(llm=inference, personas=persona_registry)` を instantiate して `runtime.attach_dialog_generator(generator)` を呼ぶ
  - module top に `_ZERO_MODE_DELTAS: Mapping[ERREModeName, SamplingDelta]` 定数追加

- **`src/erre_sandbox/__main__.py`**
  - argparse に `--disable-erre-fsm` / `--disable-dialog-turn` / `--disable-mode-sampling` (`action="store_false"`, `dest="enable_*"`, `default=True`) 追加
  - `cli()` で `bootstrap(cfg, enable_erre_fsm=args.enable_erre_fsm, ...)` を明示的に渡す
  - `--help` に "これらは M5 ロールバック用フラグ。本番は全 ON を維持" を明示

- **`src/erre_sandbox/cognition/cycle.py`**
  - `CognitionCycle.__init__` に `erre_sampling_deltas: Mapping[ERREModeName, SamplingDelta] | None = None` kwarg 追加
  - `self._erre_sampling_deltas = erre_sampling_deltas or SAMPLING_DELTA_BY_MODE` を init で設定
  - `_maybe_apply_erre_fsm` の `SAMPLING_DELTA_BY_MODE[candidate]` 参照を
    `self._erre_sampling_deltas[candidate]` に置換

- **`src/erre_sandbox/world/tick.py`**
  - `attach_dialog_generator(generator: DialogTurnGenerator) -> None` method 追加 (`attach_dialog_scheduler` と対称)
  - `_on_cognition_tick` 末尾に `if self._dialog_generator is not None: await self._drive_dialog_turns(current_world_tick)` 追加
  - `_drive_dialog_turns(world_tick)` method 実装:
    1. scheduler が None or generator が None なら早期 return
    2. `scheduler.iter_open_dialogs()` で enumerate
    3. 各 dialog に対して:
       - `transcript = scheduler.transcript_of(did)` / `turn_index = len(transcript)`
       - `speaker_id = init_id if turn_index % 2 == 0 else target_id`
       - speaker の AgentRuntime を `self._agents[speaker_id]` で取得
       - `turn_index >= speaker_state.cognitive.dialog_turn_budget` なら
         `scheduler.close_dialog(did, reason="exhausted")` して次へ
       - それ以外なら `await generator.generate_turn(...)` を並列タスク化
    4. `asyncio.gather(*tasks, return_exceptions=True)` で並列実行
    5. 各結果に対して `record_turn + inject_envelope` or `None` なら skip

- **`src/erre_sandbox/integration/dialog.py`**
  - `InMemoryDialogScheduler.iter_open_dialogs() -> Iterator[tuple[str, str, str, Zone]]` method 追加 (~4 行)

### 新規作成するファイル

- **`tests/test_integration/test_dialog_orchestration_wiring.py`** — WorldRuntime + scheduler + fake generator の単体:
  - `_drive_dialog_turns` が budget 判定で `reason="exhausted"` close する
  - speaker alternation (turn_index % 2)
  - generator が None を返したとき record も emit も起こらない
  - 複数 open dialog が `gather` で並列処理される
  - generator が例外を投げても他 dialog の turn 生成は止まらない

- (テストフィクスチャの拡張は `tests/conftest.py` と `tests/test_bootstrap.py` に追加)

### 削除するファイル

なし。

## 影響範囲

| 対象 | 影響 | 対策 |
|---|---|---|
| `BootConfig` | 変更なし (v1 と逆の判断) | — |
| `cognition/cycle.py` | 1 kwarg 追加、既存テスト 0 破損 | default=None で維持 |
| `integration/dialog.py` | 1 method 追加 (read-only) | — |
| `world/tick.py` | 1 attach method + 1 async method 追加 | `_pump` 依存テストは `_pump_until_stable` に差し替え必要 |
| `__main__.py` | 3 flag 追加 | `test_main.py` smoke test 先行 |
| `tests/test_world/test_tick.py` | `_pump` 増分必要な test がある可能性 | impact-analyzer 指摘 |
| `tests/test_bootstrap.py` | flag 組み合わせ smoke test 追加 | 4 ケース (baseline + 3 flag 個別 OFF) |

## 既存パターンとの整合性

- `attach_dialog_scheduler` (`world/tick.py:276`) と対称な `attach_dialog_generator`
- `CognitionCycle(erre_policy=None)` optional DI と対称な
  `CognitionCycle(erre_sampling_deltas=None)`
- `asyncio.gather(..., return_exceptions=True)` で per-agent exception 隔離
  (既存 `_on_cognition_tick` の cognition gather と同型)
- `Reflector` collaborator の "失敗時 None 返し、例外絶対に外へ漏らさない"
  契約を generator 呼び出しでも踏襲 (generator 自体は既にそうなっている)
- feature flag は long-lived config (BootConfig) と分けて bootstrap kwargs に

## テスト戦略

### 単体テスト (TDD 順序で先行作成)

1. `tests/test_integration/test_dialog_orchestration_wiring.py`:
   - budget 境界 (5 turns OK / 6 turns → exhausted close)
   - speaker alternation
   - generator の None / 例外の graceful 処理
   - gather 並列処理の検証
   - `iter_open_dialogs` が open 件数と一致
2. `tests/test_integration/test_dialog.py` に `iter_open_dialogs` の単体追加
3. `tests/test_cognition/test_cycle_erre_fsm.py` に `erre_sampling_deltas` 注入の
   検証 (zero-delta テーブルで sampling_overrides が空になる)
4. `tests/test_main.py` に 3 flag の argparse → bootstrap kwargs mapping smoke

### 統合テスト

- `tests/test_bootstrap.py` に 4 smoke case:
  - all ON (baseline — M5 fully wired)
  - `enable_erre_fsm=False` (FSM no-op、既存挙動)
  - `enable_dialog_turn=False` (generator wire されず、timeout close 経路)
  - `enable_mode_sampling=False` (FSM 動くが delta 適用なし)

### 回帰テスト

- `uv run pytest -q` で PR #61 時点の 549 passed + 新規テスト分 (〜8-12 件) を追加
- `uv run ruff check src tests` / `ruff format --check` / `mypy src/erre_sandbox` 全 PASS

### live acceptance

**本 task のスコープ外**。次タスク `m5-acceptance-live` の責務。

## ロールバック計画

本案では 3 軸全てに対応する flag を用意:

| flag | OFF 時の挙動 | 機構 |
|---|---|---|
| `--disable-erre-fsm` | FSM 不動、`ERREMode` は boot 時の zone default 固定 | `CognitionCycle(erre_policy=None)` |
| `--disable-dialog-turn` | dialog_initiate 後は timeout close のみ (M4 挙動) | `attach_dialog_generator` 呼ばれない |
| `--disable-mode-sampling` | FSM mode 変遷は動くが sampling delta は全ゼロ | `CognitionCycle(erre_sampling_deltas=_ZERO_MODE_DELTAS)` |

3 flag 全 OFF = M4 完全相当。緊急時は `git revert` で本 PR をそのまま戻す。
schema 0.3.0-m5 は wire 互換 (additive default のため flag OFF でも envelope 互換)。

## 関連する Skill

- `implementation-workflow` — 共通骨格
- `error-handling` — `_drive_dialog_turns` の async gather + return_exceptions
- `python-standards` — kwargs-only, 型ヒント, `from __future__ import annotations`
- `test-standards` — pytest-asyncio, mock scheduler / generator
- `architecture-rules` — `world/ → integration/` を避けるための Protocol 参照
  (`DialogTurnGenerator` は schemas.py §7.5 に既に Protocol として定義済で、
  world/tick.py は型として import 可能)

## 設計判断の履歴

- 2026-04-21: 初回案 (`design-v1.md`) と再生成案 (本文書 v2) を
  `design-comparison.md` で比較
- **採用**: v2 (再生成案)
- **根拠**: ユーザー選択 (option 1 "v2 そのまま採用")。
  比較表ベースの推奨根拠:
  1. v1 の 4 新構造 (DialogOrchestrator class / envelope sink chain /
     state 二重化 / 差し替え余地) はいずれも YAGNI で複雑性の総量が多い
  2. v1 の sink chain は `DialogInitiateMsg` が `dialog_id` を持たない都合上
     結局 scheduler に問い合わせる設計 — それなら `iter_open_dialogs` で
     直接列挙する v2 の方が state 単一化で素直
  3. v2 は `disable_mode_sampling` の実装経路 (`CognitionCycle.erre_sampling_deltas`
     DI スロット) まで明確で、v1 で未決だった論点が解消される
  4. feature flag を `BootConfig` でなく `bootstrap()` kwargs にすることで、
     "過渡期 rollback knob" と "永続 config" の分離が設計意図として明示される
  5. PR #61 decisions.md §2 が拒否した helper (turn generator 用の pair query)
     と v2 の `iter_open_dialogs` (orchestrator 用の全 enumerate) は用途が
     異なるため、旧決定の再解釈は妥当
