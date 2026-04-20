# 設計案比較 — m4-cognition-reflection

## v1 (初回案) の要旨

`CognitionCycle.step()` の末尾に「step 10. Reflection execution」を
inline で追加する案。`ClassVar` で tick interval / episodic window を定義し、
発火条件は `importance_sum > T or zone_entered or (tick > 0 and tick % N == 0)` を
`_detect_reflection_trigger` 内で OR 合流。LLM 蒸留・埋め込み・
semantic_memory 書き込みを `CognitionCycle` 内のヘルパー methods として
実装し、reflection prompt は既存 `prompting.py` に新 function を追加。

## v2 (再生成案) の要旨

reflection を **`Reflector` collaborator** に分離し、pure な
`ReflectionPolicy` (dataclass) が発火条件を判断する案。
`CognitionCycle` は policy や counter を持たず、`reflector.maybe_reflect(...)`
を step 末尾で delegate するだけ。per-agent の tick counter は Reflector
内で管理し、`tick % N` 方式の multi-agent 想定脆弱性を回避。
LLM / embedding の失敗は Reflector 内で swallow し `None` を返す。
新規ファイル `cognition/reflection.py` + `tests/test_cognition/test_reflection.py`。

## 主要な差異

| 観点 | v1 | v2 |
|---|---|---|
| **アプローチ** | CognitionCycle に inline 追加 | 専用 Reflector collaborator に委譲 |
| **発火条件の表現** | `ClassVar` 定数 + `_detect_reflection_trigger` 関数 | `ReflectionPolicy` (dataclass) の pure method |
| **N tick の実装** | `tick % N == 0 and tick > 0` (global tick 依存) | per-agent counter `_ticks_since[agent_id]` |
| **Multi-agent 耐性** | global tick 前提 (#6 でリスク顕在化の可能性) | per-agent 独立 (#6 でそのまま通用) |
| **テスト容易性** | CognitionCycle 経由でしかテストできない | Reflector 単体テスト可 (11 本の独立 test) |
| **public surface** | CycleResult に `reflection_event` 1 field 追加 | 同じ (契約は同一) |
| **prompt 配置** | `prompting.py` に new function 混在 | `reflection.py` に完全分離 |
| **失敗の握り潰し** | cycle.step 内で try/except | Reflector 内で try/except (境界を明確化) |
| **変更ファイル数** | 4 (cycle.py / prompting.py / test_cycle.py / architecture.md) | 7 (+ reflection.py / test_reflection.py / __init__.py / conftest.py) |
| **LOC 増加推定** | +120 LOC (cycle.py 肥大化) | +200 LOC (分散、個別は軽い) |
| **test 本数増加** | +4 本 | +12 本 (Reflector 単体で policy も網羅) |
| **既存テスト影響** | tick=0 前提のため影響なし | 同じく影響なし |
| **リスク** | cycle.py が 470 LOC → 590 LOC 級に、責務過多 | Reflector を通す indirection 追加 / 公開面増 |
| **integration (#6) との接続** | global tick の取り扱いを #6 側で吸収必須 | per-agent counter なのでそのまま通用 |

## 評価

### v1 の長所
- シンプル・変更ファイル少・レビュー量軽量
- 既存 CognitionCycle の「9 step」構造の延長上で読みやすい
- mock 構築コストが低い (既存 fixture そのまま使える)

### v1 の短所
- `CognitionCycle` が action 選択と reflection の 2 責務を持つ (責務肥大)
- `ClassVar` による policy は tests で override しにくい (subclass / monkey-patch 必要)
- `tick % N == 0` は multi-agent で tick がずれた場合や再同期時に破綻
- reflection 単体を test したいときに CognitionCycle フル構築が必要
- prompting.py に action 用と reflection 用の prompt が混在し責務が曖昧化

### v2 の長所
- 責務分離 (CognitionCycle = action selection, Reflector = distillation)
- policy が pure object として独立、テストでも prod でも差し替えやすい
- per-agent counter により #6 multi-agent 合流時の手戻りがない
- reflection の failure semantics を集中管理 (LLM / embedding 両方の失敗を
  Reflector 内で一貫処理)
- Reflector 単体の test が 11 本書け、reflection logic のカバレッジが厚い

### v2 の短所
- ファイル数が増える (+3 本)、PR review 範囲が広い
- `CognitionCycle.__init__` に新 param 追加 (default で互換は取るが、
  API 面は増える)
- "小さな PR" の観点では v1 に劣る

## 推奨案

**v2 を採用**。

### 根拠

1. **#6 (multi-agent orchestrator) との接続コストが v1 > v2**  
   Critical Path の次工程 (#6) が multi-agent。そこで `tick % N` 方式は
   agent ごとに tick がずれる瞬間 (再同期・追加・削除) に発火漏れ/重複を
   生む可能性が高い。per-agent counter は multi-agent でそのまま通用する
   ので、#5 の時点で正しい抽象を入れることが Contract-First の精神と整合。

2. **M2 で確立した injection パターンに忠実**  
   `CognitionCycle` は既に `retriever/store/embedding/llm` を injection して
   いる。reflection も同じく外から差し込めるのが一貫性。

3. **memory feedback_reimagine_trigger / _scope の意図**  
   「設計タスクでは確証バイアスを排する」ために /reimagine を適用した結果、
   責務分離の案 (v2) が浮上した。この浮上自体が /reimagine の価値。

4. **ファイル数増加のコストは低い**  
   `reflection.py` は 150-200 LOC 程度、`test_reflection.py` は単一責務で
   review は速い。`cycle.py` に 120 LOC 積むより、分散のほうが認知負荷が低い。

5. **既存テスト影響ゼロは同等**  
   両案とも既存 446 tests に手を入れない。破壊的変更のリスクは同じ。

### ハイブリッド要素 (v2 に取り込む v1 の良い点)

- v1 の「既存 `REFLECTION_IMPORTANCE_THRESHOLD` ClassVar を残す」互換措置
  は v2 にも採用 (default ReflectionPolicy が ClassVar を参照)
- v1 の「prompt を `prompting.py` に足す」は採用せず、v2 の
  `reflection.py` 内に閉じる案を維持 (責務分離を優先)
