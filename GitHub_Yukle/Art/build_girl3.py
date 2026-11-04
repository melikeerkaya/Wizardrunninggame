"""
Kız büyücü v3 (ayrıntılı, yumuşak gölgeli). Kullanıcının verdiği referansa göre orijinal tasarım:
geniş kenarlı pembe şapka (mor bant, altın üçgen desen ve halkalar, altın ay, serpiştirilmiş yıldızlar,
geriye kıvrılan ucunda turuncu yıldız), hacimli dalgalı kahverengi saç ve kâkül, büyük kahve gözler ve gülen ağız,
altın işlemeli teal tunik, omuz pelerini ve yıldız-ay desenli lacivert pelerin, çapraz çanta, bordo parmaksız eldivenler,
pembe-mor çizgili tayt, kanatlı ve bağcıklı pembe botlar.
Çalıştırma: WIZARD_FBX, WIZARD_BLEND, WIZARD_PREVIEW ortam değişkenleriyle blender -b -P build_girl3.py
Sonuç (üçgen sayısı, boy ya da hata) WIZARD_PREVIEW/girl3_log.txt dosyasına yazılır.

Parçalar renk anahtarına göre birleştirilir: nesne adları "RenkAnahtarı_Grup" (renkleri Unity verir, bkz. ModelPalette.cs).
Kollar "Tunic_SleeveL/R" omuzda, bacaklar "Boot_BootL/R" kalçada döner; aynı gruptaki diğer renkler bunların çocuğudur.
Karakter +Y yönüne bakar, ayak tabanı z=0, şapkanın tepesi ~2.05.
"""
import math
import os
import random
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bmesh
import bpy
from mathutils import Vector

import mesh_kit as k
import modeling as m

FBX_PATH = os.environ["WIZARD_FBX"]
BLEND_PATH = os.environ["WIZARD_BLEND"]
PREVIEW_DIR = os.environ["WIZARD_PREVIEW"]

COLORS = {
    "Hat": (1.0, 0.15, 0.55), "HatBand": (0.55, 0.22, 0.85), "Gold": (1.0, 0.75, 0.0), "StarTip": (1.0, 0.72, 0.3),
    "Skin": (1.0, 0.76, 0.62), "NoseTip": (1.0, 0.62, 0.52), "Hair": (0.55, 0.28, 0.12), "HairLight": (0.85, 0.55, 0.25),
    "Tunic": (0.25, 0.58, 0.75), "Cape": (0.17, 0.22, 0.55), "Strap": (0.6, 0.33, 0.12),
    "Pink": (1.0, 0.35, 0.65), "Cream": (1.0, 0.97, 0.9), "Eye": (0.45, 0.25, 0.1), "Pupil": (0.05, 0.03, 0.03),
    "Shine": (1.0, 1.0, 1.0), "Blush": (1.0, 0.4, 0.5), "Mouth": (0.6, 0.08, 0.15), "Brow": (0.4, 0.2, 0.08),
    "Boot": (1.0, 0.25, 0.6), "BootToe": (0.65, 0.36, 0.15), "StripeA": (1.0, 0.3, 0.7), "StripeB": (0.55, 0.2, 0.8),
    "Wing": (0.85, 0.93, 1.0), "Glove": (0.6, 0.2, 0.32),
}

SIDES = (("L", -1), ("R", 1))
HIP_Z = 0.66
SHOULDER_Z = 1.08
# Baş, saç ve şapka bu kadar aşağıda durur (boyun kısa görünsün diye).
DZ = -0.04


class Builder:
    """Parçaları grup ve renk anahtarına göre tek mesh'te toplar (az nesne = az çizim çağrısı).
    Dönen gruplarda (kol, bacak) pivot rengi grubun ana nesnesi olur, diğer renkler onun çocuğudur."""

    def __init__(self, root):
        self.root = root
        self.groups = {}

    def group(self, name, origin=(0, 0, 0), pivot_key=None, pivot_name=None):
        self.groups[name] = {"origin": Vector(origin), "pivot_key": pivot_key, "pivot_name": pivot_name, "parts": {}}

    def add(self, group, key, bm):
        parts = self.groups[group]["parts"]
        if key in parts:
            k.merge(parts[key], bm)
            bm.free()
        else:
            parts[key] = bm

    def build(self):
        for name, g in self.groups.items():
            origin, pivot = g["origin"], None
            for key in sorted(g["parts"], key=lambda part_key: part_key != g["pivot_key"]):
                bm = g["parts"][key]
                bmesh.ops.translate(bm, vec=-origin, verts=bm.verts)
                bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
                is_pivot = key == g["pivot_key"]
                obj_name = g["pivot_name"] if is_pivot else "%s_%s" % (key, name)
                mesh = bpy.data.meshes.new(obj_name)
                bm.to_mesh(mesh)
                bm.free()
                obj = bpy.data.objects.new(obj_name, mesh)
                bpy.context.collection.objects.link(obj)
                obj.data.materials.append(m.material(key, COLORS[key]))
                if pivot is not None:
                    obj.parent = pivot
                else:
                    obj.parent = self.root
                    obj.location = origin
                if is_pivot:
                    pivot = obj


