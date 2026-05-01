# Codex independent review — LOW-1 RoleEval wording 決着 (P2a 着手直前)

## 状況

- タスク: `m9-eval-system` (M9-A event-boundary observability の後続、4 タスク化された M9 milestone の 1)
- 現在: Phase 1 完了 + P0a-P1b 完了。P2a (stimulus battery YAML 起草、4h、Mac) 着手直前
- main = `ff29ca2`、 P0-P1 完了分は未コミット (15 ファイル、本タスク完了時に単一 commit 予定、ユーザー指示)
- 前回の Codex review (`codex-review.md`、HIGH 5 / MEDIUM 6 / LOW 1) は Phase 1 終了時実施済、
  HIGH 全件は `design-final.md` に反映、MEDIUM は `decisions.md` の ME-1〜ME-6 に ADR 化済、
  **LOW-1 (RoleEval wording) のみ defer**、本セッション冒頭で決着が必要

## レビューしてほしい判断: LOW-1 RoleEval wording

`design-final.md` §"Hybrid baseline 採取" の stimulus battery は以下:

```
- 最初の 200 turn: curated stimulus battery を fixed order で投入
  - Wachsmuth Toulmin 引き出す prompt: 30
  - ToM info-asymmetric scenario (chashitsu): 20
  - RoleEval-adapted Kant biographical MCQ: 10  ← LOW-1 該当
  - persona-conditional moral dilemma: 10
  - 計 70 stimulus × 3 巡 = 210 turn
- 残り 300 turn: 自然対話
```

stimulus YAML は per-persona (`golden/stimulus/{kant,nietzsche,rikyu}.yaml`) で起草するため、
"RoleEval-adapted **Kant** biographical MCQ" のままでは Nietzsche / Rikyū 用 YAML が
意味不成立。`blockers.md` LOW-1 で 3 案 defer:

- **Option A**: 各 persona に biographical MCQ 10 問ずつ起草 (Kant / Nietzsche / Rikyū それぞれの
  伝記・思想史的 attested fact から)
- **Option B**: Kant biographical MCQ は Kant のみ、Nietzsche / Rikyū は別の floor diagnostic
  (Wachsmuth Toulmin に振替) で 70 turn 構成は維持
- **Option C**: RoleEval を全廃し Wachsmuth/ToM/dilemma の 60 stimulus × 3.5 巡で 210 turn 構成

## Claude (本体エージェント) の暫定推薦: Option A

trade-off 比較表 (Claude 提示):

| 軸 | A | B | C |
|---|---|---|---|
| stimulus 構成の persona 間斉一性 | ◎ 全 persona 70 = (30/20/10/10) で同形 | △ Kant (30/20/10/10), 他 (40/20/0/10) | ◎ (35/23/0/12) |
| bootstrap CI cross-persona 比較 | ◎ category mass 同一 | × stimulus type imbalance 交絡 | ◎ |
| persona-factuality dimension | ◎ 全 persona | △ Kant のみ | ✗ 完全消失 |
| Rikyū MCQ 起草難度 | △ legend 多、attested fact は 5-7 件確保可 | ○ 不要 | ◎ 不要 |
| Nietzsche MCQ 起草難度 | ○ Basel 1879 / Sils Maria / Overbeck 書簡で十分 | ○ 不要 | ◎ 不要 |
| drafting 工数 | +1.5h (30 MCQ) | ≈同等 | -0.5h |
| 後続 m9-eval-corpus で再 open 余地 | ◎ MCQ pool 別途精緻化可 | △ asymmetry 固定 | ✗ battery 再設計要 |

Claude の推薦理由:
1. **persona-factuality は 4 軸の 1 つ** (argumentation / ToM / persona-factuality / moral disposition) —
   RoleEval を切ると "persona knows itself" の dimension が消え、style / argumentation /
   ToM の 3 軸偏重に
2. **bootstrap CI 交絡を持ち込まない** — option B は per-persona stimulus mass 違いで
   Vendi/Burrows の persona 横比較が "stimulus 種類効果 × persona 効果" 分離不能
