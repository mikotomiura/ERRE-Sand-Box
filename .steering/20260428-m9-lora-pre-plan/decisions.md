# 重要な設計判断

> **Status: PRE-PLAN — no execution.**
> 本文書は M9 着手前の意思決定を 5 ADR で確定する。実 LoRA training は含まない。
> 採用方針: 全 ADR で `/reimagine` の v1 (保守延長) + v2 (前提覆し) 並列起草、
> hybrid を採用する (acceptance L43 必須項目)。

---

## D1. LoRA 適用 trigger 閾値

- **判断日時**: 2026-04-28
- **背景**: M9 で persona 別 LoRA fine-tuning に進むが、いつ適用するかの定量基準が
  L6 ADR D1 で「≥500 turns/persona + baseline 固定」と緩く定義されたまま。具体的な
  trigger metric を確定する必要がある。
- **現状**: ζ run-01-zeta (1800s, 76 tick) で dialog_turn=18, episodic_memory rows=201
  (= 0.112 rows/sec), reasoning_trace 比 36/74/16 (kant/nietzsche/rikyu)。Run 1
  baseline は self_rep=0.0, cross_echo=0.0, bias_fired=0.5556 で固定済。

- **選択肢**:
  - **v1 (保守延長)**: dialog_turn ≥ 500/persona AND baseline floor 維持
    (self_rep ≤ 0.10, cross_echo ≤ 0.10) AND bias_fired_rate ≥ 0.5556 を再現。
    episodic_log row は補助指標 (≥ 500 × 3 / 0.112 ≒ 13,400s ≒ 3.7h live)。
    L6 ADR D1 の延長そのまま。
  - **v2 (前提覆し)**: turn 数ではなく **persona divergence の停滞** を trigger に。
    ζ で reasoning_trace が 36:74:16 (約 4.6x 乖離) と発散した事実を逆手に、N
    連続 run で divergence 比率が flat 化したら LoRA 発火。turn 数は無関係扱い
    (corpus が薄くても発散が止まれば prompt-only の限界と判定)。
  - **hybrid (採用)**: v1 を **必要条件** (baseline floor 維持 + bias_fired 再現性)、
    v2 を **十分条件** (発火 trigger) に統合する。
    - v1 から: floor regression (self_rep > 0.10 OR cross_echo > 0.10) 時は
      発火 reject、bias_fired ≥ 0.5556 維持を要求。
    - v2 から: 発火 trigger は (a) dialog_turn ≥ 500/persona OR
      (b) ζ 比率 (kant:nietzsche:rikyu = 36:74:16 起点) が連続 3 run で
      ±20% に flat 化、いずれか先到達。
    - **論理式**: `LoRA 発火 = (baseline floor 維持: self_rep ≤ 0.10 AND
      cross_echo ≤ 0.10 AND bias_fired ≥ 0.5556) AND ((a) OR (b))`

- **採用**: hybrid (上記)
- **根拠**:
  - baseline 数値 cite: `.steering/20260425-m7-beta-live-acceptance/baseline.md` L36-42
  - ζ 数値 cite: `.steering/20260426-m7-slice-zeta-live-resonance/run-01-zeta/run-01.zeta_live_analysis.json` L36-45
  - L6 ADR D1: `.steering/20260424-steering-scaling-lora/decisions.md` L6-44
  - 実態予測: ζ 起点で dialog_turn=18 → 500/persona 到達には ~83x 必要
    (= ~150,000s live)。現実的には v2 の divergence 停滞 trigger が
    先行発火する見込み。M8 spike で連続 run 計測体制を整備後、v2 trigger の
    閾値 (±20%) 妥当性を再評価する。

- **トレードオフ**: v1 単独だと unreachable で M9 が永遠に着手できない。v2 単独だと
  baseline regression を見逃すリスク。AND/OR の論理結合で両リスクを最小化したが、
  v2 閾値 (±20%) は 1 サンプルからの外挿で根拠が弱い。