def surface_normal(fn, u, v, h=0.01):
    du = fn(u + h, v) - fn(u - h, v)
    dv = fn(u, min(v + h, 1.0)) - fn(u, max(v - h, 0.0))
    return du.cross(dv).normalized()


def profile(zs, rs, samples=6):
    """Dik bir borunun yüksekliğe göre yarıçapı (tunik süslerini yüzeye oturtmak için)."""
    zz = [p.x for p in k.spline([(z, 0, 0) for z in zs], samples)]
    rr = k.smooth_values(rs, samples)

    def radius(z):
        z = min(max(z, zz[0]), zz[-1])
        for i in range(len(zz) - 1):
            if z <= zz[i + 1]:
                t = (z - zz[i]) / (zz[i + 1] - zz[i]) if zz[i + 1] > zz[i] else 0.0
                return rr[i] + (rr[i + 1] - rr[i]) * t
        return rr[-1]
    return radius


# ---------- Gövde ölçüleri ----------

TUNIC_Z = (0.70, 0.76, 0.84, 0.90, 0.98, 1.06, 1.13, 1.17)
TUNIC_R = (0.31, 0.255, 0.205, 0.188, 0.19, 0.2, 0.165, 0.10)
TUNIC_SQ = 0.82
tunic_r = profile(TUNIC_Z, TUNIC_R)


def tunic_pt(z, ang, lift=0.006):
    r = tunic_r(z) + lift
    return Vector((r * math.sin(ang), r * TUNIC_SQ * math.cos(ang), z))


# ---------- Baş ----------

HEAD_C = Vector((0.0, 0.0, 1.46 + DZ))
HEAD_R = Vector((0.25, 0.232, 0.235))


def head_pt(lon, lat, off=0.0):
    """Baş yüzeyinde boylam/enlem (derece) ile nokta ve normal. lon 0 = burun, + = karakterin sağı (+X)."""
    lo, la = math.radians(lon), math.radians(lat)
    d = Vector((math.cos(la) * math.sin(lo), math.cos(la) * math.cos(lo), math.sin(la)))
    n = Vector((d.x / HEAD_R.x, d.y / HEAD_R.y, d.z / HEAD_R.z)).normalized()
    p = HEAD_C + Vector((d.x * HEAD_R.x, d.y * HEAD_R.y, d.z * HEAD_R.z))
    return p + n * off, n


# ---------- Saç ----------

HAIR_C = Vector((0.0, -0.06, 1.5 + DZ))
HAIR_R = (0.255, 0.245, 0.24)


def hair_point(z, phi, lift=0.0):
    """Saç kabuğu: tepede başı sarar, aşağıda ense ve omuzlara doğru daralarak iner. phi 0 = ön, + = sağ."""
    if z >= HAIR_C.z:
        s = math.sqrt(max(0.0, 1 - ((z - HAIR_C.z) / HAIR_R[2]) ** 2))
        rx, ry = HAIR_R[0] * s, HAIR_R[1] * s
    else:
        d = min(1.0, (HAIR_C.z - z) / 0.45)
        rx, ry = HAIR_R[0] + 0.025 * d, HAIR_R[1] - 0.12 * d
    rx += 0.018 + lift
    ry += 0.018 + lift
    return Vector((rx * math.sin(phi), HAIR_C.y + ry * math.cos(phi), z))


def hair_mass_fn(u, v):
    """Buklelerin altındaki dolgun saç kütlesi: sağ şakaktan enseyi dolaşıp sol şakağa, alt kenarı dalgalı."""
    phi = math.radians(66 + 228 * u)
    bottom = 1.1 + 0.035 * math.sin(9 * phi) + 0.025 * math.cos(4 * phi + 0.5)
    z = 1.5 + DZ + (bottom - 1.5 - DZ) * v
    return hair_point(z, phi, 0.02 * v)


