---
description: >
  Claude Code 環境構築の入口コマンド。環境チェック、進捗記録ファイルの作成、
  構築計画の提示を行う。新規プロジェクトで Claude Code 環境をゼロから構築する時、
  または既存環境を再構築する時に最初に実行する。他の setup-* コマンドはすべて
  このコマンドの実行後に順番に実行される前提。
allowed-tools: Read, Write, Glob, Bash(mkdir *), Bash(git *), Bash(date *), Bash(ls *)
---

# /bootstrap — Claude Code 環境構築の入口

> 一発でやろうとしない。10 段階 (Phase 0〜9) に分け、各セッションで一つずつ完璧に仕上げる。
> Let's think step by step.

## このコマンドの目的

Claude Code 環境構築の **唯一の手動配置ファイル** として機能する。このコマンドが他のすべての構築コマンドの実行を統括し、進捗を `.steering/_setup-progress.md` に記録することで、`/clear` を挟んでも次のセッションが前回の続きから始められる。

## 設計方針 (v2: Codex CLI / 公式 Skill 連携対応版)

このセットアップは Claude Code 単独前提から拡張され、以下 2 つを統合する:

- **(A) anthropics/skills 公式 plugin marketplace** — pdf/docx/xlsx/pptx (proprietary)、claude-api、mcp-builder、skill-creator、webapp-testing、web-artifacts-builder、frontend-design、theme-factory 等の公式 Skill を Phase 2 で導入。自前 Skill との重複を Phase 4 で回避する。
- **(B) Codex CLI 連携** — Codex を **独立レビュアー / 重い実装委譲先** として使う。役割分担は「Claude = 設計・オーケストレーション」「Codex = セカンドオピニオン・rescue 実装」。Phase 5 で `codex-review` (read-only) と `codex-rescue` (要明示承認・worktree 隔離) を別 Skill として導入し、Phase 7-8 で予算/秘匿ガード付きの `/cross-review` ワークフローを構築する。

これらを使わない構成 (Claude 単独運用) も可能。各 Phase 冒頭に skip 可否を明記する。

## 環境チェックブロック（必須）

このコマンドを実行する前に、以下を順番に確認してください。**一つでも満たしていない場合は中断し、ユーザーに通知してください。**

### Check 1: コンテキスト予算

ユーザーに以下を実行するよう依頼:

```
/context
```

使用率が **30% を超えている場合は中断**し、「`/clear` でセッションをリセットしてから再実行してください」と通知。

### Check 2: モデル

ユーザーに以下を実行するよう依頼:

```
/model
```

現在のモデルを確認。**Opus でない場合は警告**を出し、「設計判断のため `/model opus` への切り替えを強く推奨します」と通知。ユーザーが Sonnet で続けたい意思を示した場合のみ進む。

### Check 3: Plan Mode

Plan Mode に入っているかをユーザーに確認。入っていない場合は「`Shift+Tab` を 2 回押して Plan Mode に入ることを推奨します」と通知。

### Check 4: 作業ディレクトリ

```bash
pwd
git rev-parse --is-inside-work-tree 2>/dev/null
```

git リポジトリの中にいることを確認。いない場合は中断し、「git リポジトリのルートで実行してください」と通知。

### Check 5: 既存の Claude Code 環境

```bash
ls -la .claude/ 2>/dev/null
ls -la docs/ 2>/dev/null
ls CLAUDE.md 2>/dev/null
ls AGENTS.md 2>/dev/null
ls -la .codex/ 2>/dev/null
```

既存の構築物がある場合、ユーザーに「既存の構築物が見つかりました。上書きしますか?それとも追記モードで進みますか?」と確認。

### Check 6: Codex CLI（任意・Phase 5 以降で必要）

```bash
which codex 2>/dev/null && codex --version 2>&1 | head -1
gh --version 2>&1 | head -1
```

**警告止まり** (block しない):

- `codex` 未インストールの場合: 「Phase 5 (`/setup-codex-bridge`) で必要になります。後でインストールしてください: `brew install codex` 等」
- `gh` 未インストールの場合: 「Phase 2 (`/setup-marketplace`) で `gh api` を使います。後でインストールしてください」

Phase 5 / Phase 2 の冒頭で再確認するため、ここでは進行を止めない。

## 実行フロー

### Step 1: プロジェクトの初期調査

