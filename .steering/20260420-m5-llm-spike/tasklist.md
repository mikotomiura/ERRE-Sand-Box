# タスクリスト — m5-llm-spike

## 準備

- [x] `.steering/20260420-m5-planning/decisions.md` 判断 4 (throwaway 方針) を再読
- [x] `personas/{kant,rikyu}.yaml` の default_sampling 値を確認
- [x] `persona-erre` Skill §ルール 2 の ERRE mode delta 表を確認
- [x] Ollama の稼働確認 (`qwen3:8b` + `nomic-embed-text` ロード済)

## 環境準備

- [x] `.gitignore` に `_ad_hoc/` を追加 (`.gitignore:54`)
- [x] `_ad_hoc/` ディレクトリ作成 + `_ad_hoc/README.md` に動かし方メモ
- [x] `_ad_hoc/personas_snapshot.py` — YAML を dict として読む最小 loader

## Spike 実装 (commit 対象外)

- [x] `_ad_hoc/spike_dialog.py` 作成:
  - [x] `ollama_generate(prompt, options)` の薄い wrapper (httpx + `/api/generate`)
  - [x] `build_spike_system_prompt(persona, addressee, mode, zone)` (dialog 専用最小版、per-persona 言語ヒント付き)
  - [x] `build_spike_user_prompt(transcript, next_turn_index)`
  - [x] `run_dialog(persona_a, persona_b, mode, zone, max_turns, options)` 主ループ
  - [x] JSONL で `_ad_hoc/spike-logs/<timestamp>-<mode>-<axis>.jsonl` に turn ごと記録
- [x] qwen3:8b の `think=false` 発見 (thinking model のため default では空応答になる)

## Spike 実行 (知見収集)

### 軸 1: utterance 長

- [x] Kant / Rikyū で `num_predict=60 / 80 / 120` を 2 run × 4 turn ずつ (peripatos)
- [x] char 数分布を `decisions.md` 実機統計サマリに記録 (Kant median=20 max=118, Rikyū median=15 max=35)

### 軸 2: 停止語彙

- [x] 全 80 turn ログから stage direction / `{` / `Kant:` / `"` の混入を検索 → いずれも 0 件
- [x] 改行連続の multi-utterance 混入を 2/80 件観察 → `stop=["\n\n"]` で単発化
- [x] 最終的な stop tokens を `decisions.md` 判断 2 に記録

### 軸 3: 温度帯

- [x] peripatos / chashitsu / deep_work の 3 mode × Kant/Rikyū の 2 persona で合成 temperature を算出
- [x] 各組み合わせで 2 run × 4 turn で実行、幻覚的破綻は 0 件
- [x] 低温 mode (chashitsu/zazen) で反復率が上がる観察を `decisions.md` 判断 3 に記録

### 軸 4: turn_index 上限

- [x] Kant ↔ Rikyū (peripatetic, 10 turns) で 1 run
- [x] turn ≥ 2 で完全反復が始まる挙動を観察
- [x] anti-repeat 指示で novel rate 100% に改善する recipe を確立 (判断 4)

### 軸 5: 幻覚パターン

- [x] 全 80 turn ログから 5 パターン (言語崩壊 / 完全反復 / 近傍言い換え / 過短 / 改行連続) を手動カウント
- [x] 頻度と具体例を `decisions.md` 判断 6 に列挙

## 集約

- [x] `decisions.md` を書き起こす (requirement.md ゴール 5 項目 + 後続タスクで使う値のまとめ 2 ブロック)
- [x] 各項目に実機統計 (80 turn, 17 session, 54% / 59% / 2/80 等) の根拠を紐付け
- [x] 後続 `m5-contracts-freeze` が参照すべき field / default 値を明示
- [x] 後続 `m5-dialog-turn-generator` が参照すべき options / prompt 構造を明示
- [x] M5 planning 判断 1 の C 案退避は**不要**と判定 (判断 7)

## 完了処理

- [x] `git status` が `.gitignore` + `.steering/20260420-m5-llm-spike/` のみ変更状態
      であることを確認 (`_ad_hoc/` は ignored)
- [x] tasklist.md の全項目チェック
- [ ] `feature/m5-llm-spike` branch 作成
- [ ] commit → PR 作成 → self-review → merge
- [ ] MEMORY.md 更新 (qwen3:8b の think=false 要件など feedback memory 候補あり)

## 制約・リマインダ

- spike コードは `src/erre_sandbox/` に import されない (throwaway の原則)
- クラウド LLM 禁止 (qwen3:8b local のみ)
- `main` 直 push 禁止、feature branch + PR
- 既存 525 test に触れない (spike は pytest を走らせない)
- `_ad_hoc/` は `.gitignore` で除外 (誤 commit 防止)
