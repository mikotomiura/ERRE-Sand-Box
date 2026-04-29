---
description: >
  プロジェクト固有の Skill 群を .claude/skills/ 配下に構築する。
  各 Skill は SKILL.md と必須の補足ファイル（examples.md, patterns.md など）
  を含む。description は具体的トリガー語を必須とし、Shell Preprocessing
  を活用した動的 Skill を最低 1 つ含める。/setup-claude-md の完了後に実行する。
allowed-tools: Read, Write, Glob, Grep, Bash(mkdir *), Bash(ls *), Task
---

# /setup-skills — Skill 群構築コマンド

> Phase 4 of 9. Let's think step by step.

## 環境チェックブロック

### Check 1: 進捗ファイル

```bash
cat .steering/_setup-progress.md
```

Phase 3 完了を確認。

### Check 2: docs の存在

```bash
ls docs/
ls docs/external-skills.md 2>/dev/null
```

5 つのドキュメントが揃っていることを確認。`docs/external-skills.md` (Phase 2 で生成、skip 時は Phase 3 で空テンプレ生成) も Read して、**公式 Skill が既にカバーする領域** を把握する。Skill はこれらを参照して作成する。

### Check 3: コンテキスト予算

`/context` で 30% 以下を確認。

### Check 4: モデル

`/model` で Sonnet を確認。Skill 作成は Sonnet で十分。

## 実行フロー

### Step 1: 既存 docs の精査と公式 Skill カバレッジ確認

以下のドキュメントを Read で読む（Skill の内容を docs と整合させるため）:

```
docs/architecture.md
docs/development-guidelines.md
docs/repository-structure.md
docs/external-skills.md   ← Phase 2 で導入された公式 Skill 一覧 (空テンプレの場合もある)
```

**重要**: `docs/external-skills.md` の表から **既にカバーされている領域** をリスト化する。例:

- `pdf` 公式 Skill が導入済み → 自前で「PDF 操作 Skill」を作らない
- `webapp-testing` 公式 Skill が導入済み → 自前で「E2E テスト Skill」を作らない
- `skill-creator` 公式 Skill が導入済み → 自前 Skill 作成時の補助役として使う (ただし主導権は本コマンドが持つ)
- `claude-api` 公式 Skill が導入済み → Claude API 実装パターンを自前 Skill に書かない

Phase 2 を skip して external-skills.md が空テンプレの場合: 全領域を自前で作成する前提で進む。

### Step 2: 必要な Skill の特定

ユーザーに以下を順番に質問する。一度に複数質問しない:

1. 主要な言語は何ですか?（Python, TypeScript, Rust など）
2. 採用しているフレームワークは?（FastAPI, Next.js, Tauri など）
3. テストフレームワークは?（pytest, vitest, jest など）
4. 特殊な規約やパターンはありますか?
5. データベースやインフラで使う技術は?
6. CI/CD で使うツールは?

回答を踏まえ、作成する Skill のリストを以下のような形で提案する:

```markdown
## 作成する Skill の提案

### 必須 Skill
1. **test-standards** — テスト設計と実装の基準
2. **[language]-standards** — 言語固有のコーディング規約
3. **error-handling** — エラーハンドリング戦略
4. **git-workflow** — git の運用ルール
5. **implementation-workflow** — 実装タスクの共通骨格
   （調査→設計→実装→テスト→レビューの流れ。
   `/add-feature`, `/fix-bug`, `/refactor` から参照される）
6. **empirical-prompt-tuning** — Skill・コマンドの指示品質を実測評価する手法
   （Grill me の構造的限界を補完。重要 Skill の品質保証に使用。
   Task tool で新規 subagent を dispatch し、両面評価で反復改善する）

### プロジェクト固有 Skill
6. **[framework]-patterns** — フレームワーク固有のパターン
7. **architecture-rules** — アーキテクチャ制約

### 動的 Skill（Shell Preprocessing 活用）
8. **project-status** — 現在のプロジェクト状態を動的に取得

### 公式 Skill でカバー済み (作らない)
- PDF 操作 → 公式 `pdf` Skill (Phase 2 で導入済) を使う
- Excel / Word / PowerPoint → 公式 `xlsx` / `docx` / `pptx`
- E2E (Web) テスト → 公式 `webapp-testing`
- React/Tailwind Artifact → 公式 `web-artifacts-builder`
- Claude API 実装 → 公式 `claude-api`
- MCP server 開発 → 公式 `mcp-builder`
- (Phase 2 を skip した場合、この節は「該当なし」)

合計: 自前 [N] 個 + 公式 [M] 個 = [N+M] 個の Skill が利用可能になる
```

