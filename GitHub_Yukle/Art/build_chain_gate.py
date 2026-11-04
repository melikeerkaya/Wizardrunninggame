"""
Zincir kapısı (Çöl Diyarı yüksek engeli): iki kumtaşı sütun ve aralarında sarkan kalın demir zincir.
Büyücü zincirin altından kayarak geçer. Bir şerit içindir: sütunlar şerit sınırlarında (x = ±1.25) durur.
Z yukarı, koşu yönü +Y, zemin z=0. Alttaki zincirin en alçak noktası ~1.2 (Subway Surfers oranındaki ~1.44 boylu
karakterin göğsü). Oyunda artık kullanılmıyor: yerini Art/convert_archway.py'nin taş kemeri aldı.
Çalıştırma: GATE_FBX, GATE_BLEND, GATE_PREVIEW ortam değişkenleriyle blender -b -P build_chain_gate.py
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

FBX_PATH = os.environ["GATE_FBX"]
BLEND_PATH = os.environ["GATE_BLEND"]
PREVIEW_DIR = os.environ["GATE_PREVIEW"]

PILLAR_X = 1.25
ANCHOR_Z = 2.9
SAG = 1.35
INNER_FACE = 0.43

m.reset_scene()

for key, rgb in {
    "Sandstone": (0.88, 0.58, 0.4), "SandstoneDark": (0.78, 0.48, 0.32), "SandstoneLight": (0.94, 0.68, 0.48),
    "Iron": (0.56, 0.58, 0.62), "Bronze": (0.8, 0.55, 0.22), "BronzeDark": (0.55, 0.36, 0.16), "Sand": (0.95, 0.75, 0.55),
}.items():
    m.material(key, rgb)

root = m.make_root("ChainGateRoot")


def part(name, bm, key):
    return m.finish(name, bm, key, (0, 0, 0), root)


def block(name, key, cx, z0, size, rot_deg, tilt_deg=0.0):
    """Kenarları yuvarlatılmış taş blok. rot_deg dik eksende, tilt_deg koşu ekseninde hafif çarpıklık verir."""
    bm = m.box(size, (cx, 0, z0 + size[2] / 2))
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.04, segments=2, affect="EDGES", profile=0.5)
    m.rotate_z(bm, rot_deg, (cx, 0, z0))
    if tilt_deg:
        m.rotate_y(bm, tilt_deg, (cx, 0, z0))
    part(name, bm, key)


def add_link(bm, center, t, n, half_len=0.095, radius=0.075, tube=0.03, ring=6):
    """Yuvarlatılmış dikdörtgen (stadyum) biçimli zincir halkası. t uzun eksen, n halka düzlemindeki dik eksen."""
    t, n = t.normalized(), n.normalized()
    b = t.cross(n).normalized()
    path = []
    for side, a0 in ((1, -90), (-1, 90)):
        for i in range(7):
            ang = math.radians(a0 + i * 30)
            c, s = math.cos(ang), math.sin(ang)
            p = center + t * (c * radius + side * half_len) + n * (s * radius)
            d = t * (-s) + n * c
            path.append((p, d.normalized()))
    rings = []
    for p, d in path:
        side_vec = d.cross(b).normalized()
        rings.append([bm.verts.new(p + b * math.cos(2 * math.pi * k / ring) * tube
                                   + side_vec * math.sin(2 * math.pi * k / ring) * tube) for k in range(ring)])
    count = len(rings)
    for i in range(count):
        j = (i + 1) % count
        for k in range(ring):
            q = (k + 1) % ring
            bm.faces.new((rings[i][k], rings[i][q], rings[j][q], rings[j][k]))


CHAIN_HEIGHTS = (1.3, 2.15)
SLACK = 0.1


def chain_curve(x, z=ANCHOR_Z):
    end = PILLAR_X - INNER_FACE
    return z - SLACK * (1 - (x / end) ** 2)


# Sütunlar: yüksek, üst üste konmuş, hafifçe kaymış kumtaşı bloklar ve taşan başlık (toplam ~5.7 birim)
for side, sign in (("L", -1), ("R", 1)):
    x = sign * PILLAR_X
    block("SandstoneDark_Base" + side, "SandstoneDark", x, 0.0, (1.0, 1.0, 1.0), 2 * sign)
    block("Sandstone_Mid" + side, "Sandstone", x, 0.95, (0.88, 0.88, 0.95), -3 * sign, 1.5 * sign)
    block("SandstoneDark_Upper" + side, "SandstoneDark", x + 0.01 * sign, 1.85, (0.9, 0.9, 0.95), 2 * sign)
    block("Sandstone_Top" + side, "Sandstone", x, 2.75, (0.86, 0.86, 0.95), -2 * sign, -1.0 * sign)
    block("SandstoneDark_Crown" + side, "SandstoneDark", x + 0.01 * sign, 3.65, (0.84, 0.84, 0.95), 3 * sign, 1.0 * sign)
    block("Sandstone_Spire" + side, "Sandstone", x, 4.55, (0.8, 0.8, 0.9), -2 * sign, -1.0 * sign)
    block("SandstoneLight_Cap" + side, "SandstoneLight", x, 5.4, (1.25, 1.25, 0.3), 4 * sign, -2 * sign)

    # Zincirin bağlandığı bronz plaka (iç yüzde) ve küçük halka
    inner = x - sign * INNER_FACE
    for k, z in enumerate(CHAIN_HEIGHTS):
        plate = m.box((0.05, 0.36, 0.3), (inner - sign * 0.015, 0, z))
        part("BronzeDark_Plate" + side + str(k), plate, "BronzeDark")

    # Dış yüzde sarkan kısa zincir ve dipte kuma bırakılmış halka (süs)
    outer = x + sign * 0.46
    bm = bmesh.new()
    for i in range(6):
        center = Vector((outer + sign * 0.03, 0.12, 3.35 - i * 0.17))
        n = Vector((1, 0, 0)) if i % 2 == 0 else Vector((0, 1, 0))
        add_link(bm, center, Vector((0, 0, 1)), n, 0.05, 0.045, 0.016)
    part("Iron_Hanging" + side, bm, "Iron")
    ring_bm = bmesh.new()
    add_link(ring_bm, Vector((outer + sign * 0.18, -0.25, 0.03)), Vector((1, 0, 0)), Vector((0, 1, 0)), 0.0, 0.13, 0.03, 8)
    part("Iron_GroundRing" + side, ring_bm, "Iron")

# Sütunlar arasında sarkan ana zincir: eğri boyunca eşit aralıkla dizilen, birbirine dik halkalar
end = PILLAR_X - INNER_FACE
samples = [(-end + 2 * end * i / 400) for i in range(401)]
chain = bmesh.new()
for height in CHAIN_HEIGHTS:
    points = [Vector((x, 0, chain_curve(x, height))) for x in samples]
    pitch = 0.25
    centers = [points[0]]
    walked = 0.0
    for a, b in zip(points, points[1:]):
        walked += (b - a).length
        if walked >= pitch:
            centers.append(b)
            walked = 0.0
    for i, c in enumerate(centers):
        nxt = centers[min(i + 1, len(centers) - 1)]
        prv = centers[max(i - 1, 0)]
        t = (nxt - prv).normalized()
        n = Vector((-t.z, 0, t.x)) if i % 2 == 0 else Vector((0, 1, 0))
        add_link(chain, c, t, n)
part("Iron_Chain", chain, "Iron")

# Yalnızca önizleme için kum zemin (dışa aktarılmaz)
ground = bmesh.new()
bmesh.ops.create_grid(ground, x_segments=1, y_segments=1, size=4.0)
ground_mesh = bpy.data.meshes.new("PreviewGround")
ground.to_mesh(ground_mesh)
ground.free()
ground_obj = bpy.data.objects.new("PreviewGround", ground_mesh)
ground_obj.data.materials.append(m.material("Sand", (0.95, 0.75, 0.55)))
bpy.context.collection.objects.link(ground_obj)

m.render_views("gate", PREVIEW_DIR, [
    ("player", (0.0, -9.0, 1.6)),
    ("side", (6.5, -6.5, 3.0)),
], target=(0, 0, 2.2), size=(700, 600), background=(0.85, 0.75, 0.85), lens=45, gain=1.1)

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
