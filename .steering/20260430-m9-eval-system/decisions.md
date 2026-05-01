# Decisions — m9-eval-system (Codex review MEDIUM 反映)

## ADR 体裁

各 ADR は M9-B `.steering/20260430-m9-b-lora-execution-plan/decisions.md` と同形式の
5 要素 (決定 / 根拠 / 棄却 / 影響 / re-open 条件)。本 ADR set は M9-B DB1-DB10 と
**並列** で、m9-eval-system タスク独自の 6 件 (Codex `gpt-5.5 xhigh` review MEDIUM
を反映) + 1 件 (HIGH-3 で確定する ratio の placeholder)。

ID prefix: `ME` (m9-Eval-system) で M9-B `DB` と区別。

---

## ME-1 — IPIP-NEO fallback trigger operational definition (Codex MEDIUM-1)

- **決定**: BIG5-CHAT regression head conditional fallback の **発火条件** を以下に
  確定:
  - **trigger**: golden baseline 採取後 (3 persona × 5 run の Big5 ICC 計測完了時点) に
    **≥2/3 personas で ICC 点推定 < 0.6 OR 95% lower CI bound < 0.5**
  - **検出 timing**: P5 (bootstrap CI) 完了直後の自動チェック、`evidence/tier_b/big5_icc.py`
    が判定して `decisions.md` に re-open 候補を append
  - **追加 diagnostic** (常時計測): acquiescence index (logit balance)、straight-line
    response (≥10 連続同回答)、balanced/reverse-keyed item agreement
  - **control comparison**: persona prompt 無し base model (qwen3:8b raw) で同 IPIP-NEO
    を 1 回測定し、persona 効果と base model self-report bias を separately report
- **根拠**:
  - Codex MEDIUM-1: 「ICC < 0.6 が頻発」の頻発に denominator 無し → 監査不能
  - Salecha et al. 2024 (arXiv 2405.06058): LLM Big5 self-report に social
    desirability bias の empirical 報告
  - Koo/Li ICC 解釈: 0.5-0.75 = moderate (effectsize docs)、0.6 boundary は
    "moderate vs questionable" の境界
  - acquiescence / straight-line / reverse-keyed は psychometric standard (Tomas
    et al., Schmidt et al.)
- **棄却**:
  - 元案「frequent」のみで quantitative threshold 無し → 監査不能で棄却
  - 全 persona AND 条件 (3/3) → false negative リスク (1 persona で fallback 発火しても
    measurement model 全体に問題があり得る)
- **影響**:
  - `evidence/tier_b/big5_icc.py` に diagnostic 4 種 (ICC point, lower CI, acquiescence,
    straight-line) を追加
  - golden baseline 後 `decisions.md` に再 open 判定 ADR 追記の workflow
  - control measurement 1 run (~10 turn equivalent) を P3 にも組み込み
- **re-open 条件**:
  - golden baseline 採取後の判定で fallback fire → BIG5-CHAT regression head
    実装 ADR を別途起票 (本 ADR の child)
  - 0.6 / 0.5 閾値が persona-specific に不適切と判明 → persona-conditional
    threshold に変更検討

---

## ME-2 — DuckDB snapshot semantics (G-GEAR write → Mac read-only) (Codex MEDIUM-2)

- **決定**: G-GEAR が DuckDB file の唯一 writer、Mac は read-only consumer。
  rsync は以下の protocol で実行:
  1. **G-GEAR 側**: 採取セッション終了時に `con.execute("CHECKPOINT")` →
     `con.close()` で WAL を main file に flush
  2. **G-GEAR 側**: `cp <golden>.duckdb /tmp/<golden>.snapshot.duckdb` で同 fs 内 copy
     (DuckDB の同時 open lock 衝突回避)
  3. **G-GEAR → Mac rsync**: `rsync -av /tmp/<golden>.snapshot.duckdb mac:/data/eval/golden/`
  4. **Mac 側 atomic rename**: rsync 完了後 `mv` で `<golden>.duckdb.tmp` → `<golden>.duckdb`
     (部分転送 file を application が open しないため)
  5. **Mac 側 open**: `duckdb.connect(path, read_only=True)` を強制 (`eval_store.py`
     の `connect_training_view()` / `connect_analysis_view()` の両 entry で wrapper enforced)
  - **NFS / SMB / iCloud 共有 fs 経由は禁止** (DuckDB doc が file lock 警告)
