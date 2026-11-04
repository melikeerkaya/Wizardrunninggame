"""
Eğik palmiye (Çöl Diyarı alçak engeli): dibi bir yanda kuma gömülü, gövdesi yolun üzerinden alçak bir açıyla
uzanan, ucu öbür yanda yapraklarıyla yere yaslanan palmiye. Kök yoktur, halkalar belli belirsizdir.
Bir şerit içindir (2 birim genişlik): gövde x = -1.2'den x = +1.1'e uzanır, şeridin içinde en fazla ~1 birim yüksektir.
Z yukarı, koşu yönü +Y, zemin z=0. Üzerinden zıplanır.
Çalıştırma: PALM_FBX, PALM_BLEND, PALM_PREVIEW ortam değişkenleriyle blender -b -P build_leaning_palm.py
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
    "Trunk": (0.8, 0.45, 0.17), "TrunkLight": (0.86, 0.53, 0.22),
    "Leaf": (0.38, 0.8, 0.12), "LeafDark": (0.26, 0.66, 0.1), "LeafLight": (0.52, 0.88, 0.2),
    "Coconut": (0.45, 0.27, 0.12), "Sandstone": (0.88, 0.58, 0.4), "Sand": (0.95, 0.82, 0.58),
}.items():
    m.material(key, rgb)

root = m.make_root("LeaningPalmRoot")


def part(name, bm, key):
    return m.finish(name, bm, key, (0, 0, 0), root)


def leaf(origin, direction, length, width, droop, teeth=9):
    """Palmiye yaprağı: ince, V biçiminde katlanmış, kenarı yaprakçık uçlarıyla testere dişi gibi.
    Orta damar boyunca kavislenip sarkar; yere değen kısım kuma serilir. İki yüzlüdür (alttan da görünür)."""
    bm = bmesh.new()
    d = Vector(direction).normalized()
    side = d.cross(Vector((0, 0, 1)))
    side = side.normalized() if side.length > 1e-3 else Vector((0, 1, 0))
    up = side.cross(d).normalized()
    if up.z < 0:
        up = -up

    def rib(s):
        c = Vector(origin) + d * length * s + Vector((0, 0, -droop * s * s))
        c.z = max(c.z, 0.04)
        return c

    def envelope(s):
        return width * math.sin(math.pi * min(1.0, 0.1 + s)) ** 0.6

    steps = teeth * 2
    thick = 0.012
    top, bot = [], []
    for i in range(steps + 1):
        s = 0.05 + 0.95 * i / steps
        c = rib(s)
        # Çift adımlar yaprakçık ucu (geniş, ileri çekik), tek adımlar aradaki çentik (dar)
        tooth = i % 2 == 0 and 0 < i < steps
        w = envelope(s) * (1.0 if tooth else 0.55)
        fwd = d * (0.04 if tooth else 0.0)
        row = [
            c + side * w - up * 0.35 * w + fwd,
            c + up * 0.02,
            c - side * w - up * 0.35 * w + fwd,
        ]
        top.append([bm.verts.new(v) for v in row])
        bot.append([bm.verts.new(v - up * thick) for v in row])
    for i in range(steps):
        for k in range(2):
            bm.faces.new((top[i][k], top[i + 1][k], top[i + 1][k + 1], top[i][k + 1]))
            bm.faces.new((bot[i][k + 1], bot[i + 1][k + 1], bot[i + 1][k], bot[i][k]))
        for k in (0, 2):
            bm.faces.new((top[i][k], bot[i][k], bot[i + 1][k], top[i + 1][k]) if k == 0 else
                         (top[i + 1][k], bot[i + 1][k], bot[i][k], top[i][k]))
    tip = bm.verts.new(rib(1.0) + d * 0.08)
    for k in range(2):
        bm.faces.new((top[-1][k], tip, top[-1][k + 1]))
        bm.faces.new((bot[-1][k + 1], tip, bot[-1][k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def trunk_center(t):
    """t=0 kuma gömülü dip (sol), t=1 tepe (sağ). Gövde yavaşça yükselir ve hafifçe öne kıvrılır."""
    return Vector((-1.25 + 2.35 * t, 0.12 * math.sin(t * math.pi), -0.12 + 1.0 * t ** 1.7))


def trunk_radius(t):
    return 0.21 - 0.07 * t


# Tek parça gövde: her halkanın sonunda çok hafif bir kabarma (belli belirsiz halkalar).
# Dip kumun içinden başlar, böylece kesik ucu görünmez.
segments = 9
path, radii = [], []
for i in range(segments):
    for f, bump in ((0.0, 0.985), (0.6, 1.0), (0.92, 1.015)):
        t = (i + f) / segments
        path.append(tuple(trunk_center(t)))
        radii.append(trunk_radius(t) * bump)
path.append(tuple(trunk_center(1.0)))
radii.append(trunk_radius(1.0) * 0.95)


def trunk_loft(path, radii, segs):
    """m.loft gibi, ama halka yönü hep dünya yukarısına göre alınır; yatık gövdede kıvrılma (dikiş) olmaz."""
    bm = bmesh.new()
    rings = []
    for i, p in enumerate(path):
        p = Vector(p)
        d = (Vector(path[i + 1]) - p) if i < len(path) - 1 else (p - Vector(path[i - 1]))
        d.normalize()
        a = d.cross(Vector((0, 0, 1))).normalized()
        b = a.cross(d).normalized()
        rings.append([bm.verts.new(p + a * math.cos(2 * math.pi * k / segs) * radii[i]
                                   + b * math.sin(2 * math.pi * k / segs) * radii[i]) for k in range(segs)])
    for i in range(len(rings) - 1):
        for k in range(segs):
            j = (k + 1) % segs
            bm.faces.new((rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


part("Trunk_Body", trunk_loft(path, radii, 14), "Trunk")

# Dibin gömüldüğü kum tümseği ve yanında birkaç küçük taş
part("Sand_Mound", m.sphere(0.4, (1.3, 1.1, 0.35), 2, (-1.12, 0.0, 0.0)), "Sand")
for i, (pos, r) in enumerate((((-0.8, -0.34, 0.03), 0.09), ((-1.4, 0.34, 0.03), 0.07))):
    part("Sandstone_Pebble%d" % i, m.sphere(r, (1.2, 1.0, 0.7), 1, pos), "Sandstone")

# Tepedeki yaprak topuzu ve hindistan cevizleri
tip = trunk_center(1.0)
crown = (tip.x + 0.04, tip.y, tip.z + 0.02)
part("Trunk_Crown", m.sphere(0.15, (1.1, 1.0, 1.0), 2, crown), "Trunk")
for i, (dx, dy, dz) in enumerate(((-0.02, 0.12, -0.13), (-0.02, -0.11, -0.14), (0.06, 0.0, -0.19))):
    part("Coconut_%d" % i, m.sphere(0.08, (1, 1, 1.05), 2, (crown[0] + dx, crown[1] + dy, crown[2] + dz)), "Coconut")

# Yapraklar: (yön, uzunluk, genişlik, sarkma, renk). Çoğu yere doğru sarkar, ikisi yukarı kalkıp kıvrılır.
leaves = [
    ((0.35, 1.0, 0.3), 1.15, 0.2, 0.8, "Leaf"),
    ((0.35, -1.0, 0.3), 1.15, 0.2, 0.8, "LeafDark"),
    ((1.0, 0.5, 0.25), 1.1, 0.19, 0.75, "LeafLight"),
    ((1.0, -0.5, 0.25), 1.1, 0.19, 0.75, "Leaf"),
    ((0.2, 0.45, 1.0), 0.95, 0.18, 0.8, "LeafLight"),
    ((0.25, -0.45, 1.0), 0.95, 0.18, 0.8, "LeafDark"),
    ((-0.55, 0.85, 0.55), 0.9, 0.18, 0.75, "LeafDark"),
    ((-0.55, -0.85, 0.55), 0.9, 0.18, 0.75, "Leaf"),
]
for i, (direction, length, width, droop, key) in enumerate(leaves):
    part("%s_Leaf%d" % (key, i), leaf(crown, direction, length, width, droop), key)

# Yumuşak gölgelendirme (çizgi film görünümü)
for obj in m.all_objects():
    for poly in obj.data.polygons:
        poly.use_smooth = True

# Yalnızca önizleme için kum zemin (dışa aktarılmaz)
ground = bmesh.new()
bmesh.ops.create_grid(ground, x_segments=1, y_segments=1, size=3.5)
ground_mesh = bpy.data.meshes.new("PreviewGround")
ground.to_mesh(ground_mesh)
ground.free()
ground_obj = bpy.data.objects.new("PreviewGround", ground_mesh)
ground_obj.data.materials.append(m.material("Sand", (0.95, 0.82, 0.58)))
bpy.context.collection.objects.link(ground_obj)

m.render_views("palm", PREVIEW_DIR, [
    ("player", (0.0, -6.0, 2.0)),
    ("side", (4.0, -4.0, 2.0)),
], target=(0.0, 0, 0.5), size=(700, 600), background=(0.96, 0.86, 0.66), lens=45, gain=1.15)

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
