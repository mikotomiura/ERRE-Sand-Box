# 設計案比較 — m5-orchestrator-integration

## v1 (初回案) の要旨

3 軸とも中間抽象を導入する案。feature flag は `BootConfig` に 3 bool 追加、
dialog turn 駆動は新規 class `DialogOrchestrator` (新規ファイル
`integration/dialog_orchestrator.py`) を作って WorldRuntime にアタッチ、
dialog_id は orchestrator が envelope sink chain を interception して
`DialogInitiateMsg` 観測時に `scheduler.get_dialog_id(init, target)` で取得し
自前 map を保持。`disable_mode_sampling` の実装経路は未決 (/reimagine v2 で
決定するペンディング項目として残っていた)。

## v2 (再生成案) の要旨

既存構造への最小同化案。feature flag は `bootstrap()` の kwargs (BootConfig
不変)、dialog turn 駆動は WorldRuntime 内部に直接 method 2 本
(`attach_dialog_generator` + `_drive_dialog_turns`) として同化、dialog 列挙は
scheduler に minimal accessor `iter_open_dialogs()` を 1 本追加、
`disable_mode_sampling` は `CognitionCycle.__init__` に
`erre_sampling_deltas: Mapping | None = None` kwarg を追加し bootstrap が
zero-delta テーブルを注入。新規ファイルは test 1 本のみ。

## 主要な差異

| 観点 | v1 | v2 |
|---|---|---|
| feature flag の置き場 | `BootConfig` 拡張 (3 bool 追加) | `bootstrap()` keyword-only kwargs |
| flag の位置付け | 永続 config と同列 | 過渡期 rollback 専用と明確に分離 |
| dialog turn 駆動 | 新規 class `DialogOrchestrator` | `WorldRuntime` に method 2 本追加 |
| 新規ファイル (src) | 1 (`integration/dialog_orchestrator.py`) | 0 |
| dialog_id 取得経路 | envelope sink interception + 自前 map | `scheduler.iter_open_dialogs()` 直接 |
| scheduler の surface | 変更なし (sink chain で回避) | 1 method 追加 (4 行、read-only) |
| state の真実の source | scheduler + orchestrator 二重 | scheduler 単一 |
| `disable_mode_sampling` 実装 | 未決 (v1 最後に "v2 で決定" と残置) | `CognitionCycle` に `erre_sampling_deltas` DI スロット追加 |
| `cognition/cycle.py` 変更 | なし (v1 では本ファイルに触らない) | 1 kwarg 追加 + 1 行置換 |
| `_on_cognition_tick` の async 影響 | 同 (await 新設必須) | 同 |
| 単体テスト粒度 | orchestrator class 単体 + bootstrap smoke | WorldRuntime inline method 単体 + bootstrap smoke |
| ロールバック容易性 | `attach_dialog_orchestrator` 不呼び出し | `attach_dialog_generator` 不呼び出し (対称) |
| 読者の認知負荷 | 中間 class を読む必要あり | WorldRuntime を読めば coordination 全体が見える |
| architecture-rules 整合性 | Protocol で duck-type して回避 | `DialogTurnGenerator` Protocol (既存) を直接利用 |

## 評価 (各案の長所・短所)

### v1 の長所

- orchestration ロジックが 1 class に凝集して分離テストしやすい
- WorldRuntime が fat にならない (単一責務原則的に綺麗)
- `DialogOrchestrator` を将来別実装に差し替える余地が明示的

### v1 の短所

- **state 二重化**: scheduler が `_open: dict[str, _OpenDialog]` を持つのに
  orchestrator も `_open: dict[str, (init, target, zone)]` を持つ。更新タイミング
  (sink chain) がずれると inconsistent state が発生するリスク
- **envelope sink chain の間接性**: sink が 3 段になる
  (scheduler → orchestrator → runtime.inject_envelope)。例外ハンドリングの
  責務が分散し、どこでエラーを catch するか考える必要
- **新規ファイル 1 本・新規 class 1 本を "糊付けのためだけに" 作る**: 実装上は
  20-30 行の iteration ロジック。class にするほどの振る舞いがない