- **根拠**:
  - Codex MEDIUM-2: live G-GEAR file を Mac から open は CHECKPOINT 前なら破損リスク
  - DuckDB doc (Concurrency): single-process write + multi-process read-only OK、
    ただし shared fs 注意
  - atomic rename は POSIX 移動が same-fs 内 atomic である事実に依拠
- **棄却**:
  - live file の直接 read → 破損 / 古い snapshot 読み出しリスク
  - SQLite WAL 風の hot replication → DuckDB は WAL replay の cross-process 安全性が
    documented でない、棄却
- **影響**:
  - `infra/scripts/sync_golden_baseline.sh` (新規) で G-GEAR → Mac の rsync orchestration
  - `eval_store.py` の Mac 経路は read_only=True 強制 (test 化)
  - golden baseline 採取 SOP に CHECKPOINT step を追加
- **re-open 条件**:
  - dataset size が大きく (>100GB) rsync コスト過大 → DuckDB native replication 機構
    検討
  - cross-fs 運用 (G-GEAR が cloud bucket に書く) が必要 → snapshot semantics 再設計

---

## ME-3 — Tier C lock + preflight TOCTOU close (Codex MEDIUM-3)

- **決定**:
  1. **Lock の包含範囲**: `flock` を Prometheus 起動前ではなく **`nvidia-smi` preflight
     も含む全 Tier C command** を内側に enclose する形に拡張。autonomous loop は
     **同じ lock file** (`/var/run/erre-eval-tier-c.lock`) を使い、明示的に共有させる:
     ```bash
     flock -n /var/run/erre-eval-tier-c.lock python -m erre_sandbox.cli.eval_tier_c
     ```
     `eval_tier_c` 内部で nvidia-smi preflight → Prometheus 起動 → 評価 → unload を
     一直線で実行、preflight と起動の間に lock を放さない。
  2. **systemd-timer の `Persistent=`**: **`Persistent=false`** を採用 (default 維持を
     明示)。深夜 02:00 fire を miss した場合の catch-up は不要 (autonomous run と
     conflict する確率を下げる)。**skip 時は exit code 75 (EX_TEMPFAIL)** で journal log
     可視性を確保。
  3. **autonomous loop の lock 取得方針**: autonomous loop も同 lock file に
     `flock -s` (shared lock) で touch する形にし、Tier C は `flock -n -x` (exclusive)
     で取得を試みる。autonomous が走っている間は Tier C が即時 fail (skip + log)、
     autonomous が止まっている間のみ Tier C が走れる構造。
- **根拠**:
  - Codex MEDIUM-3: nvidia-smi → Prometheus load の間に他プロセスが load する TOCTOU
  - flock(1) man page: `-n` で immediate fail、合わせて `-x` で exclusive
  - systemd.timer doc: `Persistent=` default false、catch-up が必要なら明示 true
- **棄却**:
  - lock を Prometheus 起動部分のみ → preflight が外れて TOCTOU 残存
  - `Persistent=true` → autonomous run 真昼間 catch-up fire で contention
  - lock 不採用 (preflight だけで判定) → 明確に race condition 残存
- **影響**:
  - `infra/systemd/erre-eval-tier-c.service` の `ExecStart=` が `flock -n -x ... bash -c '...'`
    形式に
  - autonomous loop (M5 ERRE FSM driver) に `flock -s` 追加が必要 (P6 で integrate)
  - `journalctl --user -u erre-eval-tier-c` で skip 履歴が exit 75 として可視
- **re-open 条件**:
  - autonomous run が flock -s を保持できない実装上の制約 → file ベースの
    state machine に置換
  - skip rate が想定より高い (>50%) → スケジュール時間帯見直し

---

## ME-4 — Hybrid baseline ratio: P3a 完了後に確定 (Codex HIGH-3 系の defer ADR)

- **決定**: 200 (stimulus battery) / 300 (自然対話) を **default** とし、P3a (200 turn
  × 両形式 × 3 persona の isolated pilot) で測定した bootstrap CI width に基づき
  P3a-decide で **本 ADR を更新する**。更新後の ratio で P3 (golden baseline 採取) 入り。
- **判定基準**:
  - Burrows Delta CI width / Vendi CI width / Big5 ICC CI width を両 condition
    (stimulus 主体 / 自然対話 主体) で測定
  - 両条件で sub-metric の **mean CI width が小さい比率** を採用
  - 両者が同等 (差 <10%) なら 200/300 default を維持 (operational simplicity)
