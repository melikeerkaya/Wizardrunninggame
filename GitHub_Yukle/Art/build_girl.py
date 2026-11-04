"""
Kız büyücü (genç, ~1.9 birim boyunda, koşucu oyunu karakteri oranlarında): pembe şapka, kahverengi dalgalı saç,
mavi tunik ve pelerin, çizgili tayt, pembe botlar, çapraz çanta. Orijinal tasarım.
Çalıştırma: WIZARD_FBX, WIZARD_BLEND ve WIZARD_PREVIEW ortam değişkenleri verilip blender -b -P build_girl.py

Nesne adları "RenkAnahtarı_Parça" biçimindedir. Unity renkleri bu anahtara göre kodla verir (ModelPalette.cs).
Kollar ("Tunic_SleeveL/R") omuzda, bacaklar ("Boot_BootL/R", içinde çizgili tayt parçaları) kalçada döner;
Unity bunları koşarken kodla sallar. Karakter +Y yönüne bakar, ayak tabanı z=0'dadır.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy

import modeling as m

FBX_PATH = os.environ["WIZARD_FBX"]
BLEND_PATH = os.environ["WIZARD_BLEND"]
PREVIEW_DIR = os.environ["WIZARD_PREVIEW"]

m.reset_scene()

COLORS = {
    "Hat": (1.0, 0.15, 0.55), "HatBand": (0.5, 0.2, 0.85), "Gold": (1.0, 0.75, 0.0),
    "Skin": (1.0, 0.72, 0.55), "Hair": (0.55, 0.28, 0.12), "HairLight": (0.7, 0.4, 0.18),
    "Tunic": (0.2, 0.55, 0.95), "TunicDark": (0.12, 0.38, 0.75), "Cape": (0.3, 0.25, 0.8),
    "StripeA": (1.0, 0.35, 0.75), "StripeB": (0.55, 0.2, 0.85), "Boot": (0.78, 0.32, 0.42),
    "Glove": (0.95, 0.3, 0.65), "Strap": (0.55, 0.3, 0.12), "Cream": (1.0, 0.97, 0.9),
    "Eye": (0.18, 0.1, 0.07), "Shine": (1.0, 1.0, 1.0), "Blush": (1.0, 0.4, 0.5), "Mouth": (0.75, 0.15, 0.2),
}
for key, rgb in COLORS.items():
    m.material(key, rgb)

root = m.make_root("GirlRoot")


def part(name, bm, key, origin=(0, 0, 0), parent=None):
    return m.finish(name, bm, key, origin, parent or root)


HIP_Z = 0.8

# Bacaklar: kalçada dönen çizgili tayt ve pembe bot (bot ana parça, tayt çizgileri onun çocuğu)
for s, sx in (("L", -1), ("R", 1)):
    hip = (0.1 * sx, 0.0, HIP_Z)
    boot = part("Boot_Boot" + s, m.loft([(0.1 * sx, 0.0, 0.3), (0.1 * sx, 0.0, 0.1)], [0.082, 0.095], 8), "Boot", hip)
    toe = m.sphere(0.095, (0.95, 1.5, 0.75), 1, (0.1 * sx, 0.07, 0.075))
    part("Boot_Toe" + s, toe, "Boot", hip, boot)
    part("Cream_BootCuff" + s, m.loft([(0.1 * sx, 0.0, 0.32), (0.1 * sx, 0.0, 0.28)], [0.092, 0.092], 8), "Cream", hip, boot)
    bands = 6
    for i in range(bands):
        z0 = HIP_Z - 0.04 - i * (HIP_Z - 0.36) / bands
        z1 = z0 - (HIP_Z - 0.36) / bands
        key = "StripeA" if i % 2 == 0 else "StripeB"
        r0, r1 = 0.082 - 0.012 * i / bands, 0.082 - 0.012 * (i + 1) / bands
        part("%s_Leg%s%d" % (key, s, i), m.loft([(0.1 * sx, 0.0, z0), (0.1 * sx, 0.0, z1)], [r0, r1], 8), key, hip, boot)

# Tunik: yukarıdan aşağı genişleyen mavi elbise, altın etek ve kahverengi kemer
part("Tunic_Body", m.loft([(0, 0, 0.58), (0, 0, 0.72), (0, 0, 0.88), (0, 0, 1.06)], [0.255, 0.22, 0.18, 0.165], 12, (0.82, 1.0)), "Tunic")
part("Gold_Hem", m.loft([(0, 0, 0.58), (0, 0, 0.63)], [0.256, 0.248], 12, (0.82, 1.0)), "Gold")
part("TunicDark_Collar", m.loft([(0, 0, 1.04), (0, 0, 1.12)], [0.165, 0.1], 10, (0.9, 1.0)), "TunicDark")
part("Strap_Belt", m.loft([(0, 0, 0.84), (0, 0, 0.9)], [0.19, 0.185], 12, (0.82, 1.0)), "Strap")
part("Gold_Buckle", m.sphere(0.04, (1, 0.5, 1), 1, (0, 0.17, 0.87)), "Gold")
part("Skin_Neck", m.loft([(0, 0, 1.1), (0, 0, 1.2)], [0.055, 0.05], 8), "Skin")

# Kollar: omuzda dönen mavi kol, pembe parmaksız eldiven
for s, sx in (("L", -1), ("R", 1)):
    shoulder = (0.21 * sx, 0.0, 1.02)
    sleeve = part("Tunic_Sleeve" + s, m.loft([shoulder, (0.27 * sx, 0.02, 0.78)], [0.065, 0.075], 8), "Tunic", shoulder)
    part("Gold_Cuff" + s, m.loft([(0.265 * sx, 0.02, 0.8), (0.27 * sx, 0.02, 0.76)], [0.078, 0.078], 8), "Gold", shoulder, sleeve)
    part("Glove_Hand" + s, m.sphere(0.062, (1, 1, 1.15), 2, (0.275 * sx, 0.03, 0.7)), "Glove", shoulder, sleeve)

# Çapraz çanta: omuzdan kalçaya kayış ve yanda küçük çanta
part("Strap_Sash", m.loft([(0.12, 0.02, 1.08), (0.0, 0.17, 0.95), (-0.14, 0.12, 0.8)], [0.018, 0.018, 0.018], 4), "Strap")
part("Strap_Bag", m.box((0.13, 0.1, 0.16), (-0.26, -0.02, 0.76)), "Strap")
part("Gold_BagClasp", m.sphere(0.022, (1, 1, 1), 1, (-0.26, 0.04, 0.81)), "Gold")

# Pelerin: omuzlardan arkaya akan mavi-mor kumaş, altın yıldızlı
part("Cape_Cape", m.loft([(0, -0.15, 1.1), (0, -0.2, 0.9), (0, -0.25, 0.68), (0, -0.3, 0.5)], [0.2, 0.25, 0.3, 0.33], 10, (0.2, 1.0)), "Cape")
part("Gold_CapeHem", m.loft([(0, -0.29, 0.53), (0, -0.3, 0.5)], [0.325, 0.33], 10, (0.2, 1.0)), "Gold")
bc = (0, -0.275, 0.82)
part("Gold_CapeStar", m.rotate_z(m.star(0.1, 0.045, 0.02, bc), 180, bc), "Gold")

# Baş
part("Skin_Head", m.sphere(0.22, (1.0, 0.93, 1.0), 2, (0, 0, 1.36)), "Skin")
for s, sx in (("L", -1), ("R", 1)):
    part("Eye_" + s, m.sphere(0.045, (0.9, 0.6, 1.2), 2, (0.085 * sx, 0.19, 1.37)), "Eye")
    part("Shine_" + s, m.sphere(0.014, (1, 0.6, 1), 1, (0.095 * sx, 0.225, 1.39)), "Shine")
    part("Blush_" + s, m.sphere(0.05, (1.2, 0.3, 0.7), 1, (0.14 * sx, 0.165, 1.28)), "Blush")
part("Skin_Nose", m.sphere(0.025, (1, 1, 1), 1, (0, 0.215, 1.31)), "Skin")
part("Mouth_Smile", m.sphere(0.045, (1.2, 0.2, 0.5), 1, (0, 0.205, 1.24)), "Mouth")

# Dalgalı kahverengi saç: arkada ve yanlarda omuzlara dökülür, alında perçem
part("Hair_Back", m.loft([(0, -0.1, 1.5), (0, -0.17, 1.28), (0, -0.2, 1.08), (0, -0.2, 0.96)], [0.2, 0.22, 0.19, 0.1], 10, (0.55, 1.0)), "Hair")
for s, sx in (("L", -1), ("R", 1)):
    part("Hair_Side" + s, m.loft([(0.17 * sx, 0.0, 1.45), (0.22 * sx, -0.04, 1.25), (0.24 * sx, -0.06, 1.04), (0.21 * sx, -0.03, 0.96)],
                                  [0.07, 0.085, 0.08, 0.04], 6), "Hair")
    part("HairLight_Wave" + s, m.sphere(0.07, (1, 1, 1.2), 1, (0.235 * sx, -0.07, 1.1)), "HairLight")
part("Hair_Fringe", m.sphere(0.2, (1.05, 0.55, 0.45), 2, (0.02, 0.1, 1.5)), "Hair")

# Pembe sivri şapka: geniş kenar, mor bant, altın yıldız ve ucunda yıldız
HAT_Z = 1.5
part("Hat_Brim", m.loft([(0, 0, HAT_Z - 0.02), (0, 0, HAT_Z + 0.03)], [0.4, 0.3], 14), "Hat")
part("Hat_Crown", m.loft([(0, 0, HAT_Z), (0, -0.01, HAT_Z + 0.17), (0, -0.06, HAT_Z + 0.33), (0, -0.17, HAT_Z + 0.45),
                           (0, -0.33, HAT_Z + 0.5), (0, -0.48, HAT_Z + 0.46)], [0.25, 0.2, 0.14, 0.09, 0.05, 0.012], 10), "Hat")
part("HatBand_Band", m.loft([(0, 0, HAT_Z + 0.02), (0, 0, HAT_Z + 0.1)], [0.255, 0.235], 12), "HatBand")
c = (0, 0.165, HAT_Z + 0.2)
part("Gold_HatStar", m.rotate_x(m.star(0.065, 0.03, 0.016, c), 18, c), "Gold")
part("Gold_HatTipString", m.loft([(0, -0.48, HAT_Z + 0.46), (0, -0.48, HAT_Z + 0.4)], [0.006, 0.006], 4), "Gold")
part("Gold_HatTipStar", m.star(0.06, 0.027, 0.014, (0, -0.48, HAT_Z + 0.36)), "Gold")

m.render_views("girl", PREVIEW_DIR, [
    ("front", (2.6, 4.8, 1.7)),
    ("side", (5.0, 0.0, 1.4)),
    ("back", (-2.6, -4.8, 1.7)),
], target=(0, -0.05, 1.0), size=(600, 800), background=(0.9, 0.88, 0.94), lens=55, gain=1.25)

# Dışa aktar
bpy.ops.object.select_all(action="DESELECT")
root.select_set(True)
for obj in m.all_objects():
    obj.select_set(True)

os.makedirs(os.path.dirname(FBX_PATH), exist_ok=True)
bpy.ops.export_scene.fbx(
    filepath=FBX_PATH,
    use_selection=True,
    object_types={"MESH", "EMPTY"},
    apply_unit_scale=True,
    bake_space_transform=True,
    axis_forward="-Z",
    axis_up="Y",
    mesh_smooth_type="FACE",
    add_leaf_bones=False,
)
bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
