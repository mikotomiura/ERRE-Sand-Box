# Strings — UI locale dictionary (M7-ζ-1 Live Resonance).
#
# All ReasoningPanel / DebugOverlay user-facing strings live in a single
# const dict so the JP <-> EN swap (or future ``tr()`` migration) needs
# only one file edit. We do **not** introduce a Godot ``.csv``
# localisation pipeline because the live-resonance scope is ≤15 labels —
# translation tooling cost would dwarf it. When the project does adopt
# full i18n (post-M11), this dict becomes the seed for the locale CSV
# and consumer call-sites swap to ``tr()`` mechanically.
#
# Live-verification context: 2026-04-22 issue "LATEST REFLECTION 内の
# 文字が英語なので日本語に" — see
# ``.steering/20260426-m7-slice-zeta-live-resonance/requirement.md``
# §"軸 C の根本原因" C6.
extends RefCounted

const LABELS: Dictionary = {
	# Reasoning panel — section headers
	"SALIENT": "気づき",
	"DECISION": "判断",
	"NEXT_INTENT": "次の意図",
	"LATEST_REFLECTION": "最新の反省",
	"RELATIONSHIPS": "関係性",
	# Reasoning panel — title & status
	"PANEL_TITLE": "Reasoning Panel",
	"PANEL_TITLE_FOR_AGENT": "Reasoning Panel — %s",
	"PANEL_TITLE_FOR_AGENT_PERSONA": "Reasoning Panel — %s (%s)",
	"AGENT_NONE": "(エージェント未選択)",
	"AGENT_WAITING": "(トレース待ち)",
	"AGENT_MODE_TICK": "モード: %s   |   tick: %d",
	# Reasoning panel — empty / fallback states
	"REFLECTION_NONE": "(まだなし)",
	"REFLECTION_EMPTY_SUMMARY": "(空の要約)",
	"RELATIONSHIPS_NONE": "(対話なし)",
	"VALUE_DASH": "—",
	# Agent selector
	"SELECTOR_PROMPT": "(エージェント選択)",
}
