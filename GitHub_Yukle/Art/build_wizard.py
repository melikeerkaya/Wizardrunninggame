"""
Pembe büyücü (büyük başlı, sakallı, pembe cübbeli): oyun için son model. Orijinal tasarım.
Çalıştırma: WIZARD_FBX, WIZARD_BLEND ve WIZARD_PREVIEW ortam değişkenleri verilip
blender -b -P build_wizard.py

Nesne adları "RenkAnahtarı_Parça" biçimindedir. Unity renkleri bu anahtara göre kodla verir
(Assets/Scripts/Player/PlayerModel.cs), Blender'daki renkler yalnızca önizleme içindir.
Kollar ve botlar eklem noktasında dönen ayrı parçalardır; Unity bunları kodla hareket ettirir.
Karakter +Y yönüne bakar, ayak tabanı z=0'dadır.
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
    "Robe": (1.0, 0.15, 0.55), "RobeDark": (0.8, 0.05, 0.4), "Hat": (1.0, 0.15, 0.55),
    "Gold": (1.0, 0.75, 0.0), "Skin": (1.0, 0.7, 0.5), "Cream": (1.0, 0.97, 0.9),
    "Nose": (1.0, 0.4, 0.45), "Eye": (0.05, 0.04, 0.08), "Shine": (1.0, 1.0, 1.0),
    "Blush": (1.0, 0.35, 0.5), "Boot": (0.55, 0.25, 0.05),
    "BroomHandle": (0.6, 0.35, 0.1), "BroomBristle": (1.0, 0.8, 0.1),
}
for key, rgb in COLORS.items():
    m.material(key, rgb)

root = m.make_root()


def part(name, bm, key, origin=(0, 0, 0), parent=None):
    return m.finish(name, bm, key, origin, parent or root)


# Botlar: cübbenin altından görünür, koşarken ileri geri sallanır (üstten dönerler)
for s, sx in (("L", -1), ("R", 1)):
    part("Boot_Boot" + s, m.sphere(0.12, (1.0, 1.45, 0.7), 2, (0.15 * sx, 0.14, 0.07)), "Boot", (0.15 * sx, 0.04, 0.3))

# Uzun cübbe: yere doğru genişler, altın etek, kemer ve toka
part("Robe_Body", m.loft([(0, 0, 0.12), (0, 0, 0.35), (0, 0, 0.58), (0, 0, 0.70)],
                         [0.41, 0.34, 0.25, 0.2], 12, (0.95, 1.0)), "Robe")
part("Gold_Hem", m.loft([(0, 0, 0.12), (0, 0, 0.2)], [0.415, 0.395], 12, (0.95, 1.0)), "Gold")
part("RobeDark_Belt", m.loft([(0, 0, 0.40), (0, 0, 0.47)], [0.325, 0.31], 12, (0.95, 1.0)), "RobeDark")
part("Gold_Buckle", m.sphere(0.05, (1, 0.5, 1), 1, (0, 0.31, 0.44)), "Gold")
part("RobeDark_Collar", m.loft([(0, 0, 0.64), (0, 0, 0.76)], [0.23, 0.19], 12), "RobeDark")

# Geniş cübbe kolları (omuzda döner), altın manşet ve eller
for s, sx in (("L", -1), ("R", 1)):
    shoulder = (0.25 * sx, 0.02, 0.62)
    sleeve = part("Robe_Sleeve" + s, m.loft([shoulder, (0.4 * sx, 0.12, 0.38)], [0.1, 0.15], 8), "Robe", shoulder)
    part("Gold_Cuff" + s, m.loft([(0.385 * sx, 0.11, 0.41), (0.42 * sx, 0.125, 0.35)], [0.15, 0.15], 8), "Gold", shoulder, sleeve)
    part("Skin_Hand" + s, m.sphere(0.075, (1, 1, 1), 2, (0.43 * sx, 0.14, 0.32)), "Skin", shoulder, sleeve)

# Büyük baş
part("Skin_Head", m.sphere(0.4, (1.05, 0.95, 0.93), 2, (0, 0, 0.97)), "Skin")
for s, sx in (("L", -1), ("R", 1)):
    part("Eye_" + s, m.sphere(0.047, (1, 0.6, 1.1), 2, (0.135 * sx, 0.355, 1.03)), "Eye")
    part("Shine_" + s, m.sphere(0.014, (1, 0.6, 1), 1, (0.147 * sx, 0.395, 1.055)), "Shine")
    part("Blush_" + s, m.sphere(0.06, (1.2, 0.35, 0.7), 1, (0.26 * sx, 0.3, 0.9)), "Blush")
    brow = m.rotate_y(m.box((0.09, 0.02, 0.025), (0.14 * sx, 0.345, 1.12)), -12 * sx, (0.14 * sx, 0.345, 1.12))
    part("Cream_Brow" + s, brow, "Cream")
part("Nose_Nose", m.sphere(0.08, (1, 0.95, 0.9), 2, (0, 0.385, 0.94)), "Nose")

# Yumuşak, kabarık sakal ve bıyık
part("Cream_Beard", m.sphere(0.34, (1.15, 0.72, 1.0), 2, (0, 0.2, 0.68)), "Cream")
part("Cream_BeardLowL", m.sphere(0.16, (1, 0.8, 1.2), 2, (-0.14, 0.3, 0.52)), "Cream")
part("Cream_BeardLowR", m.sphere(0.16, (1, 0.8, 1.2), 2, (0.14, 0.3, 0.52)), "Cream")
part("Cream_BeardTip", m.loft([(0, 0.3, 0.55), (0, 0.34, 0.36), (0, 0.35, 0.2)], [0.17, 0.12, 0.02], 8, (0.8, 1.0)), "Cream")
for s, sx in (("L", -1), ("R", 1)):
    part("Cream_Mustache" + s, m.sphere(0.12, (1.35, 0.75, 0.8), 2, (0.11 * sx, 0.36, 0.855)), "Cream")

# Pembe sivri şapka: geriye bükülür, ucunda pon pon ve yıldız
part("RobeDark_HatBand", m.loft([(0, 0, 1.18), (0, 0, 1.30)], [0.43, 0.43], 14), "RobeDark")
part("Hat_Hat", m.loft([(0, 0, 1.2), (0, -0.03, 1.52), (0, -0.1, 1.82), (0, -0.23, 2.0), (0, -0.4, 2.04)],
                       [0.41, 0.31, 0.21, 0.13, 0.075], 12), "Hat")
part("Cream_Pompom", m.sphere(0.1, (1, 1, 1), 2, (0, -0.5, 2.01)), "Cream")
c = (0, 0.285, 1.52)
part("Gold_HatStar", m.rotate_x(m.star(0.095, 0.043, 0.02, c), 18, c), "Gold")

# Arka tasarım (oyunda kamera karakteri arkadan görür): beyaz saç, kukuleta, altın yıldız ve kemer kurdelesi
part("Cream_HairBack", m.sphere(0.34, (1.1, 0.8, 0.95), 2, (0, -0.2, 0.98)), "Cream")
for s, sx in (("L", -1), ("R", 1)):
    part("Cream_HairTuft" + s, m.sphere(0.13, (0.8, 0.9, 1.5), 1, (0.34 * sx, -0.05, 0.88)), "Cream")
    part("RobeDark_Ribbon" + s, m.loft([(0.05 * sx, -0.31, 0.44), (0.09 * sx, -0.33, 0.24)], [0.035, 0.03], 5), "RobeDark")
part("RobeDark_Hood", m.sphere(0.2, (1.25, 0.5, 0.9), 2, (0, -0.2, 0.7)), "RobeDark")
bc = (0, -0.325, 0.4)
part("Gold_BackStar", m.rotate_z(m.star(0.14, 0.065, 0.02, bc), 180, bc), "Gold")

m.render_views("wizard", PREVIEW_DIR, [
    ("front", (2.6, 4.8, 1.9)),
    ("back", (-2.6, -4.8, 1.9)),
], target=(0, -0.05, 1.05), size=(700, 800), background=(0.9, 0.88, 0.94), lens=60, gain=1.25)

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
