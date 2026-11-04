"""
Çöl harabesi engelleri (Çöl Diyarı). Her biri ayrı bir FBX olarak çıkar (oyunda Resources/Models/Desert/Ruins):
  FallenColumn - devrilmiş, ikiye ayrılmış yivli sütun ve başlığı         (alçak engel: üzerinden zıplanır)
  BrokenStones - tepesi kırık kesme taş, yan yatmış blok ve kaya yığını   (alçak engel)
  SandBlocks   - kumdan eğik çıkan, turkuaz-altın işlemeli kesme taşlar   (alçak engel)
  RuinArch     - iki sütun, taş lento ve üstünde yıkık duvar              (yüksek engel: altından kayılır)
Ölçüler oyun birimindedir. Alçak engeller şeritte ~1.8 birim yer kaplar, tepeleri en çok ~0.8 (Chunk.LowHeight: ~1.5 boylu
karakterin beli). Kemerin sütunları zincir kapısındaki gibi şerit sınırlarında (x = ±1.25), lentonun altı 1.25'te,
duvar ortada ~2.4'e kadar çıkar: ayaktaki karakter lentoya çarpar, kayarak geçilir, üzerinden zıplanamaz (zıplamanın
tepesinde ayaklar 2.0'dadır).
Hepsi zincir kapısıyla aynı kumtaşı ailesinden, çömleklerdeki turkuaz-altın süslerle; kırık yüzler bir ton koyudur.
Low-poly: düz gölgeli yüzler, parçalar renk anahtarına göre tek mesh'te birleşir (az çizim çağrısı).
Z yukarı, zemin z=0. FBX dışa aktarımı modeli dik eksende 180° döndürür: Unity'de oyuncuya dönük yüz buradaki +Y yüzüdür.
Çarpışma kutularını Obstacle.cs kurar: adında "Decor" geçen parçalar (kum tümseği, çakıl) sayılmaz, kemerin sütun
taşlarının adında "Post" geçer (yan yana iki kemerde ortak sütun bir kez çizilir).
Çalıştırma: RUINS_DIR (FBX klasörü), RUINS_BLEND, RUINS_PREVIEW ve önizlemedeki karşılaştırma için RUINS_OLD
(Resources/Models klasörü) ortam değişkenleriyle blender -b -P build_ruins.py. Sonuç RUINS_PREVIEW/ruins_log.txt'ye yazılır.
Nesne adları "RenkAnahtarı_Parça" biçimindedir (renkleri Unity kodla verir, bkz. ModelPalette.cs).
"""
import math
import os
import random
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

import modeling as m

OUT_DIR = os.environ["RUINS_DIR"]
BLEND_PATH = os.environ["RUINS_BLEND"]
PREVIEW_DIR = os.environ["RUINS_PREVIEW"]
OLD_DIR = os.environ.get("RUINS_OLD")

# ModelPalette.cs ile aynı (sRGB). Önizlemede eski modeller de bunlarla boyanır.
PALETTE = {
    "Skin": (1.0, 0.75, 0.62), "Blush": (0.96, 0.52, 0.5), "Lip": (0.86, 0.42, 0.42), "Mouth": (0.55, 0.18, 0.2),
    "Sclera": (0.98, 0.96, 0.94), "Iris": (0.52, 0.25, 0.17), "Pupil": (0.16, 0.07, 0.06), "Shine": (1.0, 1.0, 1.0),
    "Lash": (0.2, 0.09, 0.08), "Brow": (0.38, 0.17, 0.14), "Hair": (0.8, 0.4, 0.42), "HairLight": (0.92, 0.55, 0.53),
    "HairDark": (0.6, 0.27, 0.32), "Hat": (0.86, 0.42, 0.53), "HatDark": (0.74, 0.33, 0.46),
    "HatBand": (0.33, 0.21, 0.27), "HatGem": (0.9, 0.42, 0.3), "Brass": (0.95, 0.67, 0.33), "Coat": (0.98, 0.9, 0.86),
    "CoatBack": (0.93, 0.52, 0.62), "CoatTrim": (0.78, 0.33, 0.44), "Top": (0.3, 0.24, 0.31),
    "Shorts": (0.34, 0.27, 0.33), "Stocking": (0.27, 0.21, 0.24), "Leather": (0.45, 0.27, 0.22),
    "Boot": (0.45, 0.24, 0.27), "BootCuff": (0.76, 0.5, 0.46), "Sole": (0.9, 0.8, 0.7), "Glove": (0.4, 0.24, 0.23),
    "Gold": (1.0, 0.75, 0.0), "Cream": (1.0, 0.97, 0.9), "Sandstone": (0.88, 0.58, 0.4),
    "SandstoneDark": (0.78, 0.48, 0.32), "SandstoneLight": (0.94, 0.68, 0.48), "SandstoneDeep": (0.62, 0.36, 0.25),
    "Iron": (0.56, 0.58, 0.62), "Bronze": (0.8, 0.55, 0.22), "BronzeDark": (0.55, 0.36, 0.16),
    "Sand": (0.95, 0.82, 0.58), "Dune": (0.85, 0.75, 0.55), "Clay": (0.86, 0.46, 0.32), "ClayDark": (0.22, 0.13, 0.1),
    "Earth": (0.62, 0.5, 0.34), "EarthDark": (0.4, 0.3, 0.2), "Plum": (0.5, 0.36, 0.42),
    "Turquoise": (0.2, 0.75, 0.8), "PotOrange": (0.95, 0.58, 0.25),
}
# Kırık ve kesik yüzler parçanın renginden bir ton koyu olur.
DARKER = {"SandstoneLight": "Sandstone", "Sandstone": "SandstoneDark", "SandstoneDark": "SandstoneDeep",
          "SandstoneDeep": "SandstoneDeep"}
