# m5-erre-sampling-override-live

## 背景

M5 で `ERREModeTransitionPolicy` FSM が `CognitionCycle` に配線済 (PR #58)。
FSM がモード遷移を検出すると `cycle.py::_maybe_apply_erre_fsm` が
新しい `ERREMode(name=candidate, entered_at_tick=...)` を生成するが、
このとき `sampling_overrides` は `SamplingDelta` のデフォルト (全フィールド 0.0)
のままであるため、**モード遷移がサンプリングに影響していない**。

一方、`compose_sampling(base, delta)` は 3 箇所
(`cognition/cycle.py`, `cognition/reflection.py`, `inference/ollama_adapter.py`)
で既に `agent_state.erre.sampling_overrides` を参照している。
→ delta を live で埋める責務だけが未実装。

persona-erre Skill §ルール 2 に 8 モード × 3 パラメータの加算値テーブルが
ドキュメント化済だが、Python コードとして存在しない。

## ゴール

8 つの ERRE モードごとの `SamplingDelta` テーブルを Python コード化し、
FSM がモード遷移を検出したときに `AgentState.erre.sampling_overrides`
に live で反映する。次の LLM 呼び出しで `compose_sampling()` が
temperature / top_p / repeat_penalty の delta を確実に拾う状態にする。

## スコープ

### 含むもの

- `src/erre_sandbox/erre/sampling_table.py` 新規作成
  - 8 モード (PERIPATETIC / CHASHITSU / ZAZEN / SHU_KATA / HA_DEVIATE /
    RI_CREATE / DEEP_WORK / SHALLOW) → `SamplingDelta` の定数マップ
  - 値は persona-erre Skill §ルール 2 と完全一致
  - 公開 API: `SAMPLING_DELTA_BY_MODE: Mapping[ERREModeName, SamplingDelta]`
  - `erre/__init__.py` に re-export
- `cognition/cycle.py::_maybe_apply_erre_fsm` のモード遷移時、新 `ERREMode`
  を `sampling_overrides=SAMPLING_DELTA_BY_MODE[candidate]` で生成
- `tests/test_erre/test_sampling_table.py` 新規作成
  - 8 モード全部の delta 値が persona-erre Skill §ルール 2 と一致
  - clamp 境界: `compose_sampling(base, delta)` が `ResolvedSampling` の
    field range 内に必ず収まる (persona YAML の extreme base でも)
  - 各 delta が `SamplingDelta` の field constraint を満たす
- `tests/test_cognition/test_cycle_erre_fsm.py` を拡張
  - FSM がモード遷移を提案した時、新 `AgentState.erre.sampling_overrides`
    がテーブル値と一致することを検証

### 含まないもの

- `DialogTurnGenerator` 実装 (別タスク `m5-dialog-turn-generator`)
- ERRE mode tint の Godot 側表示 (別 PR #59 で完了済)
- 新規ペルソナ YAML の `default_sampling` 変更
- feature flag での無効化 (`m5-orchestrator-integration` で扱う)
- schemas.py の `SamplingDelta` 定義変更 (M5 contracts freeze で固定)
- `cognition/reflection.py` の reflection 専用サンプリング経路の変更
  (既に同じ `agent_state.erre.sampling_overrides` を参照するため、
  本タスクでは自動的に恩恵を受ける)

## 受け入れ条件

- [ ] `src/erre_sandbox/erre/sampling_table.py` が存在し、8 モード全部が
      定義されている
- [ ] `SAMPLING_DELTA_BY_MODE` の値が persona-erre Skill §ルール 2 の
      テーブルと完全一致 (review で手作業確認)
- [ ] `DEEP_WORK` の delta は全 0.0 (persona base のまま)
- [ ] FSM がモード遷移を検出した時、`AgentState.erre.sampling_overrides`
      が新モードの delta で更新される (unit test)
- [ ] 遷移なし (FSM None 返却 / candidate == current) のケースでは
      `sampling_overrides` が変更されない (回帰 test)
- [ ] `compose_sampling` が extreme base (`temperature=2.0` 等) でも
      `ResolvedSampling` の range 内に clamp される (boundary test)
- [ ] `uv run pytest -q` が全 グリーン (M5 merge 後 = 549+ test に回帰なし)
- [ ] `uv run ruff check src tests` PASS
- [ ] `uv run ruff format --check src tests` PASS
- [ ] `uv run mypy src/erre_sandbox` → 0 errors
- [ ] `code-reviewer` agent レビュー HIGH なし

## 関連ドキュメント

- `.claude/skills/persona-erre/SKILL.md` §ルール 2 (delta テーブル原典)
- `.steering/20260420-m5-planning/design.md` §Phase 2 並列 4 本
- `.steering/20260420-m5-erre-mode-fsm/design.md` (v2 採用、FSM 設計)
- `.steering/20260421-m5-world-zone-triggers/decisions.md` (cognition層配線)
- `src/erre_sandbox/inference/sampling.py` (`compose_sampling` + clamp)
- `src/erre_sandbox/erre/fsm.py` (`DefaultERREModePolicy`)
- `src/erre_sandbox/cognition/cycle.py:377` (FSM hook、改修対象)

## 運用メモ

- 破壊と構築（/reimagine）適用: **No**
- 理由: 実装パターンは persona-erre Skill §ルール 2 で確定済、
  新規モジュールはテーブル定数 + 軽い wire のみで設計判断が少ない。
  FSM 本体と cognition 配線は PR #57 / #58 で済み、本タスクは
  「既存の hook に delta を流す 1 ライナー相当」の拡張。
