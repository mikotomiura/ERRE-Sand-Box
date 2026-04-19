# 設計 v1 (初回案) — 素直な「ひとつの大きな関数」

> **状態**: 破棄 (reimagine 後)
> これを破壊し v2 を再生成 → `design-comparison.md` で比較、`design.md` に
> 採用版 (v2) を記録する。

## 1. 全体構造

```
src/erre_sandbox/cognition/
├── __init__.py
└── cycle.py               # 1 ファイルにすべて
```

全てを `cycle.py` の 1 関数に詰め込む素直案。

## 2. API

```python
# src/erre_sandbox/cognition/cycle.py
from __future__ import annotations

import asyncio
import logging
import math
import random
import re
from typing import Any

from erre_sandbox.inference import OllamaChatClient, compose_sampling
from erre_sandbox.memory import MemoryStore, Retriever
from erre_sandbox.schemas import (
    AgentState, Observation, PersonaSpec, Zone,
    MoveMsg, SpeechMsg, AnimationMsg, AgentUpdateMsg, ControlEnvelope,
)

logger = logging.getLogger(__name__)


async def run_cognition_cycle(
    state: AgentState,
    observations: list[Observation],
    persona: PersonaSpec,
    *,
    retriever: Retriever,
    store: MemoryStore,
    llm: OllamaChatClient,
) -> tuple[AgentState, list[ControlEnvelope]]:
    """Run one 10-second cognition cycle."""
    try:
        # Step 1: write observations
        for obs in observations:
            importance = _estimate_importance(obs)
            await _write_memory(obs, importance, store)

        # Step 2: update physical
        new_physical_dict = {}
        for field in ["sleep_quality", "physical_energy", "mood_baseline", "cognitive_load", "fatigue"]:
            prev = getattr(state.physical, field)
            new_physical_dict[field] = prev * 0.95 + random.gauss(0, 0.02)
        new_physical = state.physical.model_copy(update=new_physical_dict)

        # Step 3: retrieve
        query = " ".join(o.content for o in observations if hasattr(o, "content"))
        memories = await retriever.retrieve(state.agent_id, query)

        # Step 4: build prompt
        system_prompt = (
            f"You are {persona.display_name} ({persona.era}).\n"
            f"Habits: {persona.cognitive_habits}\n"
            f"State: {state.model_dump_json()}\n"
            f"Memories: {[m.entry.content for m in memories]}\n"
        )
        user_prompt = f"Observations: {observations}\nWhat do you do next?"

        # Step 5: LLM call
        sampling = compose_sampling(persona.default_sampling, state.erre.sampling_overrides)
        resp = await llm.chat(
            [{"role": "system", "content": system_prompt},
             {"role": "user", "content": user_prompt}],
            sampling=sampling,
        )

        # Step 6: parse free text with regex
        utterance_match = re.search(r"SPEAK:\s*(.*)", resp.content)
        utterance = utterance_match.group(1) if utterance_match else None
        dest_match = re.search(r"GO:\s*(\w+)", resp.content)
        destination = dest_match.group(1) if dest_match else None

        # Step 7: update cognitive (pseudo)
        new_valence = state.cognitive.valence + random.gauss(0, 0.1)
        new_valence = max(-1.0, min(1.0, new_valence))
        new_cognitive = state.cognitive.model_copy(update={"valence": new_valence})

        # Step 8: build envelopes
        new_state = state.model_copy(update={
            "tick": state.tick + 1,
            "physical": new_physical,
            "cognitive": new_cognitive,
        })
        envelopes: list[ControlEnvelope] = [
            AgentUpdateMsg(tick=new_state.tick, agent_state=new_state)
        ]
        if utterance:
            envelopes.append(SpeechMsg(
                tick=new_state.tick, agent_id=state.agent_id,
                utterance=utterance, zone=state.position.zone,
            ))
        if destination:
            envelopes.append(MoveMsg(
                tick=new_state.tick, agent_id=state.agent_id,
                target=state.position.model_copy(update={"zone": destination}),
                speed=1.3,
            ))
        return new_state, envelopes

    except Exception as e:
        logger.warning("Cognition cycle failed, continuing current action: %s", e)
        return state, [AgentUpdateMsg(tick=state.tick + 1, agent_state=state)]


def _estimate_importance(obs: Observation) -> float:
    return 0.5  # TODO


async def _write_memory(obs: Observation, importance: float, store: MemoryStore) -> None:
    ...  # TODO
```

