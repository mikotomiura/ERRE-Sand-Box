# 設計

> **Status: PRE-PLAN — no execution.**
> 本タスクは documentation only。実 LoRA training・vLLM 起動・persona YAML 追加は
> 含まない。M9 着手の go/no-go 判断材料を 5 ADR + prerequisites として確定する。

## §1. 実装アプローチ

採用する方針: L6 ADR (`.steering/20260424-steering-scaling-lora/decisions.md`) の
**defer-and-measure** 哲学を M9 へ発展させ、5 つの決定 (LoRA trigger / model+rank+dataset
/ agent 拡張 / player dialog / rollback) を実数値で確定する。

すべての ADR は `/reimagine` メタ手順を適用する:
- **v1 案** = 現行 L6 ADR の保守延長 (数値・方針を締める)
- **v2 案** = 前提を疑う再構成 (scope / 順序 / actor を入れ替える)
- **hybrid 採用** = v1+v2 から具体的に何を採用するか明記、cite 付き

理由: 単一エージェントの 1 発案には構造的バイアスが残る (CLAUDE.md「破壊と構築」)。
M9 は実投資コストが大きいため、起点 ADR で前提検証を二重化する。

L6 ADR の「≤20 行/節」規約は本 task で緩和する (1 ADR あたり 30-40 行見込み)。
v1/v2/hybrid 3 ブロック構造を持つため、節長は L6 の 1.5-2 倍を許容する。

## §2. スコープ

### 含むもの
- M8 episodic_log / session_phase / baseline_metric を利用する data pipeline 設計
- δ run-02 / ζ run-01-zeta 数値 baseline 起点の閾値導出
- 成長 UI / xAI 化要件 (D1 後半「説明可能 AI」) の方向性洗い出し
- L6 ADR D1 (defer-and-measure) / D2 (3 metric trigger) / D3 (session_phase enum) の M9 接続

### 含まないもの
- 実 LoRA training 実行 (M9 本体: `m9-lora-training-pipeline` / `m9-lora-runtime-swap`)
- 新 model architecture 採用 (現行 qwen3:8b base 維持を前提)
- PEFT / unsloth tool 選定の commit (情報蓄積のみ、最終決定は M9 spike)
- persona YAML 追加 (4th persona 候補は仮説段階に留める)
- Godot UI 変更 (xAI 化 UI は M10+ 別タスク)

## §3. データソース

受け入れ条件「ζ run-01-zeta 数値で照合可能」を担保する根拠表。
本 design + decisions の数値主張はすべて以下 4 source に閉じる。

| source | 内容 | 主な参照 ADR |
|---|---|---|
| `.steering/20260425-m7-beta-live-acceptance/baseline.md` L36-42 | Run 1 baseline (固定): self_rep=0.0, cross_echo=0.0, bias_fired=0.5556, turn=12, num_agents=3 | D1, D5 |
| `.steering/20260426-m7-slice-zeta-live-resonance/run-01-zeta/run-01.zeta_live_analysis.json` L36-45 | reasoning_trace per persona: kant=36 / nietzsche=74 / rikyu=16 (合計 126), 1800s/76 tick | D1, D2, D3, D5 |
| `.steering/20260426-m7-slice-zeta-live-resonance/run-01-zeta/run-01.jsonl.summary.json` | envelope counts: dialog_turn=14 (envelope), reflection_event=47, reasoning_trace=126 | D1, D2 |
| `.steering/20260426-m7-slice-zeta-live-resonance/run-01-zeta/run-01.db_summary.json` L4-8 | episodic_memory=201 (= 0.112 rows/sec), dialog_turns=18 (DB row count, ≠ envelope=14 due to dialog_close/initiate 分離) | D1, D2 |
| `.steering/20260426-m7-slice-zeta-live-resonance/run-01-zeta/run-01.scaling_metrics.json` | alerts=[], M1=43% (0.6862/1.585 bits), M2=33%, M3=34% (0.7985/2.322 bits), thresholds: M1≥30% / M2≤60% / M3≥30% | D3 |
| `.steering/20260424-steering-scaling-lora/decisions.md` L1-99 | L6 ADR D1 (defer-and-measure) / D2 (3 metric trigger) / D3 (session_phase enum) | D1, D3, D4 |
| `.steering/20260425-m8-scaling-bottleneck-profiling/profile.md` L170-201 | scaling trigger live calibration (M1=43% / M2=33% / M3=34%), agora 主体 4th 候補 | D3 |
| `.steering/20260418-implementation-plan/MASTER-PLAN.md` L48, L146-147, L268, L393 | 推論 stack (vLLM+LoRA M9+), M8/M9 タスク定義, R12 (LoRA データ不足) | D1, D2 |
| `.steering/20260422-m6-observatory-carryover/requirement.md` L5-9 | D1 / D2 元発言 (xAI 化、対話可能化) | D3, D4 |

## §4. /reimagine v1/v2 並列方法論

各 ADR (D1-D5) で以下のテンプレートを踏襲:

```
### Dn. <タイトル>

- 現状: ...
- 選択肢:
  - v1 (保守延長): ...
  - v2 (前提覆し): ...
- 採用: hybrid
  - v1 から: ...
  - v2 から: ...
- 根拠: <ζ 数値 / baseline / L6 ADR cite>
- 次アクション: <tasklist.md の対応チェックボックス>
```

v1 と v2 は **本当に異なる方向性** であること (単なる程度差ではなく前提を変える)。
hybrid は v1+v2 から具体的に何を採用するか literal で記述すること。

これは acceptance L43 の必須項目「/reimagine v1+v2 並列で hybrid 採用記録」に
相当する。

## §5. テスト戦略 (documentation 検証)

コード変更ゼロのため、検証は grep ベース:

| 受け入れ条件 | 検証コマンド | 期待 |
|---|---|---|
| 1: 5 ADR enumerated | `grep -E '^### D[1-5]\.' decisions.md` | 5 行 |
| 2: ζ 数値で照合可能 | `grep -E '126\|18\|201\|0\.112\|36\|74\|16\|43%\|34%' decisions.md` | 4 つ以上 |
| 3: v1+v2 hybrid 記録 | `grep -cE 'v1\|v2\|hybrid' decisions.md` | 15 行以上 |
| 4: prerequisites 列挙 | `grep -c '^- \[ \]' tasklist.md` | 15 以上 |
| 5: documentation only | `git diff --name-only` | 本 task 配下 3 ファイルのみ |

## §6. ロールバック計画

documentation のみなので git revert 1 コマンド:

```
git revert <commit-sha>
```

誤って M9 着手と読まれないよう冒頭 status 節に "PRE-PLAN — no execution" を明記
(本 design.md 冒頭、decisions.md 冒頭、tasklist.md 冒頭の 3 箇所)。

実 LoRA training は本 task の scope 外であるため、コード差分・モデル差分は発生
しない。差分検査:

```
git diff -- 'src/**' 'tests/**' 'godot_project/**' 'personas/**'
# → 出力なしを期待
```
