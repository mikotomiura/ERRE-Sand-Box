# Tasklist — L6 Steering (LoRA / Scaling / User-Dialogue IF)

> 全て文書タスク、Plan mode 不要 (設計判断 ≠ 実装判断)。
> 1-2h、並走可能 (Slice β / γ の待ち時間に進められる)。

## Setup

- [ ] `feat/steering-scaling-lora` branch を main から切る
- [ ] `llm-inference` Skill を Read、VRAM 予算と現在のモデル体系を把握
- [ ] `persona-erre` Skill を Read、ERRE mode との関係を把握

## ADR 1 — LoRA による persona 分化 (30m)

- [ ] 現状: 1 base (gpt-oss:20b MoE) + prompt injection で 3 persona
- [ ] 選択肢:
  - (a) 現状維持 (prompt injection)
  - (b) persona ごとに LoRA adapter
  - (c) 混合 (一部 persona のみ LoRA、他は prompt)
- [ ] 採用 (暫定): M8 で (c) 試作、判定は 3 agent 以上に増えたときの差異観察
- [ ] 根拠: VRAM 圧と persona 分化の trade-off、学習コスト、再学習ループ
- [ ] 次アクション: M8 で LoRA spike task を立てる preconditions を明示

## ADR 2 — Agent scaling (30m)

- [ ] 現状: 3 agent 並列、10s tick、VRAM 余裕あり
- [ ] 選択肢:
  - (a) 4th persona (Socrates / 孔子 / 他) 追加
  - (b) 同 persona 複数インスタンス (Kant × 2 等)
  - (c) 現状維持、3 agent で深掘り
- [ ] 採用 (暫定): (a) を M8 で試作、ペルソナは思想史的に補完的な人物を選ぶ
- [ ] 根拠: dialog_turn 組み合わせ爆発 (3 agent = 3 pair、4 agent = 6 pair)、
      VRAM、観察可能性の劣化点
- [ ] 次アクション: candidate persona list、dialog_turn pairing scheduler の
      設計タスクを起票

## ADR 3 — User-dialogue IF (30m)

- [ ] 現状: 研究者は観察のみ、対話口なし
- [ ] 選択肢:
  - (a) Godot UI の text input box → DialogTurnMsg で特殊 agent "user" として
  - (b) MIND_PEEK UI 経由の prompt injection
  - (c) 別 WebSocket channel で user-only envelope
- [ ] 採用 (暫定): (a)、user を特殊 agent として扱うと既存 dialog_turn loop に
      最小侵襲で乗る
- [ ] 根拠: 既存 schema の再利用、affinity 測定の整合性、prompt injection は
      debug 用途に留める
- [ ] 次アクション: user agent の persona YAML 雛形、turn-taking policy、
      user 発話から動くべき agent 選定ロジックの設計タスクを起票

## Review + PR

- [ ] `decisions.md` の 3 ADR を読み直し、Skill との不整合がないか確認
- [ ] MASTER-PLAN.md に L6 完了行を追加、M8 preconditions を追記
- [ ] branch diff が **docs のみ** であることを確認 (`git diff --stat`)
- [ ] `git push -u origin feat/steering-scaling-lora`
- [ ] `gh pr create`、title `docs(steering): L6 — scaling / LoRA / user-dialogue IF roadmap`
- [ ] merge 後、本 tasklist を完了記録して close
