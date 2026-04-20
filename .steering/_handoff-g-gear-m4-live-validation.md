# G-GEAR セッション用 handoff — M4 live 検証

このファイルは G-GEAR 側で新しい Claude Code セッションを開始した際に
Read するか、下記 "コピペ用プロンプト" セクションを貼り付けて使用する。

---

## コピペ用プロンプト (G-GEAR 側 Claude Code に貼る)

```
M4 live 検証タスクを実行する。M4 の Critical Path + 並列タスク全 6 本 (#1-#6)
は MacBook 側で merge 済 (PR #43/#44/#45/#46/#47/#48)、main HEAD = 51b282a。
本タスクは G-GEAR の実機リソース (GPU + Ollama + sqlite-vec) で
`uv run erre-sandbox --personas kant,nietzsche,rikyu` を実際に走らせ、
M4 acceptance 5 項目の evidence を収集する。

## 必ず先に Read
1. `.steering/20260420-m4-multi-agent-orchestrator/live-checklist.md`
   — 本タスクの詳細手順 (5 項目の期待値 + コマンド)
2. `.steering/20260420-m4-planning/design.md` §M4 全体の検収条件
3. `docs/architecture.md` §Composition Root (m4-multi-agent-orchestrator
   で導入した CLI と bootstrap の新フロー)

## 前提条件
- G-GEAR 上の Ollama が起動済、qwen3:8b と nomic-embed-text が pull 済
- MacBook 側で Godot project を起動準備可能 (live 中に接続)
- ネットワーク: G-GEAR と MacBook が同 LAN、G-GEAR の IP を把握済

## ワークフロー

### Step 0: Git 同期
```bash
cd ~/ERRE-Sand\ Box   # または G-GEAR の repo パス
git checkout main
git pull --ff-only origin main
git log --oneline -3   # 51b282a (M4 #6 merge) が HEAD に来ているか確認
```

### Step 1: タスクディレクトリ + branch 作成
`/start-task m4-acceptance-live` で `.steering/20260420-m4-acceptance-live/`
を作成。branch 名は `feature/m4-acceptance-live-evidence`。
requirement.md には「M4 live 検証 5 項目 evidence 収集、G-GEAR 実機で
PASS 判定、v0.2.0-m4 タグ付与の前提を作る」旨を記入。

### Step 2: 環境プリフライト
```bash
# Ollama の model が揃っているか
ollama list | grep -E "qwen3:8b|nomic-embed-text"
# GPU VRAM 状況
nvidia-smi --query-gpu=memory.used,memory.total --format=csv
# sqlite-vec build / uv 同期
uv sync --frozen
uv run pytest -q   # baseline 503 passed / 20 skipped を確認
```

想定外の差 (失敗 test / モデル欠落) があれば **ここで停止してユーザーに
報告**。live 検証に進まない。

### Step 3: evidence ディレクトリ準備
```bash
mkdir -p .steering/20260420-m4-acceptance-live/evidence
```

### Step 4: 5 項目 evidence 収集

`live-checklist.md` の #1-#5 を順に実行し、すべて
`.steering/20260420-m4-acceptance-live/evidence/` 配下に保存する。

**#1 起動 + /health**:
- 別ターミナルで `uv run erre-sandbox --personas kant,nietzsche,rikyu
  --port 8000 --db var/m4-live.db --log-level info` を起動
  (bash Bash run_in_background=true で Claude Code セッション内から起動可能)
- 数秒待って `curl -s http://127.0.0.1:8000/health` を
  `evidence/gateway-health-<ts>.json` に保存
- `schema_version="0.2.0-m4"` と `active_sessions` counter を確認

**#2 3-agent walking (60s)**:
- `websocat -n ws://127.0.0.1:8000/ws/observe >
  evidence/cognition-ticks-<ts>.log &` で envelope stream を tail 開始
- 60 秒以上放置 (MacBook Godot を繋げる場合はこのタイミング)
- stream 停止後、log 内に 3 agent 分の `agent_update` × 6 以上が
  現れていることを grep で検証

**#3 Reflection + semantic_memory**:
- 起動後 3 分以上走らせてから:
  ```bash
  sqlite3 var/m4-live.db \
    "SELECT agent_id, substr(content,1,60), origin_reflection_id
     FROM semantic_memory ORDER BY created_at" \
    | tee evidence/semantic-memory-dump-<ts>.txt
  ```
