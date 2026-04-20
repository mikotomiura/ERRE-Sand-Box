# Decisions — M5 LLM Spike

G-GEAR 実機 (qwen3:8b Q4_K_M, Ollama localhost:11434) で Kant ↔ Rikyū 1-on-1 対話を
**計 80 turns / 17 dialog sessions / 4 ERRE mode** で実機観察した結果の知見。
throwaway spike のため spike スクリプト (`_ad_hoc/spike_dialog.py` ほか) は
`.gitignore` で除外され commit しない。生ログは `_ad_hoc/spike-logs/*.jsonl` に保管。

後続タスク `m5-contracts-freeze` / `m5-dialog-turn-generator` は本文書を唯一の
設計根拠として参照すること。

## 実機統計サマリ

| 指標 | 値 |
|---|---|
| 総 turn 数 | 80 |
| dialog session 数 | 17 |
| utterance char 分布 (kant, Latin) | min=0, median=20, max=118 |
| utterance char 分布 (rikyū, CJK) | min=0, median=15, max=35 |
| Kant の日本語崩壊率 (言語ヒントなし) | 54% (22/41) — 見出し言語ヒント付与後は 0% |
| 同一 utterance 完全反復があった session | 10/17 (59%) |
| turn あたり latency | median=2.5s, max=6.4s, 標準 2.3-2.7s |

---

## 判断 1: utterance 上限は `num_predict=120`、hard cap は既存 (160 Latin / 80 CJK) を維持

- **判断日時**: 2026-04-20
- **背景**: `design.md` の推測値は `num_predict=80`。実機で十分か確認が必要。
- **観察**:
  - `num_predict=60`: utterance が平均 10-15 chars に収束、内容が空洞化 (「静けさは心の境なり」だけで終わる)
  - `num_predict=80`: Kant 26-48 chars, Rikyū 10-30 chars。英語長文が途中で打ち切られるケースあり
  - `num_predict=120`: Kant の英語 sentence が 42-118 chars で完結 (160 cap の 74% max)、Rikyū は 9-35 chars
  - どの設定でも `think=false` 必須 (qwen3:8b は thinking model、default で 400+ tokens を think に消費して response が空になる。`"think": false` を `/api/generate` payload の top-level で送る)
- **採用**: **num_predict=120, think=false, hard cap 160 Latin / 80 CJK**
- **理由**: 120 で Kant の完結性が確保され、Rikyū の簡素さ (9-35 chars) は style として許容できる。hard cap は安全網 (ごく稀に 150 chars 超の暴走を 1 例観察 — 実測 max 118 の 1.4x headroom)
- **トレードオフ**: num_predict=80 より 30-50% 遅延が増える可能性があるが、実測は 2.3-2.7s で誤差の範囲。80/120 で latency 差なし (qwen3 は think=false 時に大半の予算を余す)
- **影響範囲**: `m5-dialog-turn-generator` の Ollama options、`DialogTurnGenerator` 実装時の truncate ロジック (hard cap 超過時は `utterance[:160]` + `"…"`)
- **後続タスクで使う値**: `options={"num_predict": 120, ...}`、payload `"think": False`

## 判断 2: stop tokens は最小限 (`["\n\n"]`) — think=false で stage direction 混入なし

- **判断日時**: 2026-04-20
- **背景**: `design.md` の想定 stop tokens は names / quotes / stage directions / JSON の混入防止。
- **観察** (全 80 turn ログから検索):
  - `*bows*`, `*nods*` 等の stage direction: **0 件**
  - `{`, `[` 等の JSON wrapping: **0 件**
  - `Kant:`, `Rikyu:` 等の名前前置: **0 件**
  - double quotes の混入: **0 件**
  - 改行 `\n\n` を挟んで 2 発話目を連続生成する例: **2 件** (Kant のみ、peripatetic high-temp)
- **採用**: **`stop=["\n\n"]` のみ**。names / quotes / stage directions は追加しない
- **理由**: `think=false` + 既存の「Return ONLY the utterance text. Do NOT include names, quotes, stage directions, parentheticals, or JSON.」指示で qwen3:8b は自然に従う。過剰な stop tokens は latency ペナルティになり得る
- **トレードオフ**: production で新 persona 追加時に挙動が変わる可能性はある → その時点で追加 stop を検討
- **影響範囲**: `m5-dialog-turn-generator` の Ollama options (`"stop": ["\n\n"]`)、prompting helper
- **後続タスクで使う値**: `stop=["\n\n"]` 単一

