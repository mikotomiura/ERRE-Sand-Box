# タスクリスト

> **Status: PRE-PLAN — no execution.**
> 本タスクは documentation only。下記は M9 着手 prerequisites であり、
> 本 PR の DoD は decisions.md / design.md / 本 tasklist の起草完了まで。
> 各 prerequisite は別 task scaffold で個別に着手する。

## 本 PR DoD (本 task の完了条件)

- [x] requirement.md 確定 (L1-51, scaffold 時に既に充実)
- [x] design.md 起草 (§1-§6, defer-and-measure + /reimagine 方法論宣言)
- [x] decisions.md 起草 (D1-D5, 各 v1/v2/hybrid + cite + ζ 数値照合)
- [x] tasklist.md (本ファイル) 起草
- [x] 受け入れ条件 4 項目を grep 検証 (AC1=5 ADR / AC2=8 ζ literals: 126・18・201・0.112・36/74/16・36:74:16・43%・34% / AC3=v1+v2+hybrid 43 行 / AC4=25 checkbox + 6 section / AC5=src diff zero)
- [ ] git commit (Conventional Commits, scope=m9-lora-pre-plan, refs L6 ADR)

---

## M9 着手 prerequisites (本 pre-plan で確定、別 task で実行)

### データ閾値 [D1]

- [ ] dialog_turn 数: persona 別 ≥500 OR divergence 比率 (ζ 36:74:16 起点) が
  連続 3 run で ±20% に flat 化、いずれか先到達を確認 [D1 hybrid]
  - 現状: ζ で 18 turn / 1800s (~83x 不足)、v2 trigger が先行発火見込み
- [ ] baseline floor 維持確認 (Run 1 比 self_rep ≤ 0.10, cross_echo ≤ 0.10,
  bias_fired ≥ 0.5556) を毎 run で計測 [D1 hybrid v1 必要条件]
- [ ] persona reasoning_trace 比率を 3 run 連続記録 (ζ 36/74/16 起点で
  stability 判定の baseline 構築) [D1 hybrid v2 trigger]

### Tool / インフラ [D2]

- [ ] vLLM --enable-lora 起動確認 (qwen3:8b base, llm-inference Skill 参照) [D2 hybrid v1]
- [ ] Parquet export pipeline 実装 (m8-baseline-quality-metric design.md L133 で
  M9 scope 確認済) [D2 hybrid]
- [ ] PEFT vs unsloth 選定 spike (rank=8 統一で 1 回比較実験) [D2 hybrid]
- [ ] dataset 結合 schema 凍結 (dialog_turn + reasoning_trace 必須、
  episodic_memory 補助) [D2 hybrid v2 dataset]

### Agent 拡張 [D3]

- [ ] M1 / M3 metric を long-run (>360s, 推奨 1800s 複数本) で再計測
  (ζ で M3=34% 僅か超過、確定値が必要) [D3 hybrid v1 必要条件]
- [ ] 4th persona 候補 (agora 主体仮説) の persona YAML 雛形草案
  (persona-erre Skill 参照、profile.md L195 cite) [D3 hybrid v2 仮説駆動]
- [ ] N=4 で VRAM 実測 (現 N=3 で 13GB / 余裕 3GB の確認) [D3 hybrid 上限制約]

### M11 接続 [D4]

- [ ] m8-session-phase-model spike の <500ms 往復遅延達成 [D4 hybrid v1 latency]
- [ ] evaluation epoch (annotation-only) の schema 定義
  (player annotation 入力、agent との直接対話なし) [D4 hybrid v2 正規定義]
- [ ] autonomous epoch のログ汚染ゼロ確認テスト [D4 hybrid v1 prerequisite]

### Rollback [D5]

- [ ] adapter swap 手順 documented (vLLM --enable-lora unload runbook) [D5 hybrid v1 機構]
- [ ] persona signature divergence metric 暫定実装 (KL or cosine,
  ζ 36:74:16 起点、暫定閾値 0.5) [D5 hybrid v2 detection]
- [ ] rollback 発火 → 人間裁定 → unload までの runbook 雛形 [D5 hybrid AND 条件]

### Documentation

- [ ] CLAUDE.md / MASTER-PLAN §11 R12 への cross-reference 追記検討
  (本 pre-plan を cite) [全 ADR]
- [ ] 成長 UI / xAI 化要件 (D1 後半) の M10 spike 起票候補リスト [D3, D4]
- [ ] L6 ADR (`.steering/20260424-steering-scaling-lora/decisions.md`) に本
  pre-plan への forward link 追記検討 [全 ADR]

---

## 完了処理 (本 task)

- [x] design.md / decisions.md / tasklist.md の cite 切れ最終確認
  (decisions=9 paths / design=8 paths すべて exist 確認済)
- [x] documentation only 保証
  (`.steering/20260428-m9-lora-pre-plan/` 配下 3 ファイルのみ変更、src/tests/godot/personas 差分ゼロ)
- [ ] git commit (例: `docs(m9-pre-plan): 5 ADR with /reimagine v1+v2 hybrid for LoRA trigger / model / scaling / M11 / rollback`)
- [ ] PR 作成 (refs L6 ADR PR、本 task は docs-only として merge)
