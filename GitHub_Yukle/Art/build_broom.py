"""
Sihirli süpürge (low-poly): ahşap sap, üstünde hilal ay kupası ve içinde yüzen altın yıldız,
pembe-altın sargılar, sarkan mor kristal ve yelpaze gibi açılan faset faset saman demeti.
Süpürge +Y yönüne bakar, fırça arkada (-Y) durur. Oyunda artık kullanılmıyor: yerini Art/convert_prop.py'nin süpürgesi aldı.
Çalıştırma: BROOM_FBX, BROOM_BLEND, BROOM_PREVIEW ortam değişkenleriyle blender -b -P build_broom.py
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

FBX_PATH = os.environ["BROOM_FBX"]
BLEND_PATH = os.environ["BROOM_BLEND"]
PREVIEW_DIR = os.environ["BROOM_PREVIEW"]

m.reset_scene()

for key, rgb in {
    "Wood": (0.6, 0.33, 0.1), "Straw": (1.0, 0.78, 0.1), "StrawDark": (0.95, 0.5, 0.05),
    "Band": (1.0, 0.15, 0.55), "Gold": (1.0, 0.75, 0.0), "Gem": (0.55, 0.25, 1.0),
    "Cream": (1.0, 0.97, 0.9),
}.items():
    m.material(key, rgb)

root = m.make_root("BroomRoot")


def part(name, bm, key):
    return m.finish(name, bm, key, (0, 0, 0), root)


def crescent(cy, cz, radius, start_deg, end_deg, max_width, thickness, steps=9):
    """YZ düzleminde (yandan bakınca) uçları sivri hilal; kalınlığı X yönünde."""
    bm = bmesh.new()
    outer, inner = [], []
    for i in range(steps + 1):
        s = i / steps
        t = math.radians(start_deg + (end_deg - start_deg) * s)
        w = max_width * math.sin(math.pi * s) ** 0.8 + 0.004
        for r, ring in ((radius + w / 2, outer), (radius - w / 2, inner)):
            ring.append([bm.verts.new((x, cy + r * math.sin(t), cz + r * math.cos(t))) for x in (-thickness, thickness)])
    for i in range(steps):
        for side in (0, 1):
            bm.faces.new((outer[i][side], outer[i + 1][side], inner[i + 1][side], inner[i][side]))
        bm.faces.new((outer[i][0], outer[i][1], outer[i + 1][1], outer[i + 1][0]))
        bm.faces.new((inner[i][1], inner[i][0], inner[i + 1][0], inner[i + 1][1]))
    bm.faces.new((outer[0][0], outer[0][1], inner[0][1], inner[0][0]))
    bm.faces.new((outer[-1][1], outer[-1][0], inner[-1][0], inner[-1][1]))
    return bm


# Kalın, hafif kavisli ahşap sap
shaft = [(0, -0.25, -0.06), (0, 0.30, -0.03), (0, 0.80, 0.02), (0, 1.12, 0.04)]
part("Wood_Shaft", m.loft(shaft, [0.06, 0.05, 0.047, 0.045], 6), "Wood")

# Sap ucu: içe doğru kıvrılan spiral kıvrım
cy, cz = 1.27, 0.07
spiral, spiral_r = [], []
for i in range(15):
    s = i / 14
    t = math.radians(-100 + 540 * s)
    r = 0.14 - 0.095 * s
    spiral.append((0, cy + r * math.sin(t), cz + r * math.cos(t)))
    spiral_r.append(0.045 - 0.022 * s)
part("Wood_Curl", m.loft(spiral, spiral_r, 6), "Wood")

# Sapı saran pembe sargı
part("Band_Wrap", m.loft([(0, 0.70, 0.0), (0, 0.80, 0.015)], [0.062, 0.062], 6), "Band")
part("Gold_Ring", m.loft([(0, 0.80, 0.015), (0, 0.83, 0.017)], [0.066, 0.066], 6), "Gold")

# Sapın üstünde dolgun pembe fiyonk (iki kulak, düğüm, iki kuyruk)
bow_c = (0, 0.96, 0.07)
for name, sx in (("Band_BowL", -1), ("Band_BowR", 1)):
    bm = m.sphere(0.15, (1.0, 0.8, 0.8), 1, (sx * 0.15, bow_c[1], bow_c[2]))
    part(name, m.rotate_y(bm, sx * 18, (sx * 0.15, bow_c[1], bow_c[2])), "Band")
part("Band_Knot", m.sphere(0.075, (1, 0.9, 1), 1, bow_c), "Band")
part("Band_TailL", m.loft([(-0.02, 0.93, 0.07), (-0.07, 0.82, 0.07), (-0.11, 0.72, 0.07)], [0.04, 0.045, 0.02], 4, (0.4, 1.0)), "Band")
part("Band_TailR", m.loft([(0.02, 0.93, 0.07), (0.08, 0.80, 0.07), (0.14, 0.70, 0.07)], [0.04, 0.045, 0.02], 4, (0.4, 1.0)), "Band")

# Fiyonktan ince iple sarkan altın hilal charm
part("Cream_String", m.loft([(0.0, 1.05, 0.06), (0.0, 1.05, -0.02), (0.0, 1.05, -0.10)], [0.006, 0.006, 0.006], 4), "Cream")
part("Gold_Moon", crescent(1.05, -0.17, 0.07, -230, 50, 0.04, 0.016, 7), "Gold")

# Fırçanın boynu: pembe kemer ve altın yıldız tokası
part("Band_Collar", m.loft([(0, -0.24, -0.06), (0, -0.36, -0.065)], [0.125, 0.14], 8), "Band")
buckle_c = (0, -0.30, 0.085)
part("Gold_Buckle", m.rotate_x(m.star(0.075, 0.034, 0.014, buckle_c), 90, buckle_c), "Gold")

# Geniş, yassı, faset saman demeti (X yönünde geniş, Z yönünde ince)
body = [(0, -0.36, -0.065), (0, -0.56, -0.075), (0, -0.80, -0.085), (0, -1.00, -0.09)]
part("Straw_Body", m.loft(body, [0.12, 0.27, 0.34, 0.30], 6, (0.6, 1.0)), "Straw")
part("StrawDark_Back", m.loft([(0, -0.40, -0.12), (0, -0.70, -0.15), (0, -0.95, -0.15)], [0.1, 0.24, 0.22], 6, (0.4, 1.0)), "StrawDark")

# Alt kenarda tırtıklı saman uçları
tips = [(-0.28, 1.45), (-0.17, 1.62), (-0.06, 1.50), (0.06, 1.65), (0.17, 1.52), (0.28, 1.42)]
for i, (x, tip) in enumerate(tips):
    key = "Straw" if i % 2 == 0 else "StrawDark"
    path = [(x * 0.8, -0.90, -0.09), (x * 1.1, -1.1, -0.09), (x * 1.25, -tip, -0.09)]
    part("%s_Tip%d" % (key, i), m.loft(path, [0.11, 0.1, 0.008], 4, (0.6, 1.0)), key)

m.render_views("broom", PREVIEW_DIR, [
    ("front", (4.2, 3.2, 1.9)),
    ("back", (-4.2, -3.8, 1.6)),
], target=(0, 0.1, -0.1), size=(700, 700), background=(0.9, 0.88, 0.94), lens=50, gain=1.25)

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
