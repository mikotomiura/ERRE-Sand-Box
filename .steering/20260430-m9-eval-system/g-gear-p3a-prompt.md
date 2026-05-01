# G-GEAR セッション用プロンプト — m9-eval-system P3a 実行

> このファイルは Mac セッション (2026-05-01) 末尾で起草。
> G-GEAR (RTX 4090 24GB / Ubuntu / Claude Code 同居) で /clear 後に
> 全文をコピペして送る前提。Mac → G-GEAR の sync は user が事前に
> `git fetch && git checkout main && git pull` で完了している想定。

---

タスク 20260430-m9-eval-system Phase P3a を G-GEAR で実行する。

# 前セッション (Mac, 2026-05-01) の到達点

P0a-P2c 全完了。`main` には P0-P2c 累積の単一 PR が merged 済 (PR 番号 / merge コミットは
user 通知)。

- P0a-c: contracts/eval_paths.py + evidence/eval_store.py (DuckDB raw_dialog +
  metrics schema、`connect_training_view()` constrained relation、CHECKPOINT +
  atomic_temp_rename helper)
- P1a-b: tier_a/ 5 metric (Burrows Delta z-score L1 / MATTR / NLI / novelty /
  Empath proxy) + reference_corpus (PD-only Kant 独 / Nietzsche 独 / Rikyū 日 +
  synthetic 4th)
- P2a-b: golden/stimulus/{kant,nietzsche,rikyu}.yaml (70 stim × 3 = 210)、
  integration/dialog.py に `golden_baseline_mode: bool` minimum patch
- P2c: **`evidence/golden_baseline.py` driver** + `golden/seeds.json` (5 run × 3
  persona uint64 seed manifest) + `tests/fixtures/synthetic_4th_mcq.yaml` +
  23 unit test 全 PASS

フル test suite "not godot and not eval" 1221 passed / 31 skipped / 14 deselected、
mypy src 0、ruff/format clean、eval-egress-grep-gate 緑。

# 本セッションで作る不足コンポーネント

P3a を実機で動かすには **driver を real LLM に繋ぐ CLI** が必要 (P2c までは mock LLM
unit test のみ)。本セッションは Step 1 でこれを起草、Step 2 で P3a 採取に入る。

# まず Read (この順)

1. `.steering/20260430-m9-eval-system/design-final.md`
   - §"Hardware allocation" (P3a の owner=Operator/G-GEAR、6-8h、出力は両 condition の bootstrap CI width)
   - §"Orchestrator: 既存 scheduler に minimum patch + 外部 golden driver" (driver は公開 API 経由のみ)
   - §"Hybrid baseline 採取" (200 stimulus + 300 自然対話、ratio defer)
2. `.steering/20260430-m9-eval-system/decisions.md`
   - **ME-2** (CHECKPOINT + cp /tmp/snapshot + rsync + atomic rename + `read_only=True` 強制、NFS/SMB/iCloud 経由禁止)
   - **ME-4** (ratio P3a 後に確定、`design-final.md` の placeholder ADR を実測値で Edit)
   - **ME-5** (blake2b uint64 seed、`golden/seeds.json` と `derive_seed()` の identity)
   - **ME-7** (MCQ schema 11 field、cycle 1 only primary scoring、source_grade=legend exclude)
3. `.steering/20260430-m9-eval-system/tasklist.md` §P3a + §P3a-decide (本セッションは P3a まで、
   P3a-decide は Mac セッションで P4a/P5 完了後)
4. `src/erre_sandbox/evidence/golden_baseline.py`
   - `GoldenBaselineDriver` dataclass の `__init__` / `run_persona` / `run_stimulus` / `enable_natural_phase`
   - `derive_seed` / `shuffled_mcq_order` / `load_stimulus_battery` /
     `assert_seed_manifest_consistent`
5. `src/erre_sandbox/evidence/eval_store.py`
   - `bootstrap_schema(con)` / `connect_analysis_view(path)` /
     `write_with_checkpoint(con)` / `atomic_temp_rename(temp, final)` /
     `ALLOWED_RAW_DIALOG_KEYS` (15 列の lockstep)
6. `src/erre_sandbox/integration/dialog.py` の `InMemoryDialogScheduler`
   (`golden_baseline_mode` / `record_turn` の `turn_sink` 契約 / `tick()` の自然対話 driver)