- `disable_mode_sampling` の実装経路が未決のまま
- 既存 PR #61 decisions.md §2 (scheduler は不変) に厳密に従おうとした結果、
  envelope chain という複雑な回避策を選ぶ形になっている

### v2 の長所

- **最小差分**: 新規 src ファイル 0、既存ファイル 4 個の局所編集のみ
- **state 単一化**: scheduler が真実の source、他が query する一方向
- **`WorldRuntime` の coordination 全体が 1 ファイルで読める**: 物理・認知・
  heartbeat・dialog scheduler tick・dialog turn driving が同じ
  `_on_cognition_tick` に並ぶ
- PR #61 decisions.md §2 を「dialog_turn_generator の文脈での拒否」と再解釈し、
  orchestrator integration という別文脈での 1 method 追加は妥当と判断
- `disable_mode_sampling` を `CognitionCycle` の DI スロット追加で綺麗に実装
- envelope sink interception が不要で、既存 sink flow が無変更

### v2 の短所

- `WorldRuntime` が僅かに肥大化 (2 method 追加)
- 将来 `DialogTurnGenerator` の駆動ロジックを差し替えたくなったときに
  WorldRuntime 内部を編集する必要がある (v1 は orchestrator 差し替えで済む)
- `cognition/cycle.py` に触る — PR #60 で最近変更されたファイルのため差分が
  読まれやすい (ただし追加 kwarg + 1 行置換で回帰リスクは極小)
- PR #61 decisions.md §2 を再解釈することになる (拒否された helper 群とは
  別系統だが、"scheduler 不変" の方針を緩める第一歩になる)

## 推奨案

**v2 採用を推奨**。

**根拠**:

1. **複雑性の総量が少ない**: v1 は `DialogOrchestrator` class + envelope sink
   chain + state 二重化 + orchestrator 差し替えの余地、という 4 つの構造を
   導入する。v2 はそのどれも持たず、既存構造に追加する method 3 本と
   `iter_open_dialogs` 1 本で完結する。現時点で class 化を正当化する差し替え
   要件は存在しない (YAGNI)

2. **state の真実の source が scheduler 単一になる**: v1 の envelope sink chain
   は、DialogInitiateMsg が `dialog_id` を持たないため
   `scheduler.get_dialog_id(init, target)` を結局呼ぶ設計になる。どのみち
   scheduler を信頼するなら、`iter_open_dialogs` で直接取ればよい

3. **`disable_mode_sampling` の実装経路が明確**: v1 は "未決、v2 で決定" と
   残置していたが、v2 は `CognitionCycle.erre_sampling_deltas` 注入点で
   綺麗に実装できる。これは cognition/cycle.py の責務 (sampling 合成) に
   自然に収まる

4. **feature flag の設計がより正確**: v1 は `BootConfig` に 3 bool を追加し
   永続 config と同列にしたが、これらは M5 acceptance 後に削除される
   transient knob。bootstrap kwargs への切り出しは「長命 config と過渡期
   flag の分離」という設計意図が明示される

5. **PR #61 decisions.md §2 との整合性**: 同 §2 が拒否した helper は
   `participants_of` / `should_take_turn` / `turn_index_of` の 3 種で、すべて
   *turn generator 用* の pair 単位 query。v2 の `iter_open_dialogs` は
   *orchestrator 用* の全 open enumerate で、用途が異なる。旧決定の再解釈は
   妥当

### ハイブリッド余地 (ユーザーが指摘した場合)

- v2 で採用するが **feature flag は BootConfig へ** → 運用上のシンプルさ
  (全設定が 1 箇所) を重視したい場合。この場合 v1 の Axis 1 を採用
- v2 で採用するが **orchestration ロジックは別 method ではなく既存 `_run_dialog_tick`
  を async 化して同化** → `_run_dialog_tick` の責務を proximity auto-fire +
  timeout close + turn driving に広げる案。v2 + v1 より軽量

## 次のステップ

ユーザーの採用判断を受けて:

- v2 採用 → 現 `design.md` をそのまま確定 (末尾に "採用判断の履歴" 追記)
- v1 採用 → `cp design-v1.md design.md` で置換 + 履歴追記
- ハイブリッド → `design.md` を Edit で整形 + 履歴追記