## 3. 弱点 (v1 を破壊する理由)

| # | 弱点 | 深刻度 | 影響 |
|---|---|---|---|
| V1-W1 | 1 関数 200+ 行、テストで部分モックが困難 | 致命 | state 更新だけテストしたいのに LLM / DB を全部モック必要 |
| V1-W2 | 自由テキスト + regex で `utterance` / `destination` 抽出 | 致命 | LLM が行頭に空白入れるだけで破綻、多言語で崩壊、テストは正規表現の仕様テストに堕ちる |
| V1-W3 | 状態遷移の物理式がべた書き (`prev * 0.95 + gauss(0, 0.02)`) | 高 | CSDG 半数式 (`base = prev*(1-decay) + event_impact*event_weight`) の公式に沿っていない、4 要素導出 (sleep/energy/mood/load の依存連鎖) も実装されていない |
| V1-W4 | 戻り値 `tuple[AgentState, list[ControlEnvelope]]` | 高 | どれが move か speech かを呼び出し側が `isinstance` で分岐、`llm_fell_back` のような副次情報を side-channel で返せない |
| V1-W5 | `random.gauss(0, 0.02)` を global 呼び出し | 高 | テストで再現性がない、seed 注入できない、ガウスノイズの回帰防止が成立しない |
| V1-W6 | `except Exception as e:` でエラー握りつぶし | 致命 | 本来バグである `AttributeError` / `KeyError` もサイレントに「継続」扱い。crash-loud 原則違反 (error-handling Skill §ルール 5 の ValidationError 限定 fallback に反する) |
| V1-W7 | `importance = 0.5` のプレースホルダ | 中 | Retriever のランキング品質が event_type 独立に退化、peripatos 入室イベントが散歩中の発話と同じ重要度になる |
| V1-W8 | system prompt が 1 文字列 f-string | 中 | docstring ルール / persona-erre Skill §ルール 3 の fact/legend/speculative 注記を反映できず、RadixAttention prefix 最適化 (共通 prefix → ペルソナ固有) も崩れる |
| V1-W9 | `llm_fell_back` フラグを外に出せない | 中 | T14 gateway で「このサイクルは継続フォールバック」と metrics に残せない、debug 困難 |
| V1-W10 | `ChatMessage(role=..., content=...)` を dict で手書き | 低 | T11 で `ChatMessage` Pydantic 型を契約として提供済なのに dict で渡して型安全性を捨てる |
| V1-W11 | 重要度・プロンプト・パースが cycle 内 private に埋もれる | 中 | M4+ で importance を LLM scoring に切り替える・prompt を RadixAttention-aware に改修する時に cycle.py 全体を書き直す羽目になる |
| V1-W12 | Reflection トリガーが未実装 | 中 | peripatos/chashitsu 入室時の自由連想 window が発火しない、MVP 仕様 §2.58 と不整合 |

### 弱点サマリ

致命: V1-W1 / V1-W2 / V1-W6 (3 件)
高: V1-W3 / V1-W4 / V1-W5 (3 件)
中: V1-W7 / V1-W8 / V1-W9 / V1-W11 / V1-W12 (5 件)
低: V1-W10 (1 件)

→ **v1 はそのまま採用できない**。特に (a) テスト可能性 (W1), (b) 構造化パース
(W2), (c) エラー握りつぶし (W6) の 3 つはプロジェクト原則に反する。

## 4. v1 を破棄する

/reimagine で再設計:

1. **5 モジュール分割** (state / prompting / parse / importance / cycle) で
   純粋関数を部分テスト可能にする
2. **LLM 出力は JSON を指示 + Pydantic (`LLMPlan`) でパース**、失敗時は fallback
   明示 (regex を完全排除)
3. **CSDG 半数式を pure function に抽出**、RNG をコンストラクタ注入で決定論化
4. **`CycleResult` Pydantic 戻り型**で envelopes + new_memory_ids + llm_fell_back
   フラグを構造化
5. **例外は種類別 catch** (OllamaUnavailableError / EmbeddingUnavailableError /
   ValidationError のみ fallback、それ以外は crash-loud)
6. **Reflection トリガー検出は cycle で実装、実行は M4+ に送り、ログ + metric
   として記録**

採用版は `design.md`、比較表は `design-comparison.md` を参照。
