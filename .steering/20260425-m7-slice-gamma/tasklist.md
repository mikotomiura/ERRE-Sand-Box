# Tasklist — M7 Slice γ

> 次セッション開始時の action plan。各項目 30 分粒度。
> **最初に Plan mode + Opus で /reimagine を走らせ、design.md を確定させる**。

## Session 開始時

- [ ] `git fetch && git pull origin main` で最新化
- [ ] `feat/m7-slice-gamma` を main から切る
- [ ] Plan mode (Shift+Tab 2 回) に入り Opus 指定
- [ ] `design.md` の 5 軸で `/reimagine` を発動、v1 → 破壊 → v2 → synthesis
- [ ] ExitPlanMode で承認を得る
- [ ] context 30% 超なら `/clear` してから実装に入る

## Commit 1: schemas 拡張 (1.5h)

- [ ] `src/erre_sandbox/schemas.py` に ReasoningTrace 追加フィールド
- [ ] `src/erre_sandbox/schemas.py` に `WorldLayoutMsg` 定義
- [ ] schema_version bump、compatibility chart 更新
- [ ] `tests/fixtures/control_envelope/` に golden JSON 追加
- [ ] `tests/test_schemas.py` + `tests/test_schemas_m7.py` パス
- [ ] commit

## Commit 2: cognition (affinity hook + 相互反省 + trace 根拠) (4h)

- [ ] `src/erre_sandbox/memory/store.py` に `record_dialog_interaction`
- [ ] `src/erre_sandbox/cognition/cycle.py` の DialogTurnMsg 経路に hook 発火
- [ ] `src/erre_sandbox/cognition/reflection.py` に相互反省 prompt 追加
- [ ] `src/erre_sandbox/cognition/cycle.py` ReasoningTrace 構築時に
      affinity / preferred_zones を decision に埋め込み
- [ ] unit tests 追加 (hook / prompt 構造 / trace 内容)
- [ ] commit

## Commit 3: gateway WorldLayoutMsg 送信 (1h)

- [ ] `src/erre_sandbox/ui/gateway.py` or `ui/godot_bridge.py` で on-connect
      時に WorldLayoutMsg emit
- [ ] integration test で connect → WorldLayoutMsg 受信を assert
- [ ] commit

## Commit 4: Godot Relationships UI + layout consumer (3h)

- [ ] `godot_project/scripts/ReasoningPanel.gd` に Relationships section
- [ ] `godot_project/scripts/BoundaryLayer.gd` が WorldLayoutMsg を受領して
      zone_rects / prop_coords 更新 (hardcode 除去、TODO(slice-γ) 解消)
- [ ] `godot_project/scenes/zones/Chashitsu.tscn` の scene root を
      (33.33, 0, -33.33) に修正 (β 送り債務)
- [ ] `godot_project/scenes/zones/Zazen.tscn` に 石灯籠 primitive 追加
      (β 送り債務)
- [ ] `uv run pytest tests/test_godot_project.py` headless boot 緑
- [ ] commit

## Commit 5: γ 受入 + C3 判定 (1.5h)

- [ ] 受入 test 追加 (`tests/test_integration/test_slice_gamma_e2e.py`)
- [ ] C3 (agent anatomy visual) の要否判定を decisions.md に記録
- [ ] 不要と判断 → "C3 deprecated (Slice γ 後)" を decisions に追記
- [ ] 必要と判断 → 新 task dir `.steering/YYYYMMDD-m7-c3-anatomy/` を起票、
      3 案 /reimagine を Plan mode で
- [ ] commit

## Verification + PR

- [ ] `uv run pytest tests/` 全パス
- [ ] `uv run ruff check src/ tests/` / `--format --check` clean
- [ ] code-reviewer agent で 5 commit レビュー、HIGH 全対応
- [ ] security-checker skip 可 (外部入力なし、WebSocket は既存 envelope の拡張のみ)
- [ ] `.steering/20260425-m7-slice-gamma/decisions.md` に D1-DN 記録
- [ ] live G-GEAR で 90-120s run、受入条件 5 項目を満たすことを確認
- [ ] `git push -u origin feat/m7-slice-gamma`
- [ ] `gh pr create` with 本 tasklist 受入チェック + live 項目
- [ ] PR URL を decisions.md に記録

## Follow-up

- [ ] Slice δ (LoRA spike / 4 agent 目 / user-dialogue IF) を L6 steering 再読の
      上で起票
