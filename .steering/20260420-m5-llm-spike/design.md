# 設計 — m5-llm-spike

## 実装アプローチ

**Throwaway spike** — commit 対象は `.steering/20260420-m5-llm-spike/` の
steering ドキュメント 4 点 (requirement / design / tasklist / decisions) のみ。
spike スクリプト本体は `_ad_hoc/` 以下に作成し `.gitignore` で除外する。

qwen3:8b を localhost:11434 経由で `/api/generate` (streaming=false) で叩き、
Kant ↔ Rikyū の 1-on-1 対話を 3 ERRE mode × 2-3 run 実施。生ログは
`_ad_hoc/spike-logs/` に保存して subjective 評価 → 知見を `decisions.md` に集約。

### なぜ throwaway か

- spike の目的は「プロンプト shape の経験的確定」であり、正式 `DialogTurnGenerator`
  は `m5-dialog-turn-generator` で別途実装される
- commit すると技術負債化 (参照関係の曖昧化) → M5 planning 判断 4 で棄却済
- 代わりに知見を `decisions.md` に十分な粒度で残し、後続タスクが設計根拠として
  参照できる形にする

### spike の評価軸 (成果物の構造)

| # | 軸 | 測定方法 | 出力 |
|---|---|---|---|
| 1 | utterance 長 | `num_predict` を {60, 80, 120} で走らせて実測 char 数分布 | Kant (Latin), Rikyū (CJK) それぞれの目安値 |
| 2 | 停止語彙 | 出力ログから stage direction (`*bows*`) / JSON wrapping (`{`) / 名前混入 (`Kant:`) を検出 → `stop=[...]` で再実行 | stop tokens リスト |
| 3 | 温度帯 | peripatos / chashitsu / deep_work の 3 mode × persona default+delta の 6 組で 3 run ずつ、読み取れる/崩壊する を subjective 分類 | mode × persona の実効 temperature 推奨帯 |
| 4 | turn_index 上限 | 1 対話で最大 10 turn まで走らせ、turn 毎に「自然さ」「幻覚」を 1-5 で採点、減衰曲線から打ち切り推奨 turn を導出 | `dialog_turn_budget` 推奨値 |
| 5 | 幻覚パターン | 全 run ログから以下をカウント: 相手名誤生成、無限繰返し、stage direction、言語崩壊、空応答 | 頻度上位 3 種以上を具体例で `decisions.md` に引用 |

### プロンプト骨格 (spike 用簡易版)

spike では既存 `build_system_prompt` (cognition 用、JSON 契約付き) を流用せず、
dialog 専用の最小 system prompt を手書きする。正式版のビルダーは後続タスクで
`cognition/prompting.py` に兄弟関数として追加。

```
SYSTEM:
You are {display_name} ({era}), {preferred_zones}.
Cognitive habits:
- {habit_1 desc} [{flag}]
- {habit_2 desc} [{flag}]
- ...
Current ERRE mode: {mode}. Zone: {zone}.

You are engaged in a 1-on-1 dialog with {addressee_display_name}.
Respond as a single utterance in your own voice, <= 80 Japanese chars or
160 Latin chars. Do NOT include names, quotation marks, stage directions,
or JSON wrapping. Return ONLY the utterance text.

USER:
Dialog so far (oldest -> newest, turn_index 0 = opening):
[turn 0, speaker={speaker_id}] {utterance}
[turn 1, speaker={speaker_id}] {utterance}
...

Your turn (turn_index = {k}). Respond in one utterance.
```

## 変更対象

### 修正するファイル

- `.gitignore` — `_ad_hoc/` を追加 (spike 成果物を誤 commit しないため)

### 新規作成するファイル (commit される)

- `.steering/20260420-m5-llm-spike/requirement.md` — 記入済 (Step 5 で対応)
- `.steering/20260420-m5-llm-spike/design.md` — 本ファイル
- `.steering/20260420-m5-llm-spike/tasklist.md` — Step 6 で対応
- `.steering/20260420-m5-llm-spike/decisions.md` — spike 完了後に知見集約

### 新規作成するファイル (commit されない、`_ad_hoc/` 配下)

- `_ad_hoc/spike_dialog.py` — qwen3:8b を呼ぶ spike ランナー
- `_ad_hoc/personas_snapshot.py` — `personas/{kant,rikyu}.yaml` を読む thin wrapper
- `_ad_hoc/spike-logs/*.jsonl` — run ごとの生ログ
- `_ad_hoc/README.md` — spike の動かし方メモ (個人用)

### 削除するファイル

なし。

## 影響範囲

- **コード**: `src/erre_sandbox/` には一切手を入れない
- **schema**: 変更なし (後続 `m5-contracts-freeze` で実施)
- **test**: 追加なし (pytest は走らせない)
- **CI**: 影響なし
- **Ollama**: 既に qwen3:8b (Q4_K_M, 8.2B) + nomic-embed-text が常駐、spike 実行中
  のみ 5-10 GB VRAM を占有 (既存プロセスと競合なし)
- **.gitignore**: `_ad_hoc/` 1 行追加 (無害、trivial)

## 既存パターンとの整合性

- `src/erre_sandbox/cognition/prompting.py` の 3 段構成 (prefix / persona / tail) を
  spike プロンプトに**流用しない**。正式実装で兄弟関数化する想定のため、
  spike では dialog 固有の最小版を手書きして「何が足りないか」を発見する
- `src/erre_sandbox/inference/sampling.py` の `compose_sampling` ロジック
  (persona default + ERRE delta → clamp) は spike では手計算で再現
  (import すると spike が正式コードパスに依存し throwaway の原則が破れる)
- ad-hoc スクリプトを `_ad_hoc/` 配下に隔離する規約は、ERRE-Sandbox で新規導入
  (既存の `tests/` / `scripts/` とは別の throwaway 領域として明示)

## テスト戦略

- **単体テスト**: 無し (spike コードは test を持たない、throwaway のため)
- **統合テスト**: 無し
- **E2E テスト**: 無し
- **人手評価**: 各 run の生 utterance を目視で subjective 採点 (1-5)、
  `_ad_hoc/spike-logs/scoring.md` に走り書き → `decisions.md` に要約
- **回帰確認**: 既存 525 test に触れないので不要。念のため `git status` clean で
  検証できる状態にしておく

## ロールバック計画

- spike 成果物 (`_ad_hoc/`) は `.gitignore` で除外されるため誤 commit リスク低
- `.steering/20260420-m5-llm-spike/*` と `.gitignore` の 1 行追加は trivial revert 可
- 万一 spike 結果が想定外 (例: qwen3:8b で peripatos 対話が全て幻覚) だった場合、
  M5 planning 判断 1 の「見直しタイミング」に従い C 案 (mode のみ先行) へ退避する
  判断材料を `decisions.md` に明記する
