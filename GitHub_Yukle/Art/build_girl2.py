"""
Kız büyücü v2 (sevimli, büyük başlı, referans görsele göre): geniş kenarlı pembe şapka (mor bant, altın ay ve üçgen desen,
ucunda yıldız), dalgalı kahverengi saç, teal tunik, yıldızlı lacivert pelerin, çizgili tayt, kanatlı pembe botlar, çanta.
Çalıştırma: WIZARD_FBX, WIZARD_BLEND, WIZARD_PREVIEW ortam değişkenleriyle blender -b -P build_girl2.py
Nesne adları "RenkAnahtarı_Parça" biçimindedir (renkleri Unity kodla verir, bkz. ModelPalette.cs).
Kollar "Tunic_SleeveL/R" omuzda, bacaklar "Boot_BootL/R" kalçada döner. Karakter +Y'ye bakar, ayak tabanı z=0.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bmesh
import bpy

import modeling as m

FBX_PATH = os.environ["WIZARD_FBX"]
BLEND_PATH = os.environ["WIZARD_BLEND"]
PREVIEW_DIR = os.environ["WIZARD_PREVIEW"]

m.reset_scene()

COLORS = {
    "Hat": (1.0, 0.15, 0.55), "HatBand": (0.55, 0.22, 0.85), "Gold": (1.0, 0.75, 0.0), "StarTip": (1.0, 0.72, 0.3),
    "Skin": (1.0, 0.72, 0.55), "Hair": (0.55, 0.28, 0.12), "HairLight": (0.8, 0.5, 0.2),
    "Tunic": (0.25, 0.58, 0.75), "TunicDark": (0.15, 0.4, 0.58), "Cape": (0.15, 0.2, 0.55),
    "StripeA": (1.0, 0.3, 0.7), "StripeB": (0.55, 0.2, 0.8), "Boot": (1.0, 0.25, 0.6), "BootToe": (0.7, 0.4, 0.15),
    "Wing": (0.85, 0.93, 1.0), "Glove": (0.6, 0.2, 0.32), "Strap": (0.6, 0.33, 0.12), "Pink": (1.0, 0.35, 0.65),
    "Cream": (1.0, 0.97, 0.9), "Eye": (0.3, 0.17, 0.08), "Pupil": (0.05, 0.03, 0.03), "Shine": (1.0, 1.0, 1.0),
    "Blush": (1.0, 0.4, 0.5), "Mouth": (0.7, 0.1, 0.18), "Brow": (0.4, 0.2, 0.08),
}
for key, rgb in COLORS.items():
    m.material(key, rgb)

root = m.make_root("GirlRoot")


def part(name, bm, key, origin=(0, 0, 0), parent=None):
    return m.finish(name, bm, key, origin, parent or root)


def crescent_front(cx, cy, cz, radius, max_width, thickness, steps=10):
    """XZ düzleminde (önden bakınca) uçları sivri hilal; +Y'ye bakar."""
    bm = bmesh.new()
    outer, inner = [], []
    for i in range(steps + 1):
        s = i / steps
        t = math.radians(40 + 280 * s)
        w = max_width * math.sin(math.pi * s) ** 0.8 + 0.004
        for r, ring in ((radius + w / 2, outer), (radius - w / 2, inner)):
            ring.append([bm.verts.new((cx + r * math.sin(t), cy + y, cz + r * math.cos(t))) for y in (-thickness, thickness)])
    for i in range(steps):
        for side in (0, 1):
            bm.faces.new((outer[i][side], outer[i + 1][side], inner[i + 1][side], inner[i][side]))
        bm.faces.new((outer[i][0], outer[i][1], outer[i + 1][1], outer[i + 1][0]))
        bm.faces.new((inner[i][1], inner[i][0], inner[i + 1][0], inner[i + 1][1]))
    bm.faces.new((outer[0][0], outer[0][1], inner[0][1], inner[0][0]))
    bm.faces.new((outer[-1][1], outer[-1][0], inner[-1][0], inner[-1][1]))
    return bm


