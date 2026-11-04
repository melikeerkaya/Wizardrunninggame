"""
Karakter adayları: genç büyücü kız ve tilki büyücü (hafif sevimli, yaklaşık 4,5 kafa boyunda, low-poly).
Çalıştırma: CHAR=girl veya CHAR=fox, OUT=önizleme klasörü
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import modeling as m

CHAR = os.environ.get("CHAR", "girl")
OUT = os.environ["OUT"]

m.reset_scene()

for key, rgb in {
    "Hat": (1.0, 0.45, 0.72), "Gold": (1.0, 0.82, 0.3), "Skin": (1.0, 0.85, 0.75),
    "Hair": (0.96, 0.84, 0.62), "Eye": (0.12, 0.08, 0.15), "Shine": (1.0, 1.0, 1.0),
    "Blush": (1.0, 0.6, 0.65), "Dress": (0.5, 0.3, 0.6), "Cape": (1.0, 0.55, 0.78),
    "Bow": (0.9, 0.2, 0.5), "Boot": (0.4, 0.24, 0.2), "Stocking": (0.97, 0.93, 0.93),
    "Wood": (0.55, 0.36, 0.2), "Gem": (1.0, 0.3, 0.55),
    "Fur": (0.97, 0.56, 0.22), "Cream": (1.0, 0.93, 0.8), "Dark": (0.28, 0.16, 0.12),
    "Amber": (0.95, 0.65, 0.1), "Cloak": (0.45, 0.35, 0.8),
}.items():
    m.material(key, rgb)


def mirrored(name, path, radii, key, segs=8, squash=(1, 1), caps=(True, True)):
    for side, sx in (("L", -1), ("R", 1)):
        p = [(x * sx, y, z) for x, y, z in path]
        m.finish(name + side, m.loft(p, radii, segs, squash, caps), key)


def common_body(dress_key, cape_key, arm_key, leg_key, boot_key, hand_key):
    # Çizmeler ve bacaklar
    for side, sx in (("L", -1), ("R", 1)):
        x = 0.09 * sx
        m.finish("Leg" + side, m.loft([(x, 0, 0.20), (x, 0, 0.62)], [0.045, 0.055], 6), leg_key)
        m.finish("Boot" + side, m.loft([(x, 0, 0.02), (x, 0, 0.25)], [0.075, 0.062], 8), boot_key)
        foot = m.sphere(0.07, (1.0, 1.6, 0.7), 1, (x, 0.05, 0.06))
        m.finish("Foot" + side, foot, boot_key)

    # Elbise (A biçimli) ve pelerin
    m.finish("Dress", m.loft([(0, 0, 0.46), (0, 0, 0.66), (0, 0, 0.90), (0, 0, 1.10)],
                             [0.28, 0.24, 0.17, 0.12], 10, (0.88, 1.0)), dress_key)
    m.finish("Cape", m.loft([(0, -0.12, 1.12), (0, -0.19, 0.86), (0, -0.26, 0.56)],
                            [0.17, 0.22, 0.28], 8, (0.16, 1.0)), cape_key)
    m.finish("Collar", m.loft([(0, 0, 1.08), (0, 0, 1.16)], [0.15, 0.11], 10), cape_key)

    # Kollar ve eller
    for side, sx in (("L", -1), ("R", 1)):
        arm = [(0.16 * sx, 0, 1.04), (0.22 * sx, 0.03, 0.88), (0.25 * sx, 0.09, 0.72)]
        m.finish("Arm" + side, m.loft(arm, [0.05, 0.052, 0.042], 6), arm_key)
        m.finish("Hand" + side, m.sphere(0.052, (1, 1, 1), 1, (0.25 * sx, 0.1, 0.68)), hand_key)

    # Asa
    m.finish("Wand", m.loft([(0.25, 0.10, 0.50), (0.25, 0.14, 1.08)], [0.016, 0.014], 5), "Wood")
    m.finish("WandStarBack", m.star(0.085, 0.04, 0.014, (0.25, 0.135, 1.16)), "Gold")
    m.finish("WandStar", m.star(0.062, 0.03, 0.02, (0.25, 0.15, 1.16)), "Gem")


def eyes_and_face(eye_key, y_front=0.185, z=1.31, eye_scale=(0.8, 0.35, 1.2), eye_r=0.046):
    for side, sx in (("L", -1), ("R", 1)):
        x = 0.078 * sx
        m.finish("Eye" + side, m.sphere(eye_r, eye_scale, 2, (x, y_front, z)), eye_key)
        m.finish("Shine" + side, m.sphere(0.014, (1, 0.5, 1), 1, (x + 0.012, y_front + 0.014, z + 0.018)), "Shine")
        m.finish("Blush" + side, m.sphere(0.036, (1.1, 0.3, 0.7), 1, (0.125 * sx, 0.165, 1.245)), "Blush")
    m.finish("Mouth", m.sphere(0.02, (1.6, 0.3, 0.5), 1, (0, 0.196, 1.225)), "Eye")


def build_girl():
    common_body("Dress", "Cape", "Dress", "Stocking", "Boot", "Skin")
    m.finish("Bow", m.sphere(0.05, (1.5, 0.6, 1.0), 1, (-0.075, 0.13, 1.065)), "Bow")
    m.finish("BowR", m.sphere(0.05, (1.5, 0.6, 1.0), 1, (0.075, 0.13, 1.065)), "Bow")
    m.finish("BowKnot", m.sphere(0.03, (1, 1, 1), 1, (0, 0.135, 1.065)), "Gold")

    m.finish("Neck", m.loft([(0, 0, 1.08), (0, 0, 1.18)], [0.055, 0.05], 8), "Skin")
    m.finish("Head", m.sphere(0.2, (0.98, 0.93, 1.0), 2, (0, 0, 1.32)), "Skin")
    m.finish("Nose", m.sphere(0.014, (1, 1, 1), 1, (0, 0.2, 1.275)), "Skin")
    eyes_and_face("Eye")
    for side, sx in (("L", -1), ("R", 1)):
        brow = m.rotate_y(m.box((0.05, 0.012, 0.01), (0.08 * sx, 0.188, 1.375)), -10 * sx, (0.08 * sx, 0.188, 1.375))
        m.finish("Brow" + side, brow, "Hair")

    # Saç: üst kısım, kakül, yan perçemler ve sırttan akan uzun saç
    m.finish("Hair_Top", m.sphere(0.215, (1.02, 1.0, 1.0), 2, (0, -0.03, 1.35)), "Hair")
    for i, (x, y, z) in enumerate([(-0.09, 0.15, 1.43), (0.0, 0.16, 1.45), (0.09, 0.15, 1.43)]):
        m.finish("Bang%d" % i, m.sphere(0.065, (1.3, 0.8, 0.7), 1, (x, y, z)), "Hair")
    for side, sx in (("L", -1), ("R", 1)):
        m.finish("Lock" + side, m.sphere(0.06, (0.7, 0.9, 2.0), 1, (0.19 * sx, 0.02, 1.25)), "Hair")
    m.finish("Hair_Back", m.loft([(0, -0.16, 1.42), (0, -0.2, 1.2), (0, -0.2, 0.98)],
                                 [0.17, 0.15, 0.07], 8, (0.8, 1.1)), "Hair")

    m.witch_hat(1.50)


def build_fox():
    common_body("Cloak", "Cape", "Cloak", "Dark", "Dark", "Fur")
    m.finish("Chest", m.sphere(0.1, (1.1, 0.7, 1.0), 1, (0, 0.1, 0.98)), "Cream")

    # Gövde üstü ve baş
    m.finish("Neck", m.loft([(0, 0, 1.08), (0, 0, 1.18)], [0.06, 0.055], 8), "Fur")
    m.finish("Head", m.sphere(0.21, (1.12, 0.95, 0.92), 2, (0, 0, 1.31)), "Fur")
    m.finish("Muzzle", m.loft([(0, 0.15, 1.275), (0, 0.29, 1.255)], [0.1, 0.05], 8, (0.95, 1.0)), "Cream")
    m.finish("Nose", m.sphere(0.028, (1.2, 1, 0.9), 1, (0, 0.305, 1.262)), "Eye")
    for side, sx in (("L", -1), ("R", 1)):
        m.finish("Cheek" + side, m.loft([(0.15 * sx, 0.07, 1.25), (0.28 * sx, 0.05, 1.21)], [0.06, 0.006], 6), "Cream")
        # Kulaklar şapkanın yanından yukarı çıkar
        ear = [(0.22 * sx, 0.0, 1.40), (0.34 * sx, 0.0, 1.72)]
        m.finish("Ear" + side, m.loft(ear, [0.085, 0.012], 6, (0.55, 1.0)), "Fur")
        inner = [(0.225 * sx, 0.04, 1.41), (0.335 * sx, 0.04, 1.68)]
        m.finish("EarIn" + side, m.loft(inner, [0.05, 0.008], 6, (0.4, 1.0)), "Cream")
    eyes_and_face("Amber", y_front=0.19, z=1.33, eye_scale=(0.8, 0.35, 1.25), eye_r=0.05)
    m.finish("Mouth2", m.sphere(0.012, (1, 1, 1), 1, (0, 0.285, 1.215)), "Eye")

    # Gür kuyruk ve krem uç
    tail = [(0, -0.15, 0.70), (0, -0.34, 0.66), (0, -0.58, 0.76), (0, -0.76, 0.95), (0, -0.82, 1.12)]
    m.finish("Tail", m.loft(tail, [0.05, 0.12, 0.17, 0.16, 0.12], 8, caps=(True, False)), "Fur")
    m.finish("TailTip", m.loft([(0, -0.82, 1.12), (0, -0.82, 1.26), (0, -0.80, 1.38)], [0.12, 0.1, 0.012], 8, caps=(False, True)), "Cream")

    m.witch_hat(1.50)


if CHAR == "girl":
    build_girl()
else:
    build_fox()

m.render_views(CHAR, OUT, [
    ("front", (2.3, 4.0, 1.7)),
    ("side", (4.6, 0.6, 1.5)),
    ("back", (-2.3, -4.0, 1.8)),
], target=(0, 0, 1.15))