ユーザーに「このリストで進めてよいですか?追加・削除があれば指摘してください」と確認。

### Step 3: Skill を 1 つずつ作成

> **重要**: 必ず 1 つずつ作成し、各 Skill 完成後に **(a) ユーザー承認** + **(b) Grill me ステップ** を実施。
> 各 Skill には **SKILL.md と最低 1 つの補足ファイル** を作成する。

各 Skill の作成プロセス:

#### Phase A: ディレクトリ作成

```bash
mkdir -p .claude/skills/[skill-name]
```

#### Phase B: SKILL.md の作成

以下の構造で作成:

```markdown
---
name: [skill-name]
description: >
  [この Skill の目的を 1-2 行で]
  以下の状況で必須参照: [トリガー状況を具体的に箇条書き]
  [必ず含める要素: 具体的な技術名、動作トリガー語（書く/修正する/レビューする）、
  ファイル命名パターン]
allowed-tools: [必要なツールのリスト]
---

# [Skill のタイトル]

## このスキルの目的

[なぜこの Skill が存在するか、何を達成したいか]

## 適用範囲

### 適用するもの
- [どこに適用するか]

### 適用しないもの
- [明示的に適用外とする範囲]

## 主要なルール

### ルール 1: [具体的なタイトル]

[詳細な説明]

\`\`\`[language]
// ✅ 良い例
[code]
\`\`\`

\`\`\`[language]
// ❌ 悪い例
[code]
\`\`\`

### ルール 2: ...

## チェックリスト

このルールに従っているか確認するためのチェックリスト:

- [ ] チェック項目 1
- [ ] チェック項目 2

## 補足資料

詳細は以下を参照:

- `examples.md` — 具体的な実装例集
- `patterns.md` — よく使うパターン
- `anti-patterns.md` — 避けるべき実装

## 関連する他の Skill

- [skill-name-X] — 何のために参照するか
```

#### Phase C: description の品質チェック（必須）

作成した description が以下を **すべて満たしているか確認**:

- [ ] 具体的な技術名が含まれている（例: pytest, FastAPI, Tauri）
- [ ] 動作トリガー語が含まれている（書く / 修正する / レビューする / デバッグする）
- [ ] ファイル命名パターンが含まれている（例: `test_*.py`, `*.tsx`）
- [ ] 「以下の状況で必須参照:」のような明示的な召喚条件がある
- [ ] 200 文字以上ある（短すぎると Claude が判断材料を持てない）

**1 つでも欠けていれば書き直す。** 曖昧な description は自動召喚されない。

#### Phase D: allowed-tools の設定

用途別に適切な権限を設定:

| 用途 | allowed-tools の例 |
|---|---|
| 参照のみ（規約チェック） | `Read, Grep, Glob` |
| テスト関連 | `Read, Edit, Bash(pytest *)` |
| git 関連 | `Bash(git *), Read` |
| 編集が必要 | `Read, Edit, Write, Glob, Grep` |
| 動的データ取得 | 用途に応じて `Bash(...)` を限定的に |

#### Phase E: 補足ファイルの作成（必須）

**この Skill にとって最も価値が高い補足ファイルを最低 1 つ作成する。**

選択肢:

1. **examples.md** — 具体的なコード例集
   - 良い例 / 悪い例
   - 実プロジェクトから抽出したサンプル

2. **patterns.md** — よく使うパターン集
   - デザインパターン
   - 実装パターン

3. **anti-patterns.md** — 避けるべき実装
   - よくある失敗
   - その理由

4. **decision-tree.md** — 判断フローチャート
   - いつ何をすべきか

5. **checklist.md** — 詳細なチェックリスト
   - レビュー時に使う

Skill の性質に応じて 1-2 個を選んで作成する。3 個以上は作らない（多すぎると保守できない）。

#### Phase F: ユーザー承認

作成した SKILL.md と補足ファイルを表示:

```bash
ls -la .claude/skills/[skill-name]/
cat .claude/skills/[skill-name]/SKILL.md
```

「この Skill で問題ないですか? description のトリガー条件は具体的ですか?」と確認。

#### Phase G: Grill me ステップ

> この Skill を批判的にレビューします:
> - description が抽象的すぎないか?
> - ルールが具体的か? (「適切に」「綺麗に」のような曖昧語を使っていないか)
> - 良い例 / 悪い例が実際に区別可能か?
> - チェックリストが実用的か?
> - 他の Skill との重複はないか?
> - allowed-tools が必要最小限か?

問題があれば修正してから次の Skill へ。

#### Phase H: Empirical 評価（tier 選択付き）

> 全 Skill に適用するが **tier を選択** してコストを抑える。
> - **Full**（Iter 0〜7、2-3 シナリオ、hold-out、タグ監査）: `implementation-workflow` + ユーザーが「特に重要」と指定した Skill
> - **Lite**（1 シナリオ × 2 iter 固定）: 中程度の Skill
> - **Structural-only**（Iter 0 + Grill me 拡張のみ、dispatch なし）: 軽量 Skill、dispatch 不可環境

Grill me（自己レビュー）では排除できない「書き手のバイアス」を、新規 subagent による実行で客観的に検証する。

`.claude/skills/empirical-prompt-tuning/SKILL.md` を Read で参照し、tier に応じたワークフローで評価・改善を実施する。Full の場合はシナリオ diversity rubric（median / edge-low / edge-high / adversarial のうち 3 象限）、hold-out 最低 2 本、`[critical]` タグ比率 20-40% を遵守する。結果をユーザーに提示して承認を得てから次の Skill へ進む。

**`empirical-prompt-tuning` Skill 自身には Phase H を適用しない**（メタ循環）。代わりに `/reimagine` を Skill ファイルに適用する手順（本 Skill「メタ循環対策」節参照）を使う。

#### Phase H+: Codex 第三者検証 (限定的に発動)

Phase H の subagent dispatch (Claude 内部の別エージェント) ではなく、**外部 LLM (Codex CLI)** に評価させるオプション。Claude のバイアスをより独立した視点で補正する。

**発動条件 (具体化、トリガー方式)**:

以下のいずれかに該当する **重要 Skill のみ** Phase H+ を実施する。「使うかどうかコストと相談」ではなく、トリガーが揃ったら自動的に実施する明確な閾値:

| トリガー | 該当例 | 理由 |
|---|---|---|
| `implementation-workflow` 等の **複数コマンドが参照する共通骨格** | `/add-feature`, `/fix-bug`, `/refactor` から呼ばれる Skill | 1 箇所のバグが波及するので独立検証の価値が高い |
| ユーザーが「特に重要」と明示指定した Skill | プロジェクト固有のドメインルール、規制対応 Skill | プロダクション安全性に直結 |
| Phase H (Claude 内 subagent dispatch) で Iter 4-7 まで進んでも **収束しない** Skill | description 改善を繰り返しても改善幅が頭打ち | Claude バイアスが原因の可能性。外部視点で打破 |
| **過去 30 日以内に実問題が発生した** Skill (運用 ↔ セットアップ循環) | 「この Skill 通り作業したのに XXX が起きた」事例あり | 既知バイアスを Codex に検出させる |

**適用前提 (すべて満たす)**:

- Phase 5 (`/setup-codex-bridge`) が完了している (`.codex/config.toml` 存在 + `codex --version` が応答)
- 対象 Skill の SKILL.md と補足ファイルが **公開可能な抜粋にできる** (proprietary plugin 出力 / 機密情報を含まない、`docs/external-skills.md` の「外部 LLM への送信」列で確認)
- `.codex/budget.json` の予算余裕が `per_invocation_max * 2` 以上 (`xhigh` reasoning は通常の 1.5-2 倍消費する)
- ユーザーが追加コスト (Codex API token) を承諾済み

**送信内容の最小化**:

SKILL.md と補足ファイルをそのまま送らず、以下の **公開可能な最小抜粋** に絞る:

1. description (frontmatter) — そのまま
2. 主要なルール / 原則 (1-2 セクション) — そのまま
3. 良い例 / 悪い例 — プロジェクト固有名は仮名化 (`UserService` → `XxxService`)
4. アンチパターン — そのまま