HIP_Z = 0.62

# Bacaklar: kalçada dönen çizgili tayt; bot ana parça, tayt çizgileri ve kanat onun çocuğu
for s, sx in (("L", -1), ("R", 1)):
    x = 0.1 * sx
    hip = (x, 0.0, HIP_Z)
    boot = part("Boot_Boot" + s, m.loft([(x, 0.0, 0.3), (x, 0.0, 0.1)], [0.075, 0.09], 8), "Boot", hip)
    part("BootToe_Toe" + s, m.sphere(0.095, (1.0, 1.55, 0.8), 1, (x, 0.07, 0.07)), "BootToe", hip, boot)
    part("BootToe_Sole" + s, m.box((0.17, 0.3, 0.03), (x, 0.06, 0.015)), "BootToe", hip, boot)
    part("Pink_BootLace" + s, m.box((0.07, 0.03, 0.1), (x, 0.085, 0.2)), "Pink", hip, boot)
    wing = m.rotate_z(m.sphere(0.04, (0.3, 1.8, 0.8), 1, (x + 0.085 * sx, -0.005, 0.2)), -25 * sx, (x + 0.085 * sx, -0.005, 0.2))
    part("Wing_Wing" + s, wing, "Wing", hip, boot)
    bands = 6
    z_top, z_bot = HIP_Z - 0.03, 0.28
    for i in range(bands):
        z0 = z_top - i * (z_top - z_bot) / bands
        z1 = z0 - (z_top - z_bot) / bands
        key = "StripeA" if i % 2 == 0 else "StripeB"
        part("%s_Leg%s%d" % (key, s, i), m.loft([(x, 0.0, z0), (x, 0.0, z1)], [0.075, 0.07], 8), key, hip, boot)

# Tunik: teal elbise, altın etek, kemer, ön süs
part("Tunic_Body", m.loft([(0, 0, 0.46), (0, 0, 0.58), (0, 0, 0.74), (0, 0, 0.92)], [0.285, 0.23, 0.19, 0.17], 12, (0.85, 1.0)), "Tunic")
part("Gold_Hem", m.loft([(0, 0, 0.46), (0, 0, 0.5)], [0.286, 0.278], 12, (0.85, 1.0)), "Gold")
part("Strap_Belt", m.loft([(0, 0, 0.66), (0, 0, 0.72)], [0.208, 0.202], 12, (0.85, 1.0)), "Strap")
part("Gold_Ornament", m.sphere(0.05, (1.0, 0.3, 2.0), 1, (0, 0.17, 0.82)), "Gold")
part("TunicDark_Collar", m.loft([(0, 0, 0.9), (0, 0, 0.98)], [0.17, 0.11], 10, (0.9, 1.0)), "TunicDark")
part("Pink_Brooch", m.sphere(0.035, (1, 0.5, 1), 1, (0, 0.11, 0.94)), "Pink")
part("Skin_Neck", m.loft([(0, 0, 0.96), (0, 0, 1.0)], [0.06, 0.055], 8), "Skin")

# Kollar: omuzda dönen puf kol, kolluk, bordo parmaksız eldiven
for s, sx in (("L", -1), ("R", 1)):
    shoulder = (0.2 * sx, 0.0, 0.88)
    sleeve = part("Tunic_Sleeve" + s, m.loft([shoulder, (0.25 * sx, 0.02, 0.73)], [0.08, 0.09], 8), "Tunic", shoulder)
    part("Gold_Cuff" + s, m.loft([(0.245 * sx, 0.02, 0.76), (0.25 * sx, 0.02, 0.72)], [0.092, 0.092], 8), "Gold", shoulder, sleeve)
    part("Skin_Forearm" + s, m.loft([(0.25 * sx, 0.02, 0.72), (0.28 * sx, 0.04, 0.6)], [0.05, 0.05], 8), "Skin", shoulder, sleeve)
    part("Glove_Hand" + s, m.sphere(0.07, (1, 1, 1.15), 2, (0.285 * sx, 0.05, 0.56)), "Glove", shoulder, sleeve)
    part("Pink_GloveGem" + s, m.sphere(0.022, (1, 1, 1), 1, (0.285 * sx, 0.115, 0.58)), "Pink", shoulder, sleeve)

