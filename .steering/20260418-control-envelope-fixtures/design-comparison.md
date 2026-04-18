# T07 control-envelope-fixtures — 設計案比較

## v1（初回案）の要旨

pytest コンベンションに沿い `tests/fixtures/control_envelope/` 配下に
minimal な 7 JSON を配置し、`tests/test_envelope_fixtures.py` が
glob で読み込んで TypeAdapter validate + round-trip を検証する
**pytest-centric test fixture** 設計。README なし、値は validator 通過の最小限、
各 fixture は独立し物語的整合なし。

## v2（再生成案）の要旨

`fixtures/control_envelope/` を `personas/` と並ぶ top-level **first-class
契約リポジトリ** に格上げする。7 fixture を「Kant が peripatos で歩行しつつ
発話する」一貫シナリオのスナップショット群として realistic 値で記述。
Godot-first README でファイル目的・GDScript/Python 両側の消費パターン・
schema_version bump 時の運用規則を解説。pytest は parametrize で 1 ファイル
1 テスト ID 化して可視化。repository-structure.md に top-level dir 追加を記録。

## 主要な差異

| 観点 | v1 | v2 |
|---|---|---|
| 設計思想 | pytest-centric test fixture | Contract-repository-first (多者利用の正式資産) |
| 配置場所 | `tests/fixtures/control_envelope/` | `fixtures/control_envelope/` (top-level、personas/ と並列) |
| README | なし | Godot-first ガイド (目的 / GDScript サンプル / Python サンプル / 更新規則) |
| 内容 | minimal-validator-passing な値 | realistic coherent scenario (Kant が peripatos を歩行する 1 シーン) |
| 物語的整合性 | 各 fixture 独立、共通文脈なし | 全 7 fixture が同一 tick / agent_id / wall_clock のスナップショット |
| speech の値 | プレースホルダー | Kant 原典 (Kritik praktischen Vernunft 結語) の German 断片 |
| AgentState (agent_update) | minimal デフォルト | peripatetic mode / Kant physical-cognitive prof / peripatos position |
| pytest テスト書き方 | 通常の関数テスト 5 件 | parametrize で 1 ファイル 1 ID 3 件 + 非 param 2 件 |
| kind filename 一致検証 | あり | あり (parametrize 内で明示) |
| Godot 側参照性 | 低 (tests/ は「テスト用」) | 高 (README + fixture リポジトリの位置付け) |
| 後続拡張性 (Observation / MemoryEntry) | tests/ 配下に追加することになる | `fixtures/{domain}/` の階層パターン確立、将来追加が自然 |
| repository-structure.md 更新 | なし | §1 ツリー + §2 責務表に `fixtures/` を追記 |
| 変更規模 | 7 JSON + 1 test + Skill | 7 JSON + 1 README + 1 test + Skill + repo-structure 追記 |
| Kant 持続性への接続 | persona_id="kant" 言及のみ | Kant 伝記 (peripatos 15:30、deutsche Rede) が value に染み出す |
| 整合性テスト | filename-kind、round-trip | 上記 + schema_version + agent_update.persona_id="kant" + 全 kind 網羅 |

## 評価（各案の長所・短所）

### v1 の長所
- pytest の慣習に従っており新規導線が少ない
- 実装量が軽い (README / repository-structure.md 変更なし)
- minimal 値なので schema 変更時に値をいじる手間が最小

### v1 の短所
- **requirement.md §背景の 3 目的のうち 2 (Godot dev reference) に応えきれない**:
  「両言語から読める」「Godot developer が Python 依存なしで読める形式 + 場所 + README」と明記されているのに、pytest 配下配置 + README なしは読者文脈を弱める
- minimal 値の fixture は「実データで Godot を動かしてみる」テスト用途に不足
- 各 fixture 独立で物語がないため、Godot 開発者が複数ファイルを並べて読んでも 1 シーンが立ち上がらない
- 後続の Observation / MemoryEntry fixture の配置方針が未決

### v2 の長所
- **requirement.md §スコープに書かれている `fixtures/control_envelope/` + README を素直に満たす**
- `personas/` との配置パラレル性により「ERRE-Sandbox のドメイン資産は top-level に置く」パターンを統一 (kant.yaml と同じ方針)
- realistic coherent scenario が Godot/Python 両開発者に「実データで触れる reference」として機能
- parametrize による 1 ファイル 1 テスト ID で CI 失敗時の原因特定が速い
- repository-structure.md の更新で将来の `fixtures/observation/` / `fixtures/memory/` 拡張が自然
- T06 の「contract specimen としての persona YAML」方針と同一精神

### v2 の短所
- 変更規模が v1 の 1.4 倍 (README + repo-structure.md 追記が増える)
- realistic 値 (Kant persona 依存) が agent_update.json を他より長く (~40 行) する
- Kant 原典の German fragment を使うと将来 persona を Nietzsche 等に差し替える時に書き直し必要
- top-level `fixtures/` 新規追加で repo ルートの cognitive load が増える (既存は `personas/` / `corpora/` のみ)

## 推奨案

**v2 を採用** — 理由:

1. **requirement.md § 背景 / §スコープが明示的に v2 を要求している**:
   「両言語から読める JSON fixture」「Godot 開発者が Python 依存なしで読める
   形式 + 場所 + README」「`fixtures/control_envelope/` 配下」と明記されており、
   v1 の `tests/fixtures/` + README なし構成は要件を満たしていない

2. **`personas/` との一貫した方針**:
   T06 で確立した「top-level のドメイン資産 (persona YAML)」パターンを
   fixture にも適用すると、ERRE-Sandbox のリポジトリが「言語中立な
   契約資産 + 言語別テスト/実装」の二層構造として理解しやすくなる

3. **Contract-First 精神の実装層への浸透**:
   T05 schemas-freeze で立てた Contract-First の方針を、T07 でも
   「fixtures = contract の具体例」と位置付けることで一貫させる。
   tests/ に閉じ込めると「Python 側のテストデータ」に格下げされ、
   Godot 側から見えづらくなる

4. **realistic scenario の価値**:
   Godot 開発者が T16 を実装する時に「まず peripatos で Kant が
   歩いているシーンを動かす」ことから始められる。minimal 値では
   「まず何を表示させれば良いか」の判断材料が足りない

5. **v2 の短所は対処可能**:
   - 変更規模の 1.4 倍は設計意図を明確化するコストとして適正
   - Kant 依存部分は README で「persona 差し替え時は本 fixture も更新」と
     明記すれば管理可能
   - 将来の拡張 (`fixtures/observation/` 等) は v2 の階層パターンで
     自然に収まる

**ハイブリッド不採用の理由**:
v1 の「tests/fixtures/ 配置」と v2 の「README あり + realistic content」を
混ぜると「テスト専用 dir に README と realistic 値を置く」という中途半端な
構成になり、Godot 開発者から見えにくいまま README だけが浮く。
全体を v2 で揃える方が整合。
