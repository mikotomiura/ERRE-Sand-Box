---
description: >
  Claude Code 環境構築の整合性を検証する。docs, CLAUDE.md / AGENTS.md / docs/agent-shared.md,
  .steering, skills, agents, commands, hooks のすべてが正しく構築され、相互参照が破綻して
  いないかを確認する。Phase 5 (Codex 連携) を実施した場合は .codex/ / scripts/secrets-filter.sh /
  codex-review・codex-rescue Skill / cross-reviewer エージェント / /cross-review コマンド /
  Codex ガード hook 群 / Codex 疎通テストを追加検証する。さらに AGENTS↔CLAUDE 同期検証と
  ライセンス整合検証 (proprietary plugin 経路の漏れ確認) を行い、検証レポートを生成する。
  /setup-hooks の完了後、または既存環境の健全性を確認したい時に実行する。
allowed-tools: Read, Glob, Grep, Bash(ls *), Bash(cat *), Bash(wc *), Bash(find *), Bash(grep *), Bash(jq *), Bash(codex *)
---

# /verify-setup — 環境構築の整合性検証

> Phase 9 of 9. Let's think step by step.
> このコマンドは構築物の最終チェックと健全性の確認を行う。
> 月次メンテナンスでも繰り返し使える。

## 環境チェックブロック

### Check 1: 進捗ファイル

```bash
cat .steering/_setup-progress.md
```

Phase 0-8 がすべて完了マークされている (または `[~] skipped` で意図的に skip されている) ことを確認。未完了のフェーズがあれば、そのフェーズに戻るよう通知。

skip 可能な Phase の組み合わせ:

- Phase 2 (`/setup-marketplace`) skip: 公式 plugin 不使用。docs/external-skills.md は Phase 3 で空テンプレ生成済の前提
- Phase 5 (`/setup-codex-bridge`) skip: Codex 連携不使用。AGENTS.md / .codex/ / scripts/secrets-filter.sh / codex-* Skill / cross-reviewer / /cross-review / Codex ガード hook の検証はすべて skip

両方 skip した場合は Claude Code 単独運用構成として検証する (検証項目は減るが破綻はしない)。

## 実行フロー

### Step 1: ファイル存在チェック

以下のすべてが存在することを確認:

```bash
# Phase 1: 永続ドキュメント (5)
ls docs/functional-design.md
ls docs/architecture.md
ls docs/repository-structure.md
ls docs/development-guidelines.md
ls docs/glossary.md

# Phase 2: 公式 Skill metadata (Phase 2 完了 OR skip 時の空テンプレ — どちらでも存在必須)
ls docs/external-skills.md

# Phase 3: CLAUDE.md / AGENTS.md / docs/agent-shared.md
ls CLAUDE.md
ls docs/agent-shared.md
ls AGENTS.md 2>/dev/null && echo "[ok] AGENTS.md present (Phase 5 enabled?)"

# .steering
ls .steering/README.md
ls .steering/_setup-progress.md
ls .steering/_template/requirement.md
ls .steering/_template/design.md
ls .steering/_template/tasklist.md
ls .steering/_template/blockers.md
ls .steering/_template/decisions.md

# .claude
ls .claude/skills/
ls .claude/agents/
ls .claude/commands/
ls .claude/hooks/
ls .claude/settings.json

# Phase 5 完了時のみ: Codex 連携基盤
if [ -f .codex/config.toml ]; then
  ls .codex/config.toml
  ls .codex/budget.json
  ls scripts/secrets-filter.sh
  ls scripts/run-codex-consult.sh
  ls scripts/run-codex-review.sh
  ls .claude/skills/codex-consult/SKILL.md
  ls .claude/skills/codex-review/SKILL.md
  ls .claude/skills/codex-rescue/SKILL.md
  ls .claude/agents/cross-reviewer.md
  ls .claude/commands/cross-review.md
  ls .claude/hooks/codex-budget-guard.sh
  ls .claude/hooks/secrets-pre-filter.sh
  ls .claude/hooks/token-report-stop.sh
fi
```

不足しているファイルがあればリストアップ。Phase 5 が skip されているのに codex-* ファイルが残っていないか、その逆もチェック (取り残し検出)。

### Step 2: CLAUDE.md / AGENTS.md / docs/agent-shared.md の品質チェック

```bash
wc -l CLAUDE.md docs/agent-shared.md
[ -f AGENTS.md ] && wc -l AGENTS.md
```

#### CLAUDE.md (Claude Code 固有)

- [ ] 行数が 150 以下か
- [ ] `@docs/agent-shared.md` を 1 回参照しているか (`grep -c '@docs/agent-shared.md' CLAUDE.md` で 1 以上)
- [ ] `.steering/` の運用ルール / Plan mode / モデル選択ルール / コンテキスト管理ルールが含まれているか
- [ ] sandbox / approval / Codex 固有事項が **混入していない** か (それは AGENTS.md の責務)

#### AGENTS.md (Codex CLI 固有、Phase 5 完了時のみ)

