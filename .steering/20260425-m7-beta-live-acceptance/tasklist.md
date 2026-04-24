# Tasklist — M7 Slice β Live G-GEAR Acceptance

> 次セッションで G-GEAR に ssh / 直接触る。Plan mode 不要 (観察タスクのみ)。

## Pre-flight

- [ ] G-GEAR 側で最新 main を pull (`git pull origin main`)
- [ ] Ollama + SGLang サーバ稼働確認 (`nvidia-smi` で VRAM、`ollama list`)
- [ ] Godot client (MacBook 側) の起動、WebSocket 接続先が G-GEAR を向いていること

## Run 1 — bias_p=0.1

- [ ] G-GEAR で `ERRE_ZONE_BIAS_P=0.1 uv run python evidence/_stream_probe_m6.py`
      を 60-90s 実行
- [ ] 同時に Godot client 側で目視観察、スクショ 3 枚
      (top-down / zone 拡大 / ReasoningPanel)
- [ ] `evidence/<run>.summary.json` と stdout log を手元 `.steering/20260425-m7-beta-live-acceptance/run-01-bias01/` に保存
- [ ] `grep 'bias.fired' <log>` で発火総数を記録

## Run 2 — bias_p=0.2

- [ ] 同上、`ERRE_ZONE_BIAS_P=0.2` で繰り返し
- [ ] 保存先: `run-02-bias02/`

## Analysis

- [ ] 2 run の `summary.json` から agent ごとの zone 滞留 tick % を抽出
- [ ] 受け入れ条件 5 項目 (Rikyū/Kant/Nietzsche の分布) を評価
- [ ] 5 zone rect / primitive 建物 / 100m terrain / top-down フレーミングの
      目視 5 項目を評価
- [ ] 結論を `.steering/20260425-m7-beta-live-acceptance/observation.md` に記録:
  - bias 発火頻度 (run 1 vs run 2)
  - zone 滞留分布
  - bias_p の production default 推奨値
  - 気になった不具合 → hotfix PR 起票 or γ に送る

## Follow-up

- [ ] observation.md の結論を `.steering/20260424-m7-differentiation-observability/decisions.md`
      に D9 として追記
- [ ] 必要なら `ERRE_ZONE_BIAS_P` のデフォルト値変更 hotfix PR
- [ ] γ 着手時に observation.md を参照 (D1 相互反省 prompt の材料に)
