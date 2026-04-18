# T06 persona-kant-yaml — 設計案比較

## v1（初回案）の要旨

Kuehn 2001 を中心に Kant の伝記事実を 6 件の `cognitive_habit` として列挙する
**documentary** な設計。habit は生活日程の分解 (起床 / 朝書き / 講義 / 夕食 /
非旅行 / 鼻呼吸) を並べる biographical-schedule 的配置。
`primary_corpus_refs` は Kuehn + Kritik 3 部作を全列挙。
`default_sampling = (0.65, 0.88, 1.10)` で控えめな Kant 指紋。

## v2（再生成案）の要旨

YAML を「Kant を演じる LLM + 状態機械への operational specification」として
再定義する **operational orientation**。各 habit を
(observable trigger → behavior → mechanism → cognitive consequence) の 4 要素で
読めるよう揃え、`trigger_zone` を 6 中 5 件で埋めてスキーマ機能を活用。
`flag` を fact/legend/speculative の 3-tier 完備の見本に。
`primary_corpus_refs` は実 source で使う 4 キーのみ、Kritik 3 部作は除外。
`default_sampling = (0.60, 0.85, 1.12)` で後続 persona との温度帯を明確化。

## 主要な差異

| 観点 | v1 | v2 |
|---|---|---|
| 核となる設計思想 | documentary (伝記データ整理) | operational (シミュレーション駆動仕様) |
| habit の粒度 | 生活日程の分解 (起床・朝書き・講義・夕食・非旅行・鼻呼吸) | trigger-behavior-mechanism の 4 要素で整理された 6 件 |
| trigger_zone の活用率 | 3/6 (50%) null | 1/6 (17%) null — persona-global 属性のみ null |
| flag 分布 | fact 5 / legend 1 / speculative 0 | fact 3 / legend 2 / speculative 1 — 3-tier 見本 |
| primary_corpus_refs | Kuehn + Kritik 3 部作 + Anthropologie = 5 件 | 実 source 4 件に絞る (Kuehn + Heine + Jachmann + Anthropologie) |
| default_sampling | (0.65, 0.88, 1.10) 控えめ | (0.60, 0.85, 1.12) 差別化明確 + 後続 persona 温度帯の見取り図を提示 |
| 伝記背景の扱い | habit の列挙で暗黙に伝わる | mechanism field で認知神経科学への接続を前景化 |
| 後続 persona テンプレ適合性 | 低 (biographical-schedule は persona 固有の形式) | 高 (4 要素構造はどの persona にも転用可能) |
| Kant らしさの表現 | 「朝から晩までの詳細日程」(documentary) | 「rituals trigger cognitive modes」(operational) |
| 変更規模 | YAML 約 50 行 + test 約 80 行 | YAML 約 55 行 + test 約 100 行 |
| 観察可能性 | habit が時間帯記述中心で、ゾーン入室トリガーへの接続が弱い | trigger_zone によりゾーン入退室で即 habit 発火できる |
| 史料キー整備 | Kritik 著作キーは source 未使用で primary_corpus_refs だけに存在 | 全 primary_corpus_refs が habit.source から参照される |

## 評価（各案の長所・短所）

### v1 の長所
- 伝記データとして情報量が多い (起床時刻・講義時刻・私的時間の詳細)
- Kritik 3 部作を早期に corpus_refs に登録しておけば将来の corpora/ 整備と整合
- 生活日程の網羅性が高く、Kant 研究者に説明しやすい

### v1 の短所
- **null trigger_zone が 50%** — スキーマの `trigger_zone` フィールドが十分活用されていない
- **T11/T12 の認知サイクル駆動に弱い** — 「05:00-07:00 writing」のような時間帯 habit は 10 秒 tick のシミュレーションに落とし込みにくい
- **後続 persona テンプレとして使いにくい** — biographical-schedule は Kant 固有。Rikyu の茶道、Dogen の座禅、Nietzsche の山歩きは別フォーマットが必要になる
- **Kritik 著作キーが宙に浮く** — `primary_corpus_refs` に入っているが `cognitive_habits.source` のどこでも使われていない
- **Epistemic 3-tier の見本にならない** — legend 1 件のみ、speculative ゼロ

### v2 の長所
- **operational orientation** により T11 (LLM prompt 組み立て) / T12 (認知サイクル) / M10 (Critic の persona consistency 評価) の全てで直接利用可能
- **trigger_zone 活用率 83%** で、ゾーン入退室イベントで habit を即発火できる
- **Epistemic 3-tier 完備**で後続 persona の参考例として機能する
- **後続 persona テンプレ適合性**: 4 要素構造はどの偉人にも転用可能。次の Nietzsche YAML を書く時に「観察行動 → mechanism → 温度帯」の枠が既にある
- **温度帯見取り図**を design.md に明記することで将来の persona 衝突を予防
- **YAML が lean**: primary_corpus_refs が実 source に絞られ、冗長なし

### v2 の短所
- habit 件数は変わらないが、各 habit の情報密度が上がるため **total YAML 行数は若干増える**
- Kritik 3 部作キーが primary_corpus_refs から消えることで、Kant 研究者視点では「主著が書かれていない」印象。ただし corpora/ に実テキストを置く段階で再追加可能
- speculative flag の #6 "Königsberg radius → 空間認知 scaffold" は Constantinescu 2016 へのかなり強い interpretation を含む
- heine1834 / jachmann1804 が史料キーとして未確定

## 推奨案

**v2 を採用** — 理由:

1. **要件の「M2 E2E 駆動ソース」**という本質要求への直接応答: requirement.md §背景が
   「カント一体のペリパトス散歩 → 認知サイクル実行 → Godot 可視化」を掲げている。
   v1 の biographical-schedule は documentary として正確だが、シミュレーション駆動への
   翻訳コストが高い。v2 の operational orientation は T11/T12 が直接使える。

2. **後続 M4 persona (Nietzsche / Rikyu / Dogen / Thoreau) のテンプレート効果**:
   Kant YAML は「最初の偉人 YAML」であり、後続の参照例になる。
   v2 の 4 要素構造は汎用的で、どの偉人にも適用可能。v1 の biographical-schedule は
   Kant 固有で、他偉人 (例: Dogen の経行と作務) には使えない形式。

3. **Epistemic 3-tier の完備**: PDF §3.1 が「事実と伝説の区別フラグを必ず付す」と
   明言している。v1 は legend 1 / speculative 0 で 3-tier を体現しきれない。
   v2 は fact 3 / legend 2 / speculative 1 で 3-tier の見本として機能する。

4. **スキーマ機能の活用**: T05 で `trigger_zone` フィールドを意図的に導入した。
   v1 の null 率 50% はこの意図に反する。v2 の 17% は健全。

5. **温度帯見取り図の追記**: v2 は Kant だけでなく「後続 6-7 persona の温度レンジ」を
   明記。Contract-First と同じ精神で future-proof を最初に入れる。

**ハイブリッド不採用の理由**: v1 の「Kritik 3 部作を primary_corpus_refs に入れる」案は
v2 の「lean な refs」原則と相反する。中途半端に混ぜると整合性が崩れる。
Kritik 3 部作は corpora/ 実テキスト投入時 (M5 以降) に別タスクで追加する方が clean。