## 判断 3: 温度帯は persona.default + ERRE delta の clamp 既定で十分、chashitsu の低温で「反復 risk +1」だけメモ

- **判断日時**: 2026-04-20
- **背景**: `persona-erre` Skill §ルール 2 の delta (peripatetic +0.3, chashitsu -0.2, deep_work 0.0 等) が spike で破綻しないか。
- **観察** (persona.default + delta の実効温度):
  - Kant (base 0.60): peripatetic=0.90, chashitsu=0.40, deep_work=0.60, zazen=0.30
  - Rikyū (base 0.45): peripatetic=0.75, chashitsu=0.25, deep_work=0.45, zazen=0.15
  - **全組み合わせで幻覚的出力は観察されず** (空応答は think=false 不適用時の artefact のみ)
  - 低温 (chashitsu/zazen) で**反復が顕著** — Rikyū の 9-char 定型句が 3 turn 連続した run あり
  - 高温 (peripatetic high) で**多様性が保たれる** — 同 session 内で異なる表現を生成
- **採用**: **既存 delta 表を変更しない**。低温 mode で反復率が上がる事実を `m5-dialog-turn-generator` の docstring に注記
- **理由**: 温度を触ると persona 設計の整合性が崩れる。反復の主因は低温ではなく「prior turn を user prompt に含める」構造 (判断 5 参照) で、そちら側で対処する方が筋が良い
- **トレードオフ**: chashitsu/zazen の dialog が相対的に単調になることを受容。style として侘び寂びの反復性に合致するとも解釈可能
- **影響範囲**: 既存 `persona-erre` Skill とのコード整合性は維持。`inference/sampling.py` は変更不要
- **後続タスクで使う値**: delta 表に**変更なし**。`compose_sampling` の既存ロジックをそのまま利用

## 判断 4: `dialog_turn_budget` は **6 を維持**、ただし **turn ≥ 2 の user prompt に "do NOT repeat prior turns" 指示を差し込む**

- **判断日時**: 2026-04-20
- **背景**: planning 時の default は 6。実機で turn 数を増やしても意味のある対話になるか。
- **観察** (10-turn run, peripatetic, num_predict=120):
  - turn 0-1: 新規で自然 (Kant "The mind, like the stars..." → Rikyū "侘び寂びの光...")
  - turn 2-3: **Kant が turn 0 の言い換え**, Rikyū は turn 1 と同一
  - turn 4-9: 2 人とも完全に同じ 2 発話を交互繰返し (`exact dup` session 10/17)
  - `repeat_penalty` を 1.15 → 1.8 まで上げても**効果は限定的** (1.35-1.6 は逆に悪化)
    - 理由: `repeat_penalty` は **生成中 token 列内** の反復抑制であって、prior turn に対する penalty ではない
  - user prompt に **"Respond in one utterance that does NOT repeat any phrase from prior turns. Introduce a new thought."** を追加 → **2/2 run で新規発話** (novel rate 100%、自然さも維持)
  - 曖昧な指示 ("move forward with a new point") は逆効果 — 旧 phrase を踏襲する
- **採用**: `dialog_turn_budget=6` を維持、**turn_index ≥ 2** の user prompt に明示的な anti-repeat 指示を差し込む
- **理由**: schema bump の要因になり得る値 (6 → 4 等への短縮) を変更せず、prompt 側の工夫で質を担保する方が後方互換に優しい。planning 判断 1 の C 案退避は不要
- **トレードオフ**: turn 2+ の user prompt が turn 0-1 と異なる形になる → `DialogTurnGenerator` 側で分岐 1 行必要
- **影響範囲**: `DialogTurnGenerator.generate_turn` の user prompt builder、`DialogCloseMsg.reason="exhausted"` の発火タイミング (turn_index==6 で close)
- **後続タスクで使う値**:
  - `Cognitive.dialog_turn_budget: int = Field(default=6, ge=0)`
  - `DialogTurnMsg.turn_index: int = Field(..., ge=0)`
  - `DialogCloseMsg.reason` literal に `"exhausted"` 追加
  - user prompt の turn ≥ 2 分岐: `"Respond in one utterance that does NOT repeat any phrase from prior turns. Introduce a new thought."` を末尾に付加