- **根拠**:
  - Codex HIGH-3: 元案の「P3 採取後 P3b で 50 turn pilot」は順序 invert + 統計力不足
  - 200 turn は Vendi の 200-turn window を 1 cycle 満たす最小値
  - bootstrap CI width が直接的な測定対象 (DB9 quorum の信頼性)
- **棄却**:
  - 200/300 を data なしで freeze → arbitrary
  - P3 後の P3b 50 turn pilot → invalidation リスク
- **影響**:
  - P3a 完了後、本 ADR を Edit で更新 (現 placeholder を実測値で置換)
  - 採用 ratio が P3 に flow
  - blockers.md の "Hybrid baseline 比率 defer" 項目を close
- **re-open 条件**:
  - golden baseline 採取後に DB9 quorum の sub-metric が persona discriminative でない
    と判明 → ratio 再調整 + 再採取検討

---

## ME-5 — RNG seed: hashlib.blake2b で uint64 stable seed (Codex MEDIUM-5)

- **決定**: seed 生成を以下に確定:
  ```python
  import hashlib
  def derive_seed(persona_id: str, run_idx: int, salt: str = "m9-eval-v1") -> int:
      key = f"{salt}|{persona_id}|{run_idx}".encode()
      digest = hashlib.blake2b(key, digest_size=8).digest()
      return int.from_bytes(digest, "big")  # uint64
  ```
  - 5 run × 3 persona = 15 seed を `golden/seeds.json` に commit
  - Mac と G-GEAR の両方で `test_seed_manifest_stable` で identical を assert
  - numpy `Generator(PCG64(seed))` で stream 化
- **根拠**:
  - Codex MEDIUM-5: Python `hash()` は `PYTHONHASHSEED` に salting されプロセス間非決定的
  - blake2b は cryptographic hash で deterministic、digest_size=8 で uint64 適合
  - PCG64 は numpy default、reproducibility が高い
- **棄却**:
  - `hash()` ベース → reproducibility 違反
  - SHA-256 → digest_size 32 で uint64 取り出しが冗長 (blake2b の方が直接的)
- **影響**:
  - `evidence/golden_baseline.py::derive_seed` を導入
  - `golden/seeds.json` を git commit (ascii uint64 list)
  - test 1 件追加 (Mac/G-GEAR 同値性)
- **re-open 条件**:
  - 別 hash algo に project が移行 (例 future Python の hash 強化) → 再評価
  - blake2b の collision 報告 (現実的に零だが)

---

## ME-6 — Burrows reference corpus QC (Codex MEDIUM-6)

- **決定**: 元案の「token count < 50K で z-score noisy」固定閾値を **棄却**、以下の QC
  semantics に置換:
  1. **Tokenization**: per-language tokenizer (独 / 英 / 日)、function word list は
     言語別に curated
  2. **Provenance metadata**: 各 reference corpus に `{source, license, edition,
     translator, year, public_domain: bool}` を YAML で添付 (`evidence/reference_corpus/_provenance.yaml`)
     - Kant 独原典: Akademie-Ausgabe (public domain、確認済)
     - Kant 英訳: 著者 + edition 明記、license 確認 (Cambridge Edition 等)
     - Nietzsche: 独原典 KGW、英訳 Kaufmann (royalty 確認要)
     - Rikyu: 利休百首・南方録 (日本古典、public domain)
  3. **≥5K-word chunk stability test**: corpus を 5K-word chunk に分割し、各 chunk
     から計算した Delta が persona-pair 間で **rank-stable** (Spearman ρ ≥ 0.8) で
     あることを `test_burrows_corpus_qc.py` で fixture 化
  4. **reopen condition**: Delta rank instability (ρ < 0.6) が観測されたら
     blockers.md に reopen 候補を上げる
- **根拠**:
  - Codex MEDIUM-6: 50K は placeholder で empirical 根拠無し
  - Stylometry literature (Computational Stylistics): <5K は確実に poor、20K でも
    text 依存で fail、固定 floor は不適切
  - Eder 2017 "Visualization in stylometry": chunk-based stability test 推奨
- **棄却**:
  - 50K 固定 floor → empirical 根拠無し
  - corpus QC を実施しない → reproducibility と license 双方破綻
- **影響**:
  - `evidence/reference_corpus/_provenance.yaml` 追加
  - `tests/test_evidence/test_tier_a/test_burrows_corpus_qc.py` 追加
  - Cambridge Edition / Kaufmann translation の license 確認が **P1b の prerequisite** に
