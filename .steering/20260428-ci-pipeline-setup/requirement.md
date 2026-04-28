# CI pipeline setup — pre-commit + GitHub Actions

> **Status: READY TO EXECUTE.**
> 前提条件 (PR #111 で `uv run ruff check src tests` / `ruff format --check src tests`
> / `mypy src` / `pytest` 全 exit 0) は緑化済。本 task は本 scaffold の design /
> tasklist を埋めてから着手する (codex addendum D8 + D7 hybrid 採用)。

## 背景

`docs/development-guidelines.md` と `docs/architecture.md` が「pre-commit hook
で commit 時自動検証」「GitHub Actions CI (uv sync --frozen → ruff → pytest)」
を主張していたが、`.pre-commit-config.yaml` も `.github/workflows/ci.yml` も
存在しない。codex addendum D7 で指摘された矛盾を解消するため、
codex-addendum-followup task では「現状 manual と明示」を選択 (decisions D2
hybrid 第3案、segmented)、CI 導入は本 task として分離。

PR #111 (codex review followup) で documented verification path
(`uv run ruff check src tests / ruff format --check src tests / mypy src /
pytest`) は全 exit 0 達成済 (1044 passed)。CI 化の前提は揃っている。

## ゴール

1. `.pre-commit-config.yaml` を新設し、`uv run ruff check` + `uv run ruff format --check`
   を pre-commit hook に登録
2. `.github/workflows/ci.yml` を新設し、push/PR トリガーで
   `uv sync --frozen` → `ruff check src tests` → `ruff format --check src tests`
   → `mypy src` → `pytest` を順次実行
3. README + docs/development-guidelines.md + docs/architecture.md の
   "現状 manual" 注記を CI 化後の表記に戻す

## スコープ

### 含むもの
- `.pre-commit-config.yaml` 新規作成 (ruff hook + format hook)
- `.github/workflows/ci.yml` 新規作成 (uv ベース、runner は ubuntu-latest 想定)
- pre-commit のインストール手順を README に追記
- docs 表記の "現状 manual" → "pre-commit / CI で自動化" 復元
- workflow の `pytest` ステップで Godot 依存テストを除外する仕組み (PR #111 F4 deferred との整合)

### 含まないもの
- mypy の pre-commit hook 登録 (slow なため CI のみ)
- 本物の Godot を CI 上にインストール (codex 環境で crash した F4 の真因解明とセットで別 task)
- mypy strict 化や ruff ルール拡張 (CI 緑化のみ目的、ルール変更は別 task)
- coverage 計測 (将来追加検討)

## 受け入れ条件

- [ ] `.pre-commit-config.yaml` 存在、`pre-commit run --all-files` で全 hook pass
- [ ] `.github/workflows/ci.yml` 存在、PR トリガーで実行成功
- [ ] CI run の実行時間 < 5 分 (uv キャッシュ活用)
- [ ] `docs/development-guidelines.md` の "現状 manual" 注記が CI 化後に削除
- [ ] `docs/architecture.md` L68 の CI 行が `[planned]` ではなく実態に
- [ ] README の verification command にコメントで「pre-commit / CI で自動実行されるが
  manual でも `uv run` で実行可」を追記

## 関連ドキュメント

- `.steering/20260428-codex-addendum-followup/decisions.md` D2 (D7 hybrid 採用根拠)
- `.steering/20260428-codex-review-followup/` (PR #111 で verification 緑化済)
- `docs/development-guidelines.md` (CI 化後に整合、現状 manual 注記)
- `docs/architecture.md` L68 (CI 化後に `[planned]` 削除)
- `pyproject.toml` (uv lint 設定、変更なし想定)

## 運用メモ
- 破壊と構築（/reimagine）適用: **Yes**
- 理由: pre-commit と GitHub Actions の design 判断 (Action runner、permissions、
  cache 戦略、matrix testing 必要性) は複数案あり。Plan mode 内で /reimagine 必須。
