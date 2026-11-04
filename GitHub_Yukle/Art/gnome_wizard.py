"""
Konsept: büyük başlı, küçük gövdeli, pembe kıyafetli sakallı sevimli büyücü (orijinal tasarım).
Çalıştırma: OUT=önizleme klasörü blender -b -P gnome_wizard.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import modeling as m

OUT = os.environ["OUT"]
m.reset_scene()

for key, rgb in {
    "Robe": (1.0, 0.18, 0.55), "RobeDark": (0.78, 0.08, 0.4), "Cream": (1.0, 0.95, 0.85),
    "Skin": (1.0, 0.72, 0.55), "Nose": (1.0, 0.5, 0.5), "Eye": (0.06, 0.05, 0.08),
    "Shine": (1.0, 1.0, 1.0), "Blush": (1.0, 0.4, 0.5), "Boot": (0.5, 0.25, 0.12),
    "Gold": (1.0, 0.75, 0.1),
}.items():
    m.material(key, rgb)

# Ayaklar (cübbenin altından görünür)
for s, sx in (("L", -1), ("R", 1)):
    m.finish("Boot" + s, m.sphere(0.12, (1.0, 1.45, 0.7), 2, (0.15 * sx, 0.14, 0.07)), "Boot")

# Uzun cübbe: yere doğru genişleyen, altın etekli ve kemerli
m.finish("Robe", m.loft([(0, 0, 0.12), (0, 0, 0.35), (0, 0, 0.58), (0, 0, 0.70)],
                        [0.41, 0.34, 0.25, 0.2], 12, (0.95, 1.0)), "Robe")
m.finish("RobeHem", m.loft([(0, 0, 0.12), (0, 0, 0.2)], [0.415, 0.395], 12, (0.95, 1.0)), "Gold")
m.finish("Belt", m.loft([(0, 0, 0.40), (0, 0, 0.47)], [0.325, 0.31], 12, (0.95, 1.0)), "RobeDark")
m.finish("BeltBuckle", m.sphere(0.05, (1, 0.5, 1), 1, (0, 0.31, 0.44)), "Gold")
m.finish("Collar", m.loft([(0, 0, 0.64), (0, 0, 0.76)], [0.23, 0.19], 12), "RobeDark")

# Geniş cübbe kolları, altın kol ağzı ve eller
for s, sx in (("L", -1), ("R", 1)):
    m.finish("Sleeve" + s, m.loft([(0.25 * sx, 0.02, 0.62), (0.4 * sx, 0.12, 0.38)], [0.1, 0.15], 8), "Robe")
    m.finish("Cuff" + s, m.loft([(0.385 * sx, 0.11, 0.41), (0.42 * sx, 0.125, 0.35)], [0.15, 0.15], 8), "Gold")
    m.finish("Hand" + s, m.sphere(0.075, (1, 1, 1), 2, (0.43 * sx, 0.14, 0.32)), "Skin")

# Büyük baş
HEAD = (0, 0, 0.97)
m.finish("Head", m.sphere(0.4, (1.05, 0.95, 0.93), 2, HEAD), "Skin")
for s, sx in (("L", -1), ("R", 1)):
    m.finish("Eye" + s, m.sphere(0.047, (1, 0.6, 1.1), 2, (0.135 * sx, 0.355, 1.03)), "Eye")
    m.finish("Shine" + s, m.sphere(0.014, (1, 0.6, 1), 1, (0.147 * sx, 0.395, 1.055)), "Shine")
    m.finish("Blush" + s, m.sphere(0.06, (1.2, 0.35, 0.7), 1, (0.26 * sx, 0.3, 0.9)), "Blush")
    m.finish("Brow" + s, m.rotate_y(m.box((0.09, 0.02, 0.025), (0.14 * sx, 0.345, 1.12)), -12 * sx, (0.14 * sx, 0.345, 1.12)), "Cream")
m.finish("Nose", m.sphere(0.08, (1, 0.95, 0.9), 2, (0, 0.385, 0.94)), "Nose")

# Yumuşak, kabarık sakal ve bıyık
m.finish("Beard", m.sphere(0.34, (1.15, 0.72, 1.0), 2, (0, 0.2, 0.68)), "Cream")
m.finish("BeardLowL", m.sphere(0.16, (1, 0.8, 1.2), 2, (-0.14, 0.3, 0.52)), "Cream")
m.finish("BeardLowR", m.sphere(0.16, (1, 0.8, 1.2), 2, (0.14, 0.3, 0.52)), "Cream")
m.finish("BeardTip", m.loft([(0, 0.3, 0.55), (0, 0.34, 0.36), (0, 0.35, 0.2)], [0.17, 0.12, 0.02], 8, (0.8, 1.0)), "Cream")
for s, sx in (("L", -1), ("R", 1)):
    m.finish("Mustache" + s, m.sphere(0.12, (1.35, 0.75, 0.8), 2, (0.11 * sx, 0.36, 0.855)), "Cream")

# Pembe sivri şapka: geriye bükülür, ucunda pon pon
m.finish("HatBand", m.loft([(0, 0, 1.18), (0, 0, 1.30)], [0.43, 0.43], 14), "RobeDark")
hat = m.loft([(0, 0, 1.2), (0, -0.03, 1.52), (0, -0.1, 1.82), (0, -0.23, 2.0), (0, -0.4, 2.04)],
             [0.41, 0.31, 0.21, 0.13, 0.075], 12)
m.finish("Hat", hat, "Robe")
m.finish("Pompom", m.sphere(0.1, (1, 1, 1), 2, (0, -0.5, 2.01)), "Cream")
c = (0, 0.285, 1.52)
m.finish("HatStar", m.rotate_x(m.star(0.095, 0.043, 0.02, c), 18, c), "Gold")

m.render_views("gnome", OUT, [
    ("front", (2.6, 4.8, 1.9)),
    ("side", (-4.5, 3.0, 1.6)),
], target=(0, -0.05, 1.05), size=(700, 800), background=(0.88, 0.85, 0.8), lens=60, gain=1.2)
