"""
Kız büyücü v4: kullanıcının Tripo videosundaki karaktere olabildiğince benzetilmiş sürüm.
Arkaya yatık, geniş ve sarkık kenarlı gül kurusu şapka (koyu bant, altın şerit süsleri, geriye kıvrılan uç),
hacimli dalgalı mercan rengi saç ve kâkül, iri kahve gözler, önü krem arkası pembe, önü açık uzun ceket
(gül rengi şeritler, çan manşetler, yıldızlar), koyu üst ve şort, kemer, çapraz kayış ve keseler,
jartiyerli koyu çoraplar, iri burunlu bordo botlar, parmaksız eldivenler.
Çalıştırma: WIZARD_FBX, WIZARD_BLEND, WIZARD_PREVIEW ortam değişkenleriyle blender -b -P build_girl4.py
Sonuç (üçgen sayısı, boy ya da hata) WIZARD_PREVIEW/girl4_log.txt dosyasına yazılır.

Parçalar renk anahtarına göre birleştirilir: nesne adları "RenkAnahtarı_Grup" (renkleri Unity verir, bkz. ModelPalette.cs).
Kollar "Coat_SleeveL/R" omuzda, bacaklar "Boot_BootL/R" kalçada döner. Ceketin arka eteği "CoatBack_SkirtBack"
belde döner: oyun bacak geriye gidince eteği de savurur, böylece bacak ceketin içinden çıkmaz.
Karakter +Y yönüne bakar, ayak tabanı z=0, şapkanın tepesi ~2.1.
"""
import math
import os
import random
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bmesh
import bpy
from mathutils import Matrix, Vector

import mesh_kit as k
import modeling as m

FBX_PATH = os.environ["WIZARD_FBX"]
BLEND_PATH = os.environ["WIZARD_BLEND"]
PREVIEW_DIR = os.environ["WIZARD_PREVIEW"]

COLORS = {
    "Skin": (1.0, 0.75, 0.62), "Blush": (0.96, 0.52, 0.5), "Lip": (0.86, 0.42, 0.42), "Mouth": (0.55, 0.18, 0.2),
    "Sclera": (0.98, 0.96, 0.94), "Iris": (0.52, 0.25, 0.17), "Pupil": (0.16, 0.07, 0.06), "Shine": (1.0, 1.0, 1.0),
    "Lash": (0.2, 0.09, 0.08), "Brow": (0.38, 0.17, 0.14),
    "Hair": (0.8, 0.4, 0.42), "HairLight": (0.92, 0.55, 0.53), "HairDark": (0.6, 0.27, 0.32),
    "Hat": (0.86, 0.42, 0.53), "HatDark": (0.74, 0.33, 0.46), "HatBand": (0.33, 0.21, 0.27), "HatGem": (0.9, 0.42, 0.3),
    "Brass": (0.95, 0.67, 0.33),
    "Coat": (0.98, 0.9, 0.86), "CoatBack": (0.93, 0.52, 0.62), "CoatTrim": (0.78, 0.33, 0.44),
    "Top": (0.3, 0.24, 0.31), "Shorts": (0.34, 0.27, 0.33), "Stocking": (0.27, 0.21, 0.24), "Leather": (0.45, 0.27, 0.22),
    "Boot": (0.45, 0.24, 0.27), "BootCuff": (0.76, 0.5, 0.46), "Sole": (0.9, 0.8, 0.7), "Glove": (0.4, 0.24, 0.23),
}

SIDES = (("L", -1), ("R", 1))
HIP_Z = 0.88
# Arka etek bu çizgide döner (sırttaki düğmeli kemerin hemen üstü).
SKIRT_Y, SKIRT_Z = -0.04, 0.985


class Builder:
    """Parçaları grup ve renk anahtarına göre tek mesh'te toplar (az nesne = az çizim çağrısı).
    Dönen gruplarda (kol, bacak, etek) pivot rengi grubun ana nesnesi olur, diğer renkler onun çocuğudur."""

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


# ---------- Yardımcılar ----------