- [ ] 行数が 80 以下か
- [ ] `@docs/agent-shared.md` を 1 回参照しているか
- [ ] sandbox / approval / model / rescue モードの記述があるか
- [ ] Plan mode / .steering ワークフロー / Skill 召喚規範が **混入していない** か (それは CLAUDE.md の責務)

#### docs/agent-shared.md (両 LLM 共通)

- [ ] 行数が 200 以下か
- [ ] プロジェクト概要 / アーキテクチャ要約 / 主要ディレクトリ / 規約サマリ / テスト方針 / git ワークフロー基本が記載されているか
- [ ] `@docs/external-skills.md` を 1 回参照しているか (公式 Skill リンク)
- [ ] Claude/Codex 固有事項が **混入していない** か (それは CLAUDE.md / AGENTS.md の責務)

3 ファイルを Read で読んで品質チェック。

### Step 2.5: AGENTS↔CLAUDE 同期検証 (Phase 5 完了時のみ)

> **Skip 条件**: AGENTS.md が存在しない (Phase 5 skip) 場合はこのステップ全体を skip。

CLAUDE.md と AGENTS.md の **責務分離が崩れていないか** を機械的にチェック。ただし **単純な keyword 出現で warning を出すと false positive 多発する** (CLAUDE.md が Codex 連携を説明する文脈で "sandbox" に触れるのは正当)。以下の方針で精度を上げる:

1. **ignore marker** で正当な参照箇所を明示できる: コメント `<!-- cross-ref-ok: <理由> -->` を該当行/段落の直前に置けば、その範囲は keyword leakage 検出から除外
2. **閾値方式**: 「絶対禁止」ではなく「過剰出現」を検出 (ベースライン 2 程度を許容)

```bash
# 両ファイルから @docs/agent-shared.md 参照を確認 (ベースライン)
CLAUDE_REF=$(grep -c '@docs/agent-shared.md' CLAUDE.md || echo 0)
AGENTS_REF=$(grep -c '@docs/agent-shared.md' AGENTS.md || echo 0)
echo "CLAUDE.md refs agent-shared.md: $CLAUDE_REF (expect ≥1)"
echo "AGENTS.md refs agent-shared.md: $AGENTS_REF (expect ≥1)"

# ignore-marker 適用後の content を取得するヘルパー
strip_ignore_blocks() {
  # <!-- cross-ref-ok ... --> ... <!-- /cross-ref-ok --> の範囲を空白に置換
  awk '
    /<!-- cross-ref-ok/ { skip=1; next }
    /<!-- \/cross-ref-ok -->/ { skip=0; next }
    !skip { print }
  ' "$1"
}

# 共通事項の重複検出
COMMON_KEYWORDS=("プロジェクト概要" "アーキテクチャ要約" "主要ディレクトリ" "テスト方針" "git ワークフロー")
for kw in "${COMMON_KEYWORDS[@]}"; do
  CL_HIT=$(strip_ignore_blocks CLAUDE.md | grep -c "$kw" || echo 0)
  AG_HIT=$(strip_ignore_blocks AGENTS.md | grep -c "$kw" || echo 0)
  if [ "$CL_HIT" -gt 0 ] || [ "$AG_HIT" -gt 0 ]; then
    echo "WARN: '$kw' appears in CLAUDE.md ($CL_HIT) or AGENTS.md ($AG_HIT) — should be in agent-shared.md only"
  fi
done

# 過剰出現ベースの leakage 検出 (絶対禁止ではなく閾値方式)
CODEX_LEAKS_TO_CLAUDE=$(strip_ignore_blocks CLAUDE.md | grep -cE "sandbox|approval|gpt-5|codex exec" || echo 0)
if [ "$CODEX_LEAKS_TO_CLAUDE" -gt 5 ]; then
  echo "WARN: CLAUDE.md contains $CODEX_LEAKS_TO_CLAUDE Codex-specific keywords (threshold 5; cross-ref-ok marker で正当な参照を除外可)"
fi

CLAUDE_LEAKS_TO_AGENTS=$(strip_ignore_blocks AGENTS.md | grep -cE "Plan mode|.steering/|/start-task|/add-feature" || echo 0)
if [ "$CLAUDE_LEAKS_TO_AGENTS" -gt 3 ]; then
  echo "WARN: AGENTS.md contains $CLAUDE_LEAKS_TO_AGENTS Claude-specific keywords (threshold 3)"
fi
```

> **ignore marker の使い方** (Phase 3 の CLAUDE.md / AGENTS.md 生成時に活用):
> ```markdown
> <!-- cross-ref-ok: Codex への委譲を説明する正当な参照 -->
> 6. **Codex への委譲 (任意)**: 自分の出力に独立レビューが欲しい時は ...
> <!-- /cross-ref-ok -->
> ```

問題があればレポートに記録 (FAIL ではなく WARN 扱い)。

### Step 2.6: ライセンス整合検証 (常時)