allowed-tools / 補足ファイル全文 / プロジェクト固有のパス参照は **送らない**。Codex には「この Skill は Claude を適切に召喚し、ルールが具体的か?」を判断させる最小情報だけ渡す。

**実施手順**:

1. Skill ファイルから上記 4 要素を抽出して `/tmp/skill-public-excerpt.md` に保存
2. `scripts/secrets-filter.sh` に通す (exit code 2 (検出) なら中止して原因調査)
3. ユーザーに preview を見せて送信承認を得る
4. Codex 呼び出し:
   ```bash
   codex exec --json --sandbox read-only --skip-git-repo-check \
     -m gpt-5.5 -c model_reasoning_effort=xhigh \
     "以下の Skill 抜粋について、Claude が読んで適切に動けるか批判的に評価してください。
     観点 (優先度順):
     1. description の召喚条件 (具体性、トリガー語、ファイル命名パターン)
     2. ルール / 例の具体性 (「適切に」のような曖昧語の有無)
     3. アンチパターンの網羅性
     4. 抜け漏れている観点
     300 語以内、優先度順に。改善 3 点を必ず最後に箇条書きで。
     ---
     $(cat /tmp/skill-public-excerpt.md)"
   ```
5. Claude (Phase H subagent) の評価結果と Codex の評価結果を **並べて比較**:
   - 両者が一致して指摘した問題 → 優先度高、即座に修正
   - 一方しか指摘しない問題 → false positive 可能性を Claude が判定して採用/却下
   - Codex のみが指摘した問題で実装に影響しないもの → 記録だけして却下
6. `.codex/budget.json` の `tokens_used` を更新 (codex-review Skill と同じ atomic update + flock)
7. `/tmp/skill-public-excerpt.md` を削除 (`trap` で確実に)

**Skip する場合**:

トリガー条件に該当しない (大半の Skill) / Phase 5 未実施 / Codex 未認証 / 予算超過 / proprietary 関連 Skill — の場合は Phase H 内部 subagent dispatch のみで完結する (Phase H+ は最初から無いものとして扱う)。

### Step 4: 動的 Skill の作成（必須・少なくとも 1 つ）

通常の Skill とは別に、Shell Preprocessing を活用した **動的 Skill** を最低 1 つ作成する。

#### 例: `project-status` Skill

```markdown
---
name: project-status
description: >
  プロジェクトの現在の状態をリアルタイムで取得する。
  作業を始める前、コンテキストが分からなくなった時、進捗を確認したい時、
  最近の変更を把握したい時に使う。git 状態、最近のコミット、未対応 TODO、
  テスト状況、依存関係の状態を一括で取得する。
context: fork
agent: Explore
allowed-tools: Bash(git *), Bash(grep *), Bash(find *), Bash(wc *), Read
---

# Project Status

このスキルは現在のプロジェクト状態を動的に取得します。

## 現在の git 状態
!`git status --short`

## 最近のコミット (10 件)
!`git log --oneline -10`

## 現在のブランチ
!`git branch --show-current`

## 未対応 TODO の数
!`grep -r "TODO\|FIXME\|HACK" src/ 2>/dev/null | wc -l`

## 変更ファイルの統計
!`git diff --stat HEAD`

## 最近変更されたファイル (24 時間以内)
!`find src/ -type f -mtime -1 2>/dev/null | head -10`

## あなたのタスク

上記の動的データを分析し、以下を報告してください:

1. **現状サマリ** — 1-2 行で
2. **進行中の作業** — どんな変更が進んでいるか
3. **注意すべき点** — 大量の変更、未コミットの変更、TODO の偏りなど
4. **推奨される次のアクション** — 何を優先すべきか

レポートは簡潔に。詳細は必要に応じてユーザーが追加で質問する。
```

これも他の Skill と同じく Phase A〜G を実施。

### Step 4.5: `implementation-workflow` Skill の作成（必須）

この Skill は `/add-feature`, `/fix-bug`, `/refactor` の **3 コマンドすべてから参照される共通骨格** です。
3 コマンドの重複を吸収する DRY の要なので、手を抜かず作ること。

以下の構造で `SKILL.md` を作成:

