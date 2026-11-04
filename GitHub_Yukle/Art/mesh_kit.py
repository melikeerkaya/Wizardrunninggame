"""
Ayrıntılı (yumuşak gölgeli, orta poligonlu) karakter modelleme araçları. Blender içinde çalışır.
Z yukarı, karakter +Y yönüne bakar. Her fonksiyon bir bmesh döndürür; parçalar Builder ile renk anahtarına göre birleştirilir.
Yumuşak yüzeyler face.smooth ile işaretlenir, böylece FBX'e düzgün normallerle aktarılır (kapak yüzleri düz kalır).
"""
import math

import bmesh
from mathutils import Matrix, Vector


def vec(p):
    return p.copy() if isinstance(p, Vector) else Vector(p)


def spline(points, samples=4):
    """Catmull-Rom eğrisi: noktalardan geçen yumuşak yol. Her aralığa `samples` nokta koyar."""
    pts = [vec(p) for p in points]
    count = len(pts)
    if count < 3:
        return pts
    out = []
    for i in range(count - 1):
        p0 = pts[i - 1] if i > 0 else pts[i] * 2 - pts[i + 1]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < count else pts[i + 1] * 2 - pts[i]
        for s in range(samples):
            t = s / samples
            out.append(0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (3 * p1 - p0 - 3 * p2 + p3) * t ** 3))
    out.append(pts[-1])
    return out


def smooth_values(values, samples=4):
    return [max(0.002, p.x) for p in spline([(v, 0.0, 0.0) for v in values], samples)]


def tube(path, radii, segs=8, squash=(1.0, 1.0), samples=3, ref=None, smooth=True, caps=True):
    """Yol boyunca yarıçapı değişen yumuşak boru. squash[0], `ref` yönüne dik düzlemdeki ilk eksenin genişliğidir
    (saç buklesi gibi yassı şeritler için). Kesit dönmesin diye çerçeve yol boyunca taşınır."""
    pts = spline(path, samples)
    rad = smooth_values(radii, samples)
    count = len(pts)
    tans = []
    for i in range(count):
        if i == 0:
            t = pts[1] - pts[0]
        elif i == count - 1:
            t = pts[-1] - pts[-2]
        else:
            t = pts[i + 1] - pts[i - 1]
        tans.append(t.normalized())

    hint = vec(ref) if ref is not None else (Vector((1, 0, 0)) if abs(tans[0].x) < 0.9 else Vector((0, 1, 0)))
    a = hint - tans[0] * hint.dot(tans[0])
    if a.length < 1e-6:
        a = tans[0].orthogonal()
    a.normalize()

    bm = bmesh.new()
    rings = []
    for i in range(count):
        if i > 0:
            a = tans[i - 1].rotation_difference(tans[i]) @ a
            a = a - tans[i] * a.dot(tans[i])
            a.normalize()
        b = tans[i].cross(a)
        ring = []
        for k in range(segs):
            ang = 2 * math.pi * k / segs
            ring.append(bm.verts.new(pts[i] + a * (math.cos(ang) * rad[i] * squash[0]) + b * (math.sin(ang) * rad[i] * squash[1])))
        rings.append(ring)

    for i in range(count - 1):
        for k in range(segs):
            j = (k + 1) % segs
            face = bm.faces.new((rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]))
            face.smooth = smooth
    if caps:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    return bm


def torus(center, rx, ry, tube_r, major=32, minor=6, wave=None, tube_sq=(1.0, 1.0), smooth=True):
    """Yatay halka (kemer, bilezik, şapka şeridi). wave(açı) halkanın yüksekliğini dalgalandırır."""
    cx, cy, cz = center
    bm = bmesh.new()
    rings = []
    for i in range(major):
        th = 2 * math.pi * i / major
        dz = wave(th) if wave else 0.0
        p = Vector((cx + rx * math.sin(th), cy + ry * math.cos(th), cz + dz))
        radial = Vector((math.sin(th) / rx, math.cos(th) / ry, 0.0)).normalized()
        ring = []
        for j in range(minor):
            a = 2 * math.pi * j / minor
            ring.append(bm.verts.new(p + radial * (math.cos(a) * tube_r * tube_sq[0]) + Vector((0, 0, 1)) * (math.sin(a) * tube_r * tube_sq[1])))
        rings.append(ring)
    for i in range(major):
        i2 = (i + 1) % major
        for j in range(minor):
            j2 = (j + 1) % minor
            face = bm.faces.new((rings[i][j], rings[i2][j], rings[i2][j2], rings[i][j2]))
            face.smooth = smooth
    return bm