def lock(phi0, z0, z1, r0, r1, amp, waves, phase, lift=0.0, flare=0.0, curl=0.0, n=9):
    """Yukarıdan dalgalanarak inen, ucu dışa kıvrılan dolgun bukle."""
    pts, rad = [], []
    for i in range(n):
        t = i / (n - 1)
        phi = phi0 + amp * math.sin(2 * math.pi * waves * t + phase) * (0.3 + 0.7 * t)
        bulge = 0.015 * math.cos(2 * math.pi * waves * t + phase)
        tip = max(0.0, (t - 0.7) / 0.3)
        z = z0 + (z1 - z0) * t + curl * 0.6 * tip * tip
        pts.append(hair_point(z, phi, lift + bulge + flare * t * t + curl * tip))
        rad.append(r0 + (r1 - r0) * t ** 1.6)
    return k.tube(pts, rad, segs=6, squash=(1.5, 0.85), samples=2, ref=(math.cos(phi0), -math.sin(phi0), 0))


def bang(sx, lat0, lon1, lat1, r0, phase, n=8):
    """Tepedeki ayrımdan alnın üstünden yana taranan kâkül tutamı (başa yassı yapışır)."""
    pts, rad = [], []
    normal = None
    for i in range(n):
        t = i / (n - 1)
        lon = sx * (4 + (lon1 - 4) * t ** 0.85)
        lat = lat0 + (lat1 - lat0) * t ** 1.15 + 3.0 * math.sin(math.pi * 1.6 * t + phase)
        p, nrm = head_pt(lon, lat, 0.02 + 0.012 * math.sin(math.pi * t))
        normal = normal or nrm
        pts.append(p)
        rad.append(r0 * (1 - 0.6 * t ** 1.3))
    return k.tube(pts, rad, segs=6, squash=(0.55, 1.7), samples=2, ref=normal)


# ---------- Şapka ----------

CROWN_PATH = tuple((x, y, z + DZ) for x, y, z in (
    (0, 0, 1.55), (0, 0, 1.62), (0, -0.012, 1.72), (0, -0.04, 1.82), (0, -0.10, 1.91),
    (0, -0.22, 1.98), (0, -0.38, 2.01), (0, -0.52, 1.98), (0, -0.62, 1.91)))
CROWN_R = (0.315, 0.30, 0.256, 0.205, 0.157, 0.112, 0.078, 0.052, 0.032)
CROWN_PTS = k.spline(CROWN_PATH, 5)
CROWN_RAD = k.smooth_values(CROWN_R, 5)
CROWN_LEN = [0.0]
for _a, _b in zip(CROWN_PTS, CROWN_PTS[1:]):
    CROWN_LEN.append(CROWN_LEN[-1] + (_b - _a).length)


def crown_axis(l):
    """Şapka tepesinin ekseni üzerinde, tabandan l uzaklıktaki nokta, yarıçap ve eksen yönü."""
    l = min(max(l, 0.0), CROWN_LEN[-1])
    i = 0
    while i < len(CROWN_PTS) - 2 and l > CROWN_LEN[i + 1]:
        i += 1
    seg = CROWN_LEN[i + 1] - CROWN_LEN[i]
    t = (l - CROWN_LEN[i]) / seg if seg > 0 else 0.0
    return (CROWN_PTS[i].lerp(CROWN_PTS[i + 1], t), CROWN_RAD[i] + (CROWN_RAD[i + 1] - CROWN_RAD[i]) * t,
            (CROWN_PTS[i + 1] - CROWN_PTS[i]).normalized())


def crown_at(l, ang, lift=0.0):
    """Tepe yüzeyindeki nokta ve dışa bakan yön. ang 0 = ön, + = sağ. Tüpün halkalarıyla aynı eksenleri kullanır,
    böylece süsler eğik tepede de yüzeye tam oturur."""
    p, r, tan = crown_axis(l)
    radial = Vector((math.sin(ang), tan.z * math.cos(ang), -tan.y * math.cos(ang)))
    return p + radial * (r + lift), radial


def brim_fn(u, v):
    """Geniş şapka kenarı: önü hafif kalkık, arkası hafif sarkık, kenarı dalgalı."""
    th = 2 * math.pi * u
    r = 0.30 + 0.31 * v
    dz = v * v * (0.012 + 0.05 * math.cos(th) + 0.012 * math.sin(3 * th + 0.5))
    return Vector((r * math.sin(th), r * math.cos(th), 1.545 + DZ + dz))


# ---------- Pelerin ----------

def cape_fn(u, v):
    """Omuzlardan sırta açılan pelerin: dikey kıvrımlar, etekte beş sivri uç."""
    psi = math.radians(-58 + 116 * u)
    hem = 0.60 + 0.075 * abs(math.sin(4 * math.pi * u))
    z = 1.14 + (hem - 1.14) * v
    radius = 0.19 + 0.235 * v ** 1.15 + 0.02 * v * math.sin(7 * psi + 0.6)
    return Vector((radius * math.sin(psi), -radius * math.cos(psi) * 0.9, z))