```markdown
---
name: implementation-workflow
description: >
  コード実装タスクの共通骨格。新機能追加、バグ修正、リファクタリングの
  いずれかを行う時、まずこの Skill を参照してから作業を始める。
  調査 → 設計 → 実装 → テスト → レビューの流れと、各ステップでの
  サブエージェント呼び出し方法を定義する。`/add-feature`, `/fix-bug`,
  `/refactor` コマンドから必ず参照される。
allowed-tools: Read, Edit, Glob, Grep, Task
---

# Implementation Workflow

## このスキルの目的

実装タスクに共通する骨格を一箇所に集約し、各ワークフローコマンドが
特殊制約だけに集中できるようにする。

## 共通ステップ（いずれの実装タスクでも適用）

### Step A: プロジェクト理解
以下を Read:
- `CLAUDE.md`
- `docs/architecture.md`
- `docs/development-guidelines.md`
- `docs/repository-structure.md`
- `.steering/[現在のタスク]/requirement.md`

### Step B: 既存パターンの調査
`file-finder` サブエージェントを起動:
> Task: file-finder で「[対象] に類似する既存実装」を検索。

`impact-analyzer` を起動:
> Task: impact-analyzer で影響範囲を分析。

### Step C: 設計記録
`.steering/[現在のタスク]/design.md` に記入:
- 実装アプローチ / 修正方針
- 変更対象ファイル
- 既存パターンとの整合性
- テスト戦略

ユーザーに設計の承認を求める。承認なしに Step D へ進まない。

### Step D: tasklist の作成
`.steering/[現在のタスク]/tasklist.md` にチェックボックス形式で列挙。
各タスクは 30 分以内で完了できる粒度に。

### Step E: 実装
tasklist の各項目を順番に実装。完了ごとにチェック更新。
関連 Skill（test-standards, [language]-standards など）を適宜参照。
`/context` 50% 超で `/smart-compact`。

### Step F: テストと検証
`test-runner` を起動。失敗があれば `test-analyzer` で原因分析し、
通るまで繰り返す。

### Step G: コードレビュー
`code-reviewer` を起動。HIGH は必ず対応、MEDIUM はユーザー判断。

### Step H: セキュリティチェック（該当時のみ）
外部入力・認証・認可を扱う場合のみ `security-checker` を起動。
CRITICAL/HIGH は必ず対応。

### Step I: ドキュメント更新
必要に応じて `docs/functional-design.md`, `docs/glossary.md`,
`docs/architecture.md` を更新。

## 各コマンドによるオーバーライド

このスキルの Step A〜I は共通骨格であり、`/add-feature`, `/fix-bug`,
`/refactor` はそれぞれ以下を **追加 or 上書き** する:

| コマンド | 追加する制約 / 順序変更 |
|---|---|
| `/add-feature` | 特になし（Step A〜I をそのまま実行） |
| `/fix-bug` | Step E の前に「回帰テストを先に追加」を挿入（TDD 順序） |
| `/refactor` | Step B の前に「現状テスト全部グリーン」を確認。実装は小さな単位で Step F と交互に |

## チェックリスト

- [ ] Step A でドキュメント 5 種を読んだか
- [ ] Step C でユーザー承認を得たか
- [ ] Step F で全テスト通過を確認したか
- [ ] Step G で HIGH 指摘に全対応したか

## 関連する他の Skill

- `test-standards` — Step F/tasklist のテスト部分で参照
- `[language]-standards` — Step E で参照
- `git-workflow` — コミット段階で参照
```

補足ファイルは `anti-patterns.md`（「骨格を飛ばして実装に入る」等の失敗集）を推奨。

### Step 4.6: `empirical-prompt-tuning` Skill の作成（必須）

この Skill は **他の Skill やコマンドの指示品質を客観的に検証する手法** を定義する。Phase G（Grill me）が自己レビューであるのに対し、本 Skill はバイアスを排した新規 subagent に実際に動かしてもらう実証的評価を提供する。

セットアップ時の品質ゲート（Phase H）だけでなく、日常タスクの中で既存 Skill の有効性を判断し、必要に応じて更新するランタイム品質保証としても使用する。

作成手順:

1. `.claude/skills/empirical-prompt-tuning/` ディレクトリを作成
2. プロジェクトルートの `skill-empirical-prompt-tuning.md` を `.claude/skills/empirical-prompt-tuning/SKILL.md` としてコピー
3. 補足ファイルとして `examples.md`（実際の評価イテレーション記録の具体例）を作成
4. Phase A〜G を他の Skill と同様に実施（ただし Phase H は適用しない — メタ的な循環を避ける）

### Step 5: 全 Skill の整合性レビュー

すべての Skill を作成し終えたら、全体を見渡して以下を確認:

```bash
ls -la .claude/skills/
find .claude/skills -name "SKILL.md" -exec wc -l {} \;
```

整合性チェック:

- [ ] 重複する Skill はないか?
- [ ] 互いに矛盾するルールはないか?
- [ ] 命名規則が統一されているか? (kebab-case)
- [ ] description の品質が全体的に均一か?

問題があれば修正。

### Step 6: 進捗ファイルの更新

`.steering/_setup-progress.md` の Phase 4 を完了マーク:

```markdown
- [x] **Phase 4: /setup-skills** — プロジェクト固有 Skill 群（公式 Skill 重複回避済み）
  - 完了日時: [YYYY-MM-DD HH:MM]
  - 作成 Skill (自前):
    - test-standards (SKILL.md, examples.md)
    - python-standards (SKILL.md, patterns.md, anti-patterns.md)
    - error-handling (SKILL.md, examples.md)
    - git-workflow (SKILL.md, checklist.md)
    - project-status (SKILL.md, 動的型)
    ...
  - 動的 Skill 数: [N]
  - 公式 Skill 重複回避: docs/external-skills.md 参照済み
  - Phase H で Codex 第三者検証を実施: 重要 Skill [N] 個 / 全 [M] 個 (Phase 5 完了時のみ)
```

「構築物の相互参照マップ」セクションに Skill の一覧を記録:

```markdown
### Skill リスト
自前:
- test-standards
- python-standards
- error-handling
- git-workflow
- project-status (動的)

公式 (anthropics/skills 由来):
- (docs/external-skills.md を参照)
```

### Step 7: 完了通知

```
Phase 4 完了です。

作成した自前 Skill: [N] 個
- 静的 Skill: [N] 個
- 動的 Skill: [N] 個（Shell Preprocessing 使用）

公式 Skill (Phase 2 で導入済): [M] 個
合計利用可能: [N+M] 個

各 Skill のディレクトリ:
.claude/skills/
├── test-standards/
│   ├── SKILL.md
│   └── examples.md
├── ...

次のステップ:
1. `/clear` でリセット
2. `/model sonnet` を維持
3. `/setup-codex-bridge` を実行 (Codex CLI 連携を導入する場合)
   または skip して `/setup-agents` を実行 (Codex 不使用の場合)
```

## 完了条件

- [ ] 計画した数の Skill すべてが作成されている
- [ ] 公式 Skill (`docs/external-skills.md`) と機能重複している自前 Skill が無い
- [ ] 各 SKILL.md の description が 5 つの品質基準を満たしている
- [ ] 各 Skill に最低 1 つの補足ファイルがある
- [ ] 動的 Skill が最低 1 つ作成されている
- [ ] 各 Skill で Grill me ステップ実施済み
- [ ] `empirical-prompt-tuning` Skill が作成されている
- [ ] 重要 Skill（`implementation-workflow` 等）で Phase H（Empirical 評価）実施済み
- [ ] 全体整合性レビュー実施済み
- [ ] Phase 4 が完了マーク済み

## アンチパターン

- ❌ description を「○○のベストプラクティス」と抽象的に書く
- ❌ 補足ファイルを作らない
- ❌ 動的 Skill を作らない
- ❌ 1 つの Skill に複数の責務を詰め込む
- ❌ 補足ファイルを 4 つ以上作る（保守できない）
- ❌ allowed-tools を省略する
- ❌ 複数 Skill を一気に作成する
- ❌ Grill me を省略する
- ❌ 重要 Skill の Empirical 評価（Phase H）を省略する（Grill me だけではバイアスが残る）
- ❌ Empirical 評価で自己再読を代用する（新規 subagent を必ず dispatch する）
- ❌ Empirical 評価を全 Skill に適用する（コスト爆発。重要 Skill に限定する）