GROUND = (0.85, 0.75, 0.55)  # WorldData: çöl zemini
SKY = (0.65, 0.82, 0.95)  # WorldData: çöl göğü, aynı zamanda sis rengi
FOG_START, FOG_END = 40.0, 110.0  # ChunkSpawner

log_lines = []


def log(text):
    log_lines.append(text)
    os.makedirs(PREVIEW_DIR, exist_ok=True)
    with open(os.path.join(PREVIEW_DIR, "ruins_log.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines) + "\n")


# ---------- Mesh yardımcıları ----------

def T(x=0.0, y=0.0, z=0.0):
    return Matrix.Translation(Vector((x, y, z)))


def R(x=0.0, y=0.0, z=0.0):
    return Euler((math.radians(x), math.radians(y), math.radians(z)), "XYZ").to_matrix().to_4x4()


def move(bm, matrix):
    bmesh.ops.transform(bm, matrix=matrix, verts=bm.verts)
    return bm


def oriented(bm, center=(0.0, 0.0, 0.0)):
    """Yüz normallerini merkezden dışarı çevirir (dışbükey parçalarda doğru sonuç verir)."""
    bm.normal_update()
    c = Vector(center)
    for face in bm.faces:
        if face.normal.dot(face.calc_center_median() - c) < 0:
            face.normal_flip()
    bm.normal_update()
    return bm


def cut(bm, co, no, fill=True):
    """co'dan geçen ve no'ya bakan düzlemin dış yanını siler; fill ise kesiti kapatıp yeni yüzleri döndürür."""
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-5,
                           plane_co=Vector(co), plane_no=Vector(no).normalized(), clear_outer=True)
    if not fill:
        return []
    boundary = [e for e in bm.edges if e.is_boundary]
    return bmesh.ops.holes_fill(bm, edges=boundary, sides=0)["faces"] if boundary else []


def split_off(bm, faces):
    """Yüzleri ayrı bir mesh'e taşır (kırık yüzler ayrı renk alır)."""
    out = bmesh.new()
    faces = [f for f in faces if f.is_valid]
    mapping = {}
    for face in faces:
        verts = []
        for v in face.verts:
            if v not in mapping:
                mapping[v] = out.verts.new(v.co)
            verts.append(mapping[v])
        out.faces.new(verts)
    bmesh.ops.delete(bm, geom=faces, context="FACES_ONLY")
    return out


def stone(key, size, seed=0, chips=2, chip=0.08, top=None, end=None, bevel=0.035):
    """Pahlı kesme taş (merkez orijinde). top=(derinlik, eğim_x, eğim_y): tepesi eğik kırık; end=(±1, derinlik): o x ucu
    kırık; chips: kırık köşe sayısı. [(renk, bmesh)] döndürür."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bevel, segments=1, affect="EDGES", profile=0.5)
    hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
    broken = []
    if top:
        depth, tx, ty = top
        broken += cut(bm, (0, 0, hz - depth), (tx, ty, 1.0))
    if end:
        sign, depth = end
        broken += cut(bm, (sign * (hx - depth), 0, 0), (sign, rnd.uniform(-0.35, 0.35), rnd.uniform(-0.6, 0.6)))
    corners = [Vector((a * hx, b * hy, c * hz)) for a in (-1, 1) for b in (-1, 1) for c in (-1, 1)]
    for corner in rnd.sample(corners, chips):
        d = corner.normalized()
        no = d + Vector((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3)))
        broken += cut(bm, corner - d * chip * rnd.uniform(0.7, 1.3), no)
    pieces = split_off(bm, broken)
    return [(key, oriented(bm)), (DARKER[key], oriented(pieces))]


def rock(key, radii, seed=0, jitter=0.2):
    """Kırık kaya parçası: rastgele bozulmuş ikosahedron (20 yüz)."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
    for v in bm.verts:
        s = rnd.uniform(1.0 - jitter, 1.0 + jitter)
        v.co = Vector((v.co.x * radii[0] * s, v.co.y * radii[1] * s, v.co.z * radii[2] * s))
    return [(key, oriented(bm))]


def drum(key, cap_key, x0, x1, radius, sides=16, flute=0.1, twist=0.0, broken=None, seed=0):
    """X ekseni boyunca yatan yivli sütun gövdesi (kesitte dış ve iç köşeler sırayla). broken=(uç, pürüz): o uç
    (0: x0, 1: x1) kırık ve sivri, diğeri düz kesik. Uç yüzleri cap_key rengini alır."""
    rnd = random.Random(seed)
    side = bmesh.new()
    rings = []
    for x in (x0, x1):
        ring = []
        for i in range(sides):
            a = 2 * math.pi * i / sides + math.radians(twist)
            r = radius * (1.0 - flute if i % 2 else 1.0)
            ring.append(side.verts.new((x, r * math.cos(a), r * math.sin(a))))
        rings.append(ring)
    if broken:
        end, rough = broken
        sign = -1 if end == 0 else 1
        for v in rings[end]:
            v.co.x += sign * rnd.uniform(-rough, rough * 0.5)
    for i in range(sides):
        j = (i + 1) % sides
        side.faces.new((rings[0][i], rings[0][j], rings[1][j], rings[1][i]))
    caps = bmesh.new()
    for end, ring in enumerate(rings):
        loop = [caps.verts.new(v.co) for v in ring]
        if broken and broken[0] == end:
            sign = -1 if end == 0 else 1
            x = (x0, x1)[end] + sign * broken[1] * rnd.uniform(0.4, 0.9)
            tip = caps.verts.new((x, rnd.uniform(-0.3, 0.3) * radius, rnd.uniform(-0.3, 0.3) * radius))
            for i in range(sides):
                caps.faces.new((loop[i], loop[(i + 1) % sides], tip))
        else:
            caps.faces.new(loop)
    center = ((x0 + x1) / 2, 0.0, 0.0)
    return [(key, oriented(side, center)), (cap_key, oriented(caps, center))]


def frustum(key, x0, x1, r0, r1, sides=16):
    """X ekseni boyunca kesik koni (sütun başlığının yayvan boynu, boyun bandı)."""
    bm = bmesh.new()
    rings = []
    for x, r in ((x0, r0), (x1, r1)):
        rings.append([bm.verts.new((x, r * math.cos(2 * math.pi * i / sides), r * math.sin(2 * math.pi * i / sides)))
                      for i in range(sides)])
    for i in range(sides):
        j = (i + 1) % sides
        bm.faces.new((rings[0][i], rings[0][j], rings[1][j], rings[1][i]))
    bm.faces.new(rings[0])
    bm.faces.new(rings[1])
    return [(key, oriented(bm, ((x0 + x1) / 2, 0.0, 0.0)))]


def plate(key, outline, depth):
    """XZ düzleminde dışbükey çokgen plaka (merkez orijinde, kalınlık Y yönünde): işleme, bant, çivi."""
    bm = bmesh.new()
    h = depth / 2
    front = [bm.verts.new((x, h, z)) for x, z in outline]
    back = [bm.verts.new((x, -h, z)) for x, z in outline]
    bm.faces.new(front)
    bm.faces.new(back)
    count = len(outline)
    for i in range(count):
        j = (i + 1) % count
        bm.faces.new((front[i], front[j], back[j], back[i]))
    return [(key, oriented(bm))]


def placed(pieces, matrix):
    return [(key, move(bm, matrix)) for key, bm in pieces]


def rect(w, h):
    return [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]


def rhombus(w, h):
    return [(0.0, -h / 2), (w / 2, 0.0), (0.0, h / 2), (-w / 2, 0.0)]


def mound(key, rx, ry, height, seed=0, segs=10):
    """Alçak kum tümseği (taşların dibini kuma gömer)."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    outer, mid = [], []
    for i in range(segs):
        a = 2 * math.pi * i / segs
        s = rnd.uniform(0.85, 1.12)
        outer.append(bm.verts.new((rx * s * math.cos(a), ry * s * math.sin(a), -0.02)))
        mid.append(bm.verts.new((rx * 0.55 * s * math.cos(a), ry * 0.55 * s * math.sin(a),
                                 height * rnd.uniform(0.65, 0.9))))
    top = bm.verts.new((rnd.uniform(-0.1, 0.1) * rx, rnd.uniform(-0.1, 0.1) * ry, height))
    for i in range(segs):
        j = (i + 1) % segs
        bm.faces.new((outer[i], outer[j], mid[j], mid[i]))
        bm.faces.new((mid[i], mid[j], top))
    return [(key, oriented(bm, (0.0, 0.0, -1.0)))]


class Model:
    """Bir engelin parçaları. Aynı renk anahtarı ve gruptaki parçalar tek mesh'te birleşir."""

    def __init__(self, name, center=True):
        self.name = name
        self.center = center
        self.parts = {}
        self.objects = []
        self.root = None
        self.tris = 0

    def put(self, pieces, matrix=None, group="Body"):
        for key, bm in pieces:
            if matrix is not None:
                move(bm, matrix)
            dst = self.parts.setdefault((key, group), bmesh.new())
            mapping = {v: dst.verts.new(v.co) for v in bm.verts}
            for face in bm.faces:
                dst.faces.new([mapping[v] for v in face.verts])
            bm.free()

    def clip_ground(self, depth=0.03):
        """Kumun altında kalan kısmı siler (görünmez, üçgen harcamasın)."""
        for bm in self.parts.values():
            cut(bm, (0.0, 0.0, -depth), (0.0, 0.0, -1.0), fill=False)

    def build(self):
        if self.center:
            body = [v.co.copy() for (_, group), bm in self.parts.items() if group != "Decor" for v in bm.verts]
            offset = Vector((-(min(p.x for p in body) + max(p.x for p in body)) / 2,
                             -(min(p.y for p in body) + max(p.y for p in body)) / 2, 0.0))
            for bm in self.parts.values():
                bmesh.ops.translate(bm, vec=offset, verts=bm.verts)
        self.root = m.make_root(self.name + "Root")
        for (key, group), bm in sorted(self.parts.items()):
            bmesh.ops.triangulate(bm, faces=bm.faces[:])
            self.tris += len(bm.faces)
            name = "%s_%s%s" % (key, group, self.name)
            mesh = bpy.data.meshes.new(name)
            bm.to_mesh(mesh)
            bm.free()
            obj = bpy.data.objects.new(name, mesh)
            bpy.context.collection.objects.link(obj)
            mesh.materials.append(m.material(key, PALETTE[key]))
            obj.parent = self.root
            self.objects.append(obj)
        self.parts = {}


# ---------- Engeller ----------

def fallen_column():
    """Devrik sütun: yerde yatan, çatlakla ikiye ayrılmış yivli gövde, turkuaz boyun bandı ve kare başlık."""
    model = Model("FallenColumn")
    radius = 0.37
    tilt = R(0, 0, 6)
    axis = T(0, 0, radius - 0.02) @ tilt
    model.put(drum("Sandstone", "SandstoneDeep", -0.88, -0.07, radius, broken=(0, 0.13), seed=3), axis)
    head = axis @ T(0, 0.02, 0.004) @ R(0, 0, 2.5)
    model.put(drum("Sandstone", "SandstoneDeep", -0.03, 0.42, radius, twist=11, seed=4), head)
    model.put(frustum("Turquoise", 0.35, 0.42, radius * 1.04, radius * 1.04), head)
    model.put(frustum("SandstoneLight", 0.42, 0.54, radius * 0.97, radius * 1.2), head)
    model.put(stone("SandstoneLight", (0.2, 0.8, 0.8), seed=5, chips=2, chip=0.07), head @ T(0.64, 0, 0) @ R(7, 0, 0))
    # Kırık uçtan dökülmüş parçalar ve sütunu yarı gömen kum
    for x, y, r, key, seed in ((-0.9, 0.34, 0.1, "SandstoneDark", 6), (-0.72, -0.42, 0.08, "Sandstone", 7),
                               (-0.5, 0.48, 0.12, "SandstoneDark", 8)):
        model.put(rock(key, (r, r * 0.85, r * 0.7), seed), T(x, y, r * 0.35), "Decor")
    model.put(mound("Dune", 1.0, 0.52, 0.12, seed=9), tilt, "Decor")
    return model


def broken_stones():
    """Kırık taş yığını: ortada tepesi eğik kırılmış büyük kesme taş (turkuaz şerit ve oyma izleri), solda yan yatmış
    blok, sağda yassı taş ve üstünde kaya, önde yaslanmış bir parça."""
    model = Model("BrokenStones")
    big = stone("SandstoneDark", (0.68, 0.6, 0.86), seed=11, chips=2, top=(0.16, 0.45, -0.15))
    for side in (1, -1):
        y = side * 0.3
        big += placed(plate("Turquoise", rect(0.5, 0.075), 0.018), T(-0.04, y + side * 0.008, 0.1))
        for x in (-0.2, -0.02, 0.16):
            big += placed(plate("ClayDark", rect(0.07, 0.11), 0.014), T(x, y + side * 0.006, -0.06))
    model.put(big, T(0.0, 0.0, 0.38) @ R(0, 3, 4))
    model.put(stone("Sandstone", (0.6, 0.46, 0.42), seed=12, chips=2), T(-0.56, 0.05, 0.19) @ R(0, -6, 24))
    model.put(stone("SandstoneLight", (0.52, 0.48, 0.26), seed=13, chips=1), T(0.56, -0.04, 0.12) @ R(0, 4, -14))
    model.put(rock("SandstoneDark", (0.19, 0.16, 0.15), seed=14), T(0.58, -0.02, 0.36))
    model.put(stone("Sandstone", (0.28, 0.16, 0.42), seed=15, chips=1, top=(0.1, -0.6, 0.3)),
              T(0.3, 0.36, 0.17) @ R(22, 0, 10))
    model.put(rock("Sandstone", (0.1, 0.09, 0.07), seed=16), T(-0.2, 0.46, 0.03), "Decor")
    model.put(rock("SandstoneDark", (0.08, 0.07, 0.06), seed=17), T(0.05, -0.46, 0.03), "Decor")
    model.put(rock("SandstoneDark", (0.07, 0.06, 0.05), seed=18), T(-0.75, -0.32, 0.02), "Decor")
    model.put(mound("Dune", 0.98, 0.58, 0.09, seed=19), None, "Decor")
    return model


def sand_blocks():
    """Kumdan eğik çıkan üç kesme taş; ortadakinin iki yüzünde altın çerçeveli turkuaz baklava işleme."""
    model = Model("SandBlocks")
    blocks = (("SandstoneDark", (0.64, 0.6, 1.2), 0.0, (7, -10, 8), 0.8, 21),
              ("Sandstone", (0.46, 0.5, 0.9), -0.6, (-6, -15, -12), 0.56, 22),
              ("SandstoneLight", (0.5, 0.48, 0.8), 0.6, (5, 15, 15), 0.5, 23))
    for index, (key, size, x, rot, top, seed) in enumerate(blocks):
        pieces = stone(key, size, seed=seed, chips=2, chip=0.09)
        if index == 0:
            for side in (1, -1):
                y = side * size[1] / 2
                pieces += placed(plate("Gold", rhombus(0.27, 0.36), 0.016), T(0, y + side * 0.006, 0.24))
                pieces += placed(plate("Turquoise", rhombus(0.18, 0.25), 0.016), T(0, y + side * 0.014, 0.24))
        rotation = R(*rot)
        lift = top - max((rotation @ v.co).z for _, bm in pieces for v in bm.verts)
        model.put(pieces, T(x, 0, lift) @ rotation)
        model.put(mound("Dune", size[0] * 0.75, size[1] * 0.78, 0.16, seed=seed), T(x, 0, 0), "Decor")
    model.put(mound("Dune", 1.0, 0.52, 0.07, seed=24), None, "Decor")
    model.clip_ground()
    return model


def ruin_arch():
    """Harabe kemeri: şerit sınırlarında iki sütun, aralarında taş lento (altın kenarlı turkuaz bant, altın çiviler),
    lentonun üstünde basamak basamak yıkılmış duvar. Altından kayılır, üzerinden zıplanamaz."""
    model = Model("RuinArch", center=False)
    px = 1.25
    lintel_bottom, lintel_top = 1.25, 1.85

    def post(group, x, courses, seed):
        rnd = random.Random(seed)
        for i, (key, width, z0, z1, top) in enumerate(courses):
            h = z1 - z0
            model.put(stone(key, (width, width, h), seed=seed + i, chips=1, chip=0.06, top=top),
                      T(x + rnd.uniform(-0.02, 0.02), rnd.uniform(-0.02, 0.02), z0 + h / 2) @ R(0, 0, rnd.uniform(-3, 3)),
                      group)

    post("PostA", -px, (("SandstoneDark", 0.92, 0.0, 0.64, None), ("Sandstone", 0.86, 0.63, 1.26, None),
                        ("SandstoneDark", 0.9, 1.25, 1.86, None), ("Sandstone", 0.86, 1.85, 2.45, None),
                        ("SandstoneDark", 0.84, 2.44, 3.05, (0.26, -0.55, 0.2))), 31)
    post("PostB", px, (("SandstoneDark", 0.92, 0.0, 0.62, None), ("Sandstone", 0.86, 0.61, 1.26, None),
                       ("SandstoneDark", 0.9, 1.25, 1.86, None), ("Sandstone", 0.86, 1.85, 2.5, None),
                       ("SandstoneDark", 0.84, 2.49, 3.1, None)), 41)
    model.put(stone("SandstoneLight", (1.1, 1.1, 0.22), seed=47, chips=2, chip=0.05), T(px, 0, 3.2) @ R(0, -2, 4), "PostB")

    # Lento sütunların ortasına kadar uzanır: yan yana iki kemerde ortak sütunun içinde biter, üst üste binmez.
    lintel = stone("SandstoneLight", (2.5, 0.8, lintel_top - lintel_bottom), seed=51, chips=2, chip=0.07)
    for side in (1, -1):
        y = side * 0.4
        lintel += placed(plate("Turquoise", rect(1.62, 0.15), 0.024), T(0, y + side * 0.012, 0.0))
        for z in (-0.085, 0.085):
            lintel += placed(plate("Gold", rect(1.62, 0.025), 0.03), T(0, y + side * 0.016, z))
        for x in (-0.6, -0.3, 0.0, 0.3, 0.6):
            lintel += placed(plate("Gold", rhombus(0.07, 0.09), 0.03), T(x, y + side * 0.026, 0.0))
    model.put(lintel, T(0, 0, (lintel_bottom + lintel_top) / 2))

    # Duvar bilerek alçak: kamera ~4.5 yüksekte, yüksek duvar arkasındaki sırayı son ana kadar gizlerdi.
    # (renk, x0, x1, z0, z1, derinlik, kırık tepe, kırık uç, seed)
    wall = (("Sandstone", -1.25, -0.06, 1.85, 2.42, 0.7, None, None, 61),
            ("SandstoneDark", -0.04, 1.25, 1.85, 2.38, 0.7, (0.1, -0.2, 0.1), None, 62),
            ("SandstoneDark", -1.25, -0.42, 2.42, 2.86, 0.62, None, (1, 0.12), 63),
            ("Sandstone", 0.56, 1.25, 2.38, 2.72, 0.62, (0.1, -0.5, 0.2), None, 64))
    for key, x0, x1, z0, z1, depth, top, end, seed in wall:
        rnd = random.Random(seed)
        model.put(stone(key, (x1 - x0, depth, z1 - z0), seed=seed, chips=1, chip=0.06, top=top, end=end),
                  T((x0 + x1) / 2, rnd.uniform(-0.02, 0.02), (z0 + z1) / 2) @ R(0, 0, rnd.uniform(-1.5, 1.5)))
    return model


# ---------- Dışa aktarım ----------

def mesh_bounds(objects):
    points = [o.matrix_world @ v.co for o in objects if "Decor" not in o.name for v in o.data.vertices]
    return (Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points))),
            Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points))))