`docs/external-skills.md` を **単一の真実源** として、Phase 5 wrapper / Phase 8 hook がカバーする proprietary 拡張子セットがそこから派生しているか検証する。**hardcode された拡張子リストは陳腐化するので、ファイル間の集合差分で比較する**。

```bash
# Step 1: external-skills.md から「外部 LLM への送信」列が「禁止」の行を抽出して拡張子セットを作る
# (proprietary plugin の Skill 名に対応する拡張子をマップ)
declare -A SKILL_TO_EXT=(
  [pdf]=pdf [docx]=docx [xlsx]=xlsx [pptx]=pptx
  # 将来 anthropics/skills が追加した proprietary Skill はここに追記
)

# external-skills.md から「禁止」を含む行に対応する Skill 名を抽出
PROHIBITED_SKILLS=$(grep -E '禁止' docs/external-skills.md | grep -oE '\| [a-z-]+ \|' | tr -d '| ' | sort -u)
echo "Proprietary Skills per external-skills.md: $PROHIBITED_SKILLS"

# 期待される拡張子セット (集合 A)
EXPECTED_EXTS=()
for skill in $PROHIBITED_SKILLS; do
  if [ -n "${SKILL_TO_EXT[$skill]:-}" ]; then
    EXPECTED_EXTS+=("${SKILL_TO_EXT[$skill]}")
  else
    echo "WARN: unknown proprietary skill '$skill' — SKILL_TO_EXT mapping needs update"
  fi
done

# Step 2: Phase 5 wrapper / Phase 8 hook の実装で実際にカバーされている拡張子セット (集合 B / C)
if [ -f scripts/secrets-filter.sh ]; then
  COVERED_BY_FILTER=$(grep -oE '\\\.(pdf|docx|xlsx|pptx)' scripts/secrets-filter.sh | sed 's|\\.||' | sort -u)
fi
if [ -f .claude/hooks/secrets-pre-filter.sh ]; then
  COVERED_BY_HOOK=$(grep -oE '\\\.(pdf|docx|xlsx|pptx)' .claude/hooks/secrets-pre-filter.sh | sed 's|\\.||' | sort -u)
fi

# Step 3: 集合差分で漏れ検出 (A - B, A - C)
for ext in "${EXPECTED_EXTS[@]}"; do
  if [ -n "${COVERED_BY_FILTER:-}" ] && ! echo "$COVERED_BY_FILTER" | grep -q "^$ext$"; then
    echo "FAIL: scripts/secrets-filter.sh missing coverage for .$ext (per external-skills.md)"
  fi
  if [ -n "${COVERED_BY_HOOK:-}" ] && ! echo "$COVERED_BY_HOOK" | grep -q "^$ext$"; then
    echo "FAIL: .claude/hooks/secrets-pre-filter.sh missing coverage for .$ext (per external-skills.md)"
  fi
done

# Step 4: 逆方向 — wrapper / hook がカバーしているが external-skills.md に列挙されていない (over-coverage は OK)
# 報告のみ、FAIL にしない

# Step 5: proprietary plugin 同意ログの存在
if grep -q "document-skills" docs/external-skills.md; then
  if ! grep -q "ライセンス同意" .steering/_setup-progress.md; then
    echo "FAIL: document-skills installed but no license consent log in _setup-progress.md"
  fi
fi
```

> **`SKILL_TO_EXT` マッピングの保守**: 将来 anthropics/skills が新たな proprietary Skill (例: `audio` / `video` 等) を追加した場合、この連想配列に追記が必要。`/setup-marketplace` でも対応する更新が必要なので、両方を同時に更新する保守手順を [Phase 2 アンチパターン] に記載する。
>
> **設計原則**: `docs/external-skills.md` の表が **唯一の真実源**。wrapper / hook の実装はそこから派生した防衛線として、verify-setup が集合差分で同期を保証する。

### Step 2.7: Codex 疎通検証 (Phase 5 完了時のみ)

> **Skip 条件**: `.codex/config.toml` が存在しない場合はこのステップ全体を skip。
>
> **失敗時の扱い (重要、明文化)**: 本ステップが FAIL したとしても **verify-setup 全体は exit 0 で続行する**。FAIL は検証レポートに記録され、最終サマリで強調表示される。`codex exec` が失敗しても他の検証 (ファイル / 同期 / ライセンス) は意味があるので止めない。CI で run する場合は最終レポートを parse して exit code を導出する。

```bash
# codex CLI 疎通
which codex && codex --version

# 簡易疎通テスト (低 token コスト) — set +e で失敗しても続行
set +e
codex exec --sandbox read-only --skip-git-repo-check \
  -m gpt-5.5 -c model_reasoning_effort=low \
  "200 字以内で「Hello」と日本語で挨拶してください" \
  > /tmp/verify-codex-test.log 2>&1
CODEX_RESULT=$?
set -e
```

結果のクラス分け (Phase 5 と同じ 3 状態判定):

