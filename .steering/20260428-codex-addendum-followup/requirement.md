# Codex addendum followup — docs / steering / agent setup 整合性回復

## 背景

外部 reviewer (Codex) の Addendum (`# Addendum: Steering And Docs Review`,
`.steering/20260428-codex-review-followup/codex_review.md` L274-626) で
docs/ と .steering/ の整合性に関する 10 件の finding が追加提出された。
私 (Claude) が verdict した結果、全 10 件 VALID。前 PR #111 (F1-F6 コード修正)
の docs 反映漏れ + 既知の docs drift + Codex setup 整合性問題を一括対応する。

主要問題:
- D1: codex-review-followup の design.md が TEMPLATE のまま (decisions/tasklist は私が起草済)
- D2: contracts/ レイヤー新設を SKILL には反映したが docs/architecture.md と
  docs/repository-structure.md に伝播していない
- D4: AGENTS.md L21,23,97-99 が `.Codex/commands` を参照、実体は `.claude/`
  と `.agents/` (3 つの命名規約が混在)
- D5: docs/architecture.md に複数の stale fact (e5-small/384d→nomic/768d、
  /stream→/ws/observe、Godot 4.4→4.6、Linux/WSL2→Win native)
- D6: docs/repository-structure.md に存在しないパス列挙 (ui/ws_client.py 等)
- D7: docs/development-guidelines.md が pre-commit/CI を主張、実不在
- D8: 6 scaffold (m9 + 5 sibling) が template 状態、execution-ready に見える
- D9: m9-pre-plan tasklist が post-merge 状態を反映していない + blockers.md template
- D10: docs/glossary.md に mojibake 10 件
- D3: F4 scope の文書整合性弱い (実質問題なし、文書 cleanup)

## ゴール

1. **D1**: codex-review-followup の design.md を実態反映 (post-merge 状態)
2. **D2**: contracts/ レイヤーを docs/architecture.md + docs/repository-structure.md
   に追記、3 案比較を decisions.md に記録 (PR #111 では SKILL のみ更新だった反省)
3. **D4**: AGENTS.md の `.Codex/` 参照を実体 (`.claude/` + `.agents/`) に修正、
   `.agents/` と `AGENTS.md` 自体を git に commit (現状 untracked)
4. **D5**: docs/architecture.md の stale fact 4 件 (embedding/route/Godot/OS)
   を実態に更新
5. **D6**: docs/repository-structure.md の path 列挙を `find`/`rg --files` 実態に再生成
6. **D7**: pre-commit/CI claim を実態 (不在) に合わせて docs 更新 OR pre-commit
   導入 (Plan で /reimagine 判断)
7. **D8**: 6 scaffold (m9 含む) に "DRAFT — DO NOT EXECUTE" マーカー追加
8. **D9**: m9-pre-plan tasklist の commit/PR 項目を post-merge 状態に更新、
   blockers.md は template 削除 or "No blockers recorded" に
9. **D10**: docs/glossary.md mojibake 10 件修正
10. **D3**: codex-review-followup の requirement.md / decisions.md の F4 言及を
    "deferred、別 task で扱う" に統一

## スコープ

### 含むもの
- `.steering/20260428-codex-review-followup/design.md` の TEMPLATE 解消
- `docs/architecture.md` の embedding / WebSocket route / Godot version /
  G-GEAR OS / contracts/ レイヤー追加
- `docs/repository-structure.md` の path 列挙再生成 + contracts/ 追加 +
  存在しない governance/CI ファイル削除
- `docs/development-guidelines.md` の pre-commit/CI claim 整合
- `docs/glossary.md` mojibake 10 件修正
- `AGENTS.md` の `.Codex/` → `.claude/` (or `.agents/`) 整合 + 命名規約 note
- `.agents/` と `AGENTS.md` を git commit (現状 untracked)
- `.steering/20260428-m9-lora-pre-plan/tasklist.md` post-merge 反映
- `.steering/20260428-m9-lora-pre-plan/blockers.md` cleanup
- 6 scaffold (`.steering/20260428-{agent-presence-visualization,
  event-boundary-observability,godot-viewport-layout,godot-ws-keepalive,
  m9-lora-pre-plan,world-asset-blender-pipeline}/`) に "DRAFT" マーカー

### 含まないもの
- `.github/workflows/ci.yml` 新設 (D7 の hybrid で「現状 manual と明示」を選んだ場合)
- pre-commit hook 導入 (同様、別 task で扱う or 本 task で hybrid 採用後着手)
- 6 scaffold の design.md 完成 (各 task の本実装時に行う)
- 新機能追加 / コードロジック変更 (D7 hybrid で pre-commit 導入時のみ pyproject 変更あり)
- F4 (Godot test crash) の修正 (前 PR で deferred 確定)

## 受け入れ条件

- [ ] codex-review-followup design.md に実装アプローチ + 影響範囲 + テスト戦略 + ロールバック計画記載
- [ ] docs/architecture.md grep: `e5-small` 不在 OR "(historical)" タグ付き、
  `nomic-embed-text` + `768` 出現、`/ws/observe` 出現、`Godot 4.6` 出現
- [ ] docs/architecture.md に contracts/ レイヤー記述あり
- [ ] docs/repository-structure.md grep: `ws_client.py`/`godot_bridge.py`/`dashboard.py` (root level)
  不在、`ui/dashboard/` 出現、`contracts/` 出現
- [ ] AGENTS.md grep: `.Codex/` 不在、`.claude/` または `.agents/` 出現
- [ ] `.agents/` と `AGENTS.md` が `git ls-files` に含まれる
- [ ] docs/glossary.md grep: 置換文字 (`\xef\xbf\xbd` または `?`) 不在
- [ ] m9-pre-plan tasklist の commit/PR 項目 [x] マーク
- [ ] 6 scaffold の design.md 冒頭に "DRAFT REQUIREMENT ONLY — DO NOT EXECUTE" マーカー
- [ ] `uv run pytest` 全通過 (コード変更なしのため regression なし)
- [ ] code-reviewer HIGH/CRITICAL なし

## 関連ドキュメント

- `.steering/20260428-codex-review-followup/codex_review.md` L274-626 (Addendum 本文)
- `.steering/20260428-codex-review-followup/decisions.md` D2 (contracts/ レイヤー新設の判断、本 task で docs 伝播)
- `.claude/skills/architecture-rules/SKILL.md` (PR #111 で contracts/ 追記済、本 task で docs と整合)
- `docs/architecture.md` / `docs/repository-structure.md` / `docs/glossary.md` / `docs/development-guidelines.md`
- `AGENTS.md` (Codex 用) / `CLAUDE.md` (Claude 用)
- `.agents/skills/` (Codex 向けの 12 skill mirror、現 untracked)

## 運用メモ
- 破壊と構築（/reimagine）適用: **Yes**
- 理由: D7 (pre-commit/CI) と D4 (Codex root 命名規約) は複数案あり。
  D7 hybrid: 「docs を manual と明示」 vs 「pre-commit 導入」 vs
  「両方 (manual と CI を区別、CI は別 task)」。
  D4 hybrid: 「`.Codex/` → `.claude/` に統一」 vs 「`.agents/` を Codex 専用 root
  として正規化」 vs 「両方併存 + 役割明示」。Plan mode 内で /reimagine 必須。