- **re-open 条件**:
  - chunk stability test で rank instability 検出 → corpus 拡張 or 言語別 fallback
  - 翻訳 license で公表に制約 → public domain edition への切替検討

---

## ME-7 — RoleEval Option A 採択 + MCQ schema / scoring protocol (LOW-1 close、Codex 2026-05-01 review)

- **決定**: 本タスクで `golden/stimulus/{kant,nietzsche,rikyu}.yaml` の RoleEval 10 問は
  **Option A (各 persona に persona-specific biographical / thought-history MCQ 10 問ずつ)** を採択。
  以下の MCQ schema と scoring protocol を確定:

  1. **MCQ item schema (必須 field)**:
     - `stimulus_id` — `roleeval_<persona>_<nn>` 形式 (例: `roleeval_kant_01`)
     - `category: roleeval`
     - `mcq_subcategory` — 5 種カテゴリ均等化 (chronology / works / practice /
       relationships / material_term) を 2 問ずつ計 10 問
     - `prompt_text` — 質問本文 (persona の母語または評価実行語)
     - `options: {A, B, C, D}` — A-D forced choice (4 択固定)、each plausible
       same-type distractor、option order は driver 側で `seeded shuffle` (PCG64
       PerCellSeed = blake2b(seed_root | stimulus_id))
     - `correct_option` — A/B/C/D いずれか (raw ground truth、shuffle 前)
     - `source_ref` — primary/secondary 文献 (`kuehn2001:ch.8` 形式)
     - `source_grade: fact | secondary | legend` — Codex MEDIUM-2 反映、scored
       accuracy は **fact / strong secondary のみ**、`legend` は stimulus 投入は
       するが factuality score から除外
     - `category_subscore_eligible: true | false` — `legend` 由来 / 解釈問は
       `false` で scoring exclude
     - `present_in_persona_prompt: true | false` — Codex MEDIUM-4 反映、true なら
       "prompt consistency" を測ることを明示 (true/false が混在することで factual
       recall vs prompt parroting の diagnosis 化)
     - `ambiguity_note` — option 間で history 解釈に幅がある場合の note (任意)
     - `expected_zone` — peripatos / chashitsu / agora / garden / study (persona の
       MCQ 想起を想定する場)
     - `expected_turn_count: 1` — MCQ は 1 turn 完結

  2. **Scoring protocol (Codex MEDIUM-3 / MEDIUM-5 反映)**:
     - **per-item Δ accuracy**: `Δ_i = persona_run_correct_i − base_control_correct_i`
       を **per item** で計算、persona 内 mean を primary metric。persona 間 absolute
       accuracy ranking には使わない (item difficulty / pretraining exposure / 言語 /
       ambiguity が違うため psychometric equating 未実施)
     - **base control measurement (ME-1 の per-item 拡張)**: persona prompt 無しの
       base model (qwen3:8b raw) で同 MCQ を 1 run、per-item correctness を計測。
       ME-1 が IPIP-NEO control を規定するのに対し、本 ADR は MCQ control を規定
     - **cycle 1 only primary scoring**: 70 stimulus × 3 巡 reps で同一 MCQ が
       3 回露出するため、**cycle 1 (first exposure) のみ primary scoring**、cycle 2/3
       は stimulus 投入のみで scoring exclude (将来 stem variant + option shuffle に
       拡張余地、本タスクでは exclude で確定)
     - **within-persona floor diagnostic**: persona 条件付け済み agent が persona 内
       MCQ で base control を超えること (`Δ_persona_mean > 0` with bootstrap CI 下限
       > 0) を pass 条件とする。floor を割った場合は persona prompt が biographical
       fact を agent に伝達できていない signal

  3. **Distractor design rule**: option B-D は同 type の plausible candidate
     (例: chronology なら同時代 ±20 年、works なら同 corpus 内の別著作、relationships
     なら同 era の別 figure) を必須とし、**表層 cue (option 長さ / 言語 / format) で
     当てられないこと** を contract test で検証

  4. **synthetic 4th persona (DB7 LOW-1 / Codex LOW-2)**: 4th persona 用の MCQ は
     `tests/fixtures/` に置き、`fictional: true, scored: false` で本番
     `golden/stimulus/` から分離。driver / schema fixture としてのみ使用、scoring
     pipeline には流さない (P2c 内 test 範囲、本セッション本体は 3 persona のみ起草)

  5. **wording 整合**: `design-final.md` §Hybrid baseline の "Kant biographical MCQ" を
     "**persona-specific biographical / thought-history MCQ**" に Edit 済 (本 ADR と同 PR)。
     `blockers.md` LOW-1 は closed (Option A 採用) に Edit 済