- **影響範囲**: `m9-lora-training-pipeline` 着手判定、`m8-baseline-quality-metric`
  の連続 run 機能要件、`m8-affinity-dynamics` (belief mutation) への
  divergence 計測拡張。

- **見直しタイミング**: ζ 後継 run (n≥3) で divergence 比率が観測でき次第、
  v2 閾値 (±20%) を実測値で再校正。

- **次アクション**: `tasklist.md` データ閾値セクション [D1] 3 項目。

---

## D2. persona 別 base model + adapter rank + dataset 構成

- **判断日時**: 2026-04-28
- **背景**: LoRA 適用時の base model / adapter rank / 訓練 dataset の構成を確定する
  必要がある。MASTER-PLAN は qwen3:8b base + vLLM --enable-lora を確定 (L48, L268)
  しているが、rank・dataset format 未定。
- **現状**: Ollama 上で qwen3:8b 実績あり。M8 `m8-episodic-log-pipeline` (PR #88
  merge 済) で dialog_turn 完全永続化、reasoning_trace も episodic_memory と
  並行して記録される。Parquet export は M9 scope に含まれる
  (`.steering/20260425-m8-baseline-quality-metric/design.md` L133)。

- **選択肢**:
  - **v1 (保守延長)**: 全 persona 共通 `qwen3:8b` base + 統一 adapter rank
    (r=8, α=16, 文献標準)。dataset は episodic_memory 全 row (201 ζ 実測,
    0.112 rows/sec) を persona でフィルタしてそのまま SFT 形式に変換。
  - **v2 (前提覆し)**: persona 別に **rank を非対称化**。reasoning_trace 比
    36/74/16 (kant/nietzsche/rikyu) を「学習信号量」と解釈し、信号量に
    **反比例** で rank 配分 (例: rikyu r=16 / kant r=8 / nietzsche r=4)。
    少データ persona ほど rank を増やして overfit 余地、過剰生成 persona は
    rank を絞って collapse 防止。dataset は episodic_memory 単独ではなく
    `dialog_turns` (18 件、ζ db_summary L8, DB row count) +
    `reasoning_trace` (126 件、ζ jsonl.summary envelope) 結合を必須化。
  - **hybrid (採用)**:
    - v1 から: base model 共通 (qwen3:8b)、初期 adapter rank は **r=8 統一**
      (vLLM --enable-lora 確定との整合、llm-inference Skill 参照)。
    - v2 から: dataset format は **dialog_turn + reasoning_trace 結合必須**
      (episodic_memory 単独では会話文脈を欠く)。loss curve を persona 間で
      比較し、>2x 乖離が観測された時のみ rank 再配分 (M9 spike で実装)。

- **採用**: hybrid (上記)
- **根拠**:
  - vLLM stack cite: `.steering/20260418-implementation-plan/MASTER-PLAN.md` L48, L268
  - Parquet scope cite: `.steering/20260425-m8-baseline-quality-metric/design.md` L133
  - ζ 数値 (reasoning_trace 36/74/16, dialog_turn=18) cite:
    `.steering/20260426-m7-slice-zeta-live-resonance/run-01-zeta/run-01.zeta_live_analysis.json` L36-45
  - ζ episodic_memory rows=201:
    `.steering/20260426-m7-slice-zeta-live-resonance/run-01-zeta/run-01.db_summary.json` L4

- **トレードオフ**: rank 非対称化を初期から採用すると実験コストが 3x 化。統一
  r=8 → 観測後再配分 の段階方式は初期コストを抑える代わりに、最初の M9 run
  結果が persona 間で歪む可能性がある。

- **影響範囲**: `m9-lora-training-pipeline` 設計、`m9-inference-vllm-adapter`
  実装 (rank パラメータ受け入れ可能性)、PEFT vs unsloth 選定 spike (M9 内別 ADR)。

- **見直しタイミング**: M9 first run の loss curve で persona 間 >2x 乖離が
  観測された時点で rank 非対称化 ADR を別途起票。

- **次アクション**: `tasklist.md` Tool/インフラセクション [D2] 4 項目。

---

## D3. agent 数拡張 (3 → N) 判断基準