def loop(points, normals, radius, minor=6, squash=(1.0, 1.0), smooth=True):
    """Kapalı yol boyunca boru (eğik şapka halkası, kenar kıvrımı). normals her noktada kesitin ilk eksenidir."""
    bm = bmesh.new()
    count = len(points)
    rings = []
    for i in range(count):
        p = vec(points[i])
        t = (vec(points[(i + 1) % count]) - vec(points[i - 1])).normalized()
        n = vec(normals[i])
        n = (n - t * n.dot(t)).normalized()
        b = t.cross(n)
        rings.append([bm.verts.new(p + n * (math.cos(a) * radius * squash[0]) + b * (math.sin(a) * radius * squash[1]))
                      for a in (2 * math.pi * j / minor for j in range(minor))])
    for i in range(count):
        i2 = (i + 1) % count
        for j in range(minor):
            j2 = (j + 1) % minor
            bm.faces.new((rings[i][j], rings[i2][j], rings[i2][j2], rings[i][j2])).smooth = smooth
    return bm


def surface(fn, nu, nv, thickness=0.01, wrap_u=False, smooth=True):
    """fn(u, v) -> nokta (u, v 0..1) ile tanımlı yüzeyi kalınlık vererek kapalı bir kabuğa çevirir (pelerin, şapka kenarı)."""
    cols = nu if wrap_u else nu + 1
    grid = [[vec(fn(i / nu, j / nv)) for j in range(nv + 1)] for i in range(cols)]

    def at(i, j):
        i = i % cols if wrap_u else min(max(i, 0), cols - 1)
        return grid[i][min(max(j, 0), nv)]

    normals = [[None] * (nv + 1) for _ in range(cols)]
    for i in range(cols):
        for j in range(nv + 1):
            n = (at(i + 1, j) - at(i - 1, j)).cross(at(i, j + 1) - at(i, j - 1))
            normals[i][j] = n.normalized() if n.length > 1e-9 else Vector((0, 0, 1))

    bm = bmesh.new()
    half = thickness / 2
    top = [[bm.verts.new(grid[i][j] + normals[i][j] * half) for j in range(nv + 1)] for i in range(cols)]
    bottom = [[bm.verts.new(grid[i][j] - normals[i][j] * half) for j in range(nv + 1)] for i in range(cols)]
    for i in range(cols if wrap_u else cols - 1):
        i2 = (i + 1) % cols
        for j in range(nv):
            bm.faces.new((top[i][j], top[i2][j], top[i2][j + 1], top[i][j + 1])).smooth = smooth
            bm.faces.new((bottom[i][j], bottom[i][j + 1], bottom[i2][j + 1], bottom[i2][j])).smooth = smooth
        bm.faces.new((top[i][0], bottom[i][0], bottom[i2][0], top[i2][0]))
        bm.faces.new((top[i][nv], top[i2][nv], bottom[i2][nv], bottom[i][nv]))
    if not wrap_u:
        for j in range(nv):
            bm.faces.new((top[0][j], top[0][j + 1], bottom[0][j + 1], bottom[0][j]))
            bm.faces.new((top[cols - 1][j], bottom[cols - 1][j], bottom[cols - 1][j + 1], top[cols - 1][j + 1]))
    return bm


def frame(normal, up=(0, 0, 1)):
    """Sütunları (doğu, normal, kuzey) olan dönüş matrisi. Yerel Y normale, yerel Z yukarıya bakar."""
    n = vec(normal).normalized()
    u = vec(up)
    u = u - n * u.dot(n)
    if u.length < 1e-6:
        u = Vector((0, 1, 0)) - n * n.y
    u.normalize()
    e = n.cross(u)
    return Matrix(((e.x, n.x, u.x), (e.y, n.y, u.y), (e.z, n.z, u.z)))