def cape_point(u, v):
    p = cape_fn(u, v)
    n = surface_normal(cape_fn, u, v)
    if n.dot(Vector((p.x, p.y, 0.0))) < 0:
        n = -n
    return p, n


def collar_fn(u, v):
    """Boynu saran kısa omuz pelerini; önde broşun durduğu bir açıklık kalır."""
    psi = math.radians(-160 + 320 * u)
    r = 0.125 + 0.095 * v ** 0.9 + 0.006 * v * math.sin(10 * psi)
    return Vector((r * math.sin(psi), -r * math.cos(psi) * 0.92, 1.215 - 0.095 * v))


# ---------- Parçalar ----------

def build_legs(b):
    for s, sx in SIDES:
        g, x0 = "Leg" + s, 0.1 * sx
        # Çizgili tayt
        top, bottom, bands = 0.668, 0.34, 7
        for i in range(bands):
            z0 = top - i * (top - bottom) / bands
            z1 = z0 - (top - bottom) / bands - 0.003
            radius = [0.07 + 0.012 * (z - bottom) / (top - bottom) for z in (z0, z1)]
            b.add(g, "StripeA" if i % 2 == 0 else "StripeB", k.tube([(x0, 0, z0), (x0, 0, z1)], radius, segs=12))
        # Bot: pembe konç ve ayak, kahverengi burun ve taban, krem ağız, bağcıklar
        b.add(g, "Boot", k.tube([(x0, -0.005, 0.36), (x0, -0.005, 0.22), (x0, 0.0, 0.12)], [0.088, 0.086, 0.092],
                                segs=14, squash=(1.0, 1.1)))
        b.add(g, "Boot", k.ellipsoid((x0, 0.07, 0.092), (0.092, 0.165, 0.085), sub=3))
        b.add(g, "BootToe", k.ellipsoid((x0, 0.165, 0.078), (0.096, 0.095, 0.072), sub=3))
        b.add(g, "BootToe", k.rbox((x0, 0.075, 0.022), (0.19, 0.38, 0.05), bevel=0.018))
        b.add(g, "Cream", k.torus((x0, -0.005, 0.355), 0.095, 0.105, 0.022, major=22, minor=6))
        for z in (0.30, 0.245, 0.19):
            for sgn in (-1, 1):
                lace = [(x0 - 0.035 * sgn, 0.098, z + 0.018), (x0 + 0.035 * sgn, 0.1, z - 0.018)]
                b.add(g, "BootToe", k.tube(lace, [0.006, 0.006], segs=5))
        # Bileğin dış yanında üç tüylü küçük kanat
        base = Vector((x0 + 0.094 * sx, -0.01, 0.235))
        for d, ln, wd in (((0.18 * sx, -0.75, 0.55), 0.085, 0.022), ((0.22 * sx, -0.93, 0.28), 0.075, 0.02),
                          ((0.25 * sx, -0.95, -0.02), 0.065, 0.018)):
            d = Vector(d).normalized()
            b.add(g, "Wing", k.ellipsoid(base + d * (ln * 0.9), (wd, ln, 0.008), sub=2, basis=k.frame(d, up=(sx, 0, 0))))


