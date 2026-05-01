# G-GEAR Phase A 失敗レポート — natural re-capture stalled (post-fix)

> 起草: G-GEAR セッション 2026-05-01 22:50 UTC+9 (kant_natural sanity run after PR #130 merge)
> 目的: Mac セッション (P3a-decide finalization) が ME-8 ADR を re-open
> + design-natural-gating-fix.md v2 起草するための実機計測 hand-off。

## 1. TL;DR

- **Phase A guard tripped** — `kant_natural` 単独 sanity で `focal=6 / total=18 / dialogs=3` (10 min wall timeout)。
- SOP §"想定 hazard" の `Phase A で focal<25` 条件に該当、Phase B (3 並列) には進まず stop。
- **gating fix の半分は機能** (cross-zone admit が pair coverage を 2→3 dialog に拡大、前回 starve した Nietzsche が今回は kant-nietzsche / nietzsche-rikyu 両 pair で initial admit)。
- **未解決の gate** = `COOLDOWN_TICKS=30` × **実測 cognition_period ≈ 120 s/tick** → 実効 cooldown ≈ 60 min → 10 min wall 内で再 admit が物理的に不可能。
- design-natural-gating-fix.md §2 で **棄却された仮説 B (cooldown × cognition_period の wall 換算) を re-activate** すべき。前提値 `world_tick 50+ for 10 min wall` が empirical に成立しなかった。

## 2. 観測指標

### 2.1 採取結果 vs 期待値

| 指標 | PR #129 stall (pre-fix) | post-fix 期待 | **post-fix 実測 (本セッション)** |
|---|---|---|---|
| focal_rows (kant) | 6 | 30 | **6** |
| total_rows | 12 | ~90 | **18** |
| dialogs | 2 | ~10 | **3** |
| wall | 13 min (kill) | 5-8 min | **10 min (wall timeout)** |
| nietzsche admit | 0 (starved) | included | **2 dialogs** (kant-nietzsche + rikyu-nietzsche) |

### 2.2 dialog-by-dialog tick + wall span

| dialog_id | speakers | turns | tick range | zones (DB record) | wall span |
|---|---|---|---|---|---|
| `d_dfa4cbde` | kant ↔ nietzsche | 6 | 1 → 3 | agora, study, peripatos | ~61 s |
| `d_fa9a299f` | kant ↔ rikyu | 6 | 1 → 3 | peripatos, garden | ~60 s |
| `d_83d25195` | nietzsche ↔ rikyu | 6 | 3 → 5 | study, garden | ~35 s |

**全 18 turn が tick 1-5 内で発生**、tick=5 以降 (22:42:29 onward) は **8 分間 0 admit**。Reflection trigger log は 22:47/22:48/22:49/22:50 で継続発火しているので cognition cycle 自体は live (= world は止まっていない)。

### 2.3 inter-turn delta (順 18 turn の `created_at` 差分)

```
turn 1: +2.3s   turn 7:  +2.3s   turn 13: +0.0s
turn 2: +0.0s   turn 8:  +0.0s   turn 14: +0.4s
turn 3: +22.2s  turn 9:  +32.1s  turn 15: +12.3s
turn 4: +0.0s   turn 10: +0.0s   turn 16: +3.3s
turn 5: +1.8s   turn 11: +0.0s   turn 17: +18.4s
turn 6: +0.0s   turn 12: +0.7s
```

burst (~95 s) 内で 3 dialogs × 6 turns = 18 utterances。turn 17 後 (22:42:29) → wall timeout (22:50:30) で **8 min 0 admit**。

## 3. 仮説再評価

### 3.1 仮説 B re-activate (design-natural-gating-fix.md §2 で △ 補助 → ◎ 主因に格上げ)

- design 当時の前提: `nietzsche cognition_period=7s + DEFAULT_COGNITION_PERIOD_S=10s → world_tick 50+ in 13 min wall` → cooldown=30 ticks は OK ⇒ 棄却根拠
- **empirical**: 600 s wall で max(tick) = 5 → **120 s / tick** (cognition_period より 12× 遅い)
- 原因推定 (G-GEAR 側からの仮説、Mac で再検証要):
  1. `qwen3:8b` Q4_K_M on RTX 5060 Ti で reflection (embed + chat) + action selection (chat) + dialog turn (chat × 6) が **serial round-trip** で蓄積
  2. cognition tick が `_run_dialog_tick` 含む全 sub-stage 完了を待つため、burst 中は dialog turn 6 回分の chat call が tick advance を blocking
  3. burst 終了後は cognition+reflection だけだが、それでも Reflection trigger log の inter-arrival ~30 s ⇒ tick rate ~ 1 / 30 s が下限、cooldown 30 ticks = 15 min wall

### 3.2 仮説 C (`_close_timed_out` race) は依然棄却

- 全 dialog が 6 turn budget (= dialog_turn_budget) で正常 close、premature close ではない
- 各 dialog の last turn と CloseDialogMsg 間に異常 wall span 観測なし

### 3.3 仮説 D (zone scatter) は **fix で解決済**

- pair coverage が 2 → 3 に拡大、Nietzsche starve が消えた
- `eval_natural_mode=True` の zone-bypass が effective に動作 (ME-8 ADR の expected behaviour 一致)

## 4. Mac 側で要検討の選択肢

planning purity 制約で G-GEAR 側コード変更不可。Mac セッション (Plan + /reimagine + Codex review 起動推奨) で確定すべき:

| 案 | 内容 | trade-off |
|---|---|---|
| **α** | `eval_natural_mode=True` 時に `COOLDOWN_TICKS` も縮める (例: 5 ticks) | natural cadence の概念が薄まる、ME-8 ADR §invariant の "cooldown active" を更新要 |
| **β** | wall budget を大幅拡張 (--wall-timeout-min 90 → 180+ for natural) | wall は伸びるが概念は綺麗。実測 120 s/tick × 30 cooldown = 60 min × ~3 cycle = 180 min 必要見込 |
| **γ** | `AUTO_FIRE_PROB_PER_TICK` を eval mode で 0.25 → 1.0 | per-pair admit 加速、ただし cooldown が dominant gate なら効果限定 |
| **δ** | 採取設計再考 (eval は LLM 1 cell ずつ運用、3 並列ではなく逐次) | wall 単純倍化、ただし cognition_period 自体は変わらない |
| **ε** | dialog_turn_budget を 6 → 3 に縮めて burst 期間を短縮、cooldown 計算根拠を変える | dialog 内 turn 数が減る、Burrows/MATTR の per-dialog stylo signal が薄まる |

### 推奨判断材料

- **α (cooldown 縮小)** は最も直接的だが ME-8 ADR の "cooldown active" 文言と概念整合のため Codex review 推奨
- **β (wall 拡大)** は概念純粋だが 1 cell 180 min × 3 cell 並列で 3 時間 wall — overnight 採取になる、stimulus と異なる運用
- **α + β ハイブリッド** (eval mode で cooldown=5 + wall=60 min) が実用解の最有力候補

### Mac 側で確認すべき計算

- 60 min wall × 1 tick/120 s = 30 ticks 進行
- cooldown=5 ticks = 10 min × 0.083 cycle/min = **約 5 cycle 期待** = 5 × 3 dialogs × 6 turns = **90 utterance**
- focal kant = 1/3 × 90 = 30 ✓ (target 達成)
- → α (cooldown 5) + wall 60 min が最小実用組合せ

## 5. 保全状態

| ファイル | 状態 | サイズ |
|---|---|---|
| `data/eval/pilot/kant_natural_run0.duckdb.tmp` | **保持** (staged-rename 失敗で .tmp 残存) | 524 KB |
| `data/eval/pilot/kant_natural_run0.log` | **保持** (httpx + cognition full log) | 33 KB |
| `data/eval/pilot/{nietzsche,rikyu}_natural_*.duckdb*` | **未生成** (Phase B 未起動) | — |
| `data/eval/pilot/*_stimulus_*.duckdb` | **無傷** (PR #129 既存) | 各 524 KB |
| `data/eval/pilot/_summary.json` / `_rsync_receipt.txt` | **未更新** (失敗を _summary に書かない) | — |
| working tree | clean、git diff 0 | — |

`.duckdb*` は `.gitignore` 済 (commit 対象は markdown レポートのみ)。

## 6. ME-8 ADR re-open 候補項目

decisions.md ME-8 §re-open 条件 の 3 項目目 "fix 後も admit が初動 burst で停止する場合" が **発火**。本レポートを根拠に Mac で:

1. ME-8 ADR §影響 / §re-open 条件 を partial-update (本セッション empirical data を引用)
2. 採用案を α / β / γ / δ / ε / ハイブリッドから 1 つ確定 (Plan + /reimagine + Codex review)
3. design-natural-gating-fix.md v2 として代案比較を再実施
4. 実装 + test 後、G-GEAR 再々採取 (本レポートを base に Phase A 期待値の桁を再校正)

## 7. Hand-off チェックリスト (Mac セッション用)

- [ ] 本レポート (`g-gear-phase-a-failure.md`) を Mac で Read
- [ ] decisions.md ME-8 §re-open 条件発火を AD R partial-update
- [ ] design-natural-gating-fix.md v2 起草 (5.0 critical insight 級の re-evaluation: bias_p=0.2 の代わりに actual cognition_period が dominant)
- [ ] α / β / γ / δ / ε から採用案確定 (Codex `gpt-5.5 xhigh` review に回す)
- [ ] 実装 + 12 unit test 拡張 (cooldown 縮小 invariant 再定義 / wall 期待値 update)
- [ ] G-GEAR 再々採取 prompt (`g-gear-p3a-rerun-prompt.md` v2) を起草
- [ ] tasklist.md §P3a-decide にチェック項目追加 ("仮説 B re-activate"/ "fix v2 確定")

## 8. 注記

- 本セッションは planning purity を厳守 (コード変更 0 件)。修正は Mac セッションで Plan mode + Codex review を経由する。
- `.tmp` DuckDB は **保持**、Mac 側で読みたい場合は rsync 可能だが、本診断データは本レポート本文に inline 済 (re-rsync 不要のはず)。
- 本ブランチ `feature/m9-eval-p3a-natural-stalled-report` は本レポート 1 ファイル commit のみ。stimulus 既存データ更新なし、_summary.json 不更新。