| 状態 | 判定基準 | 検証レポート | 総合判定への影響 |
|---|---|---|---|
| ✅ PASS | exit 0 + 「Hello」/「こんにちは」を含む応答 | "Codex 疎通: ✅ verified" | 影響なし |
| ⚠️ AUTH_PENDING | exit 非 0 + ログに 401 / "Please login" / "expired" を含む | "Codex 疎通: ⚠️ AUTH_PENDING — Codex 連携は未使用状態。次回使用前に `codex login` を実行してください" | WARNINGS (ISSUES に昇格しない) |
| ❌ FAIL | exit 非 0 + 上記以外 (network / model / sandbox) | "Codex 疎通: ❌ FAIL — 詳細は /tmp/verify-codex-test.log。`/cross-review` 等の Codex 連携機能が動かない状態" | ISSUES (修正必須) |

`AUTH_PENDING` は environment 構築の失敗ではなく **再認証が必要な中間状態**。最終サマリでは「**Codex 連携は現状未使用可能。本日中に `codex login` を実行することを強く推奨**」のように、見落とされにくい強調表示にする。

予算ファイルの正常性も検証:

```bash
set +e
jq -e '.daily_token_budget and .per_invocation_max and .today.date' .codex/budget.json > /dev/null
BUDGET_OK=$?
set -e
if [ "$BUDGET_OK" -ne 0 ]; then
  echo "FAIL: .codex/budget.json corrupted or missing required keys"
fi
```

問題があればレポートに記録 (ステップ自体は exit 0)。

### Step 3: docs の整合性チェック

各 docs を Read で読み、以下を確認:

#### functional-design.md と architecture.md
- 機能と技術スタックの対応が取れているか
- 機能設計に登場するコンポーネントが technical 設計に存在するか

#### architecture.md と repository-structure.md
- アーキテクチャのレイヤーが実際のディレクトリ構造に反映されているか
- 想定するコンポーネントが repository-structure に記載されているか

#### development-guidelines.md と repository-structure.md
- テスト方針とテストディレクトリ構造が整合しているか
- 命名規則が両方で同じか

#### glossary.md と他の docs
- 重要な用語が glossary に登録されているか
- 同じ概念が異なる名前で呼ばれていないか

矛盾を発見したらリストアップ。

### Step 4: Skill の品質チェック

```bash
find .claude/skills -name "SKILL.md"
```

各 SKILL.md を Read で読み、以下を確認:

- [ ] frontmatter に name, description, allowed-tools がある
- [ ] description に具体的な技術名が含まれている
- [ ] description に動作トリガー語が含まれている
- [ ] description に「以下の状況で必須参照:」がある
- [ ] 補足ファイル（examples.md, patterns.md など）が存在する
- [ ] 動的 Skill が最低 1 つあるか（`!` 構文を使うもの）
- [ ] `empirical-prompt-tuning` Skill が存在するか
- [ ] `implementation-workflow` に Empirical 評価が実施されたか（最終イテレーションで不明瞭点 0 件）
- [ ] 重要 Skill の tier 分類が明示されているか（Full / Lite / Structural-only）
- [ ] `.steering/deferred-evaluations.md` に未評価項目が溜まっていないか（存在する場合は処理する）
- [ ] **四半期定期チェック**: 前回の Empirical 評価から 3 ヶ月以上経過している Skill について、`/reimagine` を Skill ファイルに適用（description ⇔ 本体の乖離検出）
- [ ] **公式 Skill 重複回避**: `docs/external-skills.md` の表が既にカバーする領域 (PDF / Office / E2E / Claude API / Skill 自動生成等) を自前 Skill が再実装していないか
- [ ] **Phase 5 完了時のみ**: `codex-consult` / `codex-review` / `codex-rescue` の 3 Skill が存在し、それぞれの責務分離 (設計相談 / diff レビュー / rescue 実装) が SKILL.md で明確か
- [ ] **Phase 5 完了時のみ**: `codex-consult` の入力が「公開可能な最小抜粋」に限定するルールが SKILL.md に記載されているか
- [ ] **Phase 5 完了時のみ**: `codex-review` 内部で予算チェック / proprietary・機密チェック / secrets-filter / atomic budget update (flock) が実装されているか
- [ ] **Phase 5 完了時のみ**: 各 Skill が wrapper 経由 (`scripts/run-codex-*.sh`) を使い、`Bash(codex *)` 直接許可になっていないか

問題のある Skill をリストアップ。

### Step 5: Agent の品質チェック

```bash
find .claude/agents -name "*.md"
```

各エージェント定義を Read で読み、以下を確認:

- [ ] 9 つの基本エージェントすべて存在するか:
  - file-finder
  - dependency-checker
  - impact-analyzer
  - code-reviewer
  - test-analyzer
  - security-checker
  - test-runner
  - build-executor
  - log-analyzer