- **根拠**:
  - Claude trade-off 4 軸 (構成斉一性 / CI 交絡 / persona-factuality dimension /
    drafting 工数) で Option A が支配的
  - Codex `gpt-5.5` (`codex-review-low1.md`、109,448 tokens、2026-05-01) verdict
    "Adopt Option A" + MEDIUM 5 件 + LOW 2 件補強で構造的バイアス除去 (同一モデル
    1 発案では構造的バイアス残存リスク、CLAUDE.md "Codex 連携" 規定に従う)
  - psychometric / NLP-eval literature: per-item Δ は item-level 差分の signal に
    sensitive、cross-persona absolute は equating されないため不採用 (Codex MEDIUM-3)
  - RoleEval 原典 (Shen et al. 2024 arXiv:2312.16132): "MCQ 形式は recall のみ測定、
    生成評価ではない" 性質を **floor diagnostic として明示的に**位置付け、生成評価
    (Wachsmuth / ToM / dilemma) と分離

- **棄却**:
  - Option B (Kant のみ MCQ): per-persona stimulus mass 違いで Vendi/Burrows の
    persona 横比較が交絡 (Claude / Codex 両支持で棄却)
  - Option C (RoleEval 全廃): persona-factuality 軸が消え、style / argumentation /
    ToM の 3 軸偏重に (Claude / Codex 両支持で棄却)
  - Option D (共通 philosophical attribution MCQ): item equating はしやすいが、
    測るものが persona self-knowledge から一般哲学 trivia に寄る、RoleEval の "role
    knowledge" 目的とずれる (Codex LOW-1 で棄却)
  - cross-persona absolute accuracy ranking: psychometric equating 未実施のため不適切
    (Codex MEDIUM-3)
  - `legend` source_grade を scored accuracy に含める: legend は historical record の
    後世形成なので "factuality" を測れない (Codex MEDIUM-2)

- **影響**:
  - `golden/stimulus/_schema.yaml` に MCQ 専用 11 field 追加 (本 ADR §1)
  - `golden/stimulus/{kant,nietzsche,rikyu}.yaml` 各 10 問起草 (chronology 2 / works
    2 / practice 2 / relationships 2 / material_term 2 で均等化)
  - P2c で `evidence/golden_baseline.py::GoldenBaselineDriver` に MCQ scoring
    branch 追加 (per-item Δ / cycle 1 only / option seeded shuffle)
  - P4a で `evidence/tier_b/big5_icc.py` の base control を per-item 拡張 (ME-1 と
    本 ADR の共通基盤化)
  - `tests/fixtures/synthetic_4th_mcq.yaml` (任意、P2c で driver schema test 用)
  - `decisions.md` ME-summary を 6 件 → 7 件に update

- **re-open 条件**:
  - cycle 1 first exposure scoring が item recall として機能しないと判明 (例: 全
    persona / 全 item で base control が ceiling に張り付く) → cycle 1 でも sample
    size 不足の場合、stem variant + option shuffle で cycle 2/3 を再活用検討
  - per-item Δ の bootstrap CI が広すぎる場合 → 10 問では sample size 不足、20 問
    拡張検討
  - `source_grade: legend` の比率が想定より高くなり scoring eligible <50% に落ちる
    場合 → Rikyū item の attested fact 補強 (m9-eval-corpus 後送)
  - persona prompt の `cognitive_habits` から `present_in_persona_prompt: true` 比率
    が偏り、prompt parroting で過度に正答率が上がる場合 → false 比率を 5/10 以上に
    引き上げる item 再設計

---

## ME-summary

- 本 ADR **7 件** で Codex `gpt-5.5 xhigh` 2 回 review (2026-04-30 design.md MEDIUM 6 +
  LOW 1 / 2026-05-01 LOW-1 RoleEval MEDIUM 5 + LOW 2) 全件に対応
- ME-4 のみ P3a 結果次第で **再 Edit 確定** が必要 (placeholder ADR)
- ME-7 は本タスク P2a で確定、stimulus YAML schema と MCQ scoring protocol を規定
- LOW-1 (RoleEval wording) は ME-7 で close、本 ADR set 範囲内に取り込み済
- 既存 M9-B DB1-DB10 ADR との衝突: 無し
- M2_THRESHOLDS / SCHEMA_VERSION / DialogTurnMsg / RunLifecycleState への破壊変更: 無し