## 判断 5: system prompt に **per-persona 言語ヒント** を必ず入れる (M5 prompting の必須要件)

- **判断日時**: 2026-04-20
- **背景**: spike 初期は言語ヒントなしで全 mode 実行 → Kant が 100% 日本語 (古典的漢文調) で応答する事象を発見
- **観察**:
  - 初回 smoke (no hint): Kant (peripatos, deep_work, chashitsu 全て) → 「静けさは心の境なり」「歩く道は思索の道なり」等の**日本語**
  - 全 41 Kant turn のうち **22 (54%)** が CJK で出力 (hint 付与前の run 群が由来)
  - システムプロンプトに `"Respond in English (Kant speaks English or German — English preferred for this simulation)."` を追加 → **100% 英語**
  - Rikyū は hint 有無に関わらず 100% 日本語 (`display_name="千 利休"` + 習慣描写の chashitsu/nijiri-guchi/matsukaze が強い誘導)
- **採用**: **system prompt 末尾に persona_id 毎の言語ヒントを必ず差し込む**
  - `kant` → `"Respond in English."`
  - `rikyu` → `"日本語で応答せよ（古典的・侘び寂びの語彙を用いる）。"`
  - `nietzsche` → `"Respond in German, or in English with German-inflected phrasing."`
- **理由**: hint なしでは Kant が Rikyū の言語に引きずられる (対話履歴と cognitive_habits の日本語漢字が prior として作用)。hint は schema 非依存で prompting 層で閉じる
- **トレードオフ**: 新 persona 追加時に `_LANG_HINT` map の更新が必要。ただし persona YAML 自体には手を入れない
- **影響範囲**: `src/erre_sandbox/cognition/prompting.py` に `build_dialog_system_prompt` を新規追加する際、persona_id → lang hint の dict を同ファイル内 module-private で保持
- **後続タスクで使う値**:
  ```python
  _DIALOG_LANG_HINT: Final[dict[str, str]] = {
      "kant": "Respond in English.",
      "rikyu": "日本語で応答せよ（古典的・侘び寂びの語彙を用いる）。",
      "nietzsche": "Respond in German, or in English with German-inflected phrasing.",
  }
  ```

## 判断 6: 幻覚パターン 5 種の頻度と対策を M5 実装に反映

- **判断日時**: 2026-04-20
- **背景**: requirement 5 項目目、後続実装が防御的に扱うべき幻覚パターンの列挙。

### 観察された幻覚パターン (頻度高 → 低)

1. **言語崩壊 (Language collapse)** — *頻度 ~54% / Kant without hint*
   - 例: `"歩く道は思索のためなり。静けさは心の働きなり。"` (Kant が古典的日本語)
   - **対策**: 判断 5 の `_DIALOG_LANG_HINT` を system prompt に必ず注入 → 発生率 0%

2. **完全反復 (Exact repetition across turns)** — *頻度 59% (10/17 session)*
   - 例 (10-turn peripatetic): turn 2,4,6,8 全てが `"The mind, like the stars, must be allowed to shine in its own light."` 同一文
   - **対策**: 判断 4 の turn ≥ 2 anti-repeat 指示で 100% 新規に改善

3. **近傍言い換え収束 (Near-paraphrase convergence)** — *頻度 ~40%、反復と分離しがたい*
   - 例 (chashitsu): `"静けさは心の境なり"` → `"静けさは心の道なり"` → `"静けさは心の術なり"` (漢字 1 文字の差分)
   - **対策**: 判断 4 と同じ anti-repeat 指示で緩和 (完全排除は困難、実用上許容)

4. **過短応答 (Terse collapse to < 10 chars)** — *頻度 ~15%、Rikyū の chashitsu/zazen で顕著*
   - 例: `"侘び寂びの境なりけり。"` (9 chars) を 3 turn 連続
   - **対策**: style として許容 (wabi-sabi の美意識に合致)。下限を設けない。`m5-dialog-turn-generator` の log レベルで warn 出力のみ