`file-finder` サブエージェントが存在しない（このコマンドが最初の実行）ため、ここではメインエージェントが直接以下を実行:

```bash
ls -la
cat README.md 2>/dev/null | head -50
find . -maxdepth 2 -type f -name "*.toml" -o -name "*.json" -o -name "*.yaml" 2>/dev/null
```

プロジェクトの言語、フレームワーク、規模を簡単に把握する。**深く読まない**。

### Step 2: ユーザーへの初期ヒアリング

以下を順番に質問する。一度に複数質問せず、一つずつ。

1. このプロジェクトの目的を 1-2 行で教えてください
2. 主要な技術スタック（言語、フレームワーク）は?
3. 想定するチーム規模は? (個人 / 小規模 / 中規模)
4. 既に存在するドキュメントはありますか?
5. 特に重視したい品質特性は? (パフォーマンス / セキュリティ / 保守性 / etc.)

回答を `.steering/_setup-progress.md` の「プロジェクト概要」セクションに記録する（次のステップで作成）。

### Step 3: ディレクトリ構造の作成

```bash
mkdir -p .claude/commands
mkdir -p .claude/agents
mkdir -p .claude/skills
mkdir -p .claude/hooks
mkdir -p .steering/_template
mkdir -p docs
```

### Step 4: 進捗記録ファイルの作成

`.steering/_setup-progress.md` を以下の内容で作成:

```markdown
# Claude Code 環境構築進捗

> このファイルは構築の進捗を記録する。各 setup-* コマンドが完了するたびに更新される。
> セッションを跨いだ継続のための引き継ぎ情報として機能する。

## プロジェクト概要

- **名称**: [ユーザー回答]
- **目的**: [ユーザー回答]
- **技術スタック**: [ユーザー回答]
- **チーム規模**: [ユーザー回答]
- **重視する品質特性**: [ユーザー回答]
- **構築開始日**: [YYYY-MM-DD]

## 構築進捗

- [ ] **Phase 0: Bootstrap** (このコマンド)
  - 完了日時: -
  - 備考: -
- [ ] **Phase 1: /setup-docs** — 永続ドキュメント
  - 完了日時: -
  - 作成ファイル: -
- [ ] **Phase 2: /setup-marketplace** — anthropics/skills 公式 plugin の導入
  - 完了日時: -
  - 導入 plugin: -
  - ライセンス同意: -
- [ ] **Phase 3: /setup-claude-md** — CLAUDE.md / AGENTS.md / .steering
  - 完了日時: -
  - 作成ファイル: -
- [ ] **Phase 4: /setup-skills** — プロジェクト固有 Skill 群（公式 Skill 重複回避）
  - 完了日時: -
  - 作成 Skill: -
- [ ] **Phase 5: /setup-codex-bridge** — Codex CLI 連携基盤
  - 完了日時: -
  - 作成ファイル: -
- [ ] **Phase 6: /setup-agents** — サブエージェント群
  - 完了日時: -
  - 作成エージェント: -
- [ ] **Phase 7: /setup-commands** — ワークフローコマンド群（`/cross-review` 含む）
  - 完了日時: -
  - 作成コマンド: -
- [ ] **Phase 8: /setup-hooks** — Hook 群（予算/秘匿ガード含む）
  - 完了日時: -
  - 作成 Hook: -
- [ ] **Phase 9: /verify-setup** — 整合性検証（Codex 疎通含む）
  - 完了日時: -
  - 検証結果: -

## 次に実行すべきコマンド

`/setup-docs`

## 各コマンド実行前のチェックリスト

各 setup-* コマンドを実行する前に、以下を必ず確認してください:

1. `/context` で使用率が 30% 以下か
2. 適切なモデルに切り替えてあるか（設計系は Opus、実装系は Sonnet）
3. 前のコマンドが完了し、`/clear` でセッションがリセットされているか
4. このファイル (`.steering/_setup-progress.md`) を Read で読んで進捗を確認したか

## 構築物の相互参照マップ

このセクションは各 setup-* コマンドが完了するたびに更新される。

### Skill → Agent 参照
（/setup-agents 完了時に記入）

### Agent → Command 参照
（/setup-commands 完了時に記入）

### Hook → Command 参照
（/setup-hooks 完了時に記入）
```

### Step 5: 他の構築コマンドファイルの配置

ユーザーに以下を通知:

「このコマンドの後、`/setup-docs` から `/verify-setup` まで 9 つのコマンドを順番に実行します。それぞれのコマンドファイルは別途配布されているので、`.claude/commands/` に配置してください。」

配置すべきファイル一覧:
- `setup-docs.md`
- `setup-marketplace.md` ← Phase 2 (anthropics/skills 導入)
- `setup-claude-md.md`
- `setup-skills.md`
- `setup-codex-bridge.md` ← Phase 5 (Codex CLI 連携)
- `setup-agents.md`
- `setup-commands.md`
- `setup-hooks.md`
- `verify-setup.md`

### Step 6: 構築計画の提示

ユーザーに以下の構築計画を表で提示:

```markdown
## 構築計画

| Phase | コマンド | 推奨モデル | 推奨所要時間 | 主な成果物 |
|---|---|---|---|---|
| 1 | `/setup-docs` | Opus | 1-2h | docs/ 配下 5 ファイル |
| 2 | `/setup-marketplace` | Sonnet | 30m | 公式 plugin install, docs/external-skills.md |
| 3 | `/setup-claude-md` | Opus | 45m | CLAUDE.md, AGENTS.md, docs/agent-shared.md, .steering/ |
| 4 | `/setup-skills` | Sonnet | 1-2h | .claude/skills/ (公式重複回避) |
| 5 | `/setup-codex-bridge` | Sonnet | 45m | .codex/config.toml, codex-review/codex-rescue Skill, .codex/budget.json |
| 6 | `/setup-agents` | Sonnet | 1-1.5h | .claude/agents/ × 10 (cross-reviewer 追加) |
| 7 | `/setup-commands` | Sonnet | 1-1.5h | .claude/commands/ × 9 (`/cross-review` 追加) |
| 8 | `/setup-hooks` | Sonnet | 45m | .claude/hooks/ + settings.json (予算/秘匿ガード含む) |
| 9 | `/verify-setup` | Sonnet | 30m | 検証レポート (Codex 疎通含む) |

合計所要時間: 7-10 時間（1 日強）

**重要**: 各コマンドの間で必ず `/clear` を実行してください。
**Codex 連携を使わない場合**: Phase 2, 5, 6 の `cross-reviewer` 追加部分, 7 の `/cross-review`, 8 の予算/秘匿ガード hook をスキップ可能。Phase 5 のスキップは `/verify-setup` の Codex 疎通チェックも skip させる必要がある (詳細は各コマンド冒頭参照)。
```

### Step 7: Grill Me ステップ（Bootstrap 自体の自己レビュー）

ここまでの作業を振り返り、以下を自己点検:

- [ ] 環境チェックは適切だったか
- [ ] ユーザーへのヒアリングで聞き漏らした重要事項はないか
- [ ] `.steering/_setup-progress.md` に記録した情報は次のコマンドで役立つか
- [ ] ディレクトリ構造に抜けはないか

問題があれば修正し、ユーザーに最終確認を求める。

### Step 8: 進捗記録の更新

`.steering/_setup-progress.md` の Phase 0 を完了マーク:

```markdown
- [x] **Phase 0: Bootstrap** (このコマンド)
  - 完了日時: [YYYY-MM-DD HH:MM]
  - 備考: 環境チェック完了、ディレクトリ構造作成済み
```

### Step 9: 完了通知と次のステップ

ユーザーに以下を通知:

```
Bootstrap 完了です。次のステップ:

1. このセッションを `/clear` でリセット
2. `/model opus` に切り替え（Phase 1 は設計判断のため Opus 必須）
3. `Shift+Tab` を 2 回押して Plan Mode に入る
4. `/setup-docs` を実行

詳細な進捗は `.steering/_setup-progress.md` で確認できます。
```

## 完了条件

- [ ] 環境チェック 5 項目すべてをパスしている
- [ ] ユーザーへの初期ヒアリングが完了している
- [ ] 必要なディレクトリがすべて作成されている
- [ ] `.steering/_setup-progress.md` が作成され、プロジェクト概要が記入されている
- [ ] 構築計画がユーザーに提示されている
- [ ] Phase 0 が完了マークされている

## アンチパターン

- ❌ 環境チェックをスキップする
- ❌ ユーザーへのヒアリングを省略する
- ❌ `.steering/_setup-progress.md` を作らない（次のコマンドが進捗を引き継げない）
- ❌ ディレクトリだけ作って構築計画を提示しない
- ❌ Sonnet で実行する（Opus 推奨）