# Çapraz çanta: omuzdan kalçaya kayış ve yanda kapaklı çanta
part("Strap_Sash", m.loft([(0.13, 0.02, 0.97), (0.0, 0.17, 0.85), (-0.19, 0.1, 0.62)], [0.02, 0.02, 0.02], 4), "Strap")
part("Strap_Bag", m.box((0.13, 0.19, 0.17), (-0.3, 0.0, 0.56)), "Strap")
part("Gold_BagClasp", m.sphere(0.025, (1, 1, 1), 1, (-0.3, 0.1, 0.6)), "Gold")

# Pelerin: omuzlardan arkaya yayılan lacivert kumaş, altın kenar ve yıldızlar
part("Cape_Cape", m.loft([(0, -0.12, 0.95), (0, -0.19, 0.75), (0, -0.26, 0.55), (0, -0.3, 0.38)], [0.2, 0.3, 0.38, 0.43], 10, (0.2, 1.0)), "Cape")
part("Gold_CapeHem", m.loft([(0, -0.295, 0.41), (0, -0.3, 0.38)], [0.425, 0.43], 10, (0.2, 1.0)), "Gold")
part("Cape_Collar", m.loft([(0, 0, 0.9), (0, 0, 0.96)], [0.2, 0.15], 10, (0.9, 1.0)), "Cape")
for i, (sx_, sz_, size) in enumerate([(-0.15, 0.7, 0.05), (0.12, 0.8, 0.04), (0.18, 0.6, 0.05), (-0.05, 0.55, 0.045),
                                      (-0.22, 0.5, 0.035), (0.04, 0.68, 0.06), (0.25, 0.45, 0.035)]):
    cc = (sx_, -0.255 - (0.9 - sz_) * 0.12, sz_)
    part("Gold_CapeStar%d" % i, m.rotate_z(m.star(size, size * 0.45, 0.012, cc), 180, cc), "Gold")

# Baş: büyük, sevimli yüz
part("Skin_Head", m.sphere(0.27, (1.0, 0.9, 0.95), 2, (0, 0, 1.15)), "Skin")
for s, sx in (("L", -1), ("R", 1)):
    part("Eye_" + s, m.sphere(0.058, (0.85, 0.5, 1.2), 2, (0.1 * sx, 0.225, 1.17)), "Eye")
    part("Pupil_" + s, m.sphere(0.03, (0.8, 0.4, 1.1), 1, (0.1 * sx, 0.245, 1.17)), "Pupil")
    part("Shine_" + s, m.sphere(0.017, (1, 0.6, 1), 1, (0.115 * sx, 0.255, 1.2)), "Shine")
    part("Blush_" + s, m.sphere(0.06, (1.2, 0.3, 0.7), 1, (0.17 * sx, 0.19, 1.06)), "Blush")
    brow = m.rotate_y(m.box((0.1, 0.02, 0.03), (0.105 * sx, 0.23, 1.27)), -10 * sx, (0.105 * sx, 0.23, 1.27))
    part("Brow_" + s, brow, "Brow")
part("Skin_Nose", m.sphere(0.03, (1, 1, 1), 1, (0, 0.255, 1.1)), "Skin")
part("Mouth_Smile", m.sphere(0.06, (1.4, 0.3, 0.7), 1, (0, 0.235, 1.01)), "Mouth")
part("Cream_Teeth", m.sphere(0.045, (1.4, 0.2, 0.3), 1, (0, 0.265, 1.035)), "Cream")

