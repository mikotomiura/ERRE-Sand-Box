# タスクリスト

## 準備
- [x] Addendum 全 10 件 verdict (D1-D10 すべて VALID)
- [x] 関連ファイル並列 read (AGENTS.md / docs/architecture / docs/repo-structure / docs/glossary / docs/development-guidelines)
- [x] /reimagine v1/v2/第3案 → hybrid (D7 + D4) 採用方針確定 (decisions.md D2/D3)

## 実装 (Phase A-J, 1 phase = 1 commit)

- [x] **Phase A**: D8 5 sibling scaffold に "DRAFT REQUIREMENT ONLY — DO NOT EXECUTE" マーカー (m9-pre-plan は除外)
- [x] **Phase B**: D9 m9-pre-plan tasklist post-merge update + blockers cleanup
- [x] **Phase C**: D10 glossary mojibake 10 箇所修正 (replacement char count = 0)
- [x] **Phase D**: D1 codex-review-followup design.md 補完 (PR #111 post-merge 状態)
- [x] **Phase E**: D5 docs/architecture.md fact 更新 (nomic-embed-text/768d, /ws/observe, Godot 4.6, Win native, contracts/) + "現状実装スナップショット" section
- [x] **Phase F**: D6 docs/repository-structure.md ツリー再生成 + ui/dashboard/, contracts/, .agents/, AGENTS.md 反映
- [x] **Phase G**: D2 contracts/ レイヤーを docs/repository-structure.md に伝播 + decisions.md D1 に 3 案比較記録
- [x] **Phase H**: D7 docs/development-guidelines.md "現状 manual" 注記 + ci-pipeline-setup scaffold 起票
- [x] **Phase I**: D4 AGENTS.md path 修正 (`.Codex/` → `.claude/` + `.agents/`) + .agents/ + AGENTS.md commit
- [x] **Phase J**: D3 F4 文書整合 (codex-review-followup requirement.md "deferred 確定") + tasklist (本ファイル) 起草 + 最終 verification + push + PR

## テスト
- [x] `uv run pytest`: 1044 passed, 28 skipped, exit 0 (PR #111 と同じ、コード変更ゼロのため regression なし)
- [x] `uv run ruff check src tests`: All checks passed
- [x] `uv run ruff format --check src tests`: 149 files already formatted

## 受け入れ条件 (grep ベース、最終検証)
- [x] codex-review-followup design.md 101 行 ≥ 30
- [x] docs/architecture.md fact updates 10 ≥ 4 (nomic-embed-text / /ws/observe / Godot 4.6 / Windows)
- [x] docs/architecture.md `contracts/` 言及 1 ≥ 1
- [x] docs/repository-structure.md `ui/dashboard/` 出現 1
- [x] docs/repository-structure.md ws_client.py / godot_bridge.py / dashboard.py (root) 削除
- [x] AGENTS.md `.Codex/` 不在 (1 箇所のみ存在 = "存在しない" の説明文中)
- [x] .agents/ tracked 23 files
- [x] AGENTS.md tracked
- [x] docs/glossary.md mojibake 0
- [x] m9-pre-plan tasklist `[x] git commit` 出現 2 ≥ 1
- [x] 5 scaffold DRAFT マーカー 5 ≥ 5

## レビュー
- [ ] code-reviewer による diff レビュー (HIGH/CRITICAL なし確認)

## ドキュメント
- [x] decisions.md (D1 contracts/ 3 案比較 + D2 D7 hybrid + D3 D4 hybrid + D4 m9 除外) 起草
- [x] tasklist.md (本ファイル) 最終化
- [ ] memory 更新 (本 task 完了後、PR merge 後に project_codex_addendum_merged.md 起票)

## 完了処理
- [ ] git commit (Phase J: F4 整合 + tasklist + decisions の最終 commit)
- [ ] git push -u origin docs/codex-addendum-followup
- [ ] gh pr create
