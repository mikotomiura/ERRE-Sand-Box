# 重要な設計判断 — m5-erre-sampling-override-live

## 判断 1: `SAMPLING_DELTA_BY_MODE[candidate]` はフェイルファストを採用

- **判断日時**: 2026-04-21
- **背景**: code-reviewer が MEDIUM で「enum に新しい値を追加した際、
  テーブルに漏れがあれば `cycle.py::_maybe_apply_erre_fsm` で
  `KeyError` がランタイムで出る」と指摘。
- **選択肢**:
  - A: そのまま `SAMPLING_DELTA_BY_MODE[candidate]` — 欠損時 `KeyError`
  - B: `SAMPLING_DELTA_BY_MODE.get(candidate, SamplingDelta())` + warning log
    で fail-open
- **採用**: A
- **理由**:
  - テスト `test_all_eight_modes_present` が CI で必ず enum と table の
    整合を検証するため、欠損は merge 前に確実に検出される
  - fail-open は「新モードが本来持つはずの delta を silently 失う」症状を
    隠蔽しやすく、live acceptance まで発覚しない可能性がある
  - 失敗はプログラマのミスであり、fail-loud (`KeyError`) で設定漏れを
    即座に気付かせるほうが研究プロトタイプには適切
- **トレードオフ**: 万が一テストを迂回して enum だけ拡張された場合、
  runtime で `CognitionCycle.step()` が例外で落ちる。M5 live acceptance の
  前に再現可能なので、実害は小さい
- **影響範囲**: `cognition/cycle.py::_maybe_apply_erre_fsm`
- **見直しタイミング**: M6 以降で ERRE mode が 3rd party plugin 経由で
  動的に追加可能になる場合は、`get()` + default に切り替える

## 判断 2: `SamplingDelta` の frozen 化は本タスクのスコープ外

- **判断日時**: 2026-04-21
- **背景**: code-reviewer が MEDIUM で「`SAMPLING_DELTA_BY_MODE` の value
  側の `SamplingDelta` インスタンスは Pydantic v2 の frozen ではないので、
  `SAMPLING_DELTA_BY_MODE[CHASHITSU].temperature = 999.0` のような table
  原本の汚染が理論上は可能」と指摘。
- **選択肢**:
  - A: `SamplingDelta` に `model_config = ConfigDict(frozen=True)` を追加
  - B: 本タスクでは放置、現状の Pydantic re-validation (ERREMode 構築時の
    コピー) と MappingProxyType に頼る
  - C: sampling_table.py 側で copy-on-read helper を提供
- **採用**: B
- **理由**:
  - `SamplingDelta` は schemas.py で M5 contracts freeze (PR #56) として
    既に固定済、本タスクのスコープ外
  - 実際の consumer (`ERREMode(sampling_overrides=...)`) は Pydantic v2 が
    コピー validate するので、テーブル原本の汚染経路は「ユーザーコードが
    table を直接叩く」以外にない
  - 研究プロトタイプで外部プラグインが存在しないため、悪意的汚染の現実的
    リスクは低い
- **トレードオフ**: 理論上、悪意 or バグによる table 汚染が global に
  波及する可能性は残る (mitigation: 本 task の immutability test が
  外側 Mapping の汚染は検出する)
- **影響範囲**: `schemas.SamplingDelta` 全利用者
- **見直しタイミング**: schemas.py を次に freeze 解除する機会
  (0.4.0-m6 or 1.0.0) で `ConfigDict(frozen=True)` を追加検討

## 判断 3: LOW 指摘 (非ゼロ delta agent での no-op テスト) は未対応

- **判断日時**: 2026-04-21
- **背景**: code-reviewer の LOW で「FSM no-op path が非ゼロの
  sampling_overrides を保持することを検証する追加テスト」を提案。
- **選択肢**:
  - A: 非ゼロ delta で作った agent を fixture に足し、no-op path で
    unchanged を追加検証
  - B: 本タスクでは対応しない
- **採用**: B
- **理由**: 現行の `test_cycle_erre_policy_noop_preserves_sampling_overrides`
  は `agent.erre.sampling_overrides == result.agent_state.erre.sampling_overrides`
  の等価性検証であり、左右いずれもが同じインスタンスを保持する限り
  `SamplingDelta()` でも非ゼロでも機能的に等価。no-op path の実装は
  `return agent_state` の 1 行で、ロジック分岐が存在しないため回帰リスクは
  極めて小さい
- **影響範囲**: なし (テストカバレッジの追加余地のみ)
- **見直しタイミング**: M6 で cycle の step ロジックを refactor する際

## 判断 4: テーブル配置を `erre/sampling_table.py` に単独モジュールで分離

- **判断日時**: 2026-04-21
- **背景**: delta テーブルの Python 化先として 3 候補があった。
- **選択肢**:
  - A: `erre/fsm.py` に既存の `ZONE_TO_DEFAULT_ERRE_MODE` と並べる
  - B: `inference/sampling.py` に `compose_sampling` と並べる
  - C: `erre/sampling_table.py` として独立モジュール化
- **採用**: C
- **理由**:
  - `fsm.py` は observation → mode の FSM ロジックが主題であり、mode →
    delta の表はやや責務違い (FSM が直接 delta を知る必要がない)
  - `inference/sampling.py` は `compose_sampling` の純粋関数ロジックに
    集中させたい; ERRE mode 概念を知らないほうが層が綺麗
  - 独立モジュールなら docstring で persona-erre skill §ルール 2 を
    source of truth として明示しやすく、drift 検出テストも配置が明快
- **トレードオフ**: モジュール数が 1 増える
- **影響範囲**: `erre/__init__.py` の re-export、テストファイル配置
- **見直しタイミング**: `sampling_table.py` に他のテーブル (例: prompt
  template 切替) も追加される場合は `erre/tables.py` 等にリネームを検討