def smoothstep(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def curve(zs, values, samples=6):
    """Yüksekliğe göre yumuşak değişen değer (gövde ve ceket kesitleri için)."""
    pts = k.spline([(z, v, 0.0) for z, v in zip(zs, values)], samples)
    if pts[0].x > pts[-1].x:
        pts.reverse()

    def at(z):
        if z <= pts[0].x:
            return pts[0].y
        for i in range(len(pts) - 1):
            if z <= pts[i + 1].x:
                span = pts[i + 1].x - pts[i].x
                t = (z - pts[i].x) / span if span > 1e-9 else 0.0
                return pts[i].y + (pts[i + 1].y - pts[i].y) * t
        return pts[-1].y
    return at


def surface_normal(fn, u, v, h=0.01):
    du = fn(u + h, v) - fn(u - h, v)
    dv = fn(u, min(v + h, 1.0)) - fn(u, max(v - h, 0.0))
    return du.cross(dv).normalized()


def rings_mesh(rings, smooth=True):
    """Aynı sayıda noktalı halkaları sırayla bağlayıp iki ucu kapatır (gövde, şort)."""
    bm = bmesh.new()
    verts = [[bm.verts.new(p) for p in ring] for ring in rings]
    count = len(rings[0])
    for a, b in zip(verts, verts[1:]):
        for i in range(count):
            j = (i + 1) % count
            bm.faces.new((a[i], a[j], b[j], b[i])).smooth = smooth
    bm.faces.new(list(reversed(verts[0])))
    bm.faces.new(verts[-1])
    return bm


def closed_surface(fn, nu, nv, smooth=True):
    """fn(u, v): u 0..1 çevre (kapalı), v 0..1 alt kutuptan üst kutba. Tek katlı kapalı yüzey (baş)."""
    bm = bmesh.new()
    bottom = bm.verts.new(fn(0.0, 0.0))
    top = bm.verts.new(fn(0.0, 1.0))
    rings = [[bm.verts.new(fn(i / nu, j / nv)) for i in range(nu)] for j in range(1, nv)]
    for a, b in zip(rings, rings[1:]):
        for i in range(nu):
            i2 = (i + 1) % nu
            bm.faces.new((a[i], a[i2], b[i2], b[i])).smooth = smooth
    for i in range(nu):
        i2 = (i + 1) % nu
        bm.faces.new((bottom, rings[0][i2], rings[0][i])).smooth = smooth
        bm.faces.new((top, rings[-1][i], rings[-1][i2])).smooth = smooth
    return bm


def ellipse_pt(phi, z, a, b, cy):
    ph = math.radians(phi)
    return Vector((a * math.sin(ph), cy + b * math.cos(ph), z))


# ---------- Baş ----------

HEAD_C = Vector((0.0, 0.012, 1.60))
HEAD_R = (0.152, 0.158, 0.19)


def head_pos(lon, lat):
    """Baş yüzeyi (derece). lon 0 = burun, + = karakterin sağı (+X). Alt yarıda çene daralır ve hafif öne çıkar,
    yanaklar dolgundur."""
    lo, la = math.radians(lon), math.radians(lat)
    d = Vector((math.cos(la) * math.sin(lo), math.cos(la) * math.cos(lo), math.sin(la)))
    rx, ry, rz = HEAD_R
    jaw = smoothstep(0.2, 1.0, -d.z)
    front = max(0.0, d.y)
    rx *= 1 - 0.26 * jaw
    ry *= 1 - 0.22 * jaw * (1 - front)
    p = Vector((d.x * rx, d.y * ry, d.z * rz))
    p.y += 0.022 * jaw * front * front
    p.z -= 0.012 * jaw * front
    cheek = math.exp(-((lat + 22) / 16) ** 2) * math.exp(-((abs(lon) - 48) / 22) ** 2)
    return HEAD_C + p + d * (0.016 * cheek)


def head_pt(lon, lat, off=0.0):
    """Baş yüzeyindeki nokta (yüzeyden off kadar dışarıda) ve dışa bakan normal."""
    p = head_pos(lon, lat)
    du = head_pos(lon + 0.5, lat) - head_pos(lon - 0.5, lat)
    dv = head_pos(lon, min(lat + 0.5, 89.9)) - head_pos(lon, max(lat - 0.5, -89.9))
    n = du.cross(dv).normalized()
    if n.dot(p - HEAD_C) < 0:
        n = -n
    return p + n * off, n


def on_face(bm, lon0, lat0, off=0.0, sx=1):
    """Yerel koordinatlarda (x: şakağa doğru, y: yüzeyden dışa, z: yukarı) kurulan parçayı başın yüzeyine sarar."""
    rx, rz = HEAD_R[0], HEAD_R[2]

    def fn(co):
        lat = lat0 + math.degrees(co.z / rz)
        lon = lon0 + sx * math.degrees(co.x / (rx * max(0.3, math.cos(math.radians(lat)))))
        return head_pt(lon, lat, off + co.y)[0]
    return k.wrap(bm, fn)


# ---------- Saç ----------

HAIR_C = Vector((0.0, -0.022, 1.625))
HAIR_R = (0.168, 0.168, 0.2)


def hair_point(z, phi, lift=0.0):
    """Saç kabuğu: tepede başı sarar, aşağıda omuzlara doğru genişleyip kabarık iner. phi 0 = ön, + = sağ."""
    if z >= HAIR_C.z:
        s = math.sqrt(max(0.0, 1 - ((z - HAIR_C.z) / HAIR_R[2]) ** 2))
        rx, ry = HAIR_R[0] * s, HAIR_R[1] * s
    else:
        d = min(1.0, (HAIR_C.z - z) / 0.42)
        rx = HAIR_R[0] + 0.065 * d ** 0.9
        ry = HAIR_R[1] + 0.085 * d - 0.07 * d * d
    rx += 0.012 + lift
    ry += 0.012 + lift
    return Vector((rx * math.sin(phi), HAIR_C.y + ry * math.cos(phi), z))


def hair_mass_fn(u, v):
    """Buklelerin altındaki dolgun saç kütlesi: sağ yanaktan enseyi dolaşıp sol yanağa, alt kenarı dalgalı.
    Arkada sırtın ortasına, yanlarda omuz hizasına iner."""
    phi = math.radians(74 + 212 * u)
    back = -math.cos(phi)
    bottom = 1.165 - 0.06 * back + 0.03 * math.sin(9 * phi) + 0.015 * math.cos(5 * phi + 0.5)
    top = HAIR_C.z + 0.02
    return hair_point(top + (bottom - top) * v, phi, 0.025 * v)


def lock(phi0, z0, z1, r0, r1, amp, waves, phase, lift=0.0, flare=0.0, curl=0.0, n=10):
    """Yukarıdan dalgalanarak inen, ucu dışa kıvrılan dolgun bukle. Üst ucu saç kabuğuna gömülü başlar,
    böylece kesik ucu görünmez ve şapka kenarının altında kalır."""
    pts, rad = [], []
    for i in range(n):
        t = i / (n - 1)
        rise = smoothstep(0.0, 0.35, t)
        phi = phi0 + amp * math.sin(2 * math.pi * waves * t + phase) * (0.3 + 0.7 * t)
        bulge = 0.018 * math.cos(2 * math.pi * waves * t + phase)
        tip = max(0.0, (t - 0.7) / 0.3)
        z = z0 + (z1 - z0) * t + curl * 0.6 * tip * tip
        pts.append(hair_point(z, phi, rise * (lift + bulge) + flare * t * t + curl * tip))
        rad.append(r0 + (r1 - r0) * t ** 1.6)
    return k.tube(pts, rad, segs=6, squash=(1.5, 0.85), samples=2, ref=(math.cos(phi0), -math.sin(phi0), 0))


def bang(lon0, lat0, lon1, lat1, r0, phase, n=9):
    """Tepedeki ayrımdan alnın üstünden yana taranan kâkül tutamı (başa yassı yapışır)."""
    pts, rad = [], []
    normal = None
    for i in range(n):
        t = i / (n - 1)
        lon = lon0 + (lon1 - lon0) * t ** 0.8
        lat = lat0 + (lat1 - lat0) * t ** 1.2 + 2.5 * math.sin(math.pi * 1.6 * t + phase)
        p, nrm = head_pt(lon, lat, 0.024 + 0.014 * math.sin(math.pi * t))
        if normal is None:
            normal = nrm
        pts.append(p)
        rad.append(r0 * 1.15 * (1 - 0.6 * t ** 1.3))
    return k.tube(pts, rad, segs=6, squash=(0.7, 1.6), samples=2, ref=normal)


# Kâkül: (başlangıç boylam/enlem, bitiş boylam/enlem, kalınlık, dalga evresi). Ayrım hafif sol yanda.
BANGS = (
    (-4, 64, 30, 16, 0.036, 0.0), (-2, 62, 48, 8, 0.036, 0.8), (0, 60, 64, 2, 0.032, 1.6), (2, 64, 16, 24, 0.028, 2.2),
    (-8, 64, -28, 18, 0.034, 0.4), (-8, 62, -46, 9, 0.034, 1.2), (-6, 60, -62, 3, 0.03, 2.0), (-5, 62, -12, 26, 0.022, 2.8),
)


# ---------- Şapka ----------

# Tepenin oturduğu halka arkaya 23 derece yatıktır; kenar önde yüksek, yanlarda kaş hizasında, arkada ense hizasındadır.
RING_C = Vector((0.0, -0.025, 1.77))
RING_TILT = math.radians(23)
RING_R = 0.165

CROWN_PATH = ((0, -0.025, 1.765), (0, -0.064, 1.857), (0, -0.1, 1.95), (0, -0.14, 2.03), (0, -0.19, 2.08),
              (0, -0.25, 2.103), (0, -0.32, 2.09), (0, -0.375, 2.05), (0, -0.41, 1.995), (0, -0.425, 1.955))
CROWN_R = (0.172, 0.142, 0.108, 0.08, 0.058, 0.045, 0.036, 0.028, 0.019, 0.008)
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
    """Geniş, sarkık şapka kenarı: iç kenar eğik halkadır, dış kenar önde kalkık, arkada aşağı sarkık ve hafif dalgalı."""
    th = 2 * math.pi * u
    ix = RING_R * math.sin(th)
    iy = RING_C.y + RING_R * math.cos(RING_TILT) * math.cos(th)
    iz = RING_C.z + RING_R * math.sin(RING_TILT) * math.cos(th)
    reach = 0.378 + 0.033 * math.cos(th) - 0.012 * math.cos(2 * th)
    ez = 1.625 + 0.17 * math.cos(th) - 0.025 * math.cos(2 * th) + 0.012 * math.sin(3 * th + 0.7)
    ex, ey = reach * math.sin(th), RING_C.y + reach * math.cos(th)
    return Vector((ix + (ex - ix) * v, iy + (ey - iy) * v, iz + (ez - iz) * v ** 1.35))


# ---------- Gövde ve ceket ölçüleri ----------

TOP_Z = (1.34, 1.30, 1.26, 1.20, 1.14, 1.08, 1.045)
top_a = curve(TOP_Z, (0.128, 0.142, 0.145, 0.135, 0.122, 0.12, 0.122))
top_b = curve(TOP_Z, (0.08, 0.098, 0.106, 0.096, 0.084, 0.082, 0.083))
top_cy = curve(TOP_Z, (0.018, 0.03, 0.04, 0.042, 0.036, 0.03, 0.03))


def top_pt(phi, z, lift=0.0):
    return ellipse_pt(phi, z, top_a(z) + lift, top_b(z) + lift, top_cy(z))


COAT_Z = (1.355, 1.32, 1.27, 1.18, 1.10, 1.04, 0.98, 0.85, 0.70, 0.55, 0.40)
coat_a = curve(COAT_Z, (0.105, 0.178, 0.192, 0.18, 0.176, 0.188, 0.2, 0.235, 0.278, 0.315, 0.345))
coat_b = curve(COAT_Z, (0.082, 0.108, 0.13, 0.122, 0.125, 0.126, 0.126, 0.14, 0.163, 0.183, 0.2))
coat_cy = curve(COAT_Z, (0.002, 0.022, 0.045, 0.05, 0.042, 0.04, 0.038, 0.032, 0.02, 0.005, -0.01))
# Ceketin önü açıktır: ön kenarın açısı (derece, 0 = tam ön).
coat_open = curve(COAT_Z, (42, 38, 38, 44, 50, 52, 50, 46, 41, 38, 36))
COAT_TOP, COAT_HEM = COAT_Z[0], COAT_Z[-1]


def coat_pt(phi, z, lift=0.0):
    """Ceket yüzeyi. phi 0 = ön, + = sağ (derece). Etekte hafif dikey kıvrımlar vardır."""
    fold = 0.006 * smoothstep(1.0, 0.5, z) * math.sin(math.radians(6 * phi))
    return ellipse_pt(phi, z, coat_a(z) + lift + fold, coat_b(z) + lift + fold, coat_cy(z))


def coat_surface_pt(phi, z, off=0.0):
    p = coat_pt(phi, z)
    n = (coat_pt(phi + 0.5, z) - coat_pt(phi - 0.5, z)).cross(coat_pt(phi, z + 0.005) - coat_pt(phi, z - 0.005)).normalized()
    if n.dot(p - Vector((0.0, coat_cy(z), z))) < 0:
        n = -n
    return p + n * off, n


# ---------- Kollar ----------

def arm_frame(sx):
    """Omuz noktası ve kolun yerel eksenleri: aşağı (kol boyunca), dışa ve öne. Kol 21 derece yana açık, hafif önde."""
    shoulder = Vector((0.19 * sx, 0.035, 1.30))
    down = Vector((0.36 * sx, 0.1, -0.93)).normalized()
    out = Vector((sx, 0.0, 0.0))
    out = (out - down * out.dot(down)).normalized()
    fwd = Vector((0.0, 1.0, 0.0))
    fwd = (fwd - down * fwd.dot(down) - out * fwd.dot(out)).normalized()
    return shoulder, down, out, fwd


def arm_pt(frame, length, lx=0.0, ly=0.0):
    shoulder, down, out, fwd = frame
    return shoulder + down * length + out * lx + fwd * ly


# Bot tabanının ayak izi (x, y): topuk dar, burun geniş ve yuvarlak. Plaka XZ'de kurulup yatırılır.
SOLE_OUTLINE = [(math.copysign((0.087 + 0.009 * math.sin(a)) * abs(math.cos(a)) ** 0.75, math.cos(a)),
                 0.091 + math.copysign(0.178 * abs(math.sin(a)) ** 0.75, math.sin(a)))
                for a in (2 * math.pi * i / 28 for i in range(28))]


# ---------- Parçalar ----------

def build_legs(b):
    for s, sx in SIDES:
        g = "Leg" + s
        # Uyluk (şortla çorap arasında ten), jartiyer kayışı ve tokası, çorap bandı
        b.add(g, "Skin", k.tube([(0.09 * sx, -0.005, 0.93), (0.1 * sx, -0.002, 0.84), (0.103 * sx, -0.002, 0.76)],
                                [0.066, 0.062, 0.06], segs=14))
        b.add(g, "Leather", k.torus((0.102 * sx, -0.003, 0.778), 0.064, 0.064, 0.008, major=22, minor=5, tube_sq=(1.0, 1.5)))
        b.add(g, "Brass", k.rbox((0.15 * sx, 0.04, 0.778), (0.02, 0.02, 0.024), bevel=0.004,
                                 basis=Matrix.Rotation(math.radians(45 * sx), 3, "Z")))
        b.add(g, "BootCuff", k.torus((0.103 * sx, -0.002, 0.756), 0.061, 0.061, 0.007, major=22, minor=5))
        b.add(g, "Stocking", k.tube([(0.103 * sx, -0.002, 0.765), (0.111 * sx, 0.006, 0.6), (0.12 * sx, -0.004, 0.48),
                                     (0.13 * sx, -0.012, 0.34), (0.132 * sx, -0.012, 0.22)],
                                    [0.06, 0.047, 0.051, 0.042, 0.042], segs=14))
        # İri bot: geniş konç, yuvarlak burun, kalın krem taban, katlanmış konç ağzı, tokalı kayış
        ax, ay = 0.133 * sx, -0.012
        b.add(g, "Boot", k.tube([(ax, ay, 0.26), (ax, ay + 0.002, 0.16), (ax, ay + 0.01, 0.1)], [0.067, 0.069, 0.072], segs=16))
        b.add(g, "Boot", k.ellipsoid((ax, -0.018, 0.105), (0.074, 0.08, 0.08), sub=3))
        b.add(g, "Boot", k.ellipsoid((ax + 0.004 * sx, 0.06, 0.122), (0.08, 0.1, 0.072), sub=3))
        b.add(g, "Boot", k.ellipsoid((ax + 0.006 * sx, 0.135, 0.098), (0.09, 0.13, 0.066), sub=3))
        b.add(g, "Sole", k.place(k.plate(SOLE_OUTLINE, 0.048, bevel=0.012, smooth=True), (ax + 0.004 * sx, 0.0, 0.024),
                                 Matrix.Rotation(math.radians(-90), 3, "X")))
        b.add(g, "BootCuff", k.tube([(ax, ay, 0.248), (ax, ay, 0.335)], [0.079, 0.08], segs=18))
        b.add(g, "BootCuff", k.torus((ax, ay, 0.335), 0.08, 0.08, 0.012, major=24, minor=6))
        b.add(g, "BootCuff", k.torus((ax, ay, 0.25), 0.079, 0.079, 0.01, major=24, minor=6))

        # Bileği yatay saran turuncu-altın kayış, tokası dış yanda
        b.add(g, "Brass", k.torus((ax + 0.002 * sx, 0.012, 0.178), 0.078, 0.092, 0.011, major=28, minor=6, tube_sq=(1.0, 2.1)))
        b.add(g, "Brass", k.rbox((ax + 0.078 * sx, 0.04, 0.178), (0.016, 0.05, 0.052), bevel=0.006,
                                 basis=Matrix.Rotation(math.radians(-30 * sx), 3, "Z")))
        b.add(g, "Leather", k.rbox((ax + 0.086 * sx, 0.045, 0.178), (0.006, 0.026, 0.026), bevel=0.003,
                                   basis=Matrix.Rotation(math.radians(-30 * sx), 3, "Z")))


def build_body(b):
    body = "Body"
    # Boyun dibi ve göğsün üstü (ten), koyu üst (önde yuvarlak yaka)
    b.add(body, "Skin", rings_mesh([[ellipse_pt(360.0 * i / 24, z, a, bb, cy) for i in range(24)]
                                    for z, a, bb, cy in ((1.42, 0.046, 0.044, -0.002), (1.38, 0.075, 0.06, 0.005),
                                                         (1.345, 0.118, 0.078, 0.014), (1.31, 0.132, 0.086, 0.02))]))
    rings = []
    for j, z in enumerate((1.34, 1.31, 1.28, 1.25, 1.21, 1.17, 1.13, 1.09, 1.045)):
        ring = []
        for i in range(28):
            phi = 360.0 * i / 28
            zz = z - (0.032 * max(0.0, math.cos(math.radians(phi))) ** 3 if j == 0 else 0.0)
            ring.append(top_pt(phi, zz))
        rings.append(ring)
    b.add(body, "Top", rings_mesh(rings))
    # Şort: kalça ve iki paça, paçalarda kıvrık kenar
    b.add(body, "Shorts", rings_mesh([[ellipse_pt(360.0 * i / 28, z, a, bb, cy) for i in range(28)]
                                      for z, a, bb, cy in ((1.07, 0.124, 0.085, 0.03), (1.02, 0.132, 0.092, 0.024),
                                                           (0.97, 0.14, 0.097, 0.016), (0.93, 0.145, 0.098, 0.01),
                                                           (0.905, 0.14, 0.092, 0.006))]))
    for sx in (-1, 1):
        b.add(body, "Shorts", k.tube([(0.088 * sx, 0.008, 0.935), (0.094 * sx, 0.008, 0.86)], [0.07, 0.074], segs=16))
        b.add(body, "Shorts", k.torus((0.094 * sx, 0.008, 0.864), 0.074, 0.074, 0.009, major=22, minor=5))
    # Kemer ve kare altın toka (ortası boş çerçeve)
    b.add(body, "Leather", k.torus((0, 0.03, 1.088), 0.132, 0.092, 0.012, major=48, minor=6, tube_sq=(1.0, 2.7)))
    for center, size in (((0, 0.142, 1.118), (0.088, 0.012, 0.012)), ((0, 0.142, 1.058), (0.088, 0.012, 0.012)),
                         ((-0.038, 0.142, 1.088), (0.012, 0.012, 0.072)), ((0.038, 0.142, 1.088), (0.012, 0.012, 0.072))):
        b.add(body, "Brass", k.rbox(center, size, bevel=0.004))
    b.add(body, "Brass", k.rbox((0.0, 0.14, 1.088), (0.006, 0.008, 0.05), bevel=0.002))
    # Sol omuzdan sağ kalçaya çapraz kayış
    strap = [top_pt(-40 + 100 * t, 1.345 - 0.3 * t, 0.009) for t in (i / 11 for i in range(12))]
    b.add(body, "Leather", k.tube(strap, [0.013] * 12, segs=6, squash=(0.4, 1.9), samples=2,
                                  ref=(math.sin(math.radians(-40)), math.cos(math.radians(-40)), 0)))
    # Kalçalarda kapaklı deri keseler
    b.add(body, "Leather", k.rbox((0.128, 0.105, 0.965), (0.07, 0.05, 0.08), bevel=0.014))
    b.add(body, "Leather", k.rbox((0.128, 0.128, 0.99), (0.074, 0.014, 0.042), bevel=0.006))
    b.add(body, "Brass", k.ellipsoid((0.128, 0.137, 0.983), (0.008, 0.005, 0.008), sub=1))
    b.add(body, "Leather", k.rbox((0.128, 0.1, 1.03), (0.02, 0.01, 0.06), bevel=0.003))
    b.add(body, "Leather", k.rbox((-0.112, 0.112, 0.97), (0.05, 0.04, 0.06), bevel=0.012))
    b.add(body, "Leather", k.rbox((-0.112, 0.13, 0.99), (0.054, 0.012, 0.03), bevel=0.005))


def build_coat(b):
    body = "Body"
    # Ön paneller (krem): ön kenardan yan dikişe kadar, omuzdan etek ucuna; ön kenarda ve etekte gül rengi şerit
    for _s, sx in SIDES:
        def panel(u, v, sx=sx):
            z = COAT_TOP + (COAT_HEM - COAT_TOP) * v
            o = coat_open(z)
            return coat_pt(sx * (o + (95 - o) * u), z)

        def facing(u, v, sx=sx):
            z = COAT_TOP + (COAT_HEM - COAT_TOP) * v
            return coat_pt(sx * (coat_open(z) + 6 * u), z, 0.007)

        def hem(u, v, sx=sx):
            z = COAT_HEM + 0.045 * (1 - v)
            o = coat_open(z)
            return coat_pt(sx * (o + (95 - o) * u), z, 0.007)
        b.add(body, "Coat", k.surface(panel, 12, 30, thickness=0.012))
        b.add(body, "CoatTrim", k.surface(facing, 2, 30, thickness=0.006))
        b.add(body, "CoatTrim", k.surface(hem, 12, 2, thickness=0.006))
        # Etekte altın yıldız
        p, n = coat_surface_pt(64 * sx, 0.57, 0.008)
        b.add(body, "Brass", k.place(k.star(0.055, 0.024, 0.006), p, k.frame(n)))

    # Sırtın üstü (pembe, durağan) ve belde gül rengi yarım kemer
    def back_upper(u, v):
        return coat_pt(95 + 170 * u, COAT_TOP + (0.93 - COAT_TOP) * v)
    b.add(body, "CoatBack", k.surface(back_upper, 26, 14, thickness=0.012))
    b.add(body, "CoatTrim", k.surface(lambda u, v: coat_pt(148 + 64 * u, 1.045 - 0.04 * v, 0.008), 10, 2, thickness=0.008))

    # Dik yaka: önde uçları yana açılır
    def collar(u, v):
        end = max(0.0, abs(2 * u - 1) - 0.72) / 0.28
        return ellipse_pt(42 + 276 * u, 1.345 + 0.075 * v, 0.1 + 0.03 * v + 0.035 * end * v, 0.082 + 0.028 * v, 0.004)
    b.add(body, "Coat", k.surface(collar, 40, 5, thickness=0.012))
    # Sol yakada küçük yıldız broş
    p, n = coat_surface_pt(-(coat_open(1.27) + 9), 1.27, 0.009)
    b.add(body, "Brass", k.place(k.star(0.022, 0.01, 0.005), p, k.frame(n)))

    # Arka etek (pembe, belde döner): ortada etek ucunda yırtmaç, iki düğme
    g = "SkirtBack"
    for sgn in (1, -1):
        def half(u, v, sgn=sgn):
            z = 0.99 + (COAT_HEM - 0.99) * v
            end = 180 - 3.2 * smoothstep(0.56, 0.42, z)
            return coat_pt(sgn * (88 + (end - 88) * u), z, 0.005)

        def hem_back(u, v, sgn=sgn):
            z = COAT_HEM + 0.045 * (1 - v)
            end = 180 - 3.2 * smoothstep(0.56, 0.42, z)
            return coat_pt(sgn * (88 + (end - 88) * u), z, 0.011)
        b.add(g, "CoatBack", k.surface(half, 14, 20, thickness=0.012))
        b.add(g, "CoatTrim", k.surface(hem_back, 14, 2, thickness=0.006))
        p, n = coat_surface_pt(sgn * 133, 0.905, 0.012)
        b.add(g, "Leather", k.ellipsoid(p, (0.017, 0.009, 0.023), sub=2, basis=k.frame(n)))


def build_arms(b):
    for s, sx in SIDES:
        g = "Sleeve" + s
        fr = arm_frame(sx)
        _shoulder, down, out, fwd = fr
        basis = Matrix((out, fwd, -down)).transposed()
        # Omuz başı ve aşağı doğru genişleyen kol (krem)
        b.add(g, "Coat", k.ellipsoid(arm_pt(fr, 0.012, lx=-0.008), (0.074, 0.076, 0.07), sub=3, basis=basis))
        b.add(g, "Coat", k.tube([arm_pt(fr, d) for d in (0.0, 0.08, 0.16, 0.22, 0.27)], [0.066, 0.068, 0.074, 0.083, 0.093],
                                segs=18, ref=out))

        # Gül rengi çan manşet (içi boş kalın halka) ve içindeki gölge
        def cuff(u, v, fr=fr):
            r = 0.097 + 0.016 * v ** 0.8
            a = 2 * math.pi * u
            return arm_pt(fr, 0.252 + 0.09 * v, lx=r * math.cos(a), ly=r * math.sin(a))
        b.add(g, "CoatTrim", k.surface(cuff, 24, 4, thickness=0.012, wrap_u=True))
        b.add(g, "Top", k.tube([arm_pt(fr, 0.318), arm_pt(fr, 0.324)], [0.1, 0.1], segs=20))
        # Kolun ön dış yüzünde yıldız
        nrm = (out * 0.55 + fwd * 0.83).normalized()
        b.add(g, "Brass", k.place(k.star(0.026, 0.011, 0.005), arm_pt(fr, 0.205) + nrm * 0.084, k.frame(nrm, up=-down)))
        # Parmaksız eldiven: bilek, el; parmaklar ve başparmak açıkta
        b.add(g, "Glove", k.tube([arm_pt(fr, d) for d in (0.29, 0.34, 0.37)], [0.036, 0.033, 0.031], segs=12))
        b.add(g, "Glove", k.ellipsoid(arm_pt(fr, 0.405), (0.03, 0.05, 0.054), sub=3, basis=basis))
        for dy, ln in ((-0.03, 0.05), (-0.01, 0.06), (0.01, 0.058), (0.03, 0.048)):
            finger = [arm_pt(fr, 0.44, lx=-0.002, ly=dy), arm_pt(fr, 0.44 + ln * 0.55, lx=-0.004, ly=dy + 0.004),
                      arm_pt(fr, 0.44 + ln, lx=-0.013, ly=dy + 0.011)]
            b.add(g, "Skin", k.tube(finger, [0.013, 0.012, 0.0095], segs=6, samples=2))
        thumb = [arm_pt(fr, 0.385, lx=-0.016, ly=0.04), arm_pt(fr, 0.413, lx=-0.022, ly=0.057), arm_pt(fr, 0.44, lx=-0.018, ly=0.064)]
        b.add(g, "Skin", k.tube(thumb, [0.014, 0.013, 0.01], segs=6, samples=2))


def build_face(b):
    body = "Body"
    b.add(body, "Skin", closed_surface(lambda u, v: head_pos(360 * u, -90 + 180 * v), 40, 28))
    b.add(body, "Skin", k.tube([(0, -0.008, 1.3), (0, -0.004, 1.38), (0, 0.0, 1.47)], [0.05, 0.046, 0.044], segs=14))
    for _s, sx in SIDES:
        lon0, lat0 = 33 * sx, -6
        # İri göz: beyaz, kahve iris, göz bebeği, iki parıltı (ışık iki gözde de karakterin sağından gelir)
        b.add(body, "Sclera", on_face(k.ellipsoid((0, 0, 0), (0.045, 0.006, 0.038), sub=3), lon0, lat0, 0.0, sx))
        b.add(body, "Iris", on_face(k.ellipsoid((-0.004, 0, -0.002), (0.031, 0.006, 0.034), sub=3), lon0, lat0, 0.0025, sx))
        b.add(body, "Pupil", on_face(k.ellipsoid((-0.004, 0, 0), (0.017, 0.005, 0.02), sub=2), lon0, lat0, 0.0045, sx))
        hx = 0.009 * sx
        b.add(body, "Shine", on_face(k.ellipsoid((hx, 0, 0.012), (0.009, 0.004, 0.011), sub=2), lon0, lat0, 0.007, sx))
        b.add(body, "Shine", on_face(k.ellipsoid((-hx, 0, -0.013), (0.0045, 0.003, 0.005), sub=1), lon0, lat0, 0.007, sx))
        # Kalın üst kirpik çizgisi (dış köşede yukarı kalkar), ince alt çizgi, kalın kavisli kaş
        upper = [Vector((0.047 * math.cos(t), 0.006, 0.04 * math.sin(t) + 0.002)) for t in (math.pi * (1 - i / 8) for i in range(9))]
        upper += [Vector((0.056, 0.006, 0.013)), Vector((0.064, 0.006, 0.025))]
        b.add(body, "Lash", on_face(k.tube(upper, [0.003, 0.004, 0.005, 0.0055, 0.006, 0.0062, 0.0065, 0.0065, 0.006, 0.0045, 0.002],
                                           segs=6, samples=2), lon0, lat0, 0.0, sx))
        lower = [Vector((0.044 * math.cos(t), 0.004, 0.036 * math.sin(t))) for t in (math.pi + 0.35 + (math.pi - 0.6) * i / 6 for i in range(7))]
        b.add(body, "Lash", on_face(k.tube(lower, [0.0016] * 7, segs=5, samples=2), lon0, lat0, 0.0, sx))
        brow = [(-0.042, 0.004, 0.064), (-0.012, 0.004, 0.08), (0.02, 0.004, 0.083), (0.05, 0.004, 0.072), (0.066, 0.004, 0.056)]
        b.add(body, "Brow", on_face(k.tube(brow, [0.0095, 0.012, 0.011, 0.008, 0.004], segs=6, squash=(0.7, 1.0), ref=(0, 1, 0)),
                                    lon0, lat0, 0.0, sx))
        b.add(body, "Blush", on_face(k.ellipsoid((0, 0, 0), (0.032, 0.003, 0.02), sub=2), 47 * sx, -24, 0.001, sx))
        # Saçın arasından görünen kulak ve koyu küpe
        p, n = head_pt(88 * sx, -8, -0.004)
        b.add(body, "Skin", k.ellipsoid(p, (0.028, 0.014, 0.04), sub=2, basis=k.frame(n)))
        p, n = head_pt(90 * sx, -21, 0.012)
        b.add(body, "Lash", k.ellipsoid(p, (0.008, 0.008, 0.008), sub=2))
    p, n = head_pt(0, -23.5, 0.005)
    b.add(body, "Skin", k.ellipsoid(p, (0.017, 0.013, 0.014), sub=3, basis=k.frame(n)))
    # Kapalı, hafif yan gülümseme ve alt dudak
    smile = [Vector((0.042 * t, 0.003, 0.009 * t * t + 0.002 * t)) for t in (i / 6 - 1 for i in range(13))]
    b.add(body, "Mouth", on_face(k.tube(smile, [0.0028] * 13, segs=6, samples=1), 0, -41, 0.0, 1))
    b.add(body, "Lip", on_face(k.ellipsoid((0, 0, -0.008), (0.02, 0.004, 0.006), sub=2), 0, -41, 0.001, 1))


def build_hair(b):
    body = "Body"
    rnd = random.Random(7)
    b.add(body, "Hair", k.ellipsoid(HAIR_C, HAIR_R, sub=3))
    b.add(body, "HairDark", k.surface(hair_mass_fn, 36, 9, thickness=0.05))
    # Arka: iki kat dolgun dalgalı bukle, uçları dışa kıvrık (sarkık şapka kenarının altından başlar)
    for layer in (0, 1):
        count = 13 - layer
        for i in range(count):
            phi = math.radians(112 + i * 136 / (count - 1) + 5 * layer)
            z1 = 1.12 + 0.05 * math.cos(phi) + rnd.uniform(-0.02, 0.04) + 0.03 * layer
            key = ("Hair", "HairLight", "Hair", "HairDark")[(i + 2 * layer) % 4]
            b.add(body, key, lock(phi, 1.52, z1, 0.062 - 0.008 * layer, 0.007, rnd.uniform(0.14, 0.22),
                                  rnd.uniform(1.1, 1.7), rnd.uniform(0, 6.28), lift=0.025 + 0.03 * layer, flare=0.03, curl=0.045))
    # Yanlar: kulağın arkasından omza dökülen bukleler; en öndeki ince bukle yüzü çerçeveler
    for sx in (-1, 1):
        b.add(body, "HairLight", lock(math.radians(66 * sx), 1.66, 1.24, 0.04, 0.007, 0.12, 1.4, 0.3,
                                      lift=0.012, flare=0.02, curl=0.06))
        for j, (deg, z1) in enumerate(((78, 1.19), (92, 1.16), (106, 1.14), (120, 1.13))):
            b.add(body, ("Hair", "HairLight", "Hair", "HairDark")[j],
                  lock(math.radians(deg * sx), 1.62, z1, 0.055, 0.007, 0.2, 1.3 + 0.15 * j, 0.5 + j, lift=0.025, flare=0.05, curl=0.06))
    # İnce parlak tutamlar
    for deg in (124, 147, 169, 191, 213, 236):
        b.add(body, "HairLight", lock(math.radians(deg), 1.5, 1.16 + rnd.uniform(0, 0.05), 0.026, 0.006, 0.2,
                                      rnd.uniform(1.2, 1.8), rnd.uniform(0, 6.28), lift=0.09, flare=0.03, curl=0.05))
    for lon0, lat0, lon1, lat1, r0, phase in BANGS:
        b.add(body, "Hair", bang(lon0, lat0, lon1, lat1, r0, phase))


def build_hat(b):
    body = "Body"
    b.add(body, "Hat", k.surface(brim_fn, 64, 8, thickness=0.018, wrap_u=True))
    edge = [brim_fn(i / 80, 1.0) for i in range(80)]
    b.add(body, "Hat", k.loop(edge, [Vector((math.sin(2 * math.pi * i / 80), math.cos(2 * math.pi * i / 80), 0)) for i in range(80)], 0.009))
    b.add(body, "HatDark", k.tube(CROWN_PATH, CROWN_R, segs=24, samples=5))
    band = [crown_axis(0.004 + 0.085 * i / 4) for i in range(5)]
    b.add(body, "HatBand", k.tube([p for p, r, t in band], [r + 0.011 for p, r, t in band], segs=32, samples=2))
    # Önde üst üste iki altın şerit (^), alttakinin ucunda kırmızı taş
    for l, w in ((0.125, 0.07), (0.182, 0.056)):
        r = crown_axis(l)[1] + 0.004
        for side in (-1, 1):
            arm = k.rbox((side * w * 0.45, 0.0, -w * 0.18), (w, 0.007, 0.017), bevel=0.004,
                         basis=Matrix.Rotation(math.radians(side * 28), 3, "Y"))
            b.add(body, "Brass", k.wrap(arm, lambda co, l=l, r=r: crown_at(l + co.z, co.x / r, 0.005 + co.y)[0]))
    b.add(body, "HatGem", k.ellipsoid(crown_at(0.127, 0.0, 0.012)[0], (0.011, 0.011, 0.011), sub=2))
    # Bantta altın çapraz süsler, arkada kanatlı kırmızı süs
    lb = 0.045
    rb = crown_axis(lb)[1] + 0.011
    for ang in (65, -65, 118, -118):
        for tilt in (40, -40):
            bar = k.rbox((0, 0, 0), (0.045, 0.006, 0.011), bevel=0.003, basis=Matrix.Rotation(math.radians(tilt), 3, "Y"))
            b.add(body, "Brass", k.wrap(bar, lambda co, a=math.radians(ang): crown_at(lb + co.z, a + co.x / rb, 0.013 + co.y)[0]))
    gem = k.rbox((0, 0, 0), (0.026, 0.008, 0.026), bevel=0.004, basis=Matrix.Rotation(math.radians(45), 3, "Y"))
    b.add(body, "HatGem", k.wrap(gem, lambda co: crown_at(lb + co.z, math.pi + co.x / rb, 0.014 + co.y)[0]))
    for side in (-1, 1):
        wing = k.rbox((side * 0.03, 0, 0.004), (0.036, 0.007, 0.012), bevel=0.003, basis=Matrix.Rotation(math.radians(-18 * side), 3, "Y"))
        b.add(body, "HatGem", k.wrap(wing, lambda co: crown_at(lb + co.z, math.pi + co.x / rb, 0.013 + co.y)[0]))


def main():
    m.reset_scene()
    for key, rgb in COLORS.items():
        m.material(key, rgb)
    root = m.make_root("GirlRoot")

    b = Builder(root)
    b.group("Body")
    for s, sx in SIDES:
        b.group("Leg" + s, (0.09 * sx, -0.005, HIP_Z), "Boot", "Boot_Boot" + s)
        b.group("Sleeve" + s, arm_frame(sx)[0], "Coat", "Coat_Sleeve" + s)
    b.group("SkirtBack", (0.0, SKIRT_Y, SKIRT_Z), "CoatBack", "CoatBack_SkirtBack")

    build_legs(b)
    build_body(b)
    build_coat(b)
    build_arms(b)
    build_face(b)
    build_hair(b)
    build_hat(b)
    b.build()

    bpy.context.view_layer.update()
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    by_key = {}
    for o in meshes:
        key = o.name.split("_")[0]
        by_key[key] = by_key.get(key, 0) + sum(len(p.vertices) - 2 for p in o.data.polygons)
    zs = [(o.matrix_world @ v.co).z for o in meshes for v in o.data.vertices]
    stats = "OK objects=%d tris=%d zmin=%.3f zmax=%.3f\n%s\n%s" % (
        len(meshes), sum(by_key.values()), min(zs), max(zs),
        ", ".join("%s=%d" % kv for kv in sorted(by_key.items(), key=lambda kv: -kv[1])),
        ", ".join(sorted(o.name for o in meshes)))

    # Videodaki gibi önden, soldan, arkadan ve sağdan; sonra oyun kamerası ve yakın yüz
    m.render_views("girl4", PREVIEW_DIR, [
        ("front", (0.0, 4.6, 1.3)), ("left", (-4.6, 0.0, 1.3)), ("back", (0.0, -4.6, 1.3)), ("right", (4.6, 0.0, 1.3)),
    ], target=(0, 0, 1.06), size=(540, 540), background=(0.12, 0.12, 0.13), lens=60, gain=1.2)
    m.render_views("girl4more", PREVIEW_DIR, [
        ("three", (2.4, 3.8, 1.5)), ("game", (0.0, -6.2, 3.0)), ("backthree", (-2.6, -3.6, 1.9)),
    ], target=(0, 0, 1.05), size=(540, 540), background=(0.12, 0.12, 0.13), lens=60, gain=1.2)
    m.render_views("girl4face", PREVIEW_DIR, [
        ("front", (0.0, 2.2, 1.62)), ("three", (1.4, 1.7, 1.62)), ("side", (-2.2, 0.0, 1.62)),
    ], target=(0, 0, 1.6), size=(540, 540), background=(0.12, 0.12, 0.13), lens=55, gain=1.2)

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
with open(os.path.join(PREVIEW_DIR, "girl4_log.txt"), "w", encoding="utf-8") as log:
    log.write(result)
