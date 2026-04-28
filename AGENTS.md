# ERRE-Sandbox

## このファイルについて

Codex がセッション開始時に自動で読み込む指示書。
詳細は `docs/` 配下の各ドキュメントを参照。
このファイルは **探索の起点** であり、全情報を含むことが目的ではない。

### Codex 資産の入口 (重要)

本リポジトリは Claude Code と Codex の両方をホストする。Codex の実運用入口は
以下に統一する:

- **`AGENTS.md`**: セッション開始時のプロジェクト指示
- **`.codex/config.toml`**: repo-local Codex 設定 (model / hooks / custom agents)
- **`.codex/hooks.json` + `.codex/hooks/`**: Codex lifecycle hook
- **`.codex/agents/`**: Codex custom agent 定義
- **`.agents/skills/`**: Codex 向け Skill

`.claude/commands/`, `.claude/agents/`, `.claude/skills/`, `.claude/hooks/` は
Claude Code 側の canonical 資産であり、Codex では移植元リファレンスとして扱う。
Codex からタスクワークフローを起動する時は `$erre-workflow` を使う。

## プロジェクト概要

- **名称**: ERRE-Sandbox (Autonomous 3D Society Emerging from the Cognitive Habits of Great Thinkers)
- **目的**: 歴史的偉人の認知習慣をローカル LLM エージェントとして 3D 空間に再実装し、「意図的非効率性」と「身体的回帰」による知的創発を観察する研究プラットフォーム
- **主要技術**: Python 3.11 / FastAPI / Godot 4.6 / Ollama (現状) / vLLM (M9+ planned) / sqlite-vec / Pydantic v2
- **チーム規模**: 個人
- **ライセンス**: Apache-2.0 OR MIT (本体)、GPL-3.0 (Blender 連携は別パッケージ)

## セッション開始時の行動規範

タスク開始時、以下を **この順** で実行すること。

1. **ワークフロー選定**: 実装・設計・レビュー・完了処理は `$erre-workflow`
   (`.agents/skills/erre-workflow/SKILL.md`) を入口にする
2. **Skill 参照**: 該当 Skill があれば `.agents/skills/[name]/SKILL.md` を Read してから着手
3. **サブエージェントへの委譲**: ユーザーが delegation / parallel agent work を
   明示した場合のみ `.codex/agents/` の custom agent を使う
   - 複数ファイル横断の探索 → `erre_explorer`
   - 影響範囲調査 → `erre_impact_analyzer`
   - コードレビュー → `erre_reviewer`
   - テスト実行 → `erre_test_runner`
   - セキュリティ確認 → `erre_security_checker`
4. **破壊と構築の判断**: 高難度の設計判断では `$erre-workflow` の reimagine 手順で初回案を破棄し再生成案と比較
5. **Skill の品質検証**: エージェントが Skill の指示通りに動かない、同じ Skill を使った
   タスクで繰り返し問題が起きる、Skill の記述が古くなった疑いがある場合は
   `empirical-prompt-tuning` Skill を起動し、新規 subagent で客観的に検証・改善する。

## 参照ドキュメント

| ファイル | いつ読むか |
|---|---|
| `docs/functional-design.md` | 機能の意図・要件・ユースケースを確認したい時 |
| `docs/architecture.md` | アーキテクチャ・技術スタック・データフローを確認したい時 |
| `docs/repository-structure.md` | ファイル配置・命名規則・依存方向を確認したい時 |
| `docs/development-guidelines.md` | コーディング規約・Git ワークフロー・テスト方針を確認したい時 |
| `docs/glossary.md` | ERRE 固有の用語 (peripatos, chashitsu, 守破離等) の定義を確認したい時 |

## 作業記録ルール

**すべての実装作業は `.steering/` に記録する。省略禁止。**

```
.steering/[YYYYMMDD]-[task-name]/
  ├── requirement.md   (必須) 背景・ゴール・受け入れ条件
  ├── design.md        (必須) アプローチ・変更対象・テスト戦略
  ├── tasklist.md      (必須) チェックボックス形式タスクリスト
  ├── blockers.md      (任意) ブロッカーと対処
  └── decisions.md     (任意) 設計判断と根拠
```

テンプレート: `.steering/_template/` からコピーして使用。

## コンテキスト管理

- **50% ルール**: 使用率 50% 超で次の区切りに `/compact`
- **タスク切り替え時**: `/compact` ではなく `/clear`
- **Plan mode 必須**: 設計判断・新機能・リファクタリングの**最初の段階**は必ず Codex Plan mode
  (`/plan-mode`) + `gpt-5.5` / `xhigh`。Plan 承認前の実装着手は禁止。auto mode でも Plan を飛ばさない
- **Plan 内 reimagine 必須**: 高難度設計（アーキテクチャ / 公開 API / 難しいバグ /
  複数案ありうる設計）では Plan mode 内で `$erre-workflow` の reimagine 手順を発動し、初回案を意図的に
  破棄してゼロから再生成した案と並べて比較する。単発 Plan エージェント 1 発で設計を確定しない
- **Plan → Clear → Execute ハンドオフ**: Plan 承認後、context 使用率が 30% を超えていたら
  `/clear` で切り、次セッションで plan ファイル + `.steering/<task>/design-final.md` を
  Read してから実装に入る（長セッションでの判断品質劣化を回避）

## モデル選択

| タスク | モデル |
|---|---|
| Plan Mode・設計判断 | `gpt-5.5` + `xhigh` |
| 実装・テスト・リファクタ | `gpt-5.5` + `medium/high` |
| 探索・テスト実行 subagent | `gpt-5.4-mini` |
| レビュー・セキュリティ subagent | `gpt-5.5` + `high` |

## 禁止事項

- 既存テストを無断で削除しない
- ドキュメント化されていない設計判断を勝手に変更しない
- `.steering/` への記録を省略しない
- 50% を超えてセッションを続けない
- 曖昧な指示に対して推測で実装しない (質問する)
- GPL 依存を `src/erre_sandbox/` に import しない
- クラウド LLM API を必須依存にしない (予算ゼロ制約)
- `main` ブランチに直接 push しない
- Plan mode 外で設計判断を確定しない（設計 → 実装の境界を Plan 承認で明示化する）
- 高難度設計で reimagine 手順を省略しない（同一エージェントの 1 発案は構造的にバイアスが残る）

## コマンド・エージェント

- Codex workflow: `.agents/skills/erre-workflow/SKILL.md`
- Codex custom agents: `.codex/agents/`
- Codex hooks/config: `.codex/hooks.json`, `.codex/hooks/`, `.codex/config.toml`
- Codex skills: `.agents/skills/`
- Claude Code reference assets: `.claude/` (Codex の実行入口ではない)