- [ ] **Phase 5 完了時のみ**: cross-reviewer が存在し、`Bash` 権限が `scripts/run-codex-review.sh` 等の wrapper 限定になっているか (`Bash(codex *)` のように任意 codex コマンドを許可していないか)
- [ ] **Phase 5 skip 時**: cross-reviewer が **存在しない** か (取り残しなし)
- [ ] 各エージェントに name, description, tools, model がある
- [ ] レポート形式が定義されているか
- [ ] レポートの行数制限が設けられているか
- [ ] 参照すべき Skill が明示されているか
- [ ] モデル選択が用途に合っているか
  - 実行系 (test-runner, build-executor): Haiku
  - 情報収集系: Sonnet
  - レビュー系 (code-reviewer, security-checker): Opus
  - cross-reviewer (Phase 5 完了時): Sonnet (オーケストレータなので軽め)

問題のあるエージェントをリストアップ。

### Step 6: Command の品質チェック

```bash
find .claude/commands -name "*.md"
```

各コマンド定義を Read で読み、以下を確認:

- [ ] 8 つの基本コマンドすべて存在するか:
  - /start-task
  - /add-feature
  - /fix-bug
  - /refactor
  - /reimagine
  - /review-changes
  - /smart-compact
  - /finish-task
- [ ] **Phase 5 完了時のみ**: /cross-review が存在し、cross-reviewer エージェントを呼び出しているか
- [ ] **Phase 5 skip 時**: /cross-review が **存在しない** か (取り残しなし)
- [ ] 各コマンドが単一責任を満たしているか
- [ ] 実行フローが具体的か
- [ ] Skill と Agent を適切に呼び出しているか
- [ ] 制約 / アンチパターンが記載されているか
- [ ] `/add-feature`, `/fix-bug`, `/refactor` に Empirical 評価が実施されたか（Skill 参照型のコマンドは指示の曖昧さが入りやすい）
- [ ] /cross-review (存在時) に行数閾値分岐 / proprietary・機密チェック / 予算チェックの 3 段が実装されているか

### Step 7: Hook の動作チェック

```bash
ls -la .claude/hooks/
cat .claude/settings.json
```

以下を確認（3 層構成: Preflight / Guard / Report）:

#### ファイル存在と権限
- [ ] `.claude/hooks/session-start.sh` が実行可能か (`-x` 権限)
- [ ] `.claude/hooks/preflight.sh` が存在し実行権限があるか
- [ ] `.claude/hooks/pre-edit-steering.sh` が存在し実行権限があるか
- [ ] `.claude/hooks/post-fmt.sh` が存在し実行権限があるか
- [ ] `.claude/hooks/stop-check.sh` が存在し実行権限があるか
- [ ] `.claude/hooks/pre-edit-banned.sh` が存在する場合、実行権限があるか

#### settings.json の構造
- [ ] JSON 構文が正しいか
- [ ] SessionStart, UserPromptSubmit, PreToolUse, Stop, PostToolUse の 5 種類の Hook があるか
- [ ] **全 hook が `"type": "command"` に統一されているか（`"type": "prompt"` が混在していないこと）**
- [ ] 各 command が `bash .claude/hooks/*.sh` の形式で記述されているか

#### Preflight 層（UserPromptSubmit）
- [ ] `preflight.sh` が動的チェックで実装されているか（固定文言 echo ではないこと）
- [ ] `preflight.sh` が常に `exit 0` で終了し、BLOCK しないか
- [ ] 出力が `[preflight] task: ...` / `[preflight] git: ...` の形式か

#### Guard 層（PreToolUse）
- [ ] `pre-edit-steering.sh` が実装ファイルのみを対象とし、docs/ やテストファイルをブロックしないか（偽陽性チェック）
- [ ] パス時に `[guard] PASS: steering (...)` を出力するか（**無言通過していないこと**）
- [ ] 違反時に `[guard] BLOCKED: ...` を出力するか
- [ ] `pre-edit-banned.sh` が存在する場合、パス時に `[guard] PASS: banned patterns (...)` を出すか

#### Report 層（PostToolUse / Stop）
- [ ] `post-fmt.sh` が `--check` で先判定し、変更時のみ `[fmt] ... applied` を出すか（ノイズ削減チェック）
- [ ] `post-fmt.sh` の実コマンド出力が `>/dev/null 2>&1` で抑制されているか
- [ ] `stop-check.sh` の clippy / tsc 等の出力が `>/dev/null 2>&1` で抑制されているか
- [ ] `stop-check.sh` は問題時のみ `[stop] WARN: ...` を 1 行出すか

#### 出力プレフィックス統一
- [ ] 全 hook の出力が `[preflight]` / `[guard]` / `[fmt]` / `[stop]` のいずれかのプレフィックスで始まっているか
- [ ] Hook のコマンドが存在するツール（cargo, ruff, npx 等）を参照しているか

#### 第 4 層: Codex ガード (Phase 5 完了時のみ)

> **Skip 条件**: `.codex/budget.json` が存在しない場合 (Phase 5 skip) はこのサブセクション全体を skip。