- **判断日時**: 2026-04-28
- **背景**: 現在 3 persona (Kant / Nietzsche / Rikyu)。L6 ADR D2 で 3 metric trigger
  が定義されたが、+1 persona の選定基準と上限が未定。D1 「xAI 化」要件 (成長過程
  の見える化) との接続も明確化必要。
- **現状**: ζ run-01-zeta で `alerts: []` (`run-01.scaling_metrics.json`)、3 metric
  すべて healthy 側に留まる。M1 (pair_information_gain) = 0.6862 bits / max 1.585
  = **43%** (threshold 30% より上 = healthy)、M2 (late_turn_fraction) = 0.333
  (threshold 0.6 より下 = healthy)、M3 (zone_kl_from_uniform) = 0.7985 bits /
  max 2.322 = **34%** (threshold 30% より上だが余裕約 4% のみ = healthy だが
  境界近接)。trigger 発火は M1 < 30%、M2 > 60%、M3 < 30% のいずれか。+1 persona
  投入は M3 余裕薄を理由に保留状態。4th 候補仮説「agora 主体」は profile.md L195
  に記録あり。VRAM 16GB G-GEAR で N=3 で 13GB 使用、N=4 まで余裕あり、Ollama
  並列上限 4。

- **選択肢**:
  - **v1 (保守延長)**: L6 D2 の「3 維持 + scaling trigger metric」を継承。
    M1 (pair_information_gain < 30% × log₂(C(N,2))), M2 (late_turn_fraction
    > 0.6), M3 (zone_kl < 30% × log₂(5) = 0.697) のいずれか発火で +1。ζ 実測
    では `alerts: []` (M1=43% / M2=33% / M3=34% すべて healthy bands 内)
    だが M3 は threshold 30% から 4% しか余裕がない → +1 を保留、追加 long-run
    で再評価。
  - **v2 (前提覆し)**: scaling trigger を metric ではなく **「観察者の盲点」起点**
    に変える。3 persona 構成は dialog pair が C(3,2)=3 で全 pair が常時可視
    なので「観察 demand を超える pair 数」を新指標に: pair が 4 以上 (= N≥4)
    になると人間 observer が同時追跡不能。+1 は metric ではなく研究者の問い
    (D1 xAI 化) に紐付け、「agora 主体」候補は仮説駆動で実験的投入。
  - **hybrid (採用)**:
    - v1 から: M1+M3 metric trigger を **必要条件** (一つも超過していなければ
      +1 不可)。
    - v2 から: metric 超過後の +1 候補選定は metric ではなく仮説 (例:
      「agora 占有による zone 多様性回復」) で行う。
    - **N 上限 4** (Ollama 並列 4 / VRAM 16-13=3GB の物理制約、L6 ADR D2 +
      llm-inference Skill cite)。

- **採用**: hybrid (上記)
- **根拠**:
  - L6 ADR D2 cite: `.steering/20260424-steering-scaling-lora/decisions.md` L46-86
  - ζ 実測値 cite (alerts=[], M1=43% / M2=33% / M3=34%):
    `.steering/20260426-m7-slice-zeta-live-resonance/run-01-zeta/run-01.scaling_metrics.json`
  - profile.md M8 spike 4 sample cite:
    `.steering/20260425-m8-scaling-bottleneck-profiling/profile.md` L156-158
    (M1 range 0%-37.5%, M2 range 0%-33.3%, M3 range 31.0%-42.9%)
  - 4th 候補 cite: `.steering/20260425-m8-scaling-bottleneck-profiling/profile.md` L195
  - D1 xAI 元発言: `.steering/20260422-m6-observatory-carryover/requirement.md` L5-9
  - VRAM/並列制約 cite: `.steering/20260424-steering-scaling-lora/design.md` §1
  - 現時点判断: ζ で全 metric healthy だが M3 余裕薄 (34% vs 30% threshold、
    +4% のみ) → 4th 投入は **保留**、M9 着手前に long-run で M3 再計測。

