"""
Eski çöl çömlekleri (Çöl Diyarı alçak engeli). Dört çeşit çömlek, her biri ayrı bir FBX olarak dışa aktarılır:
  PotAmphora  - iki kulplu, dar boyunlu, koyu bantlı ve noktalı kil amfora
  PotWide     - basık, geniş ağızlı, baklava desenli toprak küp
  PotGold     - altın ağızlı, turkuaz bantlı mürdüm küp
  PotZigzag   - ince boyunlu, krem zikzak desenli turuncu vazo
Her FBX bir şeridi kaplayan küçük bir gruptur: ortada büyük çömlek (~1 birim), iki yanında aynı türden küçükleri.
Grup 2 birim genişliğe göre yapılmıştır (x = -1..1). Z yukarı, koşu yönü +Y, zemin z=0. Üzerinden zıplanır.
Çalıştırma: POT_DIR (FBX klasörü), POT_BLEND, POT_PREVIEW ortam değişkenleriyle blender -b -P build_pots.py
Nesne adları "RenkAnahtarı_Parça" biçimindedir (renkleri Unity kodla verir, bkz. ModelPalette.cs).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bmesh
import bpy
from mathutils import Matrix, Vector

import modeling as m

POT_DIR = os.environ["POT_DIR"]
BLEND_PATH = os.environ["POT_BLEND"]
PREVIEW_DIR = os.environ["POT_PREVIEW"]

SEGS = 28

m.reset_scene()

for key, rgb in {
    "Clay": (0.86, 0.46, 0.32), "ClayDark": (0.22, 0.13, 0.1),
    "Earth": (0.62, 0.5, 0.34), "EarthDark": (0.4, 0.3, 0.2),
    "Plum": (0.5, 0.36, 0.42), "Turquoise": (0.2, 0.75, 0.8), "Gold": (1.0, 0.75, 0.0),
    "PotOrange": (0.95, 0.58, 0.25), "Cream": (1.0, 0.97, 0.9), "Sand": (0.95, 0.82, 0.58),
}.items():
    m.material(key, rgb)


# ---------- Mesh yardımcıları ----------

def revolve(profile, segs=SEGS):
    """(r, z) noktalarını dik eksen etrafında döndürür. r=0 olan uçlar tek noktaya kapanır."""
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        if r < 1e-6:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * k / segs), r * math.sin(2 * math.pi * k / segs), z))
                          for k in range(segs)])
    for a, b in zip(rings, rings[1:]):
        for k in range(segs):
            j = (k + 1) % segs
            if len(a) == 1:
                bm.faces.new((a[0], b[k], b[j]))
            elif len(b) == 1:
                bm.faces.new((a[k], b[0], a[j]))
            else:
                bm.faces.new((a[k], b[k], b[j], a[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def pot_body(outer, lip=0.025, depth=0.14):
    """Dış profilin üstüne kalın bir ağız ve içe doğru kısa bir iç duvar ekler (ağız boş görünür)."""
    r_top, z_top = outer[-1]
    inner = [(r_top - lip, z_top), (r_top - lip - 0.01, z_top - depth), (0.0, z_top - depth)]
    return revolve([(0.0, outer[0][1])] + outer + inner)


def radius_at(outer, z):
    for (r0, z0), (r1, z1) in zip(outer, outer[1:]):
        if z0 <= z <= z1 and z1 > z0:
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    return outer[-1][0]


def band(outer, z0, z1, push=0.008, steps=4):
    """Gövdenin üzerine boyanmış gibi duran bant (gövdeyi izleyen ince kabuk)."""
    zs = [z0 + (z1 - z0) * i / steps for i in range(steps + 1)]
    out = [(radius_at(outer, z) + push, z) for z in zs]
    inn = [(radius_at(outer, z) - 0.01, z) for z in reversed(zs)]
    return revolve(out + inn + [out[0]])


def bar(bm, a, b, width, depth):
    """a'dan b'ye uzanan, gövde yüzeyine yatık ince çubuk (zikzak çizgileri için)."""
    a, b = Vector(a), Vector(b)
    mid = (a + b) / 2
    t = (b - a)
    length = t.length
    t.normalize()
    out = Vector((mid.x, mid.y, 0)).normalized()
    s = out.cross(t).normalized()
    out = t.cross(s).normalized()
    verts = []
    for dt in (-0.5, 0.5):
        for ds in (-0.5, 0.5):
            for do in (-0.5, 0.5):
                verts.append(bm.verts.new(mid + t * dt * (length + width) + s * ds * width + out * do * depth))
    idx = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    for f in idx:
        bm.faces.new([verts[i] for i in f])


def handle_tube(points, radius, segs=8):
    """XZ düzleminde kıvrılan yuvarlak kulp. Halkalar hep Y eksenine göre kurulur (kıvrılma olmaz)."""
    bm = bmesh.new()
    rings = []
    y = Vector((0, 1, 0))
    for i, p in enumerate(points):
        p = Vector(p)
        d = (Vector(points[i + 1]) - p) if i < len(points) - 1 else (p - Vector(points[i - 1]))
        d.normalize()
        a = d.cross(y).normalized()
        rings.append([bm.verts.new(p + a * math.cos(2 * math.pi * k / segs) * radius
                                   + y * math.sin(2 * math.pi * k / segs) * radius) for k in range(segs)])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(segs):
            j = (k + 1) % segs
            bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    return bm


# ---------- Çömlek türleri (yerel koordinatta, büyük boy) ----------

def amphora():
    outer = [(0.15, 0.0), (0.17, 0.04), (0.29, 0.2), (0.38, 0.4), (0.37, 0.56), (0.28, 0.68),
             (0.15, 0.77), (0.12, 0.85), (0.14, 0.92), (0.16, 0.95)]
    parts = [("Clay_Body", pot_body(outer, 0.03, 0.16), "Clay"),
             ("ClayDark_BandLow", band(outer, 0.08, 0.12), "ClayDark"),
             ("ClayDark_BandMid", band(outer, 0.3, 0.34), "ClayDark"),
             ("ClayDark_BandHigh", band(outer, 0.54, 0.58), "ClayDark"),
             ("ClayDark_Neck", band(outer, 0.86, 0.89), "ClayDark")]
    # Gövdenin en geniş yerinde bir sıra koyu nokta
    dots = bmesh.new()
    for k in range(12):
        ang = 2 * math.pi * (k + 0.5) / 12
        r = radius_at(outer, 0.44) + 0.004
        m.add_sphere(dots, 0.032, (1, 1, 1), 1, (r * math.cos(ang), r * math.sin(ang), 0.44))
    parts.append(("ClayDark_Dots", dots, "ClayDark"))
    # İki yanda kulplar: boyundan çıkıp omuza iner
    for side, sign in (("L", -1), ("R", 1)):
        pts = []
        for i in range(9):
            t = i / 8
            ang = math.pi * t
            x = 0.13 + 0.17 * math.sin(ang) + 0.06 * t
            z = 0.86 - 0.24 * t + 0.07 * math.sin(ang)
            pts.append((sign * x, 0, z))
        parts.append(("Clay_Handle" + side, handle_tube(pts, 0.03), "Clay"))
    return parts


def wide_pot():
    outer = [(0.22, 0.0), (0.26, 0.05), (0.42, 0.22), (0.46, 0.34), (0.42, 0.46), (0.32, 0.57),
             (0.28, 0.63), (0.31, 0.68), (0.33, 0.72)]
    parts = [("Earth_Body", pot_body(outer, 0.03, 0.12), "Earth"),
             ("EarthDark_BandLow", band(outer, 0.2, 0.235), "EarthDark"),
             ("EarthDark_BandHigh", band(outer, 0.47, 0.5), "EarthDark"),
             ("EarthDark_Rim", band(outer, 0.66, 0.7), "EarthDark")]
    # Gövdenin ortasında bir sıra baklava (eşkenar dörtgen) desen
    diamonds = bmesh.new()
    count = 14
    for k in range(count):
        ang = 2 * math.pi * k / count
        c, s = math.cos(ang), math.sin(ang)
        zc, h, w = 0.345, 0.075, 0.07
        pts = [(zc + h, 0.0), (zc, w), (zc - h, 0.0), (zc, -w)]
        for (z0, o0), (z1, o1) in zip(pts, pts[1:] + pts[:1]):
            r0 = radius_at(outer, z0) + 0.006
            r1 = radius_at(outer, z1) + 0.006
            a = (r0 * c - o0 * s, r0 * s + o0 * c, z0)
            b = (r1 * c - o1 * s, r1 * s + o1 * c, z1)
            bar(diamonds, a, b, 0.018, 0.012)
    parts.append(("EarthDark_Diamonds", diamonds, "EarthDark"))
    return parts


def gold_pot():
    outer = [(0.24, 0.0), (0.27, 0.04), (0.38, 0.18), (0.43, 0.38), (0.4, 0.56), (0.31, 0.7), (0.29, 0.76)]
    parts = [("Plum_Body", pot_body(outer, 0.03, 0.12), "Plum"),
             ("Turquoise_Band", band(outer, 0.6, 0.68, 0.012), "Turquoise"),
             ("Gold_BandEdge", band(outer, 0.585, 0.605, 0.016), "Gold"),
             ("Gold_BandEdgeTop", band(outer, 0.68, 0.7, 0.016), "Gold"),
             ("Gold_Foot", band(outer, 0.0, 0.05, 0.012), "Gold")]
    # Kalın, dışa taşan altın ağız
    parts.append(("Gold_Rim", revolve([(0.26, 0.74), (0.34, 0.75), (0.355, 0.8), (0.33, 0.84),
                                       (0.26, 0.835), (0.25, 0.79), (0.26, 0.74)]), "Gold"))
    # Turkuaz bandın üzerinde küçük altın taşlar
    studs = bmesh.new()
    for k in range(10):
        ang = 2 * math.pi * k / 10
        r = radius_at(outer, 0.64) + 0.014
        m.add_sphere(studs, 0.022, (1, 1, 1), 1, (r * math.cos(ang), r * math.sin(ang), 0.64))
    parts.append(("Gold_Studs", studs, "Gold"))
    return parts


def zigzag_vase():
    outer = [(0.15, 0.0), (0.17, 0.05), (0.29, 0.28), (0.35, 0.48), (0.31, 0.64), (0.2, 0.76),
             (0.14, 0.85), (0.18, 0.93), (0.2, 0.96)]
    parts = [("PotOrange_Body", pot_body(outer, 0.03, 0.15), "PotOrange"),
             ("ClayDark_BandLow", band(outer, 0.36, 0.39), "ClayDark"),
             ("ClayDark_BandHigh", band(outer, 0.62, 0.65), "ClayDark"),
             ("Cream_Neck", band(outer, 0.86, 0.9), "Cream"),
             ("ClayDark_Foot", band(outer, 0.03, 0.07), "ClayDark")]
    # İki bant arasında krem zikzak
    zig = bmesh.new()
    count = 16
    for k in range(count):
        a0 = 2 * math.pi * k / count
        a1 = 2 * math.pi * (k + 1) / count
        z0 = 0.44 if k % 2 == 0 else 0.57
        z1 = 0.57 if k % 2 == 0 else 0.44
        r0 = radius_at(outer, z0) + 0.008
        r1 = radius_at(outer, z1) + 0.008
        bar(zig, (r0 * math.cos(a0), r0 * math.sin(a0), z0), (r1 * math.cos(a1), r1 * math.sin(a1), z1), 0.028, 0.012)
    parts.append(("Cream_Zigzag", zig, "Cream"))
    return parts


# ---------- Gruplar ----------

# (tür, x, y, ölçek, dönüş). Ortadaki büyük, yanlardakiler küçük.
LAYOUT = [(0.0, 0.0, 1.0, 0), (-0.68, 0.18, 0.62, 40), (0.7, -0.15, 0.7, -25)]

KINDS = [("PotAmphora", amphora), ("PotWide", wide_pot), ("PotGold", gold_pot), ("PotZigzag", zigzag_vase)]

roots = []
for name, build in KINDS:
    root = m.make_root(name + "Root")
    for slot, (x, y, scale, rot) in enumerate(LAYOUT):
        for part_name, bm, key in build():
            bmesh.ops.scale(bm, vec=Vector((scale, scale, scale)), verts=bm.verts)
            bmesh.ops.rotate(bm, cent=Vector((0, 0, 0)), matrix=Matrix.Rotation(math.radians(rot), 3, "Z"), verts=bm.verts)
            bmesh.ops.translate(bm, vec=Vector((x, y, 0)), verts=bm.verts)
            obj = m.finish("%s_%s%d" % (part_name, name, slot), bm, key, (0, 0, 0), root)
            for poly in obj.data.polygons:
                poly.use_smooth = True
    roots.append((name, root))

# Önizleme: dört grubu yan yana diz, sonra yerlerine geri al
for i, (_, root) in enumerate(roots):
    root.location = (0, i * 1.6 - 2.4, 0)
ground = bmesh.new()
bmesh.ops.create_grid(ground, x_segments=1, y_segments=1, size=4.0)
ground_mesh = bpy.data.meshes.new("PreviewGround")
ground.to_mesh(ground_mesh)
ground.free()
ground_obj = bpy.data.objects.new("PreviewGround", ground_mesh)
ground_obj.data.materials.append(m.material("Sand", (0.95, 0.82, 0.58)))
bpy.context.collection.objects.link(ground_obj)
m.render_views("pots", PREVIEW_DIR, [
    ("front", (-7.0, 0.0, 2.4)),
    ("close", (-3.2, -4.2, 1.6)),
], target=(0, 0, 0.45), size=(800, 600), background=(0.96, 0.86, 0.66), lens=45, gain=1.15)

for _, root in roots:
    root.location = (0, 0, 0)

os.makedirs(POT_DIR, exist_ok=True)
for name, root in roots:
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    for child in root.children:
        child.select_set(True)
    bpy.ops.export_scene.fbx(
        filepath=os.path.join(POT_DIR, name + ".fbx"), use_selection=True, object_types={"MESH", "EMPTY"},
        apply_unit_scale=True, bake_space_transform=True, axis_forward="-Z", axis_up="Y",
        mesh_smooth_type="FACE", add_leaf_bones=False,
    )
bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
