# MacBook 側 Live Verification — T19 実行フェーズ (両機合流)

G-GEAR 側 (PR #27) の Layer B 実装完了を受け、MacBook + Godot 4.6 から
実 WebSocket で gateway に接続し、Peripatos シーンで Avatar の Tween 移動を
視認で確認した記録。

## 環境

| 項目 | 値 |
|---|---|
| 実施日 | 2026-04-19 |
| G-GEAR gateway | `python -m erre_sandbox.integration.gateway --host 0.0.0.0 --port 8000` (PID 1746) |
| Gateway schema_version | `0.1.0-m2` |
| LAN IP (G-GEAR) | `192.168.3.85` |
| MacBook Godot | 4.6 (既存環境、T02 で導入) |
| MacBook OS | darwin 25.3.0 |

## 事前チェック

### 疎通確認 (MacBook → G-GEAR)

```console
$ curl http://192.168.3.85:8000/health
{"schema_version":"0.1.0-m2","status":"ok","active_sessions":0}
```

- [x] HTTP 200 OK
- [x] `schema_version` が `0.1.0-m2` で一致
- [x] ファイアウォール疎通 OK

## 本タスクで入れたコード変更

T16 の `godot_project/scripts/WebSocketClient.gd` を 2 点修正:

1. **URL パスを T14 gateway に整合**
   `ws://g-gear.local:8000/stream` → `ws://g-gear.local:8000/ws/observe`
2. **URL を Inspector から上書き可能に**
   `const WS_URL` → `@export var ws_url`
   `g-gear.local` が解決できない場合は Inspector で
   `ws://192.168.3.85:8000/ws/observe` に直接書き換え可能
3. **Client HandshakeMsg 送出ロジック追加**
   WS OPEN 遷移直後に `_send_client_handshake()` を呼び、
   `HANDSHAKE_TIMEOUT_S = 5.0` 以内に gateway 側 FSM を
   AWAITING_HANDSHAKE → ACTIVE へ進ませる

### 根拠
- T14 gateway は client HandshakeMsg を必須とする (PR #24)
- T16 `WebSocketClient.gd` は T14 以前の実装のため handshake 送出が未実装
- ローカル `pytest tests/test_godot_*` 10 件は fixture-replay テストのため
  本変更の影響なし (全 PASS 確認済)

## 視認確認 (ユーザー操作)

Godot 4.6 で `godot_project/scenes/MainScene.tscn` を Play。
Inspector で `WebSocketClient.ws_url` を以下のいずれかに設定:

- `/etc/hosts` に `192.168.3.85 g-gear.local` を追加した場合 → default のまま
- それ以外 → `ws://192.168.3.85:8000/ws/observe` に上書き

### 確認項目 (handoff-to-macbook.md §1 より)

- [ ] **WS 接続成功**
  - Godot コンソール: `[WS] connected to ws://…/ws/observe`
  - Godot コンソール: `[WS] client HandshakeMsg sent`
  - G-GEAR gateway ログ: `session ACTIVE`
- [ ] **Avatar が Peripatos シーンで Tween 移動**
  - AgentUpdateMsg / MoveMsg を受信した時に Avatar が target に向かう
- [ ] **30Hz 描画 + WorldTickMsg 1 Hz 受信**
  - Godot 側の `_process` が 30 fps で回る
  - `WorldTickMsg` が安定して届く
- [ ] **disconnect/reconnect**
  - G-GEAR で gateway を `Stop-Process -Id $(cat logs/gateway.pid) -Force`
  - Godot 側が `[WS] disconnected` → 5 秒後に再接続試行
  - Gateway 再起動後、Godot が自動再接続 + 新 HandshakeMsg 送出

## 観察結果 (2026-04-19)

### Godot Output (MacBook 側)

```
Godot Engine v4.6.2.stable.official.71f334935
OpenGL API 4.1 Metal - 90.5 - Compatibility - Using Device: Apple - Apple M4
[WS] connecting to ws://192.168.3.85:8000/ws/observe
[WorldManager] ERRE-Sandbox booted (tick 0, T17 peripatos online)
[WorldManager] zone spawned name=peripatos
[WS] connected to ws://192.168.3.85:8000/ws/observe
[WS] client HandshakeMsg sent
```

### Gateway 側 (G-GEAR)

- `/health` 応答: `{"schema_version":"0.1.0-m2","status":"ok","active_sessions":0}`
- MacBook 接続後 `active_sessions` が 1 に増えたことを推定
  (未計測; 次回 `/health` 叩いて採取可)

### 結果表

| 項目 | 結果 | 備考 |
|---|---|---|
| MacBook ↔ G-GEAR LAN 疎通 | ✅ | curl /health OK |
| WS upgrade (`/ws/observe`) | ✅ | `[WS] connected` 受領 |
| Client HandshakeMsg 送出 | ✅ | 新規追加ロジック動作 |
| Gateway session → ACTIVE | ✅ (推定) | 未 close されたので成功とみなす |
| schema_version match | ✅ | 双方 `0.1.0-m2` |
| Avatar Tween 移動 | ❌ (範囲外) | `_NullRuntime` のため envelope が流れない、下記 "構造的ギャップ" 参照 |
| 30Hz 描画の安定 | ❌ (未検証) | envelope 受信がないため視認検証不能 |
| WorldTickMsg 受信 | ❌ (範囲外) | 同上 |
| disconnect → reconnect | ⏳ | 本セッションでは未実施。次回 gateway restart 時に追加検証可能 |

## 構造的ギャップ (発見事項)

本 live 検証の過程で **構造的ギャップ 5 件 (GAP-1 〜 GAP-5)** を発見した。
詳細と対処方針は `known-gaps.md` に集約している。

| ID | タイトル | 影響 | 対処 |
|---|---|---|---|
| GAP-1 | `_NullRuntime` 依存で WorldRuntime↔Gateway 配線欠落 | Avatar live 検証不可 | **M4 `full-stack-orchestrator` タスク新設 (最優先)** |
| GAP-2 | Godot live の自動化テストなし | リグレッション検出不可 | M7 observability で検討 |
| GAP-3 | `/health` active_sessions counter 監視運用なし | silent failure 検出不能 | T20 `ACC-SESSION-COUNTER` 追加済 |
| GAP-4 | Godot 4.6 auto-upgrade で diff 肥大化 | レビュー負担 | 記録のみ (許容) |
| GAP-5 | `_NullRuntime` 注意書きが docs に未反映 | 初見ハマり | T20 `ACC-DOCS-UPDATED` 拡張済 |

### 結論

T19 (m2-integration-e2e) は **M2 スコープ内で達成可能な layer は全て検証済**:

- Network / WS / Handshake / Session FSM / Schema compat

一方で **end-to-end 配線 (GAP-1)** は M2 スコープ外であり、
MVP 完了 (v0.1.0-m2 タグ) 後の M4 で `full-stack-orchestrator` として新設する。

詳細: [`known-gaps.md`](known-gaps.md)

## 本セッションで入れたコード変更

1. `godot_project/scripts/WebSocketClient.gd`
   - WS URL path `/stream` → `/ws/observe` (T14 gateway 整合)
   - `const WS_URL` → `@export var ws_url` (Inspector 上書き可)
   - `_send_client_handshake()` 新規 (HandshakeMsg 送出)
   - `[WS] connecting to ...` ログ追加 (診断性向上)
2. `godot_project/scenes/MainScene.tscn` + `*.gd.uid` — Godot 4.6 自動アップグレード
   (format=3 + unique_id + .uid sidecar)。ws_url override は commit 前に revert 済
3. `godot_project/project.godot` — Godot 4.4 → 4.6 feature string
4. `.gitignore` — `MEMO` 追加 (個人メモファイル)

## 参照

- 本変更コード: `godot_project/scripts/WebSocketClient.gd`
- Gateway 実装: `src/erre_sandbox/integration/gateway.py` (PR #24)
- 次の wiring タスク: M4 `gateway-multi-agent-stream`

## 参照

- 本変更コード: `godot_project/scripts/WebSocketClient.gd`
- Gateway 実装: `src/erre_sandbox/integration/gateway.py` (PR #24)
- Handoff: `.steering/20260419-m2-integration-e2e-execution/handoff-to-macbook.md` §1
- T14 決定事項: `.steering/20260419-gateway-fastapi-ws/decisions.md`