- **トレードオフ**: metric AND 仮説 の論理積を要求するため、+1 タイミングは
  保守的になる。観察者の問いが metric 発火に追いつかない場合、+1 が遅延する
  リスク。

- **影響範囲**: `m9-persona-expansion` (新規 task 候補)、`personas/*.yaml` 追加、
  `integration/dialog.py` の N 上限 hardcode 削除、orchestrator scaling 設計。

- **見直しタイミング**: M3 long-run 計測で 34% → 25% 以下に収束した場合、
  4th 投入の必要性自体が消滅 → ADR 取り下げ。逆に M1 が 43% → 30% 未満に
  入った場合、+1 候補選定 ADR を別途起票。

- **次アクション**: `tasklist.md` Agent 拡張セクション [D3] 3 項目。

---

## D4. player ↔ agent dialog 開放判断基準 (M11 整合)

- **判断日時**: 2026-04-28
- **背景**: D2 (04/22) で「対話できるようにするか否か」が問われた。M11 計画は
  L6 ADR D3 で session_phase enum (autonomous / q_and_a / evaluation) を導入
  済だが、M9 着手前に M11 開放条件と scope を確定する必要がある。
- **現状**: L6 D3 で session_phase 3 値定義、`m8-session-phase-model` spike で
  <500ms 往復遅延達成が要件。M11 は player 着手ではなく評価層として位置付け
  (L6 ADR D3)。

- **選択肢**:
  - **v1 (保守延長)**: L6 D3 の session_phase 3 値 (autonomous / q_and_a /
    evaluation) をそのまま M11 で全開放。M9 → M10 → M11 順序固定、
    q_and_a (実対話) も含む。<500ms 往復遅延と autonomous epoch のログ汚染
    ゼロ証明を M11 prerequisite に課す。
  - **v2 (前提覆し)**: 「player」を **入力者ではなく評価層** として再定義。
    dialog 開放を「player が話しかける」ではなく「player が autonomous run
    の出力を裁定する」epoch として設計 (D1 xAI 化 = 成長過程の可視化と直結)。
    session_phase は autonomous / q_and_a / **evaluation** の 3 値だが、
    evaluation epoch では player は agent と直接対話せず、reasoning_trace
    に annotation を付与するのみ。介入混入リスクを構造的にゼロ化。
  - **hybrid (採用)**:
    - v2 から: **evaluation epoch (annotation-only)** を M11 正規定義として採用
      (autonomous claim の汚染回避を構造保証)。
    - v1 から: <500ms latency 要件と session_phase enum 3 値定義を保持。
    - q_and_a (実対話) は **M12+ 後送** し、M11 prerequisite からは外す
      (user 確認済 2026-04-28)。

- **採用**: hybrid (上記)
- **根拠**:
  - L6 ADR D3 cite: `.steering/20260424-steering-scaling-lora/decisions.md` L88-99
  - D1/D2 元発言 cite: `.steering/20260422-m6-observatory-carryover/requirement.md` L5-9
  - MASTER-PLAN §11 R12 (M11 評価層位置付け):
    `.steering/20260418-implementation-plan/MASTER-PLAN.md` L146-147
  - user 判断 (2026-04-28): q_and_a は M12+ 後送を選択 (annotation-only
    evaluation を M11 正規定義に)

- **トレードオフ**: q_and_a を後送することで M11 の対話 demo が遅延。一方、
  autonomous claim の純度 (= 観測対象として価値) は構造的に保証される。
  研究プラットフォームとしての強度を優先。

- **影響範囲**: `m11-evaluation-layer` (新規 task 候補)、
  `m8-session-phase-model` の session_phase enum 確定 (3 値維持、ただし
  evaluation 優先の旨明記)、godot_project の player UI 設計 (annotation
  入力のみで dialog 入力欄不要)。

- **見直しタイミング**: M11 evaluation epoch 実装後、xAI 化要件が annotation
  だけで満たされない (= player が agent に直接質問したい場面が頻発) と
  観測された時点で q_and_a 復活 ADR を別途起票。

- **次アクション**: `tasklist.md` M11 接続セクション [D4] 3 項目。