- [ ] `.claude/hooks/codex-budget-guard.sh` が存在し実行権限があるか
- [ ] `.claude/hooks/secrets-pre-filter.sh` が存在し実行権限があるか
- [ ] `.claude/hooks/token-report-stop.sh` が存在し実行権限があるか
- [ ] `codex-budget-guard.sh` と `secrets-pre-filter.sh` が冒頭で `case "$COMMAND" in *codex*) ;; *) exit 0 ;;` の高速早期 exit を持つか (Bash 全発火対策)
- [ ] `secrets-pre-filter.sh` の DENY パターンが `docs/external-skills.md` の proprietary 拡張子と整合 (Step 2.6 で別途検証済)
- [ ] `token-report-stop.sh` が冪等性キー (`$TODAY:tokens=$USED:invs=$INVS`) で重複記録を防いでいるか
- [ ] settings.json に Bash matcher の PreToolUse ブロックが登録され、`codex-budget-guard.sh` と `secrets-pre-filter.sh` が呼ばれているか
- [ ] settings.json の Stop hook に `token-report-stop.sh` が追加されているか
- [ ] **Phase 5 skip 時**: settings.json から Codex 関連ブロックが削除されているか (`jq` で確認)

```bash
# Phase 5 skip 時の包括的な取り残し検出
if [ ! -f .codex/config.toml ]; then
  echo "## Phase 5 skip 状態の取り残しチェック"

  # settings.json に Codex hook 登録残存
  if grep -q "codex-budget-guard\|token-report-stop\|secrets-pre-filter" .claude/settings.json 2>/dev/null; then
    echo "FAIL: Codex hooks registered in settings.json but Phase 5 was skipped"
  fi

  # ファイル / ディレクトリ取り残し
  for path in \
    .codex/config.toml \
    .codex/budget.json \
    scripts/secrets-filter.sh \
    scripts/run-codex-consult.sh \
    scripts/run-codex-review.sh \
    .claude/skills/codex-consult \
    .claude/skills/codex-review \
    .claude/skills/codex-rescue \
    .claude/agents/cross-reviewer.md \
    .claude/commands/cross-review.md \
    .claude/hooks/codex-budget-guard.sh \
    .claude/hooks/secrets-pre-filter.sh \
    .claude/hooks/token-report-stop.sh \
    AGENTS.md \
    .steering/_token_log.md \
    .steering/_token_log.last_key
  do
    if [ -e "$path" ]; then
      echo "FAIL: $path exists but Phase 5 was skipped (orphan)"
    fi
  done

  # cross-reviewer / /cross-review への参照が他のファイルに残っていないか
  if grep -lr "cross-reviewer\|codex-review\|/cross-review" .claude/ 2>/dev/null | grep -v "^Binary"; then
    echo "WARN: References to Codex agents/skills/commands found in .claude/ tree (Phase 5 skipped)"
  fi
fi
```

### Step 8: 相互参照の検証

`.steering/_setup-progress.md` の「構築物の相互参照マップ」を Read で確認し、以下を検証:

#### Skill → Agent
- マップに記載された Skill が実際に存在するか
- 各 Agent が記載通りに Skill を参照しているか（Read で確認）

#### Skill → Command
- `implementation-workflow` Skill が存在し、`/add-feature`, `/fix-bug`, `/refactor`
  の 3 コマンドから実際に Read 参照されているか
- 3 コマンドが共通骨格を再度コピーしておらず、Skill 参照型の薄い構造になっているか

#### Agent → Command
- マップに記載された Agent が各 Command で実際に呼ばれているか

#### Hook → Command
- Hook が各 Command の動作と矛盾しないか

破綻があればリストアップ。

### Step 9: 検証レポートの生成

すべてのチェック結果を統合し、以下の形式でレポートを生成:

```markdown
# Claude Code 環境構築 検証レポート

検証日時: [YYYY-MM-DD HH:MM]

## 総合判定

[✅ HEALTHY / ⚠️ WARNINGS / ❌ ISSUES]

## Phase 番号 旧 → 新 マッピング (移行対応)

このバージョンの verify-setup から Phase 番号体系が刷新されている。過去 verify-report との diff を取りやすくするため、旧体系との対応を明示:

| 旧 (Phase 0-7 / 8 段階) | 新 (Phase 0-9 / 10 段階) | 内容 |
|---|---|---|
| Phase 0 | Phase 0 | bootstrap |
| Phase 1 | Phase 1 | docs |
| — | **Phase 2 (新規)** | marketplace (anthropics/skills) |
| Phase 2 | **Phase 3** | claude-md → CLAUDE.md / AGENTS.md / agent-shared.md |
| Phase 3 | **Phase 4** | skills |
| — | **Phase 5 (新規)** | codex-bridge |
| Phase 4 | **Phase 6** | agents |
| Phase 5 | **Phase 7** | commands |
| Phase 6 | **Phase 8** | hooks |
| Phase 7 | **Phase 9** | verify |

## 各フェーズの状態

### Phase 1: docs ✅
- すべてのファイル存在: ✅
- 整合性: ✅
- 行数: 適切

### Phase 2: Marketplace [✅/⚠️/❌/SKIPPED]
- docs/external-skills.md 存在: ✅
- 導入済 plugin: [N] (Proprietary [N], Apache 2.0 [N])
- proprietary 同意ログ: ✅/N/A
- (skipped の場合) 空テンプレが正しく生成されているか: ✅

### Phase 3: CLAUDE.md / AGENTS.md / agent-shared.md [✅/⚠️/❌]
- CLAUDE.md 行数: [N] (上限 150)
- AGENTS.md 行数: [N] (上限 80) / または N/A (Phase 5 skip)
- docs/agent-shared.md 行数: [N] (上限 200)
- `@docs/agent-shared.md` 参照: CLAUDE.md=[N], AGENTS.md=[N]
- 責務分離 (Step 2.5 の同期検証): ✅/⚠️ leakage detected
- 必須セクション: ✅

### Phase 4: Skills [✅/⚠️/❌]
- 自前 Skill 数: [N]
- 静的 Skill: [N]
- 動的 Skill: [N] (最低 1 必要)
- description 品質: [合格 N / 全 N]
- 補足ファイル: [合格 N / 全 N]
- 公式 Skill 重複回避: ✅/⚠️ overlap detected
- 問題のある Skill:
  - [skill-name]: [問題の説明]

### Phase 5: Codex Bridge [✅/⚠️/❌/SKIPPED]
- (skipped の場合) codex-consult / codex-review / codex-rescue / cross-reviewer / /cross-review / Codex hook / wrapper の取り残しなし: ✅
- (完了の場合):
  - .codex/config.toml 存在: ✅
  - .codex/budget.json 構造正常: ✅
  - scripts/secrets-filter.sh 実行可能 + fail-closed (exit 2): ✅
  - scripts/run-codex-consult.sh 実行可能: ✅
  - scripts/run-codex-review.sh 実行可能: ✅
  - codex-consult Skill 存在 (設計相談): ✅
  - codex-review Skill 存在 (diff レビュー): ✅
  - codex-rescue Skill 存在 (rescue 実装): ✅
  - 疎通テスト (Step 2.7): ✅ PASS / ⚠️ AUTH_PENDING / ❌ FAIL

### Phase 6: Agents [✅/⚠️/❌]
- 基本エージェント数: [N] / 9
- cross-reviewer (Phase 5 完了時): ✅/N/A
- レポート形式定義: [合格 N / 全 N]
- Skill 参照: [合格 N / 全 N]
- モデル選択: [合格 N / 全 N]
- cross-reviewer の Bash 権限が wrapper 限定 (Phase 5 完了時): ✅/⚠️ overly permissive
- 問題のあるエージェント:
  - [agent-name]: [問題の説明]

### Phase 7: Commands [✅/⚠️/❌]
- 基本コマンド数: [N] / 8
- /cross-review (Phase 5 完了時): ✅/N/A
- 単一責任: [合格 N / 全 N]
- Skill/Agent 参照: [合格 N / 全 N]
- /cross-review の 3 段ガード (行数 / proprietary / 予算): ✅/N/A
- 問題のあるコマンド:
  - [command-name]: [問題の説明]

### Phase 8: Hooks [✅/⚠️/❌]
**3 層構成 (Preflight / Guard / Report) + Codex 層 (任意) の整合性**:

- **Preflight 層**:
  - UserPromptSubmit Hook (`preflight.sh`): ✅/❌
  - 動的チェック実装 (固定文言 echo でない): ✅/❌
  - `exit 0` 厳守 (BLOCK しない): ✅/❌
- **Guard 層**:
  - PreToolUse Hook (`pre-edit-steering.sh`): ✅/❌
  - PreToolUse Hook (`pre-edit-banned.sh`, 任意): ✅/❌/N/A
  - `[guard] PASS` 出力 (無言通過でない): ✅/❌
  - 偽陽性なし (docs/ やテストをブロックしない): ✅/❌
- **Report 層**:
  - PostToolUse Hook (`post-fmt.sh`): ✅/❌
  - Stop Hook (`stop-check.sh`): ✅/❌
  - `--check` 先判定で変更時のみ報告: ✅/❌
  - clippy / tsc 出力の抑制 (`>/dev/null 2>&1`): ✅/❌
- **第 4 層 (Codex ガード、Phase 5 完了時のみ)**:
  - codex-budget-guard.sh 存在 + 早期 exit 実装: ✅/N/A
  - secrets-pre-filter.sh 存在 + 早期 exit 実装: ✅/N/A
  - token-report-stop.sh 存在 + 冪等性キー実装: ✅/N/A
  - settings.json に Bash matcher 登録 (完了時) / 未登録 (skip 時): ✅
- **情報表示層**:
  - SessionStart Hook: ✅/❌
- **settings.json**:
  - 全 hook が `"type": "command"` に統一: ✅/❌
  - JSON 構文正常: ✅/❌
  - Phase 5 skip 時の Codex 関連ブロック自動削除: ✅/⚠️ leftover
- **出力プレフィックス統一** (`[preflight]` / `[guard]` / `[fmt]` / `[stop]`): ✅/❌
- 問題:
  - ...

## 相互参照の整合性

- Skill → Agent: ✅/❌
- Agent → Command: ✅/❌
- Hook → Command: ✅/❌
- AGENTS↔CLAUDE 同期 (Phase 5 完了時): ✅/⚠️/N/A
- ライセンス整合 (external-skills.md ↔ secrets-filter ↔ secrets-pre-filter): ✅/❌
- Codex 疎通 (Phase 5 完了時): ✅ PASS / ⚠️ AUTH_PENDING / ❌ FAIL / N/A

## 修正が必要な項目

### CRITICAL
- [破壊的な問題があれば]

### HIGH
- [すぐに修正すべき問題]

### MEDIUM
- [計画的に修正すべき問題]

### LOW
- [改善の余地]

## 推奨される次のアクション

1. ...
2. ...
```