def export(model):
    bpy.ops.object.select_all(action="DESELECT")
    model.root.select_set(True)
    for obj in model.objects:
        obj.select_set(True)
    bpy.ops.export_scene.fbx(
        filepath=os.path.join(OUT_DIR, model.name + ".fbx"), use_selection=True, object_types={"MESH", "EMPTY"},
        apply_unit_scale=True, bake_space_transform=True, axis_forward="-Z", axis_up="Y",
        mesh_smooth_type="FACE", add_leaf_bones=False,
    )
    lo, hi = mesh_bounds(model.objects)
    log("%s: %d üçgen, %d parça, gövde x %.2f..%.2f  y %.2f..%.2f  z %.2f..%.2f" % (
        model.name, model.tris, len(model.objects), lo.x, hi.x, lo.y, hi.y, lo.z, hi.z))


# ---------- Önizleme ----------

def import_old(relative_path):
    """Mevcut bir modeli karşılaştırma için yükler ve ModelPalette renkleriyle boyar."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(OLD_DIR, relative_path))
    new = [o for o in bpy.data.objects if o not in before]
    bpy.context.view_layer.update()
    meshes = [o for o in new if o.type == "MESH"]
    for obj in meshes:
        key = obj.name.split("_")[0]
        if key in PALETTE:
            obj.data.materials.clear()
            obj.data.materials.append(m.material(key, PALETTE[key]))
    for obj in new:
        obj.hide_render = True
    return meshes


def instance(meshes, location=(0, 0, 0), scale=1.0, rot_z=0.0, skip=None):
    """Mesh verisini paylaşan kopya. Şablonlar orijinde durur, kopyanın kökü yerini ve ölçeğini verir."""
    root = bpy.data.objects.new("Kopya", None)
    bpy.context.collection.objects.link(root)
    root.location = location
    root.rotation_euler = (0, 0, math.radians(rot_z))
    root.scale = (scale, scale, scale)
    copies = []
    for obj in meshes:
        if skip and skip in obj.name:
            continue
        copy = obj.copy()
        bpy.context.collection.objects.link(copy)
        copy.parent = root
        copy.matrix_parent_inverse = Matrix.Identity(4)
        copy.matrix_basis = obj.matrix_world.copy()
        copy.hide_render = False
        copies.append(copy)
    return root, copies


def remove(root, copies):
    for obj in copies + [root]:
        bpy.data.objects.remove(obj)


def setup_render(size, background):
    # Oyundaki ışığa yakın: sahnedeki Directional Light'ın yönünde güneş, ortam ışığı arka plan renginden.
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 16
    scene.view_settings.view_transform = "Standard"
    if "Sun" not in bpy.data.objects:
        data = bpy.data.lights.new("Sun", "SUN")
        data.energy = 2.2
        data.angle = math.radians(2.0)
        sun = bpy.data.objects.new("Sun", data)
        bpy.context.collection.objects.link(sun)
        sun.rotation_euler = Vector((0.32, -0.56, -0.77)).to_track_quat("-Z", "Y").to_euler()
    scene.render.resolution_x, scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    if scene.world is None:
        scene.world = bpy.data.worlds.new("Sky")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (*(c ** 2.2 for c in background), 1.0)


def shoot(name, location, target, lens=50.0, ortho=None, fov_y=None):
    scene = bpy.context.scene
    data = bpy.data.cameras.new("Cam")
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    elif fov_y:
        data.sensor_fit = "VERTICAL"
        data.angle_y = math.radians(fov_y)
    else:
        data.lens = lens
    data.clip_end = 500.0
    camera = bpy.data.objects.new("Cam", data)
    bpy.context.collection.objects.link(camera)
    camera.location = location
    camera.rotation_euler = (Vector(target) - Vector(location)).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera
    path = os.path.join(PREVIEW_DIR, name + ".png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(camera)
    return path


def stitch(paths, name):
    images = [bpy.data.images.load(p) for p in paths]
    w, h = images[0].size
    arrays = []
    for image in images:
        buf = np.empty(w * h * 4, dtype=np.float32)
        image.pixels.foreach_get(buf)
        arrays.append(buf.reshape(h, w, 4))
    sheet = np.concatenate(arrays, axis=1)
    out = bpy.data.images.new("sheet", width=w * len(arrays), height=h, alpha=False)
    out.pixels.foreach_set(sheet.flatten())
    out.filepath_raw = os.path.join(PREVIEW_DIR, name + ".png")
    out.file_format = "PNG"
    out.save()


def ground_plane(size, location=(0, 0, 0), color=GROUND):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector((size[0], size[1], 0.1)), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector((location[0], location[1], location[2] - 0.05)), verts=bm.verts)
    mesh = bpy.data.meshes.new("Zemin")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("Zemin", mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(m.material("Zemin%.3f" % color[0], color))
    return obj


def mixed(color, f):
    return tuple(c + (s - c) * f for c, s in zip(color, SKY))


def apply_fog(copies, depth):
    """Oyundaki doğrusal sis, nesne başına (mesh'in kendi malzemesi bozulmasın diye nesneye bağlı malzemeyle)."""
    f = round(min(1.0, max(0.0, (depth - FOG_START) / (FOG_END - FOG_START))) * 20) / 20
    for obj in copies:
        key = obj.name.split("_")[0]
        if key not in PALETTE:
            continue
        slot = obj.material_slots[0]
        slot.link = "OBJECT"
        slot.material = m.material("%s@%.2f" % (key, f), mixed(PALETTE[key], f))


def previews(models):
    bpy.context.view_layer.update()
    for model in models:
        model.root.hide_render = True
        for obj in model.objects:
            obj.hide_render = True
    by_name = {model.name: model.objects for model in models}

    # 1) Yeni modeller yakından, oyuncunun geldiği yönden
    setup_render((560, 460), (0.93, 0.87, 0.74))
    ground = ground_plane((14, 14))
    shots = []
    for model in models:
        tall = model.name == "RuinArch"
        root, copies = instance(model.objects)
        location = (3.2, 7.8, 3.4) if tall else (1.7, 3.5, 1.9)
        shots.append(shoot("yeni_" + model.name, location, (0, 0, 1.55 if tall else 0.35), lens=42))
        remove(root, copies)
    stitch(shots, "yeni_engeller")
    bpy.data.objects.remove(ground)

    if not OLD_DIR:
        return

    wizard = import_old("Wizard.fbx")
    pots = [import_old("Desert/Pots/%s.fbx" % name) for name in ("PotAmphora", "PotWide", "PotGold", "PotZigzag")]
    gate = import_old("Desert/ChainGate.fbx")
    bpy.context.view_layer.update()
    wizard_top = max((o.matrix_world @ v.co).z for o in wizard for v in o.data.vertices)
    wizard_scale = 1.51 / wizard_top  # Oyundaki karakter: 1.68 birim x 0.9 ölçek

    # 2) Boy karşılaştırması: karakterle aynı ölçekte, kameranın eğimiyle (16.7°)
    def lineup(items, width, size, name, target_z):
        setup_render(size, (0.93, 0.87, 0.74))
        added = []
        step_x = 0.0
        for meshes, scale, gap in items:
            step_x += gap
            added.append(instance(meshes, (step_x, 0, 0), scale))
        center = step_x / 2
        floor = ground_plane((width + 8, 12), (center, 0, 0))
        pitch = math.radians(16.7)
        shoot(name, (center, 40 * math.cos(pitch), target_z + 40 * math.sin(pitch)), (center, 0, target_z), ortho=width)
        for root, copies in added:
            remove(root, copies)
        bpy.data.objects.remove(floor)

    lineup([(wizard, wizard_scale, 0.0), (pots[0], 0.8, 1.7), (pots[1], 0.8, 2.1), (pots[2], 0.8, 2.1), (pots[3], 0.8, 2.1),
            (by_name["FallenColumn"], 1.0, 2.2), (by_name["BrokenStones"], 1.0, 2.2), (by_name["SandBlocks"], 1.0, 2.2)],
           17.0, (1700, 380), "boy_alcak", 0.6)
    lineup([(wizard, wizard_scale, 0.0), (gate, 1.0, 2.8), (by_name["RuinArch"], 1.0, 4.2)],
           11.0, (1000, 660), "boy_yuksek", 2.3)

    # 3) Oyun kamerası: dikey ekran, 60° görüş, sisli. Unity (x, y, z) burada (-x, -z, y) olur.
    setup_render((540, 960), SKY)
    cam_loc = Vector((0, 5.3, 4.5))
    cam_target = Vector((0, -6.3, 1.0))
    forward = (cam_target - cam_loc).normalized()

    def depth(point):
        return (Vector(point) - cam_loc).dot(forward)

    for i in range(60):
        z = -10.0 + i * 2.0 + 1.0
        f = round(min(1.0, max(0.0, (depth((0, -z, 0)) - FOG_START) / (FOG_END - FOG_START))) * 20) / 20
        ground_plane((8.5, 2.0), (0, -z, 0), mixed(GROUND, f))

    lanes = {-1: 2.5, 0: 0.0, 1: -2.5}  # Unity şeridi -> Blender x
    # (uzaklık, şerit, model, ölçek, atlanacak parça). Yan yana iki kemerde sağdakinin sol sütunu çizilmez.
    layout = ((15, 1, by_name["FallenColumn"], 1.0, None),
              (25, -1, by_name["RuinArch"], 1.0, None), (25, 0, by_name["RuinArch"], 1.0, "PostB"),
              (35, 0, by_name["SandBlocks"], 1.0, None), (35, 1, pots[2], 0.8, None),
              (45, 1, gate, 1.0, None),
              (55, -1, pots[0], 0.8, None), (55, 0, by_name["BrokenStones"], 1.0, None),
              (65, 0, by_name["RuinArch"], 1.0, None),
              (75, -1, by_name["FallenColumn"], 1.0, None), (75, 1, by_name["SandBlocks"], 1.0, None))
    for z, lane, meshes, scale, skip in layout:
        location = (lanes[lane], -float(z), 0.0)
        _, copies = instance(meshes, location, scale, skip=skip)
        apply_fog(copies, depth((location[0], location[1], 0.5)))
    instance(wizard, (0, 0, 0), wizard_scale, rot_z=180)
    shoot("oyun_gorunumu", cam_loc, cam_target, fov_y=60)

    # Aynı yol, Captures/info.txt'de ölçülen kamerayla: yatay Game penceresi (1918x827), kamera 2.5 yüksekte, 2.37° eğik.
    setup_render((960, 414), SKY)
    shoot("oyun_gorunumu_yatay", (0, 5.3, 2.5), (0, -19.7, 2.5 - 25.0 * math.tan(math.radians(2.37))), fov_y=60)


def main():
    m.reset_scene()
    for key, rgb in PALETTE.items():
        m.material(key, rgb)
    models = [fallen_column(), broken_stones(), sand_blocks(), ruin_arch()]
    for model in models:
        model.build()
    bpy.context.view_layer.update()
    os.makedirs(OUT_DIR, exist_ok=True)
    for model in models:
        export(model)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
    previews(models)
    log("bitti")


try:
    main()
except Exception:
    log(traceback.format_exc())