def build_body(b):
    body = "Body"
    b.add(body, "Tunic", k.tube([(0, 0, z) for z in TUNIC_Z], TUNIC_R, segs=24, squash=(1.0, TUNIC_SQ), samples=5, ref=(1, 0, 0)))
    # Etek: dalgalı altın kenar, üstünde ince altın çizgi ve önde altın noktalar
    b.add(body, "Gold", k.torus((0, 0, 0.712), 0.316, 0.316 * TUNIC_SQ, 0.012, major=50, minor=5,
                                wave=lambda th: -0.016 * abs(math.sin(5 * th))))
    r = tunic_r(0.748) + 0.004
    b.add(body, "Gold", k.torus((0, 0, 0.748), r, r * TUNIC_SQ, 0.006, major=50, minor=4,
                                wave=lambda th: 0.007 * math.sin(10 * th)))
    for i in range(15):
        b.add(body, "Gold", k.ellipsoid(tunic_pt(0.78, -1.25 + 2.5 * i / 14, 0.003), (0.009, 0.009, 0.009), sub=1, smooth=False))
    # Kemer ve toka
    r = tunic_r(0.885) + 0.008
    b.add(body, "Strap", k.torus((0, 0, 0.885), r, r * TUNIC_SQ, 0.012, major=40, minor=6, tube_sq=(1.0, 2.3)))
    b.add(body, "Gold", k.rbox(tunic_pt(0.885, 0, 0.022), (0.07, 0.016, 0.06), bevel=0.008))
    b.add(body, "Strap", k.rbox(tunic_pt(0.885, 0, 0.03), (0.036, 0.012, 0.03), bevel=0.004))
    # Göğüste altın işleme: ortada çizgi ve elmas, iki yanda kıvrımlı dallar
    b.add(body, "Gold", k.tube([tunic_pt(z, 0, 0.004) for z in (1.08, 1.0, 0.92)], [0.005] * 3, segs=4))
    b.add(body, "Gold", k.ellipsoid(tunic_pt(0.99, 0, 0.008), (0.018, 0.008, 0.028), sub=1, smooth=False))
    for sx in (-1, 1):
        swirl = [tunic_pt(1.075 - 0.17 * t, sx * (0.1 + 0.3 * math.sin(math.pi * 1.4 * t)), 0.004) for t in (i / 13 for i in range(14))]
        b.add(body, "Gold", k.tube(swirl, [0.005] * 14, segs=4, samples=1))
    # Çapraz çanta: sağ omuzdan sol kalçaya kayış, kapaklı deri çanta
    strap = [tunic_pt(1.11 - 0.27 * t, 0.55 - 2.05 * t, 0.012) for t in (i / 11 for i in range(12))]
    strap.append(Vector((-0.31, -0.04, 0.815)))
    b.add(body, "Strap", k.tube(strap, [0.02] * len(strap), segs=6, squash=(0.45, 1.9), samples=2,
                                ref=(math.sin(0.55), math.cos(0.55), 0)))
    b.add(body, "Gold", k.ellipsoid(tunic_pt(0.98, -0.3, 0.024), (0.016, 0.01, 0.022), sub=2))
    b.add(body, "Strap", k.rbox((-0.335, -0.065, 0.735), (0.1, 0.17, 0.14), bevel=0.02))
    b.add(body, "Strap", k.rbox((-0.338, -0.065, 0.79), (0.108, 0.178, 0.06), bevel=0.014))
    b.add(body, "Gold", k.ellipsoid((-0.392, -0.065, 0.772), (0.008, 0.02, 0.02), sub=2))


def build_arms(b):
    for s, sx in SIDES:
        g = "Sleeve" + s
        # Kabarık kısa kol, altın manşet, ön kol
        b.add(g, "Tunic", k.ellipsoid((0.232 * sx, 0, 1.03), (0.088, 0.085, 0.088), sub=3))
        b.add(g, "Tunic", k.tube([(0.232 * sx, 0, 1.03), (0.245 * sx, 0.005, 0.95)], [0.082, 0.074], segs=14))
        b.add(g, "Gold", k.torus((0.246 * sx, 0.005, 0.948), 0.075, 0.075, 0.011, major=24))
        b.add(g, "Skin", k.tube([(0.246 * sx, 0.005, 0.95), (0.256 * sx, 0.02, 0.86), (0.265 * sx, 0.04, 0.79)],
                                [0.05, 0.044, 0.04], segs=10))
        # Bordo parmaksız eldiven, elin dış yüzünde pembe taş; parmaklar ve başparmak açıkta
        b.add(g, "Glove", k.torus((0.264 * sx, 0.038, 0.80), 0.046, 0.046, 0.014, major=18))
        hand = Vector((0.268 * sx, 0.045, 0.735))
        b.add(g, "Glove", k.ellipsoid(hand, (0.052, 0.046, 0.062), sub=3))
        b.add(g, "Pink", k.ellipsoid(hand + Vector((0.047 * sx, 0, 0.012)), (0.012, 0.02, 0.02), sub=2))
        for dy, ln in ((-0.027, 0.046), (-0.009, 0.056), (0.009, 0.054), (0.027, 0.044)):
            y0 = hand.y + dy
            finger = [(hand.x, y0, 0.695), (hand.x, y0 + 0.006, 0.695 - ln * 0.6), (hand.x, y0 + 0.022, 0.695 - ln)]
            b.add(g, "Skin", k.tube(finger, [0.0125, 0.0115, 0.009], segs=6, samples=2))
        thumb = [(hand.x - 0.02 * sx, 0.085, 0.75), (hand.x - 0.025 * sx, 0.103, 0.72), (hand.x - 0.012 * sx, 0.11, 0.69)]
        b.add(g, "Skin", k.tube(thumb, [0.015, 0.013, 0.01], segs=6, samples=2))