# Dalgalı kahverengi saç: hacimli, omuzlara dökülür, altın tutamlar
part("Hair_Cap", m.sphere(0.29, (1.05, 0.95, 0.85), 2, (0, -0.04, 1.2)), "Hair")
part("Hair_Back", m.sphere(0.32, (1.1, 0.7, 1.05), 2, (0, -0.2, 1.0)), "Hair")
part("Hair_BackLow", m.sphere(0.24, (1.2, 0.6, 0.9), 2, (0, -0.24, 0.82)), "Hair")
waves = [(0.0, 0.19), (0.04, 0.12), (0.0, 0.05)]
for s, sx in (("L", -1), ("R", 1)):
    for i, (dx, z) in enumerate([(0.27, 1.12), (0.31, 0.98), (0.32, 0.84), (0.28, 0.74)]):
        key = "HairLight" if i == 1 else "Hair"
        part("%s_Wave%s%d" % (key, s, i), m.sphere(0.085 - 0.006 * i, (1, 1, 1.2), 1, (dx * sx, -0.05, z)), key)
    part("Hair_Fringe" + s, m.sphere(0.13, (1.1, 0.5, 0.75), 2, (0.15 * sx, 0.17, 1.33)), "Hair")
part("Hair_FringeMid", m.sphere(0.13, (1.2, 0.5, 0.65), 2, (0, 0.2, 1.36)), "Hair")

# Şapka: geniş pembe kenar, mor bant, altın halka ve üçgen desen, ön altın ay, geriye bükülen uç ve yıldız
HZ = 1.3
part("Hat_Brim", m.loft([(0, 0, HZ - 0.03), (0, 0, HZ + 0.03)], [0.62, 0.4], 16), "Hat")
part("Hat_Crown", m.loft([(0, 0, HZ), (0, 0, HZ + 0.15), (0, -0.04, HZ + 0.3), (0, -0.13, HZ + 0.43),
                           (0, -0.28, HZ + 0.5), (0, -0.46, HZ + 0.48)], [0.31, 0.27, 0.2, 0.13, 0.075, 0.02], 12), "Hat")
part("HatBand_Band", m.loft([(0, 0, HZ + 0.04), (0, 0, HZ + 0.14)], [0.325, 0.29], 14), "HatBand")
part("Gold_RingLow", m.loft([(0, 0, HZ + 0.03), (0, 0, HZ + 0.05)], [0.33, 0.325], 14), "Gold")
part("Gold_RingHigh", m.loft([(0, 0, HZ + 0.14), (0, 0, HZ + 0.16)], [0.29, 0.285], 14), "Gold")
for k in range(10):
    ang = 2 * math.pi * k / 10
    px, py = 0.285 * math.cos(ang), 0.285 * math.sin(ang)
    part("Gold_Tri%d" % k, m.loft([(px, py, HZ + 0.02), (px * 0.97, py * 0.97, HZ + 0.13)], [0.035, 0.004], 3), "Gold")
part("Gold_HatMoon", crescent_front(0, 0.275, HZ + 0.27, 0.065, 0.045, 0.014), "Gold")
part("Gold_RingMid", m.loft([(0, -0.04, HZ + 0.3), (0, -0.045, HZ + 0.31)], [0.205, 0.2], 12), "Gold")
part("StarTip_TipStar", m.star(0.075, 0.034, 0.016, (0, -0.52, HZ + 0.42)), "StarTip")

m.render_views("girl2", PREVIEW_DIR, [
    ("front", (2.4, 4.4, 1.5)),
    ("side", (5.0, 0.0, 1.2)),
    ("back", (-2.4, -4.4, 1.5)),
], target=(0, -0.05, 0.95), size=(600, 800), background=(0.9, 0.88, 0.94), lens=55, gain=1.25)

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
