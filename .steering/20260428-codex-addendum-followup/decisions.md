# 重要な設計判断

採用方針: 全 finding で /reimagine を必要に応じて適用、hybrid を採用。
plan ファイル: `/Users/johnd/.claude/plans/indexed-growing-moth.md` (本 task 承認済)。

---

## D1. F5 contracts/ レイヤーの docs 伝播 (codex addendum D2 followup)

- **判断日時**: 2026-04-28 (本 task), 起源 2026-04-28 PR #111 (codex F5)
- **背景**: PR #111 で `src/erre_sandbox/contracts/` を新設 + `architecture-rules`
  SKILL のテーブル更新まで行ったが、`docs/architecture.md` と
  `docs/repository-structure.md` の dependency graph + import rules が未更新
  だった。codex addendum D2 で「architecture が contracts/ レイヤーをまだ受け
  入れていない」と指摘 → 三案比較を decisions.md に formal 記録。

- **選択肢 (PR #111 時点での起源判断)**:
  - **v1 (sub-path import)**: `from erre_sandbox.integration.metrics import ...`
    に切替 + SKILL allowlist 拡張。物理は治るが規範違反は残る。
  - **v2 (contracts/ 新設)**: 新レイヤー hosting、SKILL に明示追加。長期的に正面突破。
  - **第3案 (schemas.py 統合)**: Thresholds を schemas.py に追加。SKILL を
    1 文字も変えず合法化。schemas.py の責務拡大 + snapshot test 破壊リスク。

- **採用 (PR #111 で確定、本 task で docs 伝播)**: **hybrid (v2 + v1 sub-path
  shim)**
  - `contracts/__init__.py` + `contracts/thresholds.py` に Thresholds + M2_THRESHOLDS 移動
  - `integration/metrics.py` を shim に短縮 (既存 import 互換維持)
  - `ui/dashboard/state.py:27` を `from erre_sandbox.contracts import ...` に切替
  - `architecture-rules` SKILL: テーブルに `contracts/` 行追加 (PR #111)
  - **本 task 追加**: `docs/architecture.md` の §1 全体図 + §2 技術スタック
    + §3 レイヤー構成、`docs/repository-structure.md` の §1 ツリー + §2
    依存方向 + §3 ASCII deps graph + §5 新規ファイル追加判断フロー、
    すべて contracts/ レイヤーを反映
- **理由**: schemas.py 統合は責務拡大 + test_contract_snapshot.py 破壊リスク。
  sub-path import 単独は規範違反残存 (将来 metrics.py が gateway を import
  し始めたら無防備)。contracts/ 新レイヤーで正面突破 + shim で互換性二重化。
  docs 伝播は codex D2 指摘で気付いた漏れを補完。
- **トレードオフ**: docs 4 箇所 + SKILL 1 箇所のメンテ重複。「現状実装スナップ
  ショット」section に最終確認日付を埋めることでメンテ起点を明示。
- **影響範囲**: docs/architecture.md / docs/repository-structure.md /
  architecture-rules SKILL / src/erre_sandbox/contracts/ / 既存 import 全体
- **見直しタイミング**: 次の codex/Claude review で contracts/ への
  evidence/CognitionCycle.DEFAULT_TICK_SECONDS 移転検討、または別の
  軽量定数が contracts/ に集まった時点で `contracts/timing.py` 等に分割
- **次アクション**: 本 task tasklist Phase G で完了、codex Additional
  finding (evidence import) は依然棄却 (class attr access で軽量、import 自体は必要)

---

## D2. D7 (pre-commit/CI claim) hybrid: 現状 manual と明示 + 別 task scaffold

- **判断日時**: 2026-04-28
- **背景**: docs/development-guidelines.md L22-25, L84-87, L101-104、
  docs/architecture.md L68 が「pre-commit hook で commit 時自動検証」「CI
  (GitHub Actions) uv sync --frozen → ruff → pytest」と主張するが、
  `.pre-commit-config.yaml` も `.github/workflows/` も存在しない。

- **選択肢**:
  - **v1 (docs を manual と明示)**: pre-commit/CI 主張削除、"manual で
    `uv run` を実行" と書く。
  - **v2 (即時導入)**: `.pre-commit-config.yaml` + `.github/workflows/ci.yml`
    新設 (PR #111 で緑化済なので即着手可)。
  - **第3案 (segmented)**: docs を「現状 manual」と明示 + CI 導入は別 task
    scaffold (`20260428-ci-pipeline-setup`) として起票、本 task では scope 外。

- **採用 = 第3案 (segmented)**
- **理由**: pre-commit/CI 導入は別の design 判断 (uv 整合、Action permissions、
  cost management、Action runner 選定) を含む。本 task は docs 整合性回復に
  集中、CI は別 task で扱う。docs/development-guidelines.md と
  docs/architecture.md L68 の文言は「現状 manual、`.steering/20260428-ci-pipeline-setup/`
  で導入予定」と書き換え。
- **トレードオフ**: CI scaffold が起票されても着手されないリスク。scaffold
  の DoD に「BLOCKED ON ruff/mypy/pytest 緑化 → 既達 (PR #111)」と書いて
  ready-to-execute を明示。
- **影響範囲**: docs/development-guidelines.md L22-25,84-87,101-104 +
  docs/architecture.md L68 + 新規 `.steering/20260428-ci-pipeline-setup/`
- **見直しタイミング**: CI scaffold が着手・完了次第、docs を再度 "CI で
  自動化" に戻す
- **次アクション**: 本 task tasklist Phase H で実施

---

## D3. D4 (Codex root) hybrid: 両方併存 + 役割明示

- **判断日時**: 2026-04-28
- **背景**: AGENTS.md L21,23,97-99 が `.Codex/commands/`, `.Codex/agents/`,
  `.Codex/skills/` を参照するが、実体は `.claude/` (Claude Code 配下) +
  `.agents/skills/` (Codex 向け mirror) で、`.Codex/` 自体が存在しない。
  3 命名規約が混在し、Codex セッション開始時に存在しないディレクトリを
  先に探す挙動になる。

- **選択肢**:
  - **v1 (.Codex → .claude 統一)**: AGENTS.md の `.Codex/` を `.claude/`
    に rename。CLAUDE.md と同じ paths。
  - **v2 (.agents/ を Codex 専用 root として正規化)**: `.agents/skills/` のみ
    commit、AGENTS.md は `.agents/` を主参照。
  - **第3案 (両方併存 + 役割明示)**:
    - `commands/` と `agents/` (subagent 定義) は `.claude/` 配下のものを
      Codex も共有 (両 agent で同一 workflow を保証)
    - `skills/` は `.agents/skills/` (Codex 向け mirror) と `.claude/skills/`
      (Claude canonical) の併存
    - AGENTS.md 冒頭で命名規約を説明、`.agents/skills/` を主参照と明示
    - `.agents/` ディレクトリ + `AGENTS.md` を git commit

- **採用 = 第3案 (両方併存)**
- **理由**: Codex 専用の `.agents/skills/` mirror は user setup 済 (12 skill)。
  これを正規化、かつ commands/agents は共有することで保守コスト低減。
  v1 (`.claude/` 統一) は Codex に Claude 用 SKILL を直接読ませる仕様変更で
  agent モデル間の SKILL カバレッジ違いを反映できない。v2 (`.agents/` 専用)
  は commands を Codex 用に複製する保守負荷。
- **トレードオフ**: AGENTS.md と CLAUDE.md の docstring が分岐 (片方は
  `.claude/skills/`、もう片方は `.agents/skills/`)。両者の整合性監視が必要。
- **影響範囲**: AGENTS.md (L21-23, L97-99 path 全置換 + 命名規約 note 追加)、
  `.agents/` ディレクトリ (commit 対象)、AGENTS.md (commit 対象)
- **見直しタイミング**: Codex の使用が定常化し、`.agents/skills/` と
  `.claude/skills/` の divergence が観測されたら片方に統一
- **次アクション**: 本 task tasklist Phase I で実施

---

## D4. m9-pre-plan を D8 DRAFT マークから除外する判断

- **判断日時**: 2026-04-28
- **背景**: codex addendum D8 が「6 scaffold 含めて DRAFT マーカー追加」と
  指摘したが、m9-pre-plan は decisions.md (D1-D5 hybrid 完成) + tasklist.md
  (本 PR DoD 全完了) + commit/PR 完了済で execution-ready 以上の段階にある。
- **選択肢**:
  - **v1 (D8 通り全 6 マーク)**: codex 指摘そのまま。m9-pre-plan に "DRAFT" 注記。
  - **v2 (m9 除外)**: m9-pre-plan は完成済みなので除外、5 sibling のみマーク。
- **採用 = v2 (m9 除外)**
- **理由**: m9-pre-plan を DRAFT マークすると将来の reader に誤情報を与える。
  実態は execution-ready で、本 task Phase B で post-merge 状態を反映済。
- **次アクション**: 本 task tasklist Phase A で 5 sibling のみマーク。
