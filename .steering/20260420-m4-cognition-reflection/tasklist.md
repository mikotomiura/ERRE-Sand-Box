# タスクリスト — m4-cognition-reflection

## Phase 1: 設計 (完了)
- [x] requirement.md 記入
- [x] design-v1.md (初回案)
- [x] /reimagine で design.md (v2)
- [x] design-comparison.md
- [x] 採用判断: v2 + ClassVar 互換 hybrid

## Phase 2: branch & 実装
- [ ] `feature/m4-cognition-reflection` 作成 (from main d9a890a)
- [ ] `src/erre_sandbox/cognition/reflection.py` 新規
  - [ ] `ReflectionPolicy` dataclass / pydantic
  - [ ] `build_reflection_messages(persona, agent, episodic)`
  - [ ] `Reflector` class
- [ ] `src/erre_sandbox/cognition/__init__.py` export
- [ ] `src/erre_sandbox/cognition/cycle.py` 編集
  - [ ] `__init__` に `reflector` param (default None → build default)
  - [ ] step 末尾で `reflector.maybe_reflect(...)` 呼び出し
  - [ ] `CycleResult.reflection_event: ReflectionEvent | None = None`
  - [ ] fallback でも reflector を呼ばない (failure path は skip)
- [ ] `src/erre_sandbox/schemas.py` — 触らない (foundation 凍結済)

## Phase 3: テスト
- [ ] `tests/test_cognition/test_reflection.py` 新規 (11 本)
- [ ] `tests/test_cognition/conftest.py` 編集 (FakeReflector / policy fixture)
- [ ] `tests/test_cognition/test_cycle.py` 追加 1 本 (reflection_event 配線確認)
- [ ] 既存 446 PASS 維持確認

## Phase 4: 品質確認
- [ ] ruff check src/ tests/ && ruff format src/ tests/
- [ ] pytest (full)
- [ ] docs/architecture.md §Cognition 追記
- [ ] code-reviewer + security-checker (parallel)
- [ ] HIGH=0 確認

## Phase 5: PR
- [ ] decisions.md に実装中の設計判断を記録
- [ ] commit (conventional: `feat(cognition): m4 reflection — Reflector + semantic distillation`)
- [ ] push + gh pr create
- [ ] handoff file `.steering/_handoff-next-session-m4-5.md` は本タスク配下に移動 or 削除
- [ ] merge 指示待ち
