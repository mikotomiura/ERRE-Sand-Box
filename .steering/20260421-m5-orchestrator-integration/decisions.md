# Decisions — m5-orchestrator-integration

本タスクで採用した設計判断とその根拠。M5 Phase 2 の最後の 2 タスク
(`m5-acceptance-live` と `v0.3.0-m5` タグ付け) の文脈判断に利用される。

---

## 判断 1: /reimagine で v2 (既存構造同化) を採用

- **判断日時**: 2026-04-21
- **背景**: 3 軸 (feature flag 置き場 / generator 注入点 / iteration 所在) に
  複数案あり、hybrid 採用の可能性が高かった
- **比較**: `design-comparison.md` で v1 (新規 `DialogOrchestrator` class +
  envelope sink chain + `BootConfig` 拡張) と v2 (既存 `WorldRuntime` に method
  追加 + `iter_open_dialogs` 1 本追加 + `bootstrap()` kwargs) を評価
- **採用**: v2 (ユーザー選択)
- **根拠**:
  1. v1 の 4 新構造 (class + sink chain + state 二重化 + 差し替え余地) はいずれも
     YAGNI で複雑性の総量が多い
  2. v1 の sink chain は `DialogInitiateMsg` に `dialog_id` がない都合上、結局
     `scheduler.get_dialog_id()` に問い合わせる設計 — state を二重化するより
     scheduler 直問い合わせのほうが単純
  3. v2 は `disable_mode_sampling` の実装経路 (`CognitionCycle.erre_sampling_deltas`
     DI スロット) まで明確で、v1 で未決だった論点が解消される
  4. feature flag を `BootConfig` でなく `bootstrap()` kwargs にすることで、
     "過渡期 rollback knob" と "永続 config" の分離が設計意図として明示される
- **トレードオフ**: 将来 dialog turn 駆動ロジックを差し替えたいとき
  `WorldRuntime` 内部を編集する必要がある。現時点で差し替え要件は存在しない
- **影響範囲**: 全実装方針

## 判断 2: `DialogScheduler` Protocol を拡張 (`transcript_of`, `iter_open_dialogs`)

- **判断日時**: 2026-04-21 (code-reviewer HIGH 指摘後)
- **背景**: code-reviewer が「`world/tick.py` で `scheduler.iter_open_dialogs()` と
  `scheduler.transcript_of(did)` に `type: ignore[attr-defined]` が必要になっている
  のは型安全性の実質的破綻」と HIGH 指摘。`world/` → `integration/` 直接 import
  禁止のルール下で、`world/tick.py` は `DialogScheduler` Protocol (schemas.py §7.5)
  経由でしかスケジューラを触れない
- **選択肢**:
  - A: `# type: ignore[attr-defined]` のまま維持 (runtime 安全だが型表現としては不完全)
  - B: Protocol に 2 method 追加 ← **採用**
  - C: `world/tick.py` 内部に narrower Protocol を定義して runtime_check
- **採用**: B
- **根拠**:
  1. `DialogScheduler` Protocol は interface-only (wire 格納型ではない) のため、
     method 追加は `SCHEMA_VERSION` bump を要しない (contract freeze 観点で安全)
  2. 唯一の実装 `InMemoryDialogScheduler` は既に両 method を持つため、
     拡張は既存コードに対する non-breaking
  3. `type: ignore` を除去することで、将来の別実装 (mock, cross-process scheduler)
     も contract に縛られる
- **トレードオフ**: Protocol freeze の境界線を再定義することになる。ただし
  "interface-only Protocol の method 追加" は "wire 型の field 追加" とは別扱い
  と明示する先例になる (本 decisions.md)
- **影響範囲**: `src/erre_sandbox/schemas.py` §7.5 `DialogScheduler`
- **見直しタイミング**: M6+ で cross-process scheduler (Redis / gRPC) を作る時、
  `iter_open_dialogs` が pagination 必要なら再設計

## 判断 3: feature flag は `bootstrap()` kwargs (BootConfig 拡張ではない)

- **判断日時**: 2026-04-21
- **背景**: 3 rollback flag の置き場として `BootConfig` 拡張 / 環境変数 /
  `bootstrap()` kwargs が候補だった
- **採用**: `bootstrap()` 関数の keyword-only kwargs
- **根拠**:
  1. `BootConfig` は live 運用で永続する設定 (host, port, db_path, ollama_url)
     の契約。feature flag は M5 acceptance までの transient rollback knob で、
     `v0.3.0-m5` リリース後に削除する想定 — 永続 config と同じ名前空間に混ぜると
     "flag がいつまでもある" 状態になる
  2. `check_ollama` は CI / offline の恒常的ニーズ (BootConfig 残留) と違い、
     rollback 3 flag は M5 固有
  3. `bootstrap()` の signature を直接読むだけで "どの機能を ON/OFF できるか"
     が分かる → 発見性が高い
- **トレードオフ**: CLI (`__main__.py`) が `cli()` → `bootstrap()` の keyword
  mapping を 3 キー分渡す責任を持つ。漏れで silent no-op になるリスクは
  `test_main.py` の `test_cli_propagates_rollback_flags_to_bootstrap` (smoke) で検出
- **影響範囲**: `bootstrap.py::bootstrap`, `__main__.py::cli`
- **削除タイミング**: `m5-acceptance-live` で 3 flag 全 ON の挙動が live PASS
  した直後。次 PR (`m5-cleanup-rollback-flags`) で flag と `_ZERO_MODE_DELTAS` を
  一括除去する計画

## 判断 4: `disable_mode_sampling` は `CognitionCycle.erre_sampling_deltas` DI で実装

