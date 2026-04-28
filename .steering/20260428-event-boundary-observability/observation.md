# Live G-GEAR observation — event-boundary-observability (M9-A)

> **使い方**: 各セクションを埋めてください。`<…>` プレースホルダはそのまま削除して上書き。
> verdict 列は `PASS` / `FAIL` / `partial` / `skipped` のいずれかに置換。
> screenshot は `screenshots/` サブディレクトリに置き、相対パスで参照。

## メタ情報

| 項目 | 値 |
|---|---|
| 検証日時 (JST) | `<YYYY-MM-DD HH:MM-HH:MM>` |
| main commit | `<git rev-parse HEAD の出力、e66890d 期待>` |
| Godot version | `<godot --version、4.6.x.stable 期待>` |
| 検証者 | mikotomiura |
| 走行時間 | `<分>` |
| ペルソナ | Kant / Nietzsche / Rikyu (3 体) |
| 推論バックエンド | `<sglang or ollama、モデル名>` |

## Pre-flight 確認

| 項目 | 結果 |
|---|---|
| `git pull origin main` 後の HEAD が e66890d (PR #119 merge) | `<YES / NO>` |
| `src/erre_sandbox/schemas.py` SCHEMA_VERSION = "0.10.0-m7h" | `<YES / NO>` |
| `godot_project/scripts/WebSocketClient.gd` CLIENT_SCHEMA_VERSION = "0.10.0-m7h" | `<YES / NO>` |
| `EnvelopeRouter.gd` に `SPATIAL_TRIGGER_KINDS` const 存在 | `<YES / NO>` |
| `uv run pytest -m "not godot" -q` → 1064 passed | `<YES / NO>` |
| Godot client cold restart 済 (旧 .gd キャッシュなし) | `<YES / NO>` |

## V1: 3 体走行で TRIGGER 行が更新される

- **Verdict**: `<PASS / FAIL>`
- **観察内容**: `<3 ペルソナそれぞれの TRIGGER 行が tick 進行に応じて変化したか>`
- **異常**: `<TRIGGER_NONE のまま固まった agent / kind の偏り / etc.>`
- **screenshot**: `<相対パス or なし>`

## V2: zone_transition trigger 表示

- **Verdict**: `<PASS / FAIL>`
- **観察内容**: `<Kant が Study → Peripatos に移動した瞬間の TRIGGER 行表示文字列をそのまま転記>`
  - 例: `→ ゾーン移動 @ peripatos (peripatos)`
- **trigger_event の payload (debugger / log から)**: `<{kind: "...", zone: "...", ref_id: "...", secondary_kinds: [...]}>`
- **異常**: `<予期しない kind / zone / ref_id mismatch / etc.>`
- **screenshot**: `<相対パス>`

## V3: focused agent で violet pulse

- **Verdict**: `<PASS / FAIL>`
- **観察内容**: `<peripatos 矩形が violet で 0.6s 光って cyan に戻ったか>`
- **色見え方**: `<violet が薄紫として認識できたか / yellow affordance ring と区別できたか / cyan proximity ring と区別できたか>`
- **screenshot 1 (pulse 中)**: `<相対パス>`
- **screenshot 2 (復帰後)**: `<相対パス>`

## V4: focus 切替で pulse 対象が切り替わる

- **Verdict**: `<PASS / FAIL>`
- **観察内容**: `<Kant → Rikyu 切替後の挙動>`
  - Kant の zone_transition で peripatos が pulse しないか: `<YES / NO>`
  - Rikyu の affordance event で chashitsu のみ pulse するか: `<YES / NO>`
  - 切替時に in-flight pulse が正しくクリアされたか: `<YES / NO>`
- **異常**: `<前 focus の pulse が残った / 切替が反映されなかった / etc.>`
- **screenshot**: `<相対パス or なし>`

## V5: 非空間 trigger で crash しない (★最重要、PR #119 hotfix の本命)

**前回 (2026-04-28 PR #118 merge 後の初回 live) ここで crash したポイント。**
今回 crash しないこと **+** pulse も起きないことを確認する。

- **Verdict**: `<PASS / FAIL>`
- **GDScript debugger 状況**:
  - `"Trying to assign value of type 'Nil' to a variable of type 'String'"` が出ない: `<YES / NO>`
  - その他の ERROR: `<なし or 出た場合は全文>`
- **temporal-only tick の TRIGGER 行表示**: `<例: "◔ 時間帯">`
- **biorhythm-only tick の TRIGGER 行表示**: `<例: "♥ 生体リズム">`
- **観察された非空間 trigger kinds**: `<temporal / biorhythm / internal / speech / perception / erre_mode_shift のうちどれが live で発火したか>`
- **BoundaryLayer**: 非空間 trigger 発火時にどの zone も pulse しなかった: `<YES / NO>`
- **screenshot (debugger clean)**: `<相対パス、エラータブが空/関連エラー無しの状態を撮る>`

## V6: envelope/sec 計測

- **Verdict**: `<PASS / FAIL / partial>`
- **計測手順**: `<gateway log の reasoning_trace 行 grep / WS observer / etc.>`
- **本走行の envelope/sec**: `<値>`
- **ζ-3 baseline**: `<値、`.steering/20260426-m7-slice-zeta-live-resonance/run-01-zeta/` 等から>`
- **比率**: `<本走行 / baseline、1.2-2x 増まで許容>`
- **判定**: `<許容範囲内 / 過大 → 要調査>`
- **備考**: `<trigger_event の発火条件緩和の影響評価コメント>`

## 追加観察 (任意)

### 既知 warning の再確認
- **GDScript:reload "size" shadowing warning**: `<再現したか / 全文>`
- **idle_disconnect (60s no client frame)**: `<godot-ws-keepalive 別タスクで対応予定、再現状況メモ>`
- **`ERREModeShiftEvent ...` warning**: `<前回 truncated だった行の全文、出たら>`

### DX 観点での違和感
- `<live で実際に panel + zone pulse を見た時の体感、「眼球 1 サッカードで読める」は本当か、改善余地、etc.>`

### secondary_kinds の活用余地
- `<+N more の UI hint を panel に出すべきか、現実の発火頻度を見ての判断>`

## 総合 verdict

- **Overall**: `<APPROVE / APPROVE_WITH_FOLLOWUP / BLOCK>`
- **次工程**:
  - `<必要な follow-up issue / scaffold を列挙>`
  - 例: ERREModeShiftEvent warning の調査、secondary_kinds UI hint 追加、godot-ws-keepalive 着手判断、etc.

## screenshots/

```
screenshots/
├── v2-zone-transition.png
├── v3-pulse-active.png
├── v3-pulse-restored.png
├── v4-focus-switch-rikyu.png  (任意)
├── v5-debugger-clean.png
└── ...
```

## ログ抜粋 (異常があれば)

異常があった場合のみ、関連箇所を 10-30 行程度抜粋:

```
<gateway / godot / cognition log の関連部分>
```

---

Refs:
- requirement.md (background, acceptance criteria)
- design-final.md (実装仕様)
- codex-review.md (PR #118 で適用された Codex review)
- PR #118 (M9-A feature) https://github.com/mikotomiura/ERRE-Sandbox/pull/118
- PR #119 (null-guard hotfix) https://github.com/mikotomiura/ERRE-Sandbox/pull/119