7. `src/erre_sandbox/inference/ollama_adapter.py` または sglang_adapter.py
   (本リポジトリの推論クライアントパターン、persona system prompt 注入の既存例)
8. `personas/{kant,nietzsche,rikyu}.yaml` (system prompt + sampling override + ERRE mode)
9. `golden/seeds.json` (5 run × 3 persona の uint64 seed list)

# 環境確認 (Read 後、Step 1 着手前に実行)

```bash
# 依存
uv sync --all-extras  # eval extras (sentence-transformers / scipy / ollama / empath / arch) を pull

# GPU
nvidia-smi  # RTX 4090 24GB / Driver 535+ / CUDA 12.x

# LLM
ollama list | grep qwen3:8b || ollama pull qwen3:8b  # FP16 ~16GB

# Seed manifest 同値性 (Mac との identity 確認)
uv run python -m erre_sandbox.evidence.golden_baseline  # 既存 seeds.json を上書きしないか確認
uv run python -c "
from erre_sandbox.evidence.golden_baseline import load_seed_manifest, assert_seed_manifest_consistent
m = load_seed_manifest()
assert_seed_manifest_consistent(m)
print(f'seeds.json: {len(m[\"seeds\"])} rows OK, salt={m[\"salt\"]}')"

# Sanity test (P2c の 23 件 + 関連 evidence test を G-GEAR で再走)
uv run pytest tests/test_evidence/test_golden_baseline.py -q
```

# 本セッションで行う作業

## Step 1: `cli/eval_run_golden.py` 起草 (Plan mode 必須、~2h)

**Plan mode で**設計合意を取ってから実装。CLI 1 ファイル + 接続層 1-2 ファイルなので
`/reimagine` は不要 (公開 API 設計でも persona prompt 構成でもない、既存パターン踏襲)。

### 受ける引数 (argparse)

```
--persona {kant|nietzsche|rikyu}        必須
--run-idx INT                           必須 (0..4、seeds.json の lookup key)
--condition {stimulus|natural}          必須
--turn-count INT                        default 200 (P3a 専用、P3 本番は別フラグで 500)
--cycle-count INT                       default 3 (stimulus condition のみ参照)
--output PATH                           default data/eval/pilot/<persona>_<condition>_run<idx>.duckdb
--ollama-host STR                       default http://localhost:11434
--model STR                             default qwen3:8b
```

### CLI フロー

1. `seed_root = derive_seed(persona, run_idx)` + `assert_seed_manifest_consistent(load_seed_manifest())`
   で identity ガード。
2. **fresh** DuckDB を `args.output` に作成 (P3a-decide の carry-over 防止 test 化対象)。
   `eval_store.bootstrap_schema(con)` で raw_dialog + metrics schema を CREATE。
3. `InMemoryDialogScheduler(envelope_sink=..., turn_sink=..., golden_baseline_mode=True)` 構築。
   `turn_sink` は `DialogTurnMsg → ALLOWED_RAW_DIALOG_KEYS` 各列の dict に変換して
   `con.execute("INSERT INTO raw_dialog.dialog ...")` する closure。
   - `run_id`: ULID or `f"{persona}_{condition}_run{run_idx}"` 固定 + `started_at` (UTC ISO)
   - `mode_sampling` / `cognitive_habits` 由来列は persona YAML から (P0c の column 詳細は
     `eval_store.py` の `_RAW_DIALOG_COLUMNS_DDL` を Read してから埋める)
4. `inference_fn(persona_id, stimulus, cycle_idx, turn_index, prior_turns, mcq_shuffled_options)`
   は ollama HTTP に接続:
   - persona system prompt = personas/<persona>.yaml の `cognitive_habits` + ERRE mode の
     instruction text を組み立てる (既存 `inference/ollama_adapter.py` の build_system_prompt
     を踏襲)
   - user content: stimulus["prompt_text"] + (MCQ なら `mcq_shuffled_options` の A-D を整形して
     "Answer with one of A/B/C/D." を末尾に付加)
   - sampling: persona YAML の `default_sampling` を respect、ただし MCQ は
     temperature=0.0 / top_p=1 で deterministic
