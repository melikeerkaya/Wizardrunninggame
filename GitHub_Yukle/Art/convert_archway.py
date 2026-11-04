"""
Tripo'dan gelen taş kemeri (ruin-archway.glb) oyunun yüksek engeline çevirir: Resources/Models/Desert/Archway.fbx ve
Archway_basecolor.png. Altından kayılır (bkz. Obstacle.HighLayouts).
Model bozulmadan, eşit ölçeklenir: ayakların ortası şerit sınırına (x = ±1.25) gelir. Sonra kuma gömülür, böylece kemerin
altı OPENING yüksekliğinde kalır (~1.5 boylu karakterin başının biraz altı): ayakta geçilemez, kayarak geçilir. Tepesi
~1.82'dedir, zıplamanın en yüksek noktasında ayaklar 2.0'a çıktığı için iyi zamanlanırsa üstünden de aşılır. Kumun altında
kalan parçalar silinir.
Örgü sadeleştirilirken doku dikişleri korunur, normaller asıl örgüden aktarılır. Renk dokusu kodla bağlanır (ModelPalette).
Çalıştırma: ARCH_GLB, ARCH_FBX, ARCH_TEX, ARCH_BLEND, ARCH_PREVIEW ve karakter ölçeği için ARCH_WIZARD ortam değişkenleriyle
blender -b -P convert_archway.py. Sonuç ARCH_PREVIEW/archway_log.txt'ye yazılır.
"""
import math
import os
import random
import traceback

import bmesh
import bpy
from mathutils import Matrix, Vector

GLB = os.environ["ARCH_GLB"]
FBX = os.environ["ARCH_FBX"]
TEX = os.environ["ARCH_TEX"]
BLEND = os.environ["ARCH_BLEND"]
PREVIEW = os.environ["ARCH_PREVIEW"]
WIZARD = os.environ.get("ARCH_WIZARD")

SCALE = 1.25 / 1.5  # Modelin ayaklarının ortası x = ±1.5'te
OPENING = 1.3
TARGET_TRIS = 10000  # Kum altı silinince ~9300 kalır. 6000'e inince taşların yüzeyi kırışıyor, o yüzden sadeleştirilmez.
SEAM_GUARD = 100.0
TEX_SIZE = 1024
TINT = (1.0, 0.85, 0.72)  # Açık taş rengi kumla karışmasın diye diğer engellerin kumtaşına yaklaştırılır.
GROUND = (0.85, 0.75, 0.55)
SKY = (0.65, 0.82, 0.95)

lines = []


