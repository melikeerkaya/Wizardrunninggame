"""
Karakter modelleme için ortak yardımcılar (Blender içinde çalışır).
Z yukarı, karakter +Y yönüne bakar, ayak tabanı z=0.
Her mesh dünya koordinatlarında üretilir (konsept önizleme için yeterli).
"""
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

_materials = {}


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _materials.clear()


def material(key, rgb):
    if key not in _materials:
        # rgb sRGB değeri olarak verilir (Unity'deki gibi). Blender doğrusal bekler, o yüzden çeviririz.
        lin = tuple(c ** 2.2 for c in rgb)
        mat = bpy.data.materials.new(key)
        mat.diffuse_color = (*lin, 1.0)
        mat.use_nodes = True
        mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*lin, 1.0)
        _materials[key] = mat
    return _materials[key]


# ---------- Mesh üreticiler ----------

def loft(path, radii, segs=8, squash=(1.0, 1.0), caps=(True, True)):
    """Bir yol boyunca yarıçapı değişen boru. squash dik yol için (ön-arka, yan) genişlik çarpanıdır."""
    bm = bmesh.new()
    count = len(path)
    rings = []
    for i in range(count):
        p = Vector(path[i])
        d = (Vector(path[i + 1]) - p) if i < count - 1 else (p - Vector(path[i - 1]))
        d.normalize()
        ref = Vector((1, 0, 0)) if abs(d.x) < 0.9 else Vector((0, 1, 0))
        a = d.cross(ref).normalized()
        b = d.cross(a).normalized()
        ring = []
        for k in range(segs):
            t = 2 * math.pi * k / segs
            v = p + a * math.cos(t) * radii[i] * squash[0] + b * math.sin(t) * radii[i] * squash[1]
            ring.append(bm.verts.new(v))
        rings.append(ring)
    for i in range(count - 1):
        for k in range(segs):
            j = (k + 1) % segs
            bm.faces.new((rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]))
    if caps[0]:
        bm.faces.new(list(reversed(rings[0])))
    if caps[1]:
        bm.faces.new(rings[-1])
    return bm


def sphere(r, scale=(1, 1, 1), sub=1, offset=(0, 0, 0)):
    bm = bmesh.new()
    add_sphere(bm, r, scale, sub, offset)
    return bm


def add_sphere(bm, r, scale=(1, 1, 1), sub=1, offset=(0, 0, 0)):
    verts = bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)["verts"]
    bmesh.ops.scale(bm, vec=Vector(scale), verts=verts)
    bmesh.ops.translate(bm, vec=Vector(offset), verts=verts)
    return bm


def box(size, offset=(0, 0, 0)):
    bm = bmesh.new()
    verts = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    bmesh.ops.scale(bm, vec=Vector(size), verts=verts)
    bmesh.ops.translate(bm, vec=Vector(offset), verts=verts)
    return bm


def star(outer, inner, half_depth, center=(0, 0, 0)):
    """+Y yönüne bakan 5 köşeli yıldız (XZ düzleminde)."""
    bm = bmesh.new()
    front, back = [], []
    for i in range(10):
        r = outer if i % 2 == 0 else inner
        ang = math.pi / 2 + i * math.pi / 5
        x, z = r * math.cos(ang), r * math.sin(ang)
        front.append(bm.verts.new((x, half_depth, z)))
        back.append(bm.verts.new((x, -half_depth, z)))
    bm.faces.new(front)
    bm.faces.new(list(reversed(back)))
    for i in range(10):
        j = (i + 1) % 10
        bm.faces.new((front[i], back[i], back[j], front[j]))
    bmesh.ops.translate(bm, vec=Vector(center), verts=bm.verts)
    return bm


def rotate_x(bm, degrees, about=(0, 0, 0)):
    bmesh.ops.rotate(bm, cent=Vector(about), matrix=Matrix.Rotation(math.radians(degrees), 3, "X"), verts=bm.verts)
    return bm


def rotate_y(bm, degrees, about=(0, 0, 0)):
    bmesh.ops.rotate(bm, cent=Vector(about), matrix=Matrix.Rotation(math.radians(degrees), 3, "Y"), verts=bm.verts)
    return bm


def rotate_z(bm, degrees, about=(0, 0, 0)):
    bmesh.ops.rotate(bm, cent=Vector(about), matrix=Matrix.Rotation(math.radians(degrees), 3, "Z"), verts=bm.verts)
    return bm


