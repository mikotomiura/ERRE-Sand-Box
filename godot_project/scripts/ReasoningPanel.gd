# ReasoningPanel — M6-B-2 xAI side panel for the Research Observatory.
#
# Subscribes to ``EnvelopeRouter`` and renders the most recent
# :class:`ReasoningTrace` + :class:`ReflectionEvent` for a single focused
# agent. Acts as the primary "why did this agent decide that" surface for
# the researcher.
#
# Display contract:
#   * Title line        — ``agent_id`` + current ERRE mode.
#   * Salient           — what the LLM flagged as most attention-grabbing.
#   * Decision          — the one-sentence rationale.
#   * Next intent       — forward-looking plan for the coming ticks.
#   * Latest reflection — collapsible summary of the most recent
#                         :class:`ReflectionEvent` (from M4 Reflector,
#                         wired over the wire in M6-A-4).
#
# Focus selection is intentionally simple in this first cut: the panel
# locks onto the first ``reasoning_trace`` it ever sees and sticks with
# that agent unless ``set_focused_agent`` is called. A future
# SelectionManager (M6-B-1 follow-up) can drive ``set_focused_agent`` from
# avatar click events.
extends Control

@export var router_path: NodePath

var _focused_agent: String = ""
var _title_label: Label
var _mode_label: Label
var _salient_label: Label
var _decision_label: Label
var _intent_label: Label
var _reflection_label: Label
var _last_reflection_tick: int = -1


func _ready() -> void:
	_build_tree()
	var router := _resolve_router()
	if router == null:
		push_error("[ReasoningPanel] EnvelopeRouter not found at %s" % router_path)
		return
	for signal_name in ["reasoning_trace_received", "reflection_event_received"]:
		if not router.has_signal(signal_name):
			push_error("[ReasoningPanel] router missing signal: %s" % signal_name)
			return
	router.reasoning_trace_received.connect(_on_reasoning_trace_received)
	router.reflection_event_received.connect(_on_reflection_event_received)


func _resolve_router() -> Node:
	if router_path != NodePath(""):
		var node := get_node_or_null(router_path)
		if node != null:
			return node
	return get_tree().root.find_child("EnvelopeRouter", true, false)


func _build_tree() -> void:
	# Anchor the panel to the right edge, 420 px wide, full height. Padding
	# inside is handled by margin containers so the labels wrap naturally.
	anchor_left = 1.0
	anchor_right = 1.0
	anchor_top = 0.0
	anchor_bottom = 1.0
	offset_left = -420.0
	offset_right = -10.0
	offset_top = 10.0
	offset_bottom = -10.0

	var bg := ColorRect.new()
	bg.color = Color(0.06, 0.07, 0.10, 0.85)
	bg.anchor_right = 1.0
	bg.anchor_bottom = 1.0
	bg.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(bg)

	var margin := MarginContainer.new()
	margin.anchor_right = 1.0
	margin.anchor_bottom = 1.0
	margin.add_theme_constant_override("margin_left", 12)
	margin.add_theme_constant_override("margin_right", 12)
	margin.add_theme_constant_override("margin_top", 12)
	margin.add_theme_constant_override("margin_bottom", 12)
	add_child(margin)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 10)
	margin.add_child(vbox)

	_title_label = _make_label(vbox, "Reasoning Panel", 18, Color(0.9, 0.92, 0.95, 1.0))
	_mode_label = _make_label(vbox, "(no agent selected)", 12, Color(0.65, 0.75, 0.9, 1.0))
	vbox.add_child(_make_divider())

	_make_label(vbox, "SALIENT", 11, Color(0.8, 0.7, 0.4, 1.0))
	_salient_label = _make_label(vbox, "—", 14, Color(0.95, 0.95, 0.95, 1.0))

	_make_label(vbox, "DECISION", 11, Color(0.8, 0.5, 0.5, 1.0))
	_decision_label = _make_label(vbox, "—", 14, Color(0.95, 0.95, 0.95, 1.0))

	_make_label(vbox, "NEXT INTENT", 11, Color(0.4, 0.8, 0.6, 1.0))
	_intent_label = _make_label(vbox, "—", 14, Color(0.95, 0.95, 0.95, 1.0))

	vbox.add_child(_make_divider())

	_make_label(vbox, "LATEST REFLECTION", 11, Color(0.6, 0.7, 0.9, 1.0))
	_reflection_label = _make_label(vbox, "(none yet)", 13, Color(0.85, 0.85, 0.9, 1.0))


func _make_label(parent: Node, text: String, size: int, col: Color) -> Label:
	var lbl := Label.new()
	lbl.text = text
	lbl.add_theme_font_size_override("font_size", size)
	lbl.add_theme_color_override("font_color", col)
	lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	parent.add_child(lbl)
	return lbl


func _make_divider() -> HSeparator:
	var sep := HSeparator.new()
	sep.add_theme_constant_override("separation", 6)
	return sep


# ---- Focus API ----


func set_focused_agent(agent_id: String, _agent_node: Node3D = null) -> void:
	# Second arg is ignored; accepting it lets the panel bind directly to
	# SelectionManager.selected_agent_id(agent_id, agent_node) without an
	# adapter node in MainScene. A future version can use the node to show
	# per-agent persona colouring.
	if agent_id == _focused_agent:
		return
	_focused_agent = agent_id
	_salient_label.text = "—"
	_decision_label.text = "—"
	_intent_label.text = "—"
	_reflection_label.text = "(none yet)"
	_last_reflection_tick = -1
	_title_label.text = "Reasoning Panel — %s" % agent_id if agent_id != "" else "Reasoning Panel"
	_mode_label.text = "(waiting for trace)"


# ---- EnvelopeRouter signal handlers ----


func _on_reasoning_trace_received(agent_id: String, tick: int, trace: Dictionary) -> void:
	# Auto-focus on the first agent we ever see so the panel is useful
	# without a separate selection flow. A later SelectionManager can call
	# ``set_focused_agent`` to override.
	if _focused_agent == "":
		set_focused_agent(agent_id)
	if agent_id != _focused_agent:
		return
	var mode: String = trace.get("mode", "")
	_mode_label.text = "mode: %s   |   tick: %d" % [mode, tick]
	_salient_label.text = _coalesce(trace.get("salient"), "—")
	_decision_label.text = _coalesce(trace.get("decision"), "—")
	_intent_label.text = _coalesce(trace.get("next_intent"), "—")


func _on_reflection_event_received(
	agent_id: String,
	tick: int,
	summary_text: String,
	_event: Dictionary,
) -> void:
	if _focused_agent == "":
		set_focused_agent(agent_id)
	if agent_id != _focused_agent:
		return
	# Reflection events can arrive out of order after a reconnect; keep the
	# latest by tick so we never regress to an older summary.
	if tick < _last_reflection_tick:
		return
	_last_reflection_tick = tick
	_reflection_label.text = summary_text if summary_text != "" else "(empty summary)"


func _coalesce(value: Variant, fallback: String) -> String:
	if value == null:
		return fallback
	if value is String and value == "":
		return fallback
	return str(value)
