# M7 Slice β — Live G-GEAR Acceptance

## 背景

PR #83 (Slice β) が merge 済 (2026-04-24、commit `a76343c`)。
`_bias_target_zone` post-parse resample + `WORLD_SIZE_M=100m` + 3 new zone
scenes + BoundaryLayer/CameraRig 同期が本体に入った。Unit / Godot headless
boot は緑だが、**実際に 3 agent が preferred_zones に寄るか** は
live run でのみ観察可能。MacBook 開発機では LLM 推論スループットが不足
するため G-GEAR (Ubuntu + Ollama) 上で検証する。

## ゴール

G-GEAR 上で ERRE_ZONE_BIAS_P の 2 値 (0.1 / 0.2) それぞれで 60-90s run を
実施し、PR #83 の Test plan に列挙した 6 項目の live 観察を証跡として記録する。
観察結果に基づき、bias_p の production default を 0.1 / 0.2 / 他 のどれに
するか decisions に記録する。

## スコープ

### 含むもの
- G-GEAR 上での `evidence/_stream_probe_m6.py` 60-90s × 2 回 (bias_p=0.1/0.2)
- `bias.fired` log grep による発火頻度の集計
- Godot での BoundaryLayer rect / 3 new scene / 100m terrain 視認確認
- `evidence/<run>.summary.json` からの zone 滞留分布抽出
- 結果を `.steering/20260425-m7-beta-live-acceptance/observation.md` に記録
- 必要なら微修正 PR を hotfix で

### 含まないもの
- Slice γ の実装 (別 task dir)
- LoRA / user-dialogue IF (L6 別 steering)

## 受け入れ条件

- [ ] bias_p=0.1 run と bias_p=0.2 run の 2 データセット取得
- [ ] `bias.fired` 発火回数を集計 (3 agent × 60s で総計何回か)
- [ ] Rikyū の chashitsu/garden/study 合計滞留 ≥ 50%
- [ ] Kant の peripatos/study 合計滞留 ≥ 50%
- [ ] Nietzsche の peripatos/garden 合計滞留 ≥ 50%
- [ ] Godot で BoundaryLayer の 5 zone rect が新 Voronoi に沿って描画される
- [ ] Study / Agora / Garden の primitive 建物が目視可能
- [ ] BaseTerrain が 100m (既存比で明らかに広い) に見える
- [ ] top-down hotkey `0` で 100m 全景がフレームに収まる
- [ ] 観察結果を `observation.md` に記録、bias_p default の最終判断を記録

## 関連ドキュメント

- PR: https://github.com/mikotomiura/ERRE-Sandbox/pull/83 (merged 2026-04-24)
- β 設計: `.steering/20260424-m7-differentiation-observability/` (D8)
- 過去の live acceptance 手順: `.steering/20260421-m5-acceptance-live/`
  や `.steering/20260420-m4-acceptance-live/` を参照