- **判断日時**: 2026-04-21
- **背景**: `--disable-mode-sampling` 時の挙動は「FSM は動く (mode name 遷移は
  観測可能) / delta 適用だけ止める」。実装経路は (a) CognitionCycle に
  `apply_sampling_delta: bool` を足す / (b) `erre_sampling_deltas: Mapping` を
  DI する / (c) policy wrapper で返り値を None に
- **採用**: b (`Mapping[ERREModeName, SamplingDelta] | None` を DI)
- **根拠**:
  1. `_ZERO_MODE_DELTAS` を bootstrap で構築して渡すだけ、cycle の responsibility
     (sampling 合成) に自然に収まる
  2. c はそもそも FSM 遷移自体を止めてしまい `disable_erre_fsm` と区別できない
  3. a は特殊 bool で挙動を分岐、テスト matrix が増える
  4. `is not None` で fallback (`or` だと空 dict が production にフォールバック
     する罠を避ける、code-reviewer MEDIUM 指摘を反映)
- **影響範囲**: `cognition/cycle.py::CognitionCycle.__init__`,
  `cognition/cycle.py::_maybe_apply_erre_fsm` の 1 行

## 判断 5: `_drive_dialog_turns` を `_stage_dialog_turns` と分離 (C901 対応)

- **判断日時**: 2026-04-21
- **背景**: ruff C901 が "`_drive_dialog_turns` complexity 13 > 10" を指摘
- **選択肢**:
  - A: `# noqa: C901` で抑止
  - B: 同期的な判断 (speaker 選択・budget 判定・close) を `_stage_dialog_turns`
    に抽出、非同期 gather と結果処理を `_drive_dialog_turns` に残す ← **採用**
  - C: `DialogOrchestrator` class に切り出す (v1 案への逆戻り)
- **採用**: B
- **根拠**:
  1. stage (同期) と drive (非同期) の責務が自然に分離でき、テスタビリティが上がる
  2. class 導入のオーバーヘッドなしに可読性改善
  3. C の `DialogOrchestrator` は判断 1 で YAGNI 判断済
- **影響範囲**: `world/tick.py` に `_stage_dialog_turns(scheduler, generator, ...)`
  追加。`_PendingTurn` dataclass で両者を結ぶ

## 判断 6: MEDIUM 指摘のうち "unregistered agent 警告スパム" は現状維持

- **判断日時**: 2026-04-21 (code-reviewer MEDIUM 指摘)
- **背景**: `_stage_dialog_turns` で `speaker_rt is None` or `addressee_rt is None`
  時に `logger.warning` で skip する path が "1 tick ごとに毎回 warning が出続ける"
  可能性を指摘された
- **採用**: 現状 (`logger.warning`) 維持
- **根拠**:
  1. 本 path は "scheduler がランタイム未登録 agent の dialog を保持している"
     という higher-layer bug の場合のみ発火する。production で到達する経路は
     設計上存在しない (scheduler.schedule_initiate の唯一の呼び出し元は
     scheduler 自身の proximity auto-fire で、対象 agent は必ず runtime に登録
     済の `AgentView` 経由)
  2. spam が観測された時点で silent にせず調査を促す方が、データ欠損を
     発見しやすい
  3. テスト fixture で意図的に到達する場合はログレベルを caplog で抑止可能
- **見直しタイミング**: もし M6+ で cross-process scheduler / 異常系 E2E テストで
  warning スパムが CI を汚すなら、`_close_dialog(reason="interrupted")` で dialog
  側を強制的に閉じる path に変更する

## 判断 7: 3 flag 相互作用の組み合わせテスト は argparse レベルに留める

- **判断日時**: 2026-04-21 (code-reviewer MEDIUM 指摘)
- **背景**: `--disable-erre-fsm` + `--disable-mode-sampling` のような組み合わせの
  bootstrap レベルテストが `test_main.py` の argparse 解析にしかない
- **採用**: argparse + cli レベルのみ (2^3=8 組み合わせは追加しない)
- **根拠**:
  1. 各 flag は互いに独立した branch を切る (bootstrap の if 分岐 3 本が直列)
  2. 各 flag の個別 ON/OFF 挙動は `test_bootstrap.py` と `test_cognition/test_cycle_erre_fsm.py`
     でカバー済
  3. bootstrap level の全組み合わせテストは `OllamaChatClient` / `uvicorn` /
     `WorldRuntime.run` をすべて mock する必要があり、テスト費用が高い割に
     独立 branch の組み合わせ爆発は論理的に被覆可能
  4. 最終的には `m5-acceptance-live` の live 検証で all-ON 挙動が PASS すれば
     組み合わせ網羅は不要 (rollback 用途の flag なので "OFF 時に M4 相当" が
     個別確認できていれば十分)
- **影響範囲**: テスト計画
- **見直しタイミング**: flag が長期残存する場合 (acceptance 長引きなど) は
  組み合わせテストを追加する

---

## 後続タスク `m5-acceptance-live` が本文書から取り出すべき値

1. bootstrap の kwargs default `enable_erre_fsm=True, enable_dialog_turn=True,
   enable_mode_sampling=True` が本番設定
2. live run command は `python -m erre_sandbox --personas kant,nietzsche,rikyu`
   (rollback flag なし = 全 ON)
3. rollback 検証: 各 flag OFF で起動し「M4 相当」挙動 (FSM no-op / dialog turn 不動 /
   persona base sampling のみ) を確認する evidence script を回す
4. acceptance PASS 後、次タスク `m5-cleanup-rollback-flags` で 3 flag と
   `_ZERO_MODE_DELTAS` を削除する (判断 3 参照)