- 各 agent_id (kant/nietzsche/rikyu) について 1 行以上 + `origin_reflection_id`
  が NULL でないこと

**#4 Dialog 発火**:
- envelope log から dialog_* を抽出:
  ```bash
  grep -E "dialog_(initiate|turn|close)" evidence/cognition-ticks-*.log \
    > evidence/dialog-trace-<ts>.log
  ```
- `dialog_initiate` × 1 以上期待 (turn は M5 以降で LLM 接続するため、
  本検証では initiate + close のシーケンスのみ)

**#5 Godot 3-avatar 30Hz**:
- MacBook 側で Godot project を起動、gateway URL を
  `ws://<G-GEAR-IP>:8000/ws/observe?subscribe=a_kant_001,a_nietzsche_001,a_rikyu_001`
  に設定
- 60s 録画 → `evidence/godot-3avatar-<ts>.mp4` として G-GEAR 側に scp 転送
  (または MacBook 側で保存後、PR に link する)
- fps counter が 28-32 を 60s 維持していることを目視確認

### Step 5: acceptance.md まとめ
`.steering/20260420-m4-acceptance-live/acceptance.md` に 5 項目の
PASS/FAIL を表形式でまとめ、不足があれば理由と対応案を記載。

**PASS 条件**:
| # | 項目 | PASS 基準 |
|---|---|---|
| 1 | /health | schema_version=0.2.0-m4 + HTTP 200 |
| 2 | 3-agent walking | 60s 以内に各 agent の agent_update + move |
| 3 | Reflection | semantic_memory に各 agent の row + origin_reflection_id |
| 4 | Dialog | dialog_initiate × 1 以上 (turn は M5) |
| 5 | Godot 30Hz | fps 28-32 を 60s 維持 (目視) |

### Step 6: FAIL 時の扱い
- FAIL した項目は acceptance.md に root cause + 修正 PR 案を記載
- 修正不要 (v0.2.0-m4 範囲外) なら "deferred to M5+" と明記
- 全項目 PASS なら次 Step へ、一部 FAIL でも evidence は commit する

### Step 7: commit + PR
```bash
git add -A
git commit -m "chore(m4): live validation evidence — 3-agent acceptance" \
  # conventional commit、本文に PASS/FAIL サマリを記載
git push -u origin feature/m4-acceptance-live-evidence
gh pr create --base main --title "chore(m4): live validation evidence — 3-agent acceptance" \
  --body ...  # live-checklist と acceptance.md を参照する形で
```

### Step 8: v0.2.0-m4 タグ付与の判断
5 項目全て PASS の場合:
- PR merge 後、main で `git tag -a v0.2.0-m4 -m "M4 milestone: 3-agent
  reflection/dialog/orchestrator"` → `git push origin v0.2.0-m4`
- タグ判断はユーザー確認を仰ぐ (auto では打たない)

## セキュリティ / 運用上の注意
- `var/m4-live.db` は evidence dump 後に削除するか gitignore 済みか確認
  (reflection summary に LLM 応答の raw text が含まれるため)
- gateway は `0.0.0.0:8000` で listen、LAN 内からアクセス可能。G-GEAR の
  firewall で LAN 外からの接続を遮断していることを確認
- `evidence/*.log` は envelope raw JSON を含む — 個人特定情報は
  デモデータなので含まれないが、PR 公開前に長大な log は
  `evidence/summary.md` にサマリ化して log 本体は sparse 化

## ベースライン
- main HEAD: `51b282a` (PR #48 merge)
- pytest baseline: **503 passed / 20 skipped**
- SCHEMA_VERSION: `0.2.0-m4`
- 前タスク (MacBook): `.steering/20260420-m4-multi-agent-orchestrator/`

上記に従って進めて。まずは Step 0 (git 同期) から。
FAIL 時は勝手に修正せずユーザー確認を仰ぐこと (live 検証はボトルネック
診断が目的で、コード修正は MacBook 側の別 PR で)。
```

---

## このファイルについて

`.steering/_handoff-g-gear-m4-live-validation.md` として保存。
G-GEAR 側で次セッション開始時に Read すれば全文が見える。
ユーザーが上記プロンプト部分をコピペするのが確実。