def log(text):
    lines.append(str(text))
    os.makedirs(PREVIEW, exist_ok=True)
    with open(os.path.join(PREVIEW, "archway_log.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def activate(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def tris(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def color_material(name, rgb):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*(c ** 2.2 for c in rgb), 1.0)
    return mat


def place_on_ground(mesh):
    """Eşit ölçekler, kemerin altı OPENING'de kalacak kadar kuma gömer, gömülen kısmı siler."""
    mesh.data.transform(Matrix.Scale(SCALE, 4))
    keystone = [v.co.z for v in mesh.data.vertices if abs(v.co.x) < 0.1 and v.co.z > 1.2]
    sink = min(keystone) - OPENING
    mesh.data.transform(Matrix.Translation((0, 0, -sink)))
    log("kemerin altı ölçekte %.3f, gömülen %.3f" % (min(keystone), sink))

    original = mesh.copy()
    original.data = mesh.data.copy()
    bpy.context.scene.collection.objects.link(original)

    bm = bmesh.new()
    bm.from_mesh(mesh.data)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-5,
                           plane_co=(0, 0, -0.03), plane_no=(0, 0, -1), clear_outer=True)
    bm.to_mesh(mesh.data)
    bm.free()
    log("kum altı silindi: %d üçgen" % tris(mesh))
    return original


def decimate(mesh, original):
    bm = bmesh.new()
    bm.from_mesh(mesh.data)
    uv = bm.loops.layers.uv.active
    seam = set()
    for e in bm.edges:
        if len(e.link_loops) != 2:
            seam.update(v.index for v in e.verts)
            continue
        a, b = e.link_loops
        if (a[uv].uv - b.link_loop_next[uv].uv).length > 1e-5 or (a.link_loop_next[uv].uv - b[uv].uv).length > 1e-5:
            seam.update(v.index for v in e.verts)
    bm.free()
    group = mesh.vertex_groups.new(name="UVSeams")
    group.add(list(seam), 1.0, "REPLACE")

    activate(mesh)
    if tris(mesh) > TARGET_TRIS:
        dec = mesh.modifiers.new("Decimate", "DECIMATE")
        dec.ratio = TARGET_TRIS / tris(mesh)
        dec.use_collapse_triangulate = True
        dec.vertex_group = "UVSeams"
        dec.invert_vertex_group = True
        dec.vertex_group_factor = SEAM_GUARD
        bpy.ops.object.modifier_apply(modifier=dec.name)
    mesh.vertex_groups.remove(mesh.vertex_groups["UVSeams"])
    bpy.ops.object.shade_smooth()
    transfer = mesh.modifiers.new("Normals", "DATA_TRANSFER")
    transfer.object = original
    transfer.use_loop_data = True
    transfer.data_types_loops = {"CUSTOM_NORMAL"}
    transfer.loop_mapping = "POLYINTERP_NEAREST"
    bpy.ops.object.modifier_apply(modifier=transfer.name)
    bpy.data.objects.remove(original, do_unlink=True)
    log("dikiş noktası %d, sadeleşmiş %d üçgen" % (len(seam), tris(mesh)))


def setup_texture(mesh):
    """Unity'deki gibi yalnız renk dokusu kalır; doku küçültülüp kaydedilir."""
    mat = mesh.material_slots[0].material
    bsdf = next(n for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    for name in ("Normal", "Metallic", "Roughness"):
        for link in list(bsdf.inputs[name].links):
            mat.node_tree.links.remove(link)
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Roughness"].default_value = 0.6
    image = bsdf.inputs["Base Color"].links[0].from_node.image
    image.scale(TEX_SIZE, TEX_SIZE)
    pixels = list(image.pixels)
    for i, value in enumerate(pixels):
        if i % 4 != 3:
            pixels[i] = value * TINT[i % 4]
    image.pixels = pixels
    os.makedirs(os.path.dirname(TEX), exist_ok=True)
    image.filepath_raw = TEX
    image.file_format = "PNG"
    image.save()
    mat.name = "Archway"
    mesh.name = "Archway_Body"
    mesh.data.name = "Archway_Body"


def mound(name, x, rx, ry, height, seed):
    """Ayakların dibini kuma gömen alçak tümsek (geçidin içine taşmaz)."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    segs = 10
    outer, mid = [], []
    for i in range(segs):
        a = 2 * math.pi * i / segs
        s = rnd.uniform(0.88, 1.0)
        outer.append(bm.verts.new((x + rx * s * math.cos(a), ry * s * math.sin(a), -0.02)))
        mid.append(bm.verts.new((x + rx * 0.6 * s * math.cos(a), ry * 0.6 * s * math.sin(a), height * rnd.uniform(0.7, 0.9))))
    top = bm.verts.new((x, 0, height))
    for i in range(segs):
        j = (i + 1) % segs
        bm.faces.new((outer[i], outer[j], mid[j], mid[i]))
        bm.faces.new((mid[i], mid[j], top))
    center = Vector((x, 0, -1))
    bm.normal_update()
    for face in bm.faces:
        if face.normal.dot(face.calc_center_median() - center) < 0:
            face.normal_flip()
    data = bpy.data.meshes.new(name)
    bm.to_mesh(data)
    bm.free()
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    data.materials.append(color_material("Dune", GROUND))
    return obj


def measure(mesh):
    points = [v.co for v in mesh.data.vertices]
    log("sınırlar x %.2f..%.2f  y %.2f..%.2f  z %.2f..%.2f" % (
        min(p.x for p in points), max(p.x for p in points), min(p.y for p in points), max(p.y for p in points),
        min(p.z for p in points), max(p.z for p in points)))
    for z0, z1 in ((0.0, 0.3), (0.3, 0.6), (0.6, 0.9), (0.9, 1.2), (1.2, 1.5), (1.5, 1.8), (1.8, 2.1)):
        row = [p.x for p in points if z0 <= p.z < z1]
        if row:
            inner = min((abs(x) for x in row), default=0.0)
            log("z %.1f..%.1f: dış %.2f..%.2f, geçide en yakın |x| %.2f" % (z0, z1, min(row), max(row), inner))
    # Kayan kapsül (±0.5 genişlik, tepesi 0.9) ve ayaktaki kapsül (tepesi 1.5) geçitte neye değer?
    low = [p.z for p in points if abs(p.x) < 0.5]
    log("|x|<0.5 içindeki en alçak taş: %.2f" % min(low))


def copy_of(meshes, location, scale=1.0, rot_z=0.0):
    root = bpy.data.objects.new("Kopya", None)
    bpy.context.scene.collection.objects.link(root)
    root.location = location
    root.scale = (scale, scale, scale)
    root.rotation_euler = (0, 0, math.radians(rot_z))
    for obj in meshes:
        copy = obj.copy()
        bpy.context.scene.collection.objects.link(copy)
        copy.parent = root
        copy.matrix_parent_inverse = Matrix.Identity(4)
        copy.matrix_basis = obj.matrix_world.copy()
        copy.hide_render = False


def previews(parts):
    scene = bpy.context.scene
    for obj in parts:
        obj.hide_render = True
    character = []
    character_scale = 1.0
    if WIZARD:
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=WIZARD)
        character = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
        for obj in bpy.data.objects:
            if obj not in before:
                obj.hide_render = True
        bpy.context.view_layer.update()
        pink = color_material("Karakter", (0.9, 0.45, 0.6))
        for obj in character:
            obj.data.materials.clear()
            obj.data.materials.append(pink)
        top = max((o.matrix_world @ v.co).z for o in character for v in o.data.vertices)
        character_scale = 1.51 / top

    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 16
    scene.view_settings.view_transform = "Standard"
    scene.world = bpy.data.worlds.new("Sky")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (*(c ** 2.2 for c in SKY), 1.0)
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy = 2.2
    sun.data.angle = math.radians(2.0)
    bpy.context.scene.collection.objects.link(sun)
    sun.rotation_euler = Vector((0.32, -0.56, -0.77)).to_track_quat("-Z", "Y").to_euler()

    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector((8.5, 120, 0.1)), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector((0, -50, -0.05)), verts=bm.verts)
    data = bpy.data.meshes.new("Zemin")
    bm.to_mesh(data)
    bm.free()
    floor = bpy.data.objects.new("Zemin", data)
    bpy.context.scene.collection.objects.link(floor)
    data.materials.append(color_material("Zemin", GROUND))

    def shoot(name, size, location, target, fov_y):
        scene.render.resolution_x, scene.render.resolution_y = size
        cam_data = bpy.data.cameras.new("Cam")
        cam_data.sensor_fit = "VERTICAL"
        cam_data.angle_y = math.radians(fov_y)
        cam_data.clip_end = 500.0
        cam = bpy.data.objects.new("Cam", cam_data)
        bpy.context.scene.collection.objects.link(cam)
        cam.location = location
        cam.rotation_euler = (Vector(target) - Vector(location)).to_track_quat("-Z", "Y").to_euler()
        scene.camera = cam
        scene.render.filepath = os.path.join(PREVIEW, name + ".png")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(cam)

    # Unity (x, y, z) burada (-x, -z, y). Karakter ve kemer yakından, sonra iki oyun kamerasından.
    copy_of(parts, (0, 0, 0))
    if character:
        copy_of(character, (0, 1.2, 0), character_scale, 180)
    shoot("kemer_yakin", (900, 640), (1.6, 6.5, 1.5), (0, 0, 0.95), 30)
    copy_of(parts, (0, -10, 0))
    copy_of(parts, (0, -20, 0))
    copy_of(parts, (2.5, -20, 0))
    copy_of(parts, (-2.5, -35, 0))
    shoot("kemer_dikey", (540, 960), (0, 6.5, 4.5), (0, -5.1, 1.0), 60)
    shoot("kemer_yatay", (960, 414), (0, 6.5, 2.5), (0, -18.5, 2.5 - 25.0 * math.tan(math.radians(2.37))), 60)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=GLB)
    bpy.context.view_layer.update()
    mesh = next(o for o in bpy.data.objects if o.type == "MESH")
    world = mesh.matrix_world.copy()
    mesh.parent = None
    mesh.matrix_world = Matrix.Identity(4)
    mesh.data.transform(world)
    for obj in [o for o in bpy.data.objects if o.type == "EMPTY"]:
        bpy.data.objects.remove(obj)
    log("girdi: %d üçgen" % tris(mesh))

    original = place_on_ground(mesh)
    decimate(mesh, original)
    setup_texture(mesh)
    measure(mesh)
    parts = [mesh, mound("Dune_DecorA", -1.35, 0.55, 0.5, 0.14, 1), mound("Dune_DecorB", 1.35, 0.55, 0.5, 0.14, 2)]
    bpy.context.view_layer.update()

    bpy.ops.object.select_all(action="DESELECT")
    for obj in parts:
        obj.select_set(True)
    os.makedirs(os.path.dirname(FBX), exist_ok=True)
    bpy.ops.export_scene.fbx(
        filepath=FBX, use_selection=True, object_types={"MESH", "EMPTY"},
        apply_unit_scale=True, bake_space_transform=True, axis_forward="-Z", axis_up="Y",
        mesh_smooth_type="FACE", add_leaf_bones=False, path_mode="STRIP",
    )
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    previews(parts)
    log("bitti")


try:
    main()
except Exception:
    log(traceback.format_exc())