5. **stimulus condition**: `driver.run_persona(persona, stimuli=load_stimulus_battery(persona)[:N])`
   で 200 turn 相当に切り詰め。stimulus YAML の各 stimulus は `expected_turn_count` 1-3 を
   持つので、累積 turn = 200 になるよう適切に slice する (Plan mode で確定)。
6. **natural condition**: `driver.enable_natural_phase()` で `golden_baseline_mode=False` に
   flip 後、scheduler.tick(world_tick, agents) を回して 200 turn 採取するか、
   M5/M6 の自然対話 runtime (例 `world/tick.py::WorldRuntime`) を再利用。**ここは既存の
   M5/M6 driver loop に乗るのが筋**、m9-eval 専用の自然対話 driver は新設しない。
7. 採取完了で `eval_store.write_with_checkpoint(con)` → `eval_store.atomic_temp_rename(...)`。

### `cli/eval_run_golden.py` のテスト

unit test は **mock ollama client** で stimulus/natural 各 1 invocation を
`tests/test_cli/test_eval_run_golden.py` で確認:
- argparse 引数組み立て / DuckDB raw_dialog 行数 / `assert_seed_manifest_consistent` 経由
- 実 LLM 接続 test は `@pytest.mark.eval` で deselect (CI default は skip)

## Step 2: P3a 採取 (実機実行、6-8h wall)

3 persona × 2 condition = **6 invocation**。各 invocation で **fresh DuckDB file**:

```bash
mkdir -p data/eval/pilot
for persona in kant nietzsche rikyu; do
  for condition in stimulus natural; do
    uv run python -m erre_sandbox.cli.eval_run_golden \
      --persona "$persona" \
      --run-idx 0 \
      --condition "$condition" \
      --turn-count 200 \
      --output "data/eval/pilot/${persona}_${condition}_run0.duckdb" \
      2>&1 | tee "data/eval/pilot/${persona}_${condition}_run0.log"
  done
done
```

**carry-over 防止 test** (`tests/test_evidence/test_p3a_isolation.py` 新規、~30 lines):
- 6 file が独立 DuckDB であることを確認
- run_id が一意であることを確認
- 6 file 間の dialog_id 集合が disjoint であることを確認

## Step 3: rsync to Mac (ME-2 protocol)

```bash
# G-GEAR 側で snapshot
for f in data/eval/pilot/*.duckdb; do
  cp "$f" "/tmp/$(basename $f).snapshot.duckdb"
done

# Mac へ rsync (Mac の hostname は user に確認)
rsync -av /tmp/*.snapshot.duckdb mac-host:~/ERRE-Sand\ Box/data/eval/pilot/

# Mac 側で atomic rename + read_only 開封確認 は Mac セッションで実施
# (本セッションでは rsync 完了報告まで)
```

## Step 4: 採取結果のサマリ JSON 生成 (Mac セッションへの引き継ぎ)

```python
# scripts/p3a_summary.py 起草、各 DuckDB から:
#   - run_id / persona_id / condition / total_turns
#   - dialog_id 件数
#   - utterance 文字数 mean/median (Burrows / Vendi の input volume 確認)
# JSON は data/eval/pilot/_summary.json に出力、Mac 側 P3a-decide で参照
```

## Step 5: tasklist 更新 + .steering 同期

- tasklist.md の P3a checkbox を [x] 化、6 invocation の wall-clock + raw_dialog 件数を記録
- blockers.md / decisions.md ME-4 placeholder は **Mac セッション** で P3a-decide
  時に Edit (本セッションでは触らない)

# 守るべき制約 (CLAUDE.md 由来)

- **main 直 push 禁止**: 本セッションは作業ブランチ (`feature/m9-eval-p3a-pilot` 等) を切り、PR を出す
- **Plan mode 必須**: Step 1 (`cli/eval_run_golden.py` 起草) の最初の段階
- `/reimagine` 不要 (CLI 1 ファイル設計、既存 ollama_adapter パターン踏襲)
- **50% ルール**: 本セッションは Step 1 (~2h) + Step 2 wall (~6h、待ち時間は別作業可) で
  context 圧迫しやすい → 50% 到達で `/smart-compact`、Step 2 待ち時間は `/clear` 推奨
