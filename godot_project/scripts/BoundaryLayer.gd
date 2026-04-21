# BoundaryLayer — M6-B-4 xAI zone boundary wireframe.
#
# Draws a cyan rectangular outline on the ground plane for every zone defined
# in ``zone_rects``. Intended to give the researcher an at-a-glance view of
# where an agent currently is and where event boundaries (zone_transition,
# affordance radii) are being evaluated.
#
# Rendering strategy: a single :class:`ImmediateMesh` owned by one
# :class:`MeshInstance3D`. Every outline is four connected lines drawn with
# :class:`RenderingServer`-primitive ``PRIMITIVE_LINE_STRIP`` surfaces — no
# per-zone MeshInstance so the scene tree stays flat.
#
# Toggle with the ``toggle_boundary`` action (``B`` by default). The node
# starts visible because the first-run researcher benefits more from seeing
# the boundaries than from a clean view.
extends Node3D

@export var line_color: Color = Color(0.2, 0.9, 1.0, 0.9)
@export var line_height: float = 0.05

# Zone rectangles (centre_x, centre_z, size_x, size_z). Values mirror the
# ZoneManager defaults in WorldManager.gd and ``world/zones.py``; if those
# ever drift, a future task should hoist this into a shared config.
@export var zone_rects: Array = [
	# Peripatos — long corridor (matches scenes/zones/Peripatos.tscn 60x4 M6-C update)
	{"name": "peripatos", "cx": 0.0, "cz": 0.0, "sx": 60.0, "sz": 4.0},
	# Chashitsu — tea room plaza
	{"name": "chashitsu", "cx": 0.0, "cz": 15.0, "sx": 30.0, "sz": 30.0},
	# Zazen — meditation plaza
	{"name": "zazen", "cx": 0.0, "cz": -15.0, "sx": 30.0, "sz": 30.0},
	# Study — far north (approximated; becomes authored when the study
	# .blend lands in M7)
	{"name": "study", "cx": 25.0, "cz": 0.0, "sx": 18.0, "sz": 18.0},
	# Agora — far south (approximated; M7 zone)
	{"name": "agora", "cx": -25.0, "cz": 0.0, "sx": 24.0, "sz": 24.0},
]

var _mesh_instance: MeshInstance3D
var _mesh: ImmediateMesh
var _material: StandardMaterial3D


func _ready() -> void:
	_material = StandardMaterial3D.new()
	_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_material.albedo_color = line_color
	_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_material.no_depth_test = true
	_mesh = ImmediateMesh.new()
	_mesh_instance = MeshInstance3D.new()
	_mesh_instance.mesh = _mesh
	_mesh_instance.material_override = _material
	add_child(_mesh_instance)
	_redraw()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("toggle_boundary"):
		visible = not visible


func _redraw() -> void:
	_mesh.clear_surfaces()
	for zone: Dictionary in zone_rects:
		var cx: float = zone.get("cx", 0.0)
		var cz: float = zone.get("cz", 0.0)
		var sx: float = zone.get("sx", 1.0)
		var sz: float = zone.get("sz", 1.0)
		var y := line_height
		var p1 := Vector3(cx - sx * 0.5, y, cz - sz * 0.5)
		var p2 := Vector3(cx + sx * 0.5, y, cz - sz * 0.5)
		var p3 := Vector3(cx + sx * 0.5, y, cz + sz * 0.5)
		var p4 := Vector3(cx - sx * 0.5, y, cz + sz * 0.5)
		_mesh.surface_begin(Mesh.PRIMITIVE_LINE_STRIP, _material)
		_mesh.surface_add_vertex(p1)
		_mesh.surface_add_vertex(p2)
		_mesh.surface_add_vertex(p3)
		_mesh.surface_add_vertex(p4)
		_mesh.surface_add_vertex(p1)
		_mesh.surface_end()