def build_face(b):
    body = "Body"
    b.add(body, "Skin", k.ellipsoid(HEAD_C, HEAD_R, sub=4))
    b.add(body, "Skin", k.tube([(0, 0, 1.08), (0, 0, 1.26)], [0.058, 0.052], segs=12))
    for sx in (-1, 1):
        # Büyük kahverengi göz: koyu kenarlı iris, göz bebeği, iki parıltı, kalkık kirpik çizgisi, kaş, allık
        p, n = head_pt(21 * sx, -6)
        basis = k.frame(n)
        east, north = basis.col[0], basis.col[2]
        b.add(body, "Brow", k.ellipsoid(p - n * 0.002, (0.049, 0.014, 0.059), sub=3, basis=basis))
        b.add(body, "Eye", k.ellipsoid(p, (0.043, 0.016, 0.053), sub=3, basis=basis))
        b.add(body, "Pupil", k.ellipsoid(p + n * 0.008 - north * 0.004, (0.025, 0.012, 0.033), sub=2, basis=basis))
        b.add(body, "Shine", k.ellipsoid(p + n * 0.016 + east * (0.013 * sx) + north * 0.02, (0.012, 0.006, 0.014), sub=2, basis=basis))
        b.add(body, "Shine", k.ellipsoid(p + n * 0.015 - east * (0.014 * sx) - north * 0.02, (0.006, 0.005, 0.007), sub=1, basis=basis))
        lash = [head_pt(sx * (21 + dl), -6 + dt, 0.012)[0] for dl, dt in ((-10.5, 3.5), (-6, 11.5), (0, 14), (6, 12.5), (10.8, 7), (15, 10))]
        b.add(body, "Pupil", k.tube(lash, [0.005, 0.0065, 0.007, 0.0065, 0.005, 0.002], segs=5))
        brow = [head_pt(sx * (21 + dl), -6 + dt, 0.006)[0] for dl, dt in ((-12, 17), (-4, 22), (6, 22.5), (14, 18.5))]
        b.add(body, "Brow", k.tube(brow, [0.008, 0.011, 0.01, 0.005], segs=6))
        p, n = head_pt(47 * sx, -24, -0.002)
        b.add(body, "Blush", k.ellipsoid(p, (0.046, 0.01, 0.032), sub=2, basis=k.frame(n)))
    p, n = head_pt(0, -21, 0.012)
    b.add(body, "NoseTip", k.ellipsoid(p, (0.024, 0.022, 0.02), sub=3, basis=k.frame(n)))

    # Kocaman açık gülümseme: koyu ağız içi, dil ve üst dişler (yüze sarılan ince katmanlar)
    def mouth(x_scale, v0, v1, off):
        def fn(u, v):
            x = (2 * u - 1) * x_scale
            upper, lower = -35 + 5 * x * x, -45 + 15 * x * x
            return head_pt(19 * x, lower + (upper - lower) * (v0 + (v1 - v0) * v), off)[0]
        return fn
    b.add(body, "Mouth", k.surface(mouth(1.0, 0.0, 1.0, 0.002), 16, 5, thickness=0.004))
    b.add(body, "Pink", k.surface(mouth(0.6, 0.05, 0.42, 0.0035), 8, 3, thickness=0.004))
    b.add(body, "Cream", k.surface(mouth(0.8, 0.62, 0.96, 0.0045), 12, 2, thickness=0.004))


def build_hair(b):
    body = "Body"
    rnd = random.Random(11)
    b.add(body, "Hair", k.ellipsoid(HAIR_C, HAIR_R, sub=3))
    b.add(body, "Hair", k.surface(hair_mass_fn, 32, 8, thickness=0.05))
    # Arka: iki kat dolgun dalgalı bukle, uçları dışa kıvrık
    for layer in (0, 1):
        for i in range(11):
            phi = math.radians(112 + i * 136 / 10 + 7 * layer)
            z1 = 1.02 + rnd.uniform(0.0, 0.08) + 0.05 * layer
            key = "HairLight" if (i + 3 * layer) % 4 == 1 else "Hair"
            b.add(body, key, lock(phi, 1.5 + DZ, z1, 0.065 - 0.01 * layer, 0.022, rnd.uniform(0.15, 0.25),
                                  rnd.uniform(1.0, 1.6), rnd.uniform(0, 6.28), lift=0.03 + 0.03 * layer, flare=0.03, curl=0.05))
    # Yanlar: yüzü çerçeveleyip omuza dökülen bukleler
    for sx in (-1, 1):
        for j, (deg, z1) in enumerate(((60, 1.1), (74, 1.05), (88, 1.03))):
            b.add(body, "HairLight" if j == 1 else "Hair",
                  lock(math.radians(deg * sx), 1.5 + DZ, z1, 0.055, 0.02, 0.25, 1.3 + 0.2 * j, 0.8 + j, lift=0.02, flare=0.06, curl=0.06))
    # Altın parlak tutamlar
    for deg in (125, 150, 172, 196, 218, 238):
        b.add(body, "HairLight", lock(math.radians(deg), 1.48 + DZ, 1.1 + rnd.uniform(0, 0.06), 0.024, 0.008, 0.2,
                                      rnd.uniform(1.2, 1.8), rnd.uniform(0, 6.28), lift=0.075, flare=0.03, curl=0.04))
    # Kâkül: ortadan ikiye ayrılıp alnın üstünden yanlara taranır
    for sx in (-1, 1):
        for j, (lat0, lon1, lat1, r0) in enumerate(((62, 64, 12, 0.038), (58, 74, 16, 0.036), (66, 52, 10, 0.034), (55, 82, 22, 0.034))):
            b.add(body, "Hair", bang(sx, lat0, lon1, lat1, r0, 0.6 * j))


