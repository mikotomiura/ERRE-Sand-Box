# Live G-GEAR observation — event-boundary-observability (M9-A)

> **検証スコープの注記**: 本ファイルの V1/V2/V5 wire/V6 は **CLI 上の Claude Code が
> server-side で自律検証**した結果を埋めている。**V3 / V4 / V5 の Godot 描画と
> debugger 状況は人間目視によるフォローアップ session が必須** (`<TBD>` で残置)。
> V3/V4/V5-client が埋まったら overall verdict を更新して PR を land する。

## メタ情報

| 項目 | 値 |
|---|---|
| 検証日時 (JST) | 2026-04-28 22:29–22:38 (run-01+02) + 2026-04-29 00:xx–00:xx (run-03) |
| main commit | `bd0a359` 起点 (run時点)。**注**: PR #119 (`e66890d`) は GDScript 専用 fix のため、server-side wire data は #119 merge 前後で同一。`run-01-m9a/` の生データはそのまま e66890d 受け入れに利用可。 |
| Godot version | `<TBD: Godot 起動時に godot --version、4.6.x.stable 期待>` |
| 検証者 | Claude Code (server-side, CLI) + mikotomiura (V3/V4/V5-client、待) |
| 走行時間 | 合計 **12.1 分** (combined 726.3 s = 122.07 + 242.11 + 362.08) |
| ペルソナ | Kant / Nietzsche / Rikyu (3 体) |
| 推論バックエンド | Ollama (`qwen3:8b` Q4_K_M, 5.2 GB) + `nomic-embed-text:latest` |

## Pre-flight 確認