3. **Rikyū MCQ 起草実現可能** — 利休道歌構造 / 待庵物理寸法 / 北野大茶湯 1587 / Hideyoshi 確執 /
   Sakai 商人出自 / 1591 賜死 / 子 (道安・少庵) 等、attested fact 10 件は確保
4. **MCQ accuracy の cross-persona 絶対比較が無意味化する弱点** は ME-1 ADR の base model
   control measurement (`Δaccuracy = persona_run − base_control`) で吸収

## レビュー対象 (Claude のリーズニングを批判的に検証)

1. **Option A 推薦は妥当か?** Claude の論拠 4 点 (4 軸 dimension / CI 交絡 / Rikyū 実現性 /
   ME-1 で吸収) のうち、見落とし / 誤認 / 弱点はあるか?
2. **A/B/C 以外の Option D が存在するか?** (例: Kant 用 MCQ 10 を全 persona 共通の "general
   philosophical attribution" MCQ に置き換え、persona-factuality を sacrifice せずに per-persona
   起草を回避する案など、より優れた選択肢)
3. **Option A 採択時の落とし穴** — biographical MCQ の category 設計、distractor 設計、
   factual recall の信頼性確保で見落としそうな点 (例: persona prompt が "I am Kant" と
   応答する時の hallucination risk vs 史実 recall の混在)
4. **ME-1 base model control の活用が本当に絶対比較問題を吸収するか?** Δaccuracy の解釈で
   psychometric / NLP-eval literature 上の落とし穴は無いか?
5. **DB7 LOW-1 (synthetic 4th persona heldout fixture) との整合** — 4th persona 用 MCQ をどう
   設計するか (Claude は本セッションで 3 persona の MCQ のみ起草予定、4th は P2c の test 範囲)
6. **後続 P3 採取への impact** — option choice が 7500 turn 採取の解釈にどう影響するか、
   LOW-1 を P3a-decide / P3 まで再 defer する余地はあるか

## 参照ファイル

Codex は以下を読んでから判断:

- `.steering/20260430-m9-eval-system/design-final.md` (特に §Hybrid baseline / §Stimulus battery)
- `.steering/20260430-m9-eval-system/blockers.md` (LOW-1 finding 全文)
- `.steering/20260430-m9-eval-system/decisions.md` (ME-1: IPIP-NEO fallback trigger / ME-4: ratio
  defer / ME-6: Burrows corpus QC が関連)
- `.steering/20260430-m9-eval-system/codex-review.md` (前回 review の verbatim、LOW-1 の Codex
  原文がここにある)
- `personas/kant.yaml`, `personas/nietzsche.yaml`, `personas/rikyu.yaml` (cognitive_habits / flag
  分布 / primary_corpus_refs を確認、Rikyū の attested fact 量を判断)

## 報告フォーマット

verbatim で `.steering/20260430-m9-eval-system/codex-review-low1.md` に保存される。以下の構造で:

### Verdict (1 行)
"Adopt Option A" / "Adopt Option B" / "Adopt Option C" / "Adopt new Option D (described below)" /
"Re-defer to P3a-decide" のいずれか。

### Findings

各 finding に Severity (HIGH/MEDIUM/LOW) を付ける:

- **HIGH**: 採択判断を覆す根拠がある or 致命的な見落としがある
- **MEDIUM**: 採択判断は変わらないが、補強 / 明文化が必要
- **LOW**: 補足的な提案、blockers / decisions に記録すれば十分

各 finding は以下を含む:
- 一行 summary
- 観察された事実 / 根拠 (Claude の論拠のどこに対応するか明記)
- 推奨 action (具体的な編集 / 追加 / 削除指示)

### Open question (任意)

Claude が決められない / Codex でも決められない事項があれば 1-2 件まで明示。

## 制約

- read-only review。`.steering/` `personas/` `src/` のいずれも書き換えない (Codex sandbox は
  `.codex/config.toml` で `network_access=false` + read-only 既定の想定)
- 出力は日本語 + 必要箇所英語混在で OK (前回 review と同様)
- per_invocation_max=200K token の budget guard あり、本 review は narrow scope なので
  100K 以内が目安