def build_hat(b):
    body = "Body"
    rnd = random.Random(5)
    b.add(body, "Hat", k.surface(brim_fn, 48, 6, thickness=0.022, wrap_u=True))
    edge = [brim_fn(i / 72, 1.0) for i in range(72)]
    b.add(body, "Hat", k.loop(edge, [Vector((math.sin(2 * math.pi * i / 72), math.cos(2 * math.pi * i / 72), 0)) for i in range(72)], 0.013))
    b.add(body, "Hat", k.tube(CROWN_PATH, CROWN_R, segs=24, samples=5))
    # Mor bant ve altın halkalar (tepenin ekseniyle aynı eğimde)
    band = [crown_axis(0.035 + 0.12 * i / 4) for i in range(5)]
    b.add(body, "HatBand", k.tube([p for p, r, t in band], [r + 0.012 for p, r, t in band], segs=32, samples=2))
    for l, lift, thick in ((0.038, 0.02, 0.011), (0.152, 0.017, 0.009), (0.31, 0.008, 0.007)):
        pts, nrm = zip(*[crown_at(l, 2 * math.pi * i / 40, lift) for i in range(40)])
        b.add(body, "Gold", k.loop(pts, nrm, thick, minor=5))
    # Bantta altın üçgen deseni (sırayla yukarı ve aşağı bakan üçgenler)
    lc, count = 0.095, 28
    rc = crown_axis(lc)[1] + 0.017
    step = 2 * math.pi / count
    half_w, h = rc * step * 0.9, 0.037
    for i in range(count):
        outline = ((-half_w, -h), (half_w, -h), (0.0, h)) if i % 2 == 0 else ((half_w, h), (-half_w, h), (0.0, -h))
        tri = k.plate(outline, 0.008)
        b.add(body, "Gold", k.wrap(tri, lambda co, a=i * step: crown_at(lc + co.z, a + co.x / rc, 0.017 + co.y)[0]))
    # Önde altın hilal ay
    lm = 0.235
    rm = crown_axis(lm)[1] + 0.012
    b.add(body, "Gold", k.wrap(k.crescent(0.055, 0.038, 0.01, tilt=-35), lambda co: crown_at(lm + co.z, co.x / rm, 0.012 + co.y)[0]))
    # Tepede serpiştirilmiş yıldızlar ve parıltılar
    for i in range(26):
        l, a = rnd.uniform(0.19, 0.46), rnd.uniform(0, 2 * math.pi)
        if abs(math.atan2(math.sin(a), math.cos(a))) < 0.55 and l < 0.3:
            continue
        r = crown_axis(l)[1] + 0.006
        deco, key = (k.star(0.026, 0.012, 0.006), "Gold") if i % 3 == 0 else (k.disc(0.009, 0.005, sides=6), "Cream")
        b.add(body, key, k.wrap(deco, lambda co, l=l, a=a, r=r: crown_at(l + co.z, a + co.x / r, 0.006 + co.y)[0]))
    # Kenarın üstünde parıltı noktaları
    for i in range(44):
        u, v = rnd.random(), rnd.uniform(0.25, 0.92)
        n = surface_normal(brim_fn, u, v)
        if n.z < 0:
            n = -n
        b.add(body, "Cream", k.place(k.disc(0.011, 0.005, sides=6), brim_fn(u, v) + n * 0.012, k.frame(n, up=(0, 1, 0))))
    # Kıvrık ucun sonunda turuncu yıldız (arkadan bakan kameraya döner)
    tip = Vector(CROWN_PATH[-1])
    b.add(body, "StarTip", k.place(k.star(0.085, 0.04, 0.024, bevel=0.007), tip + Vector((0, -0.04, -0.03)), k.frame((0, -1, 0.3))))


