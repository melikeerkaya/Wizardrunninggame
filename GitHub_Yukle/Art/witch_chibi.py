"""
Konsept: çok büyük başlı, küçük gövdeli, pembe cübbeli ve geniş kenarlı pembe cadı şapkalı sevimli büyücü kız.
Çalıştırma: OUT=önizleme klasörü blender -b -P witch_chibi.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import modeling as m

OUT = os.environ["OUT"]
m.reset_scene()

for key, rgb in {
    "Hat": (1.0, 0.38, 0.7), "Gold": (1.0, 0.85, 0.25), "Skin": (1.0, 0.9, 0.8),
    "Hair": (1.0, 0.88, 0.55), "Eye": (0.1, 0.06, 0.14), "Shine": (1.0, 1.0, 1.0),
    "Blush": (1.0, 0.55, 0.65), "Robe": (1.0, 0.5, 0.78), "RobeDark": (0.9, 0.25, 0.6),
    "Cape": (1.0, 0.6, 0.82), "Cream": (1.0, 0.95, 0.88), "Boot": (0.45, 0.25, 0.15),
}.items():
    m.material(key, rgb)

# Botlar
for s, sx in (("L", -1), ("R", 1)):
    m.finish("Boot" + s, m.sphere(0.1, (1.0, 1.5, 0.75), 2, (0.13 * sx, 0.13, 0.07)), "Boot")

# Pembe cübbe: yere doğru genişler, altın etek, kemer, krem yaka ve fiyonk
m.finish("Robe", m.loft([(0, 0, 0.10), (0, 0, 0.28), (0, 0, 0.50), (0, 0, 0.64)],
                        [0.36, 0.30, 0.22, 0.17], 12, (0.95, 1.0)), "Robe")
m.finish("RobeHem", m.loft([(0, 0, 0.10), (0, 0, 0.17)], [0.365, 0.345], 12, (0.95, 1.0)), "Gold")
m.finish("Belt", m.loft([(0, 0, 0.34), (0, 0, 0.40)], [0.285, 0.27], 12, (0.95, 1.0)), "RobeDark")
m.finish("BeltBuckle", m.sphere(0.04, (1, 0.5, 1), 1, (0, 0.27, 0.37)), "Gold")
m.finish("Collar", m.loft([(0, 0, 0.58), (0, 0, 0.68)], [0.21, 0.17], 12), "Cream")
m.finish("BowL", m.sphere(0.06, (1.5, 0.6, 1.0), 1, (-0.08, 0.17, 0.62)), "RobeDark")
m.finish("BowR", m.sphere(0.06, (1.5, 0.6, 1.0), 1, (0.08, 0.17, 0.62)), "RobeDark")
m.finish("BowKnot", m.sphere(0.035, (1, 1, 1), 1, (0, 0.18, 0.62)), "Gold")

# Açık pembe pelerin
m.finish("Cape", m.loft([(0, -0.1, 0.66), (0, -0.17, 0.4), (0, -0.22, 0.12)], [0.16, 0.22, 0.3], 8, (0.15, 1.0)), "Cape")

# Geniş kollar, altın manşet, eller
for s, sx in (("L", -1), ("R", 1)):
    m.finish("Sleeve" + s, m.loft([(0.2 * sx, 0.02, 0.56), (0.34 * sx, 0.1, 0.34)], [0.08, 0.12], 8), "Robe")
    m.finish("Cuff" + s, m.loft([(0.325 * sx, 0.095, 0.375), (0.355 * sx, 0.11, 0.315)], [0.12, 0.12], 8), "Gold")
    m.finish("Hand" + s, m.sphere(0.065, (1, 1, 1), 2, (0.365 * sx, 0.12, 0.28)), "Skin")

# Çok büyük, yuvarlak baş
m.finish("Head", m.sphere(0.42, (1.05, 0.95, 0.95), 2, (0, 0, 0.98)), "Skin")
for s, sx in (("L", -1), ("R", 1)):
    m.finish("Eye" + s, m.sphere(0.08, (0.9, 0.4, 1.05), 2, (0.15 * sx, 0.37, 1.0)), "Eye")
    m.finish("Shine" + s, m.sphere(0.022, (1, 0.5, 1), 1, (0.15 * sx + 0.02, 0.4, 1.035)), "Shine")
    m.finish("Blush" + s, m.sphere(0.065, (1.2, 0.3, 0.7), 1, (0.27 * sx, 0.31, 0.88)), "Blush")
    m.finish("Brow" + s, m.rotate_y(m.box((0.1, 0.02, 0.02), (0.15 * sx, 0.38, 1.12)), -10 * sx, (0.15 * sx, 0.38, 1.12)), "Hair")
m.finish("Nose", m.sphere(0.025, (1, 1, 1), 1, (0, 0.405, 0.92)), "Skin")
m.finish("Mouth", m.sphere(0.03, (1.8, 0.3, 0.5), 1, (0, 0.395, 0.82)), "Eye")

# Saç: baş, kakül, yanlarda bob ve sırtta akan saç
m.finish("HairTop", m.sphere(0.43, (1.03, 1.0, 1.0), 2, (0, -0.08, 1.0)), "Hair")
for i, (x, y, z) in enumerate([(-0.19, 0.30, 1.24), (0.0, 0.34, 1.28), (0.19, 0.30, 1.24)]):
    m.finish("Bang%d" % i, m.sphere(0.1, (1.3, 0.8, 0.7), 1, (x, y, z)), "Hair")
for s, sx in (("L", -1), ("R", 1)):
    m.finish("Lock" + s, m.sphere(0.12, (0.8, 1.0, 1.7), 1, (0.4 * sx, 0.0, 0.88)), "Hair")
m.finish("HairBack", m.loft([(0, -0.3, 1.15), (0, -0.37, 0.92), (0, -0.34, 0.7)], [0.32, 0.3, 0.14], 8, (0.8, 1.1)), "Hair")

# Geniş kenarlı, geriye bükülen sivri pembe cadı şapkası
m.witch_hat(1.27, 1.15)

m.render_views("witch", OUT, [
    ("front", (2.6, 4.8, 1.7)),
    ("side", (-4.6, 2.8, 1.5)),
], target=(0, -0.05, 1.0), size=(700, 800), background=(0.9, 0.88, 0.94), lens=60, gain=1.25)