def place(bm, center, basis=None):
    mat = Matrix.Translation(vec(center))
    if basis is not None:
        mat = mat @ basis.to_4x4()
    bmesh.ops.transform(bm, matrix=mat, verts=bm.verts)
    return bm


def ellipsoid(center, radii, sub=3, basis=None, smooth=True):
    """sub: 2 = 80 üçgen, 3 = 320, 4 = 1280. Eksenler basis ile döndürülebilir."""
    bm = bmesh.new()
    verts = bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)["verts"]
    mat = Matrix.Translation(vec(center))
    if basis is not None:
        mat = mat @ basis.to_4x4()
    mat = mat @ Matrix.Diagonal(Vector((radii[0], radii[1], radii[2], 1.0)))
    bmesh.ops.transform(bm, matrix=mat, verts=verts)
    for face in bm.faces:
        face.smooth = smooth
    return bm


def rbox(center, size, bevel=0.01, basis=None, smooth=True):
    bm = bmesh.new()
    verts = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    bmesh.ops.scale(bm, vec=Vector(size), verts=verts)
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=2, affect="EDGES", profile=0.5)
    place(bm, center, basis)
    for face in bm.faces:
        face.smooth = smooth
    return bm


def plate(outline, depth, bevel=0.0, smooth=False):
    """XZ düzleminde (+Y'ye bakan) çokgen plaka; merkez orijinde, kalınlık Y yönünde."""
    bm = bmesh.new()
    h = depth / 2
    front = [bm.verts.new((x, h, z)) for x, z in outline]
    back = [bm.verts.new((x, -h, z)) for x, z in outline]
    bm.faces.new(front)
    bm.faces.new(list(reversed(back)))
    count = len(outline)
    for i in range(count):
        j = (i + 1) % count
        bm.faces.new((front[i], back[i], back[j], front[j]))
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=2, affect="EDGES", profile=0.5)
    for face in bm.faces:
        face.smooth = smooth
    return bm


def star(outer, inner, depth, points=5, bevel=0.0, smooth=False):
    outline = []
    for i in range(points * 2):
        r = outer if i % 2 == 0 else inner
        ang = math.pi / 2 + i * math.pi / points
        outline.append((r * math.cos(ang), r * math.sin(ang)))
    return plate(outline, depth, bevel, smooth)


def disc(radius, depth, sides=8):
    return plate([(radius * math.cos(2 * math.pi * i / sides), radius * math.sin(2 * math.pi * i / sides)) for i in range(sides)], depth)


def crescent(radius, max_width, depth, steps=12, start=40, end=320, tilt=0.0):
    """XZ düzleminde uçları sivri hilal (+Y'ye bakar). tilt hilalin açıklık yönünü döndürür."""
    bm = bmesh.new()
    outer, inner = [], []
    for i in range(steps + 1):
        s = i / steps
        t = math.radians(start + (end - start) * s + tilt)
        w = max_width * math.sin(math.pi * s) ** 0.8 + 0.004
        for r, ring in ((radius + w / 2, outer), (radius - w / 2, inner)):
            ring.append([bm.verts.new((r * math.sin(t), y, r * math.cos(t))) for y in (-depth / 2, depth / 2)])
    for i in range(steps):
        for side in (0, 1):
            bm.faces.new((outer[i][side], outer[i + 1][side], inner[i + 1][side], inner[i][side]))
        bm.faces.new((outer[i][0], outer[i][1], outer[i + 1][1], outer[i + 1][0]))
        bm.faces.new((inner[i][1], inner[i][0], inner[i + 1][0], inner[i + 1][1]))
    bm.faces.new((outer[0][0], outer[0][1], inner[0][1], inner[0][0]))
    bm.faces.new((outer[-1][1], outer[-1][0], inner[-1][0], inner[-1][1]))
    return bm


def wrap(bm, fn):
    """Her köşeyi fn(yerel konum) ile yeniden konumlar: düz plakaları eğri yüzeye (şapka tepesi) sarar."""
    for v in bm.verts:
        v.co = fn(v.co.copy())
    return bm


def merge(dst, src):
    mapping = {v: dst.verts.new(v.co) for v in src.verts}
    for face in src.faces:
        dst.faces.new([mapping[v] for v in face.verts]).smooth = face.smooth
