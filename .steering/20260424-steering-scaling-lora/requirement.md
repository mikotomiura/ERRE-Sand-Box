# L6 — Scaling / LoRA / User-Dialogue IF Roadmap

## 背景

M7 `.steering/20260424-m7-differentiation-observability/` decisions.md D2
で決定: "L6 (LoRA / scaling / user-dialogue IF) は別 steering で並行起票、
コード作業と戦略文書を混ぜない"。Slice β までで「3 agent が別生物として
振る舞う」の可視化は完了、Slice γ で「関係性」の可視化を進める。
L6 は M8+ スコープの基盤議論で、**コード作業なし、純粹に文書**。

3 軸ロードマップ:

1. **LoRA による persona 分化** — 今は 1 base model + prompt injection で
   3 agent を区別しているが、persona ごとに LoRA adapter を焼いた場合の
   差分を検討
2. **Agent scaling** — 4 agent 目以降を追加するときの、VRAM 予算 / 並列
   tick / dialog_turn ペアリング爆発を扱う方針
3. **User-dialogue IF** — 研究者が agent と対話できる口を設計。speech
   bubble / MIND_PEEK UI 経由の prompt injection / 別 channel 検討

## ゴール

M8+ の意思決定材料となる 3 本の軽量 ADR を `decisions.md` に、関連する
調査結果を `requirement.md` / `design.md` に書き下ろす。**コード変更ゼロ**。

## スコープ

### 含むもの
- 3 軸それぞれで現状 / 選択肢 / 採用予定 / 根拠 / 次アクションを ADR 形式で記述
- 関連 Skill (llm-inference, persona-erre, architecture-rules) との整合性確認
- MASTER-PLAN.md の更新提案 (必要なら)

### 含まないもの
- コード変更 (いかなる意味でも)
- H2 案が提案した "運用予算節" — CLAUDE.md と architecture-rules Skill に既記載
  のため DRY (decisions D2 参照)
- 4 節 + ADR 3 本構成は盛りすぎ、ADR 3 本を簡潔に (decisions D2 参照)

## 受け入れ条件

- [ ] `decisions.md` に 3 本の ADR (各 20 行以内)
- [ ] 各 ADR に "現状" / "選択肢" / "採用" / "根拠" / "次アクション" の 5 節
- [ ] 関連 Skill から参照リンクが張られている
- [ ] M8+ task の preconditions が明示されている
- [ ] コード差分が commit に含まれていない (branch diff が docs のみ)

## 関連ドキュメント

- 親 task: `.steering/20260424-m7-differentiation-observability/` (D2)
- MASTER-PLAN: `.steering/20260418-implementation-plan/MASTER-PLAN.md`
- 関連 Skill: `llm-inference` / `persona-erre` / `architecture-rules`
