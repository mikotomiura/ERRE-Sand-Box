# Blockers

## `uv run pytest` exits 1 after passing tests

Observed twice on 2026-04-28:

- Test body result: `1044 passed, 28 skipped`.
- Process exit: `1`.
- Failure occurs during pytest cleanup via `PytestUnraisableExceptionWarning`.
- Reported unraisable warnings:
  - two unclosed Unix sockets
  - one unclosed asyncio event loop

This task only added Codex configuration, hooks, custom agent manifests, and skill/docs
instructions. The failure appears unrelated to the new files, but the full regression command
does not currently produce a clean exit.

### Resolution (2026-04-28, after ci-pipeline-setup PR #113 merge)

`ci-pipeline-setup` task が同じ pre-existing flaky failure を test-analyzer で
切り分け、原因を `pytest-asyncio` 0.26.x の function-scope event loop teardown
が close されない上流既知 issue と特定。`pyproject.toml` `filterwarnings` で
`"default::pytest.PytestUnraisableExceptionWarning"` を追加し、当該 warning を
hard fail から default 表示扱いに緩和することで CI 緑化と本 task の clean exit
の両方を達成した。

検証 (post-merge, main = `de641de`):

```
uv run pytest  -> 1044 passed, 28 skipped in ~38s (3 連続 clean exit)
uv run pytest -m "not godot"  -> 1031 passed, 28 skipped, 13 deselected (3 連続 clean exit)
```

撤去トリガー (`pytest-asyncio >= 0.27`) は ci-pipeline-setup の `blockers.md`
MEDIUM-5 に記録済。本 task の verification 残項目はクリア。