---

## D5. LoRA degradation rollback シナリオ

- **判断日時**: 2026-04-28
- **背景**: LoRA 適用後に persona quality が baseline より劣化した場合の
  rollback 手順が未定義。R12 (LoRA データ不足) と並ぶ M9 リスクだが、
  rollback spike は未起票 (推測: R12 範疇に統合されていた)。
- **現状**: vLLM --enable-lora が確定 (MASTER-PLAN L48, L268)。adapter swap
  rollback の機構は使えるが、発火条件と判定 metric が未定義。
  baseline (Run 1: self_rep=0.0, cross_echo=0.0, bias_fired=0.5556) は固定済。

- **選択肢**:
  - **v1 (保守延長)**: 単純な adapter swap rollback。`vllm --enable-lora` の
    adapter ファイルを差し替えるだけ、base model は不変。発火条件は M9 run の
    baseline diff で **単一 metric 超過**: self_repetition_rate > 0.10 OR
    cross_persona_echo_rate > 0.10 OR bias_fired_rate < 0.5556 のいずれか。
    検出後は手動で adapter unload。
  - **v2 (前提覆し)**: degradation を「単一 metric 超過」ではなく
    **「persona identity loss」** で定義。ζ で観測された persona 別
    reasoning_trace 比 (kant:nietzsche:rikyu = 36:74:16, 約 2.25:4.6:1) を
    「persona signature」として基準化し、LoRA 後にこの比率が崩れた (例:
    全 persona が均質化) ら rollback。metric は signature divergence
    (KL or cosine) で 1 本化。自動 rollback は禁止 (誤発火コスト大)、必ず
    人間裁定を挟む。
  - **hybrid (採用)**:
    - v1 から: **adapter swap 機構 (vLLM --enable-lora)** を rollback
      実装基盤に採用。
    - v2 から: **persona signature divergence** (ζ 36:74:16 起点、KL or cosine)
      を検出 metric に採用。発火は **人間裁定必須** (自動 unload 禁止)。
    - 発火条件 (AND): (a) v1 の baseline floor 超過 (self_rep > 0.10 OR
      cross_echo > 0.10) AND (b) v2 の signature divergence > **暫定閾値 0.5**
      (M9 spike で確定)、両条件 → 人間裁定 → adapter unload。

- **採用**: hybrid (上記)
- **根拠**:
  - vLLM adapter swap cite: `.steering/20260418-implementation-plan/MASTER-PLAN.md` L48, L268
  - baseline 数値 cite: `.steering/20260425-m7-beta-live-acceptance/baseline.md` L36-42
  - signature 起点 cite (reasoning_trace 36/74/16):
    `.steering/20260426-m7-slice-zeta-live-resonance/run-01-zeta/run-01.zeta_live_analysis.json` L36-45
  - L6 ADR D1 (defer-and-measure 哲学):
    `.steering/20260424-steering-scaling-lora/decisions.md` L6-44
  - **D1 との関係**: D1 の baseline floor (self_rep > 0.10 等) は **LoRA 適用
    gate** (適用前 reject)、D5 の baseline floor 超過は **LoRA 適用後の rollback
    trigger**。同じ floor 数値を時系列上の異なる decision point で再利用する
    (gate → 適用 → 監視 → rollback)。

- **トレードオフ**: AND 条件で発火が保守的になる → degradation を見逃すリスク。
  signature divergence 閾値 (0.5) は 1 サンプル外挿で根拠が弱い。M9 spike で
  実測値で再校正が必須。

- **影響範囲**: `m9-lora-runtime-swap` 設計 (adapter unload API)、
  `m9-baseline-diff-runner` (新規 task 候補、baseline vs M9 run の diff 計測)、
  rollback runbook 作成。

- **見直しタイミング**: M9 first run 後、signature divergence 実測値が
  得られ次第、暫定閾値 0.5 を再校正。誤発火 1 件以上で人間裁定の閾値も再評価。

- **次アクション**: `tasklist.md` Rollback セクション [D5] 3 項目。