| 項目 | 結果 |
|---|---|
| `git pull origin main` 後の HEAD が e66890d (PR #119 merge) | **NO** (run時 bd0a359、PR #119 は GDScript only のため server-side 結果に影響なし。GUI 検証 session で MacBook 側を e66890d に揃える必要あり) |
| `src/erre_sandbox/schemas.py` SCHEMA_VERSION = "0.10.0-m7h" | **YES** (L44) |
| `godot_project/scripts/WebSocketClient.gd` CLIENT_SCHEMA_VERSION = "0.10.0-m7h" | **YES** (L28) |
| `EnvelopeRouter.gd` に `SPATIAL_TRIGGER_KINDS` const 存在 | **YES** (L23、`PackedStringArray`、加えて `BoundaryLayer.gd:101` に `_SPATIAL_TRIGGER_KINDS`) |
| `uv run pytest -m "not godot" -q` → 1064 passed | **YES** (1064 passed + 27 skipped + 2 既存 architecture-test 失敗 — 本機能と独立) |
| Godot client cold restart 済 (旧 .gd キャッシュなし) | `<TBD: GUI session 開始時に MacBook 側で確認>` |

## V1: 3 体走行で TRIGGER 行が更新される

- **Verdict**: **PASS** (server-side wire data 観察、ReasoningPanel 描画は `<TBD>`)
- **観察内容**: run-01 + run-02 + run-03 の合計 **48 件 reasoning_trace** envelope のうち **31 件 (65%) で `trace.trigger_event` が non-null**。3 ペルソナいずれも複数の trigger 種で発火:

  | agent | trace 数 | trigger_event populated | TRIGGER_NONE |
  |---|---:|---:|---:|
  | a_kant_001 | 14 | 10 | 4 |
  | a_nietzsche_001 | 28 | 18 | 10 |
  | a_rikyu_001 | 6 | 3 | 3 |

  kind 分布 (合計 31): zone_transition=18 / temporal=9 / proximity=4

  run-03 で Nietzsche が tick=2..14 にかけて peripatos↔study を 4 往復、Kant が tick=2,6 で peripatos enter, tick=7 で study return。tick 進行と共に trigger_event 値が変化することを確認。
- **異常**: `<TBD: panel 上で TRIGGER 行が "—" に張り付く agent がいないか目視確認>`
- **screenshot**: `<TBD: ReasoningPanel TRIGGER 行が agent ごとに違う表示になっている画>`

## V2: zone_transition trigger 表示

- **Verdict**: **PASS (server-side)** / 描画 `<TBD>`
- **観察内容 (server-side)**: zone_transition trigger 合計 18 件 (combined):

  | agent → zone | 件数 |
  |---|---:|
  | a_nietzsche_001 → study | 6 |
  | a_kant_001 → peripatos | 4 |
  | a_nietzsche_001 → peripatos | 4 |
  | a_rikyu_001 → peripatos | 2 |
  | a_rikyu_001 → chashitsu | 1 |
  | a_kant_001 → study | 1 |

  **Kant Study → Peripatos** は 4 回確認 (run-02 tick=11、run-03 tick=2/6)。
- **trigger_event の payload 例 (run-03 tick=6, agent=a_kant_001)**:
  ```json
  {
    "kind": "zone_transition",
    "zone": "peripatos",
    "ref_id": "peripatos",
    "secondary_kinds": ["proximity", "erre_mode_shift", "temporal"]
  }
  ```
  期待 3 key (kind=zone_transition / zone=peripatos / ref_id="peripatos") 完全一致。`secondary_kinds` も 3 件の strong loser を含み、設計通り max 8 制約内。
- **TRIGGER 行表示文字列** (Strings.gd `format_trigger` 経由): `<TBD: 例 "→ ゾーン移動 @ peripatos (peripatos)" を MacBook で目視転記>`
- **異常**: server-side では予期しない kind / zone / ref_id mismatch なし。Strings.gd 描画側の異常は `<TBD>`
- **screenshot**: `<TBD>`

## V3: focused agent で violet pulse

- **Verdict**: `<TBD: REQUIRES_HUMAN_VISUAL>` (server-side からは原理的に検証不能)
- **server-side 補助証拠**:
  - V2 の zone_transition wire data が正しく `trigger_event.kind` に出ている
  - `EnvelopeRouter.gd:23` `SPATIAL_TRIGGER_KINDS` whitelist + `BoundaryLayer.gd:337` の同 whitelist 二重ガード (Codex MEDIUM 7 反映)
  - `BoundaryLayer.gd:339-341` 周辺の focus filter (`SelectionManager.selected_agent_id` 一致時のみ pulse、Codex HIGH 4/5 反映)
- **観察内容**: `<TBD: peripatos 矩形が violet で 0.6s 光って cyan に戻ったか>`
- **色見え方**: `<TBD: violet が薄紫として認識できたか / yellow affordance ring と区別できたか / cyan proximity ring と区別できたか>`
- **screenshot 1 (pulse 中)**: `<TBD: screenshots/v3-pulse-active.png>`
- **screenshot 2 (復帰後)**: `<TBD: screenshots/v3-pulse-restored.png>`

## V4: focus 切替で pulse 対象が切り替わる

- **Verdict**: `<TBD: REQUIRES_HUMAN_VISUAL>`
- **server-side 補助証拠**: wire 上 各 agent の trigger_event は agent_id 付きで分離され、対応 zone も Kant=peripatos / Nietzsche=peripatos+study / Rikyu=chashitsu+peripatos と分散。`zone_pulse_requested(agent_id, kind, zone, tick)` signal が agent_id を含む拡張型 (Codex HIGH 4)、BoundaryLayer は `SelectionManager._focused_agent` 一致時のみ pulse。
- **観察内容**: `<TBD: Kant → Rikyu 切替後の挙動>`
  - Kant の zone_transition で peripatos が pulse しないか: `<TBD: YES / NO>`
  - Rikyu の affordance event で chashitsu のみ pulse するか: `<TBD: YES / NO>`
  - 切替時に in-flight pulse が正しくクリアされたか: `<TBD: YES / NO>`
- **異常**: `<TBD>`
- **screenshot**: `<TBD: screenshots/v4-focus-switch-rikyu.png (任意)>`

## V5: 非空間 trigger で crash しない (★最重要、PR #119 hotfix の本命)

**前回 (2026-04-28 PR #118 merge 後の初回 live) ここで crash したポイント。**
今回 crash しないこと **+** pulse も起きないことを確認する。

- **Verdict (server-side wire 部分のみ)**: **PASS** / GDScript debugger 状況は `<TBD>`
- **GDScript debugger 状況**:
  - `"Trying to assign value of type 'Nil' to a variable of type 'String'"` が出ない: `<TBD>`
  - その他の ERROR: `<TBD: なし or 出た場合は全文>`
- **temporal-only tick の TRIGGER 行表示**: `<TBD: 例 "◔ 時間帯">`
- **biorhythm-only tick の TRIGGER 行表示**: `<TBD: 例 "♥ 生体リズム">` (本 726s window では biorhythm primary trigger 未観測。secondary には現れず — primary 化させるには長時間 run 推奨)
- **観察された非空間 trigger kinds (server-side, combined)**: **temporal × 9 件**。biorhythm / internal / speech / perception / erre_mode_shift は本 726s window では primary に来なかった (但し `secondary_kinds` には `erre_mode_shift` / `temporal` が頻出 → 内部発火はしているが優先順位で勝てなかった)
- **temporal trigger sample (run-02 tick=12, agent=a_nietzsche_001)**:
  ```json
  {"kind": "temporal", "zone": null, "ref_id": null, "secondary_kinds": []}
  ```
  全 9 件で `zone=None` / `ref_id=None` を確認。EnvelopeRouter.gd の spatial-set フィルタ (`kind not in SPATIAL_TRIGGER_KINDS`) を通過しないため `zone_pulse_requested` signal は emit されず、BoundaryLayer.pulse_zone() に到達しない (wire / routing 仕様上、pulse 抑制は確定的)。
- **BoundaryLayer**: 非空間 trigger 発火時にどの zone も pulse しなかった: `<TBD: 視覚確認、YES / NO>`
- **screenshot (debugger clean)**: `<TBD: screenshots/v5-debugger-clean.png>`

## V6: envelope/sec 計測

- **Verdict**: **PASS**
- **計測手順**: `_stream_probe_m7e.py` で WS observer として handshake → 全 envelope を JSONL 記録 (run-01.jsonl / run-02.jsonl / run-03.jsonl)、`.summary.json` 内の `envelope_total` / `elapsed_s` から計算。
- **本走行の envelope/sec** (3 run combined):

  | run | duration | envelopes | env/sec |
  |---|---:|---:|---:|
  | run-01 | 122.07 s | 175 | 1.434 |
  | run-02 | 242.11 s | 324 | 1.338 |
  | run-03 | 362.08 s | 489 | 1.351 |
  | **合計** | **726.27 s** | **991** | **1.365** |

- **ζ-3 baseline**: `2493 envelopes / 1802.1 s = 1.384 env/sec` (`.steering/20260426-m7-slice-zeta-live-resonance/observation.md`)
- **比率**: 1.365 / 1.384 = **0.986 (-1.4%)**
- **判定**: **許容範囲内**。1.2-2x 増の許容ラインを遥かに下回り、`_build_envelopes` の発火条件に追加した `or trigger is not None` の OR は envelope rate を爆発させていない (cognition cycle ↔ reasoning trace の対応は run-01/02/03 全てで 1:1 維持)。
- **備考**: trigger_event の発火条件緩和は単に「TRIGGER 行が更新されるべき tick で確実に reasoning_trace を出す」効果であり、不要な envelope 発生は伴わない。1 分以上の長 window でも rate stable。

## 追加観察

### 既知 warning の再確認
- **GDScript:reload "size" shadowing warning**: `<TBD: MacBook GUI session で確認>`
- **idle_disconnect (60s no client frame)**: `<TBD: godot-ws-keepalive 別タスク扱い、本 run の orchestrator-02.log にはサーバー観点の disconnect 記録なし (probe 側は keepalive 送信)>`
- **`ERREModeShiftEvent ...` warning**: `<TBD: GUI 側 console で確認>`

### 異常観察 — MacBook (192.168.3.118) からの handshake 失敗 reconnect ループ

run 全期間にわたり orchestrator log に **MacBook 側 Godot client からの即 close cycle が大量記録** (run-01 期 orchestrator.log: 544 cycle、run-03 期 orchestrator-02.log: 継続中)。`gateway.py:580-587` で `env.schema_version != SCHEMA_VERSION` の場合に `code="schema_mismatch"` の ErrorMsg を返してから close する仕様 → MacBook 側 Godot の `CLIENT_SCHEMA_VERSION` がまだ古いまま (おそらく `0.9.0-m7z`) で、reconnect ループに入っている疑いが濃厚。

**MacBook 側で実施すべき**:
1. `git pull origin main` (e66890d まで進める)
2. Godot editor を完全終了 → 再起動 (const は editor 再起動しないと reload されない)
3. `[WebSocketClient] handshake ack` debug console log を確認
4. その後 V3/V4/V5-client の視覚検証に入る

### DX 観点での違和感
`<TBD: GUI session 後に「眼球 1 サッカードで読めるか」「DX 観点での panel + zone pulse の体感」を記述>`

### secondary_kinds の活用余地
本 31 件の trigger_event のうち、`secondary_kinds` に複数 kind が並ぶ trace は以下のパターン:
- `["proximity", "temporal"]` (Kant tick=2 zone_transition)
- `["proximity", "erre_mode_shift", "temporal"]` (Kant tick=6 zone_transition、複数回)
- `["affordance", "proximity", "temporal"]` (Rikyu tick=2 zone_transition)
- `["proximity", "erre_mode_shift"]` (Nietzsche zone_transition x 多数)

「+N more」UI hint は **panel 1 行に追加圧迫がない範囲**で価値がある。Rikyu の chashitsu 入場時は affordance も同 tick で起きていたことを secondary で示せると、ペルソナ別の認知傾向 (rikyu = 物理 affordance 優位) が読み取りやすい。本 task では task-out-of-scope だが、follow-up 候補。

## 総合 verdict

- **Server-side Overall**: **APPROVE_WITH_FOLLOWUP** (V1/V2/V5-wire/V6 = 4/4 PASS)
- **Final Overall (待)**: `<TBD: V3/V4/V5-client が埋まったら更新>`
  - V3/V4/V5-client いずれも PASS なら **APPROVE**
  - 1 つでも FAIL なら **APPROVE_WITH_FOLLOWUP** (具体的 issue を発行)
- **次工程**:
  1. **MacBook 側 git pull + Godot cold restart** (必須、handshake reject 解消)
  2. V3/V4/V5-client 視覚検証 + screenshot 取得 (`screenshots/v3-pulse-active.png` / `v3-pulse-restored.png` / `v5-debugger-clean.png` 等)
  3. 本 observation.md の `<TBD>` を埋める
  4. follow-up 候補 (現時点):
     - secondary_kinds UI hint 追加 (panel に "+N more" 表示) — DX 改善案、別 issue
     - biorhythm primary trigger 観測のための長時間 run (1 hr+) — 別 acceptance task
     - architecture-test 2 件の既存 failure (`test_layer_dependencies.py::test_ui_does_not_import_integration` / `::test_contracts_layer_depends_only_on_schemas_and_pydantic`) — 別 follow-up task

## screenshots/

```
screenshots/
├── v2-zone-transition.png     <TBD>
├── v3-pulse-active.png        <TBD>
├── v3-pulse-restored.png      <TBD>
├── v4-focus-switch-rikyu.png  <TBD, 任意>
└── v5-debugger-clean.png      <TBD>
```

## ログ抜粋 — MacBook handshake reject loop (run-01 orchestrator.log)

```
INFO:     192.168.3.118:53377 - "WebSocket /ws/observe" [accepted]
INFO:     connection open
INFO:     connection closed         ← schema_mismatch ErrorMsg 直後の close
INFO:     192.168.3.118:53401 - "WebSocket /ws/observe" [accepted]
INFO:     connection open
INFO:     connection closed
... × 544 cycles in run-01 alone
```

`gateway.py:580-587` の根拠コード:
```python
if env.schema_version != SCHEMA_VERSION:
    await _send_error(
        ws,
        code="schema_mismatch",
        detail=(
            f"client schema_version={env.schema_version!r} != "
            f"server {SCHEMA_VERSION!r}"
```

server side wire 採取 raw data:
- `run-01-m9a/run-01.jsonl` (175 envelopes / 122s / handshake → reasoning_trace x9 等)
- `run-01-m9a/run-02.jsonl` (324 envelopes / 242s)
- `run-01-m9a/run-03.jsonl` (489 envelopes / 362s)

各 `.summary.json` 同梱 (kind 別カウント + schema_version + elapsed)。

---

Refs:
- requirement.md (background, acceptance criteria)
- design-final.md (実装仕様)
- codex-review.md (PR #118 で適用された Codex review)
- PR #118 (M9-A feature) https://github.com/mikotomiura/ERRE-Sandbox/pull/118
- PR #119 (null-guard hotfix) https://github.com/mikotomiura/ERRE-Sandbox/pull/119