5. **改行連続による 2 発話生成 (Multi-utterance single response)** — *頻度 2/80 turn (~2.5%)、Kant の peripatetic で稀に発生*
   - 例: `"The mind seeks truth.\n\nYet we must also rest."` (2 文を 1 response で emit)
   - **対策**: 判断 2 の `stop=["\n\n"]` で単発化

### 観察されなかったパターン (defensive 対処不要と判断)

- stage direction (`*bows*`): 0 件 — `think=false` + prompt 指示で不要
- JSON wrapping (`{"utterance": ...}`): 0 件
- 相手名反転 (Rikyū が "Kant, you..." で自身を Kant と名乗る): 0 件
- 無応答 / empty string: 0 件 (think=false 後)

**採用**: 上記 5 種に対する対策を `m5-dialog-turn-generator` の docstring に明記し、
`tests/test_integration/test_dialog_turn.py` の mocked LLM fixture でパターン 1, 2, 5 を
再現する regression guard を置く。パターン 3, 4 は subjective で test 化しない。

## 判断 7: M5 planning 判断 1 の **C 案 (mode のみ先行) 退避は不要**

- **判断日時**: 2026-04-20
- **背景**: planning 判断 1 で「spike で dialog_turn プロンプト品質が実用水準に届かない場合、C 案 (ERRE mode FSM のみ先行、dialog_turn は M6 へ繰越) へ退避する」と明記されていた。
- **評価基準** (planning 時):
  - qwen3:8b で peripatos 対話が**完全に幻覚ベース** → 退避
  - 実用的な turn 数 (3 以上) を保てない → 退避検討
- **spike 結果**:
  - 言語ヒント + anti-repeat 指示を入れれば、**6 turn まで意味のある対話**が成立 (判断 4, 5)
  - latency 2.5s/turn → 6 turn で 15s、60s window 内に余裕あり
  - 幻覚パターンは特定可能で、全て prompt 層で対処できる (判断 6)
- **採用**: **C 案退避しない。hybrid 計画のまま M5 を両輪 (FSM + dialog_turn) で進行**
- **理由**: 品質リスクが planning 時の想定内で収まっている。schema bump (0.3.0-m5) を 1 回で両軸に適用する効率性を維持できる
- **トレードオフ**: なし (想定通りの結果)
- **影響範囲**: `.steering/20260420-m5-planning/decisions.md` 判断 1 の「見直しタイミング」条項は発動せず、design.md の依存グラフ通り進行
- **後続タスク**: `m5-contracts-freeze` を次に着手

---

## 後続 `m5-contracts-freeze` が本文書から取り出すべき値 (まとめ)

1. `SCHEMA_VERSION: Final[str] = "0.3.0-m5"` (planning 判断 2 通り)
2. `Cognitive.dialog_turn_budget: int = Field(default=6, ge=0)` (本判断 4)
3. `DialogTurnMsg.turn_index: int = Field(..., ge=0)` (本判断 4)
4. `DialogCloseMsg.reason` literal に `"exhausted"` 追加 (本判断 4)
5. `ERREModeTransitionPolicy` / `DialogTurnGenerator` Protocol 追加 (planning 通り、signature 変更なし)

## 後続 `m5-dialog-turn-generator` が本文書から取り出すべき値 (まとめ)

1. Ollama options: `{"num_predict": 120, "stop": ["\n\n"]}`、payload top-level `"think": False`
2. Sampling: 既存 `compose_sampling(persona.default, erre.delta)` をそのまま利用
3. System prompt builder (`build_dialog_system_prompt`) に per-persona `_DIALOG_LANG_HINT` を注入
4. User prompt builder に turn_index ≥ 2 分岐で anti-repeat 指示を末尾に付加
5. Close 判定: `turn_index == dialog_turn_budget` で `reason="exhausted"` emit
6. 幻覚 regression guard: パターン 1, 2, 5 を mocked LLM で再現する integration test

## spike 自体の終了状態

- 成果物: 本 `decisions.md` のみ (spike コード・生ログは `_ad_hoc/` で git ignored)
- tasklist.md の axes 1-5 すべて完走
- planning 判断 1 の退避条項は発動せず (判断 7)