def build_cape(b):
    body = "Body"
    rnd = random.Random(9)
    b.add(body, "Cape", k.surface(cape_fn, 36, 18, thickness=0.012))
    b.add(body, "Gold", k.tube([cape_fn(i / 64, 1.0) for i in range(65)], [0.009] * 65, segs=4, samples=1))
    for u in (0.0, 1.0):
        b.add(body, "Gold", k.tube([cape_fn(u, j / 16) for j in range(17)], [0.008] * 17, segs=4, samples=1))
    # Omuz pelerini, altın kenarı ve önde pembe broş
    b.add(body, "Cape", k.surface(collar_fn, 40, 6, thickness=0.016))
    b.add(body, "Gold", k.tube([collar_fn(i / 40, 1.0) for i in range(41)], [0.009] * 41, segs=5, samples=1))
    b.add(body, "Gold", k.ellipsoid((0, 0.152, 1.17), (0.036, 0.014, 0.036), sub=2))
    b.add(body, "Pink", k.ellipsoid((0, 0.162, 1.17), (0.025, 0.014, 0.025), sub=3))
    # Sırtta altın yıldızlar, hilaller ve küçük parıltılar
    for u, v, size in ((0.18, 0.32, 0.045), (0.36, 0.55, 0.035), (0.5, 0.28, 0.05), (0.66, 0.5, 0.04), (0.82, 0.33, 0.045),
                       (0.27, 0.78, 0.04), (0.5, 0.7, 0.03), (0.72, 0.8, 0.045), (0.1, 0.62, 0.03), (0.9, 0.64, 0.03),
                       (0.42, 0.9, 0.025), (0.6, 0.18, 0.025)):
        p, n = cape_point(u, v)
        b.add(body, "Gold", k.place(k.star(size, size * 0.45, 0.008), p + n * 0.009, k.frame(n)))
    for u, v, size in ((0.3, 0.42, 0.05), (0.78, 0.64, 0.045)):
        p, n = cape_point(u, v)
        b.add(body, "Gold", k.place(k.crescent(size, size * 0.6, 0.008, tilt=-40), p + n * 0.009, k.frame(n)))
    for i in range(26):
        p, n = cape_point(rnd.uniform(0.05, 0.95), rnd.uniform(0.15, 0.92))
        b.add(body, "Cream", k.place(k.disc(0.007, 0.004, sides=6), p + n * 0.0075, k.frame(n)))


def main():
    m.reset_scene()
    for key, rgb in COLORS.items():
        m.material(key, rgb)
    root = m.make_root("GirlRoot")

    b = Builder(root)
    b.group("Body")
    for s, sx in SIDES:
        b.group("Leg" + s, (0.1 * sx, 0, HIP_Z), "Boot", "Boot_Boot" + s)
        b.group("Sleeve" + s, (0.215 * sx, 0, SHOULDER_Z), "Tunic", "Tunic_Sleeve" + s)

    build_legs(b)
    build_body(b)
    build_arms(b)
    build_face(b)
    build_hair(b)
    build_hat(b)
    build_cape(b)
    b.build()

    bpy.context.view_layer.update()
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    by_key = {}
    for o in meshes:
        key = o.name.split("_")[0]
        by_key[key] = by_key.get(key, 0) + sum(len(p.vertices) - 2 for p in o.data.polygons)
    zs = [(o.matrix_world @ v.co).z for o in meshes for v in o.data.vertices]
    stats = "OK objects=%d tris=%d zmin=%.3f zmax=%.3f\n%s" % (
        len(meshes), sum(by_key.values()), min(zs), max(zs),
        ", ".join("%s=%d" % kv for kv in sorted(by_key.items(), key=lambda kv: -kv[1])))

    m.render_views("girl3", PREVIEW_DIR, [
        ("front", (2.2, 4.4, 1.9)),
        ("side", (5.2, 0.0, 1.3)),
        ("back", (-2.2, -4.4, 1.9)),
        ("game", (0.0, -6.2, 3.0)),
    ], target=(0, -0.02, 1.05), size=(520, 760), background=(0.9, 0.88, 0.94), lens=55, gain=1.25)
    m.render_views("girl3face", PREVIEW_DIR, [
        ("front", (0.6, 2.4, 1.45)),
        ("three", (1.8, 1.7, 1.5)),
        ("back", (-1.2, -2.4, 1.95)),
    ], target=(0, 0, 1.5), size=(560, 560), background=(0.9, 0.88, 0.94), lens=65, gain=1.25)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.data.objects:
        if obj.type in {"MESH", "EMPTY"}:
            obj.select_set(True)

    os.makedirs(os.path.dirname(FBX_PATH), exist_ok=True)
    bpy.ops.export_scene.fbx(
        filepath=FBX_PATH, use_selection=True, object_types={"MESH", "EMPTY"},
        apply_unit_scale=True, bake_space_transform=True, axis_forward="-Z", axis_up="Y",
        mesh_smooth_type="FACE", add_leaf_bones=False,
    )
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
    return stats


try:
    result = main()
except Exception:
    result = "ERROR\n" + traceback.format_exc()
with open(os.path.join(PREVIEW_DIR, "girl3_log.txt"), "w", encoding="utf-8") as log:
    log.write(result)