- **commit policy**: 本セッション完了時の単一 commit (Step 1 の CLI + Step 2 の採取データ
  + Step 3 の rsync ログ + Step 4 のサマリ JSON + Step 5 の tasklist 更新)
- **採取データの commit 範囲**: `data/eval/pilot/*.duckdb` は **commit しない** (大容量バイナリ)、
  代わりに `_summary.json` のみ commit。`.gitignore` に `data/eval/pilot/*.duckdb` を追加
- **ME-2 rsync semantics 厳守**: live G-GEAR file の Mac 直 open は **禁止**、CHECKPOINT +
  /tmp snapshot + rsync + atomic rename を必ず通す
- **planning purity**: src/ + cli/ + tests/ + scripts/ + data/eval/pilot/ + .steering/ /
  .gitignore のみ touch、他レイヤー無関係

# 本セッションで触らないもの

- P4a (Tier B 3 metric) — Mac セッションで実装、本タスクの sub-metric prerequisite
- P5 (bootstrap_ci.py) — Mac セッション、AR(1) synthetic test fixture で実測 data 不要
- P6 (Tier C systemd unit) — 本セッションで時間あれば draft 可、deploy は Mac→GG hand-off
- ME-4 ADR Edit — Mac セッションで P3a-decide 時に確定値で更新

# 持ち越し条件

- **Step 1 完了 / Step 2 着手前**: /clear して fresh session で Step 2 起動 (実機 6-8h を待つ
  間に context が古びるため)
- **Step 2 待機中** (LLM が走っている間): 別 terminal / 別 Claude session で P4a (Tier B)
  / P5 (bootstrap_ci) の起草に着手可能 (依存無し)
- **wall-clock オーバー**: 8h を超える場合は途中で SIGTERM 後 1 condition だけでも採取完了 →
  rsync、残りは次 G-GEAR セッション。decisions.md ME-4 の判定基準は両 condition 必須なので
  欠損があると P3a-decide 不可

# 完了条件 (本セッション done)

- [ ] `cli/eval_run_golden.py` + `tests/test_cli/test_eval_run_golden.py` (mock LLM) 全 PASS
- [ ] フル test suite "not godot and not eval" green、mypy src 0、ruff/format clean、grep gate 緑
- [ ] 6 DuckDB file (3 persona × 2 condition) 採取完了、各 200 turn ± 端数
- [ ] CHECKPOINT + /tmp snapshot + rsync to Mac 完了、Mac 側 receipt 確認
- [ ] `data/eval/pilot/_summary.json` 生成、commit 対象に追加
- [ ] tasklist.md §P3a 全 [x]、wall-clock + 件数を [Mac→GG] tag 行に記録
- [ ] PR 作成 (本セッション分)、PR description に rsync receipt + summary JSON link

# 補助 context (Read 不要、必要時のみ)

- `src/erre_sandbox/world/tick.py::WorldRuntime` (M5/M6 自然対話 driver loop の reference)
- `src/erre_sandbox/cli/baseline_metrics.py` / `cli/scaling_metrics.py` (既存 CLI argparse + JSONL out パターン)
- `.codex/budget.json` (本セッションで Codex 起動する場合は per_invocation_max=200K 厳守)
- `M9-A` 完了履歴: `.steering/20260428-event-boundary-observability/` (G-GEAR 実機検収の前例、PR #117-#124)

# 想定される hazard

- **VRAM contention**: qwen3:8b FP16 ~16GB に加えて autonomous loop が走っていると OOM。
  M5/M6 の autonomous loop が live なら停止してから P3a 起動 (`systemctl --user stop ...`)
- **ollama timeout**: 200 turn × 6 invocation は ollama HTTP keepalive を使い切る可能性、
  接続層に retry + backoff (既存 `error-handling` Skill 参照)
- **DuckDB write lock**: 同 file を二重 open すると即 fail、bootstrap_schema は 1 回のみ
- **stimulus YAML の `expected_turn_count` 累積**: 70 stimulus の expected_turn_count 合計
  (≒ 130-150) なので 1 cycle ≒ 130-150 turn、200 turn 到達には slice + 一部 cycle 拡張が要る。
  実装時に `tests/test_evidence/test_golden_baseline.py::test_70_stimulus_battery_drives_cleanly_through_three_cycles`
  の出力 (turns sink の合計件数) を Read して算出
