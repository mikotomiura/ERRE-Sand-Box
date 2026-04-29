# Claude Code 環境構築 検証レポート

検証日時: 2026-04-29 14:30 (Asia/Tokyo)
検証コマンド: `/commands_setup:verify-setup` (Phase 9 / 10 段階体系版)
検証ブランチ: `debug/event-boundary-pulse-trace`
直近 main: `5d2b542`

## 総合判定

**⚠️ WARNINGS** — 日常運用は HEALTHY だが、新旧 setup 仕様の体系差により仕様乖離が複数。CRITICAL なし、HIGH 1 件 (進捗ファイルの体系不整合)、MEDIUM 5 件、LOW 2 件。

> **重要な前提**: 本リポジトリは旧 8 段階体系 (Phase 0-7) で 2026-04-17/18 に構築完了済み。新 10 段階体系 (Phase 0-9 / Marketplace + Codex Bridge 追加) は **後から導入された仕様**であり、Phase 5 Codex 連携は本プロジェクトでは別レイアウト (`.codex/agents/*.toml` + `.codex/hooks/*.py` + `.agents/skills/` / PR #114 採用) を選択している。よって新 spec 上「MISSING」とされる項目の多くは **意図的なアーキテクチャ選択** であり、実害ではない。

## Phase 番号 旧 → 新 マッピング

| 旧 (Phase 0-7) | 新 (Phase 0-9) | 本リポでの状態 |
|---|---|---|
| Phase 0 | Phase 0 | ✅ 完了 (2026-04-17) |
| Phase 1 | Phase 1 | ✅ 完了 (2026-04-17) |
| — | Phase 2 (新規 marketplace) | ❌ skip — `docs/external-skills.md` 不在 |
| Phase 2 | Phase 3 | ✅ 完了 — ただし `docs/agent-shared.md` 不在 |
| Phase 3 | Phase 4 | ✅ 完了 (12 Skill) |
| — | Phase 5 (新規 codex-bridge) | 🔄 **代替レイアウトで完了** (PR #114) |
| Phase 4 | Phase 6 | ✅ 完了 (9 Agent) |
| Phase 5 | Phase 7 | ✅ 完了 (8 Command) |
| Phase 6 | Phase 8 | ✅ 完了 (6 hook script) |
| Phase 7 | Phase 9 | 🔁 本日再実行 (今回) |

## 各フェーズの状態

### Phase 1: docs ✅
- `docs/functional-design.md` / `architecture.md` / `repository-structure.md` / `development-guidelines.md` / `glossary.md` 全 5 件 OK

### Phase 2: Marketplace ❌ SKIPPED (新仕様)
- `docs/external-skills.md` **MISSING** — 新仕様で必須の唯一の真実源
- `anthropics/skills` 公式 plugin 未導入

### Phase 3: CLAUDE.md / AGENTS.md / agent-shared.md ⚠️
- `CLAUDE.md`: 99 行 (上限 150 ✅)
- `AGENTS.md`: 117 行 (上限 80 ⚠️ 超過 +37)
- `docs/agent-shared.md`: **MISSING** ❌
- `@docs/agent-shared.md` 参照: CLAUDE.md=0 / AGENTS.md=0 (target file が存在しないため必然)
- 必須セクション: 各々の内部規範は満たすが「3 ファイル分割」アーキテクチャは未採用

### Phase 4: Skills ✅
- 自前 Skill: 12 件すべて SKILL.md あり
  - architecture-rules / blender-pipeline / empirical-prompt-tuning / error-handling / git-workflow / godot-gdscript / implementation-workflow / llm-inference / persona-erre / project-status (動的) / python-standards / test-standards
- 動的 Skill: 1 件 (project-status) ✅
- `empirical-prompt-tuning` 存在 ✅
- `implementation-workflow` 存在 ✅
- 公式 Skill 重複回避: 検証不能 (Phase 2 skip により真実源なし)

### Phase 5: Codex Bridge 🔄 代替レイアウトで完了
新仕様が期待するパスは存在しないが、本プロジェクトは PR #114 で採用した別レイアウトで Codex を first-class partner 化している。

#### 新仕様パス (すべて MISSING、ただし不在は妥当):
- `scripts/secrets-filter.sh` / `run-codex-consult.sh` / `run-codex-review.sh`
- `.claude/skills/codex-consult/` / `codex-review/` / `codex-rescue/`
- `.claude/agents/cross-reviewer.md` / `.claude/commands/cross-review.md`
- `.claude/hooks/codex-budget-guard.sh` / `secrets-pre-filter.sh` / `token-report-stop.sh`
- `.codex/budget.json`

#### 実レイアウト (動作検証済):
- `.codex/config.toml` ✅ — `model = "gpt-5.5"`, `web_search = "live"`, `agents.max_threads = 6`
- `.codex/hooks.json` ✅ — SessionStart/UserPromptSubmit/PreToolUse/Stop の 4 hook 登録
- `.codex/hooks/*.py` 5 件: `_erre_common.py` / `pre_tool_use_policy.py` / `session_start.py` / `stop_report.py` / `user_prompt_submit.py`
- `.codex/agents/*.toml` 5 件: `erre-explorer` / `erre-impact-analyzer` / `erre-reviewer` / `erre-security-checker` / `erre-test-runner`
- `.agents/skills/` Mirror: 13 dirs (`erre-workflow` 含む 12 自前 Skill のミラー)

#### 疎通テスト (Step 2.7) ✅ PASS
```
codex exec --sandbox read-only --skip-git-repo-check -m gpt-5.5 \
  -c model_reasoning_effort=low "Reply with just: Hello"
→ exit 0, response="Hello", 17,200 tokens used
```
- `codex` CLI v0.125.0 ✅
- session_id 発行 ✅
- 4 種 hook 全 fire ✅
- `codex_core::session: failed to record rollout items` の WARN は session_id 19dd7b4 に対する非致命ログ (動作影響なし)

### Phase 6: Agents ✅
基本 9 エージェントすべて存在:
- file-finder / dependency-checker / impact-analyzer / code-reviewer / test-analyzer / security-checker / test-runner / build-executor / log-analyzer
- cross-reviewer: N/A (新 Phase 5 形態を skip したため不在で正)

### Phase 7: Commands ✅
基本 8 コマンドすべて存在:
- start-task / add-feature / fix-bug / refactor / reimagine / review-changes / smart-compact / finish-task
- /cross-review: N/A (新 Phase 5 形態を skip したため不在で正)

`commands_setup/` 配下 (bootstrap, setup-* × 7, verify-setup, skill-empirical-prompt-tuning) も独立 namespace で存在 — 本セッションの修正対象。

### Phase 8: Hooks ✅
- **settings.json**: ✅ 有効 JSON、5 イベント (SessionStart / UserPromptSubmit / PreToolUse / PostToolUse / Stop) 全登録、全 hook が `"type": "command"` に統一
- **Hook scripts (全 -rwxr-xr-x)**:
  - `session-start.sh` (1018B) ✅
  - `preflight.sh` (1991B) ✅
  - `pre-edit-steering.sh` (2179B) ✅
  - `pre-edit-banned.sh` (2128B) ✅
  - `post-fmt.sh` (666B) ✅
  - `stop-check.sh` (904B) ✅
- **Codex 第 4 層 hooks** (`codex-budget-guard` / `secrets-pre-filter` / `token-report-stop`): N/A (代替レイアウトでは `.codex/hooks/*.py` が代替)

### Phase 9: verify-setup 🔁
本ファイルが本検証の出力。

## 相互参照の整合性

| 検証項目 | 結果 |
|---|---|
| Skill → Agent (`_setup-progress.md` のマップ通り) | ✅ |
| Agent → Command | ✅ |
| Hook → Command | ✅ |
| AGENTS↔CLAUDE 同期 (Step 2.5 keyword leak threshold) | N/A (`docs/agent-shared.md` 不在のため検証 skip) |
| ライセンス整合 (Step 2.6) | N/A (`docs/external-skills.md` 不在のため検証 skip) |
| Codex 疎通 (Step 2.7) | ✅ PASS |

## 修正が必要な項目

### CRITICAL
*なし*

### HIGH
1. **`.steering/_setup-progress.md` が旧 Phase 0-7 体系のまま固定されており、新 10 段階体系との対応マップがない**
   - 影響: 月次再実行で「未完了の Phase が多数」と誤判定される
   - 推奨: 本ファイル冒頭の旧→新マッピング表を `_setup-progress.md` 末尾に追記、または各 Phase エントリを新番号で再ラベル

### MEDIUM
1. **`docs/external-skills.md` が存在しない** — Phase 2 (marketplace) を skip した結果。Phase 4 で「公式 Skill 重複回避」検証ができない
2. **`docs/agent-shared.md` が存在しない** — 新 Phase 3 が前提とする「Claude/Codex 共通基盤」を未採用。代替として CLAUDE.md と AGENTS.md がそれぞれ自己完結
3. **`AGENTS.md` 117 行 (新仕様上限 80 行に対し +37)** — Codex first-class partner 化に伴う必要記述で物理的に短縮困難
4. **CLAUDE.md / AGENTS.md ともに `@docs/agent-shared.md` 参照ゼロ** — 共通ファイル不在の必然
5. **`.codex/budget.json` 不在** — 新 Phase 5 が要求するトークン日次予算ファイル。代替の予算ガードは未実装の可能性 (要確認)

### LOW
1. **session_id rollout 記録警告** (`codex_core::session: failed to record rollout items`) — 動作影響なし、Codex 内部 telemetry の既知挙動
2. **`scripts/` 配下に `regen_schema_artifacts.py` のみ** — Codex wrapper 群を入れる場合の置き場として既に使用中。命名衝突リスクは低い

## 推奨される次のアクション

優先度順:

1. **(HIGH)** `.steering/_setup-progress.md` 末尾に旧→新 Phase マッピング表を追記し、新 verify-setup 実行時の混乱を回避
2. **(MEDIUM)** Phase 5 「代替レイアウト採用」の事実を `_setup-progress.md` に明示記録 (PR #114 への参照付き)。新仕様パスを「skip / alternate」と分類
3. **(MEDIUM, optional)** トークン予算管理が必要なら `.codex/budget.json` か等価機構を導入。本プロジェクトは個人用途で日次トークン上限管理の必要性は低い (要判断)
4. **(LOW)** 現在の event-boundary V3 violet pulse 診断作業 (memory `🔴 NEXT`) を完了させてから、setup 体系の刷新作業に戻る
5. **(参考)** 本検証は **編集中の setup コマンド群が正しく動作するかの dry-run** としても機能。新仕様の verify-setup ロジックは本リポでは「日常運用 HEALTHY だが仕様乖離あり」を正しく検出できることを確認

## 過去レポートとの差分

- `.steering/_verify-report-20260418.md` (旧 Phase 7 結果): HEALTHY / LOW 3 件のみ
- 本レポート (新 Phase 9 結果): WARNINGS / HIGH 1 + MEDIUM 5 + LOW 2
- 差分の主因: 新仕様で Phase 2 (Marketplace) と Phase 5 (Codex Bridge) が追加され、本リポはその仕様パスを採用していない (=skip + 代替レイアウト) ため、検証項目が増えて差分が表面化した