def mirror_x(path):
    return [(-p[0], p[1], p[2]) for p in path]


_origins = {}
_objects = []


def make_root(name="WizardRoot"):
    root = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(root)
    _origins[name] = Vector((0, 0, 0))
    return root


def all_objects():
    return list(_objects)


def finish(name, bm, key, origin=(0, 0, 0), parent=None):
    """origin: nesnenin dönme merkezi (dünya konumu). parent verilirse konum ona göre kaydedilir."""
    o = Vector(origin)
    bmesh.ops.translate(bm, vec=-o, verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(_materials[key])
    _origins[name] = o
    if parent is not None:
        obj.parent = parent
        obj.location = o - _origins[parent.name]
    else:
        obj.location = o
    _objects.append(obj)
    return obj


# ---------- Ortak parçalar ----------

def witch_hat(brim_z=1.50, size=1.0, parent=None):
    """Geriye bükülen sivri uçlu, altın bantlı, yıldızlı ve ucunda sarkan yıldızı olan pembe şapka.
    Nesne adları "RenkAnahtarı_Parça" biçimindedir."""
    z, s = brim_z, size
    finish("Hat_Brim", loft([(0, 0, z), (0, 0, z + 0.035 * s)], [0.50 * s, 0.33 * s], 14), "Hat", parent=parent)
    crown = loft(
        [(0, 0, z + 0.02 * s), (0, -0.01 * s, z + 0.28 * s), (0, -0.05 * s, z + 0.48 * s),
         (0, -0.13 * s, z + 0.62 * s), (0, -0.24 * s, z + 0.70 * s), (0, -0.34 * s, z + 0.72 * s)],
        [0.27 * s, 0.21 * s, 0.145 * s, 0.09 * s, 0.05 * s, 0.006 * s], 10)
    finish("Hat_Crown", crown, "Hat", parent=parent)
    finish("Gold_Band", loft([(0, 0, z + 0.03 * s), (0, 0, z + 0.10 * s)], [0.285 * s, 0.265 * s], 10), "Gold", parent=parent)
    c = (0, 0.205 * s, z + 0.28 * s)
    finish("Gold_StarFront", rotate_x(star(0.08 * s, 0.036 * s, 0.018, c), 14, c), "Gold", parent=parent)
    finish("Gold_String", loft([(0, -0.34 * s, z + 0.72 * s), (0, -0.34 * s, z + 0.60 * s)], [0.007, 0.007], 4), "Gold", parent=parent)
    finish("Gold_StarTip", star(0.058 * s, 0.026 * s, 0.014, (0, -0.34 * s, z + 0.56 * s)), "Gold", parent=parent)


# ---------- Önizleme ----------

def render_views(prefix, out_dir, views, target=(0, 0, 1.1), size=(500, 700), background=(0.82, 0.88, 0.96), lens=60, gain=1.0):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.view_settings.view_transform = "Standard"
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "MATERIAL"
    shading.show_shadows = True
    shading.shadow_intensity = 0.35
    shading.show_cavity = False
    scene.render.resolution_x, scene.render.resolution_y = size
    scene.world = bpy.data.worlds.new("Sky")
    scene.world.color = background

    cam_data = bpy.data.cameras.new("Cam")
    cam_data.lens = lens
    camera = bpy.data.objects.new("Cam", cam_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera

    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for name, loc in views:
        camera.location = loc
        camera.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        path = os.path.join(out_dir, "%s_%s.png" % (prefix, name))
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        paths.append(path)

    images = [bpy.data.images.load(p) for p in paths]
    w, h = images[0].size
    arrays = []
    for im in images:
        buf = np.empty(w * h * 4, dtype=np.float32)
        im.pixels.foreach_get(buf)
        arrays.append(buf.reshape(h, w, 4))
    sheet = np.concatenate(arrays, axis=1)
    sheet[..., :3] = np.clip(sheet[..., :3] * gain, 0.0, 1.0)
    out = bpy.data.images.new("sheet", width=w * len(arrays), height=h, alpha=False)
    out.pixels.foreach_set(sheet.flatten())
    out.filepath_raw = os.path.join(out_dir, "%s_sheet.png" % prefix)
    out.file_format = "PNG"
    out.save()