### Step 10: 進捗ファイルの更新

`.steering/_setup-progress.md` の Phase 9 を完了マーク:

```markdown
- [x] **Phase 9: /verify-setup** — 整合性検証 (Codex 疎通 / AGENTS↔CLAUDE 同期 / ライセンス整合 含む)
  - 完了日時: [YYYY-MM-DD HH:MM]
  - 検証結果: HEALTHY / WARNINGS / ISSUES
  - Phase 5 状態: 完了 / skipped (Codex 連携の有無)
  - Phase 2 状態: 完了 / skipped (公式 plugin 導入の有無)
  - Codex 疎通: PASS / AUTH_PENDING / FAIL / N/A
  - AGENTS↔CLAUDE 同期: ✅ / ⚠️ / N/A
  - ライセンス整合: ✅ / ❌
  - 修正が必要な項目: [N] 件 (CRITICAL [N] / HIGH [N] / MEDIUM [N] / LOW [N])
```

検証レポートを `.steering/_verify-report-[YYYYMMDD].md` として保存。

### Step 11: 完了通知

```
Phase 9 完了です。すべての構築フェーズが終わりました。

検証結果: [HEALTHY / WARNINGS / ISSUES]
構成: [Claude 単独 / Claude+Codex 連携] (Phase 5 [完了 / skipped])
公式 Skill: [N] 個 (Phase 2 [完了 / skipped])

[問題があれば修正リストを表示]

これで Claude Code 環境構築の全工程が完了しました。

日々の運用:
1. 新規タスク開始時: /start-task
2. 設計判断が重い時: /reimagine（プラン段階で初回案を破棄・再生成して比較）
3. 実装中: /add-feature, /fix-bug, /refactor
4. 完了時: /finish-task
5. 重要 PR の独立第二意見が欲しい時: /cross-review (Phase 5 完了時のみ)
6. 月次メンテナンス: /verify-setup を再実行

Codex 疎通が AUTH_PENDING の場合: `codex login` を実行してから再度 /verify-setup でテスト。
予算管理: .codex/budget.json で日次トークン上限・差分閾値を確認・調整可能。

検証レポートは .steering/_verify-report-[YYYYMMDD].md に保存されました。
```

## 月次メンテナンスとしての使い方

このコマンドは構築直後だけでなく、月に 1 回程度の定期メンテナンスでも実行することを推奨。
時間の経過とともに以下が起こりうる:

- Skill の description が古くなる
- 削除した Agent への参照が残る
- docs の内容が実装と乖離する
- CLAUDE.md が肥大化する

`/verify-setup` を月次で実行することで、これらを早期発見できる。

## 完了条件

- [ ] すべてのフェーズの状態をチェック済み (Phase 0-8、skip フェーズも明示)
- [ ] AGENTS↔CLAUDE 同期検証実施 (Phase 5 完了時のみ)
- [ ] ライセンス整合検証実施 (常時)
- [ ] Codex 疎通検証実施 (Phase 5 完了時のみ、3 状態判定)
- [ ] 検証レポートが生成されている (新フェーズ番号 1-8 + 相互参照 + 拡張検証 3 項目)
- [ ] 検証レポートが .steering/ に保存されている
- [ ] 進捗ファイルが更新されている (Phase 9 完了マーク)
- [ ] ユーザーに修正項目が伝えられている (CRITICAL / HIGH / MEDIUM / LOW で分類)

## アンチパターン

- ❌ ファイル存在チェックだけで終わる
- ❌ 相互参照の検証を省略する
- ❌ 検証レポートを保存しない
- ❌ 問題があっても「だいたい OK」で済ませる
- ❌ Phase 5 skip 構成で AGENTS↔CLAUDE 同期検証 / Codex 疎通検証を「失敗」扱いする (skip は失敗ではない、N/A 扱い)
- ❌ Codex 疎通の AUTH_PENDING を ISSUES として報告する (WARNINGS 止まり)
- ❌ ライセンス整合検証を skip する (proprietary 経路の漏れは重大インシデント)
- ❌ Phase 5 skip 時に Codex 関連ファイル / hook 登録の取り残しを見逃す
