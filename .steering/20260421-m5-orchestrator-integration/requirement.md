# m5-orchestrator-integration

## 背景

M5 Phase 2 の前段 3 タスク (PR #58 FSM wire / PR #60 sampling delta / PR #61 dialog
turn generator) が merge 済で、必要な部品 (`DefaultERREModePolicy`,
`SAMPLING_DELTA_BY_MODE`, `OllamaDialogTurnGenerator`) はすべて単体で動作する
状態にある。しかし composition root (`bootstrap.py` / `__main__.py`) ではまだ
いずれも instantiate されておらず、live 起動しても:

- `CognitionCycle(erre_policy=None)` のまま → ERRE mode FSM は no-op
- `DialogTurnGenerator` が wire されていない → dialog_initiate 後は timeout close
  のみ (M4 と同じ挙動)
- feature flag が存在しない → M4 相当の挙動へ即時 rollback できない

本タスクで「部品 → システム」の合流を完了させ、次の `m5-acceptance-live` で
7 項目 PASS/FAIL を判定できる状態にする。これは M5 Phase 2 の critical path 上
最後から 2 番目のタスクで、acceptance と tag 付け (`v0.3.0-m5`) の直前の関門。

併せて、先行タスク `m5-world-zone-triggers` の `tasklist.md` 末尾 3 項目
(commit/push/PR、PR #58 として merge 済) の checkbox が未更新なので、
本 PR の冒頭 chore として整合させる。

## ゴール

1. `bootstrap.py` が `DefaultERREModePolicy` と `OllamaDialogTurnGenerator` を
   instantiate し、`CognitionCycle` および dialog 経路に wire する
2. 3 つの feature flag (`--disable-erre-fsm` / `--disable-dialog-turn` /
   `--disable-mode-sampling`) が `__main__.py` から受け取れ、OFF 時に M4 相当の
   挙動に rollback できる
3. cognition tick 内で open dialog を走査し、budget 超過なら
   `scheduler.close_dialog(did, reason="exhausted")`、そうでなければ
   `generator.generate_turn(...)` で次 turn を生成 → `scheduler.record_turn` +
   envelope sink で emit する経路が常に動く
4. LLM unavailable / None return は既存の timeout close 経路に graceful に帰着
5. 既存 549 test (PR #61 時点) に回帰なし、new boot smoke test が追加されている

## スコープ

### 含むもの

- `bootstrap.py` への `DefaultERREModePolicy` / `OllamaDialogTurnGenerator`
  instantiation と wire (persona registry を generator に注入する配線を含む)
- `__main__.py` に 3 つの feature flag を追加 (argparse + `BootConfig` 拡張 or
  環境変数 or どれが最適かは /reimagine で確定)
- orchestrator が毎 cognition tick で open dialog を iterate し、budget 判定・
  turn 生成・record/emit・close 判定までを完走させる wiring (設置点は
  `WorldRuntime` 拡張 vs `CognitionCycle` 内蔵 vs 専用 `DialogOrchestrator` 新設
  の 3 択、/reimagine で確定)
- speaker 交互性のロジック (initiator / target の alternation、transcript 長から
  導出) の実装
- boot smoke test: flag 各 OFF / ON 組み合わせで bootstrap が raise せず、
  `runtime.register_agent` が期待通り呼ばれることを確認
- `m5-world-zone-triggers` の `tasklist.md` 末尾 3 checkbox を埋める整合 chore
  (本 PR に同梱、本 chore のためだけに別 PR を切らない)

### 含まないもの

- live acceptance (7 項目の evidence 収集は次タスク `m5-acceptance-live` の責務)
- `v0.3.0-m5` タグ付け (acceptance PASS 後、ユーザー確認を経て付与)
- `InMemoryDialogScheduler` への新規 helper 追加
  (PR #61 decisions.md §2 で hybrid 拒否確定済、orchestrator 側で
  `len(scheduler.transcript_of(did))` 直参照とする)
- Godot 側の変更 (PR #59 で完了済)
- 新規 schema 変更 (contracts は 0.3.0-m5 freeze 済)

## 受け入れ条件

- [ ] `bootstrap.py` が `DefaultERREModePolicy` を instantiate し、
      `CognitionCycle(erre_policy=...)` に渡している
- [ ] `bootstrap.py` が `OllamaDialogTurnGenerator(llm=..., personas={...})` を
      instantiate し、全 persona が registry に入る
- [ ] `__main__.py` で `--disable-erre-fsm` を渡すと FSM が wire されず (M4 相当)、
      既存 unit test / live 経路の両方で無事に起動すること
- [ ] `__main__.py` で `--disable-dialog-turn` を渡すと generator が wire されず、
      既存の timeout close 経路で dialog が閉じること
- [ ] `__main__.py` で `--disable-mode-sampling` を渡すと sampling override が
      bypass され、persona YAML の default sampling のみで LLM call が走ること
- [ ] open dialog iteration が cognition tick ごとに走り、budget 超過で
      `reason="exhausted"` close、未満なら turn 生成 → record + emit する
- [ ] LLM unavailable / `generate_turn` が `None` を返した場合、既存 timeout
      経路に graceful に帰着 (crash しない、zombie dialog を作らない)
- [ ] speaker 交互性が satisfied (`initiator` = index 0, 2, 4, ... /
      `target` = index 1, 3, 5, ...)
- [ ] boot smoke test で flag 3 軸の OFF / ON 組み合わせ (≥4 ケース程度) を検証
- [ ] `uv run pytest -q` で PR #61 時点の 549 passed を超え、0 failure
- [ ] `uv run ruff check src tests` / `ruff format --check` / `mypy src/erre_sandbox`
      いずれも PASS
- [ ] `m5-world-zone-triggers/tasklist.md` 末尾 3 checkbox が埋まる

## 関連ドキュメント

- `.steering/20260421-m5-dialog-turn-generator/decisions.md` — 判断 1-6
  (DI 形態・budget 判定・speaker alternation の導出方法)
- `.steering/20260421-m5-world-zone-triggers/decisions.md` — FSM は
  `CognitionCycle.__init__(erre_policy=...)` で DI 済
- `.steering/20260421-m5-erre-sampling-override-live/decisions.md` — sampling
  反映の前提 (fail-fast テーブル、cognition/cycle.py 内 wire)
- `.steering/20260420-m5-planning/design.md` §依存グラフ §ロールバック計画 — 3 flag 原則
- `docs/architecture.md` — composition root の位置付けと tick loop の流れ
- 参考 Skill: `implementation-workflow` / `error-handling` / `python-standards`
  (`architecture-rules` は `world/tick.py` に触る場合のみ)

## 運用メモ

- **破壊と構築 (/reimagine) 適用**: **Yes**
- **理由**: 以下 3 軸で複数案が存在し、どれも正解に近い hybrid 採用の可能性が高い:
  1. **feature flag の置き場**: `__main__.py` 単独 vs `BootConfig` 拡張 vs 環境変数
  2. **DialogTurnGenerator 注入点**: `WorldRuntime` vs `CognitionCycle` vs 専用
     `DialogOrchestrator` 新設
  3. **tick ごとの open dialog iteration の所在**: `scheduler.tick()` 内に追加
     vs `WorldRuntime._on_cognition_tick` 内 vs 新規 method
- **タスク種別**: 新機能追加 (→ 次は `/add-feature`)
- **先行タスク chore**: `m5-world-zone-triggers/tasklist.md` 末尾 3 checkbox を
  本 PR 冒頭で埋める (別 PR にはしない)
