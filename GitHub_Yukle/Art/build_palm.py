"""
Devrilmiş palmiye (Çöl Diyarı alçak engeli): yumuşak hatlı, hafif kavisli gövde (belli belirsiz halkalar),
ucunda geniş, parlak, kenarı birkaç yerden çentikli yapraklar ve küçük hindistan cevizleri. Kök yoktur.
Gövde X yönünde yerde yatar (uç +X tarafında), zemin z=0. Üzerinden zıplanır, en fazla ~0.55 birim yüksektir.
Çalıştırma: PALM_FBX, PALM_BLEND, PALM_PREVIEW ortam değişkenleriyle blender -b -P build_palm.py
Nesne adları "RenkAnahtarı_Parça" biçimindedir (renkleri Unity kodla verir, bkz. ModelPalette.cs).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bmesh
import bpy
from mathutils import Vector

import modeling as m

FBX_PATH = os.environ["PALM_FBX"]
BLEND_PATH = os.environ["PALM_BLEND"]
PREVIEW_DIR = os.environ["PALM_PREVIEW"]

m.reset_scene()

for key, rgb in {
    "Trunk": (0.8, 0.45, 0.17), "TrunkLight": (0.86, 0.53, 0.22), "TrunkRing": (0.62, 0.33, 0.12),
    "Leaf": (0.38, 0.8, 0.12), "LeafDark": (0.26, 0.66, 0.1), "LeafLight": (0.52, 0.88, 0.2),
    "Coconut": (0.45, 0.27, 0.12), "Sand": (0.95, 0.82, 0.58),
}.items():
    m.material(key, rgb)

root = m.make_root("PalmRoot")


def part(name, bm, key):
    return m.finish(name, bm, key, (0, 0, 0), root)


def leaf(origin, direction, length, width, droop, notches=(), steps=14):
    """Geniş, kavisli yaprak. Ortası hafif kabarık, kenarları aşağı kıvrık ince bir kalıp.
    notches: (istasyon, taraf) çiftleri; o noktada kenar içeri çekilir ve çentik oluşur (taraf +1 / -1).
    Yere değen kısım kumun üstüne serilir."""
    bm = bmesh.new()
    d = Vector(direction).normalized()
    side = d.cross(Vector((0, 0, 1)))
    side = side.normalized() if side.length > 1e-3 else Vector((0, 1, 0))
    up = side.cross(d).normalized()
    if up.z < 0:
        up = -up
    thick = 0.014
    rings = []
    for i in range(steps + 1):
        s = i / steps
        c = Vector(origin) + d * length * s + Vector((0, 0, -droop * s * s))
        c.z = max(c.z, 0.03)
        w = width * math.sin(math.pi * (0.06 + 0.94 * s)) ** 0.75 + 0.004
        wl = w * (0.68 if (i, 1) in notches else 1.0)
        wr = w * (0.68 if (i, -1) in notches else 1.0)
        top = [
            c + side * wl - up * 0.22 * wl,
            c + side * 0.5 * wl + up * 0.02,
            c + up * 0.03,
            c - side * 0.5 * wr + up * 0.02,
            c - side * wr - up * 0.22 * wr,
        ]
        bottom = [top[3] - up * thick, top[2] - up * thick, top[1] - up * thick]
        rings.append([bm.verts.new(v) for v in top + bottom])
    n = len(rings[0])
    for i in range(steps):
        for k in range(n):
            j = (k + 1) % n
            bm.faces.new((rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    return bm


def trunk_center(t):
    """t=0 dip, t=1 uç. Gövde yerde yatar, uca doğru hafifçe kalkar ve yana kıvrılır."""
    return Vector((-0.5 + 0.85 * t, 0.05 * math.sin(t * math.pi), 0.15 + 0.1 * t * t))


def trunk_radius(t):
    return 0.15 - 0.045 * t


# Tek parça gövde: her halkanın ucunda hafif bir kabarma, ardından küçük bir iniş (belli belirsiz halkalar)
segments = 7
path, radii = [], []
for i in range(segments):
    for f, bump in ((0.0, 0.965), (0.55, 1.0), (0.9, 1.04)):
        t = (i + f) / segments
        path.append(tuple(trunk_center(t)))
        radii.append(trunk_radius(t) * bump)
path.append(tuple(trunk_center(1.0)))
radii.append(trunk_radius(1.0) * 0.95)
part("Trunk_Body", m.loft(path, radii, 12), "Trunk")

# Dip tarafında açık renkli kesik yüzey
base = trunk_center(0.0)
part("TrunkLight_Cut", m.loft([(base.x - 0.012, base.y, base.z), (base.x + 0.004, base.y, base.z)], [0.135, 0.135], 12), "TrunkLight")

# Uçtaki yaprak topuzu ve küçük hindistan cevizleri
tip = trunk_center(1.0)
crown = (tip.x + 0.03, tip.y, tip.z + 0.01)
part("Trunk_Crown", m.sphere(0.1, (1.1, 1.0, 1.0), 2, crown), "Trunk")
for i, (dy, dz) in enumerate(((0.07, -0.08), (-0.06, -0.09), (0.0, -0.13))):
    part("Coconut_%d" % i, m.sphere(0.05, (1, 1, 1.05), 2, (crown[0] + 0.05, crown[1] + dy, crown[2] + dz)), "Coconut")

# Yapraklar: (yön, uzunluk, genişlik, sarkma, çentikler, renk)
leaves = [
    ((0.45, 1.0, 0.35), 0.66, 0.17, 0.4, ((12, 1),), "Leaf"),
    ((0.45, -1.0, 0.4), 0.68, 0.17, 0.4, ((11, -1), (13, 1)), "LeafDark"),
    ((0.5, 0.5, 0.95), 0.6, 0.16, 0.42, ((12, 1),), "LeafLight"),
    ((0.55, -0.55, 0.9), 0.58, 0.16, 0.42, ((12, -1),), "Leaf"),
    ((1.0, 0.1, 0.45), 0.64, 0.17, 0.36, ((11, 1), (13, -1)), "LeafDark"),
]
for i, (direction, length, width, droop, notches, key) in enumerate(leaves):
    part("%s_Leaf%d" % (key, i), leaf(crown, direction, length, width, droop, set(notches), 16), key)

# Yumuşak gölgelendirme (çizgi film görünümü)
for obj in m.all_objects():
    for poly in obj.data.polygons:
        poly.use_smooth = True

# Yalnızca önizleme için kum zemin (dışa aktarılmaz)
ground = bmesh.new()
bmesh.ops.create_grid(ground, x_segments=1, y_segments=1, size=3.0)
ground_mesh = bpy.data.meshes.new("PreviewGround")
ground.to_mesh(ground_mesh)
ground.free()
ground_obj = bpy.data.objects.new("PreviewGround", ground_mesh)
ground_obj.data.materials.append(m.material("Sand", (0.95, 0.82, 0.58)))
bpy.context.collection.objects.link(ground_obj)

m.render_views("palm", PREVIEW_DIR, [
    ("player", (0.0, -3.0, 1.4)),
    ("side", (2.4, -1.9, 1.0)),
], target=(0.05, 0, 0.2), size=(700, 600), background=(0.96, 0.86, 0.66), lens=50, gain=1.15)

bpy.ops.object.select_all(action="DESELECT")
root.select_set(True)
for obj in m.all_objects():
    obj.select_set(True)

os.makedirs(os.path.dirname(FBX_PATH), exist_ok=True)
bpy.ops.export_scene.fbx(
    filepath=FBX_PATH, use_selection=True, object_types={"MESH", "EMPTY"},
    apply_unit_scale=True, bake_space_transform=True, axis_forward="-Z", axis_up="Y",
    mesh_smooth_type="FACE", add_leaf_bones=False,
)
bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
