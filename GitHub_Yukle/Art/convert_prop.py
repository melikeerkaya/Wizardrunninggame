"""
Tripo'dan gelen hazır nesneleri (GLB) oyuna çevirir: Resources/Models altında <Ad>.fbx ve <Ad>_basecolor.png.
  Broom     - witch-broom.glb. Yerdeki süpürge ve uçuştaki süpürge (build_broom.py'deki eski süpürgenin boyunda, 3 birim).
              Sap oyunda koşu yönüne (+Z), süpürge çalısı geriye bakar: FBX dışa aktarımı Blender'daki -Y'yi Unity'de +Z yapar.
  SpellBook - spell-book.glb. Yoldaki toplanabilir kristalin görünüşü: dik duran, ~0.85 boyunda, kendi ekseninde döner.
  Desert/Scenery altındakiler - çöl yol kenarı süsleri: kemer, duvar, devrik sütun, sütun kütüğü ve üç kaktüs.
Aynı anda çok sayıda görünenler sadeleştirilir, normaller asıl örgüden aktarılır.
Renk dokusu kodla bağlanır (ModelPalette), normal haritası kullanılmaz.
Çalıştırma: PROP_SRC (GLB klasörü), PROP_OUT (Resources/Models), PROP_PREVIEW ve karakter ölçeği için PROP_WIZARD ortam
değişkenleriyle blender -b -P convert_prop.py. Sonuç PROP_PREVIEW/prop_log.txt'ye yazılır.
"""
import math
import os
import traceback

import bpy
from mathutils import Matrix, Vector

SRC = os.environ["PROP_SRC"]
OUT = os.environ["PROP_OUT"]
PREVIEW = os.environ["PROP_PREVIEW"]
WIZARD = os.environ.get("PROP_WIZARD")

IDENTITY = Matrix.Identity(4)
WARM = (1.0, 0.85, 0.72)  # Açık taşlar kumla karışmasın, kemerle aynı kumtaşına yaklaşsın
SCENERY = "Desert/Scenery"
# Ad, dosya, dönüş (GLB -> oyun yönü), hedef ölçü (uzun eksen), doku boyutu, hedef üçgen sayısı (0 = sadeleştirme yok),
# klasör, taban zeminde mi (değilse merkez orijinde), doku tonu
PROPS = (
    ("Broom", "witch-broom.glb", Matrix.Rotation(math.radians(90), 4, "Z"), 3.0, 1024, 0, "", False, None),
    ("SpellBook", "spell-book.glb", Matrix.Rotation(math.radians(180), 4, "Z") @ Matrix.Rotation(math.radians(90), 4, "X"),
     0.85, 512, 2000, "", False, None),
    # Yol kenarı süsleri (bkz. DesertScenery.cs): çarpışmaları yoktur, tabanları zeminde durur.
    ("SceneArch", "ruin-archway.glb", IDENTITY, 6.0, 1024, 3000, SCENERY, True, WARM),
    ("SceneWall", "ruin-wall-segment.glb", IDENTITY, 4.4, 1024, 2500, SCENERY, True, WARM),
    ("SceneColumns", "fallen-column-segments.glb", IDENTITY, 5.8, 1024, 3000, SCENERY, True, WARM),
    ("SceneStump", "broken-column-stump.glb", IDENTITY, 3.3, 1024, 2500, SCENERY, True, WARM),
    ("Cactus", "cactus.glb", IDENTITY, 1.6, 512, 1200, SCENERY, True, None),
    ("BarrelCactus", "barrel-cactus.glb", IDENTITY, 0.7, 512, 800, SCENERY, True, None),
    ("PricklyPear", "prickly-pear.glb", IDENTITY, 1.0, 512, 1000, SCENERY, True, None),
    # Köprü bölümünün süsleri: girişteki ahşap çit ve vadi kıyısındaki palmiyeler.
    ("Palisade", "wooden-palisade.glb", IDENTITY, 5.0, 512, 1500, SCENERY, True, None),
    ("Palm", "palm-tree.glb", IDENTITY, 7.0, 1024, 2000, SCENERY, True, None),
)
ONLY = os.environ.get("PROP_ONLY", "")  # Yalnız bu klasördekileri çevir; boşsa hepsi

lines = []


def log(text):
    lines.append(str(text))
    os.makedirs(PREVIEW, exist_ok=True)
    with open(os.path.join(PREVIEW, "prop_log.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def activate(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def tris(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def box(obj):
    points = [v.co for v in obj.data.vertices]
    return (Vector([min(p[i] for p in points) for i in range(3)]), Vector([max(p[i] for p in points) for i in range(3)]))


def simplify(mesh, target):
    original = mesh.copy()
    original.data = mesh.data.copy()
    bpy.context.scene.collection.objects.link(original)
    activate(mesh)
    dec = mesh.modifiers.new("Decimate", "DECIMATE")
    dec.ratio = target / tris(mesh)
    dec.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=dec.name)
    bpy.ops.object.shade_smooth()
    transfer = mesh.modifiers.new("Normals", "DATA_TRANSFER")
    transfer.object = original
    transfer.use_loop_data = True
    transfer.data_types_loops = {"CUSTOM_NORMAL"}
    transfer.loop_mapping = "NEAREST_POLYNOR"
    bpy.ops.object.modifier_apply(modifier=transfer.name)
    bpy.data.objects.remove(original, do_unlink=True)


def convert(name, file, rotation, length, tex_size, target, folder, on_ground, tint):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=os.path.join(SRC, file))
    bpy.context.view_layer.update()
    # Dosyada birden çok örgü varsa asıl model en büyüğüdür; yanındaki küçük parçalar alınmaz.
    mesh = max((o for o in bpy.data.objects if o.type == "MESH"), key=lambda o: len(o.data.vertices))
    world = mesh.matrix_world.copy()
    mesh.parent = None
    mesh.matrix_world = Matrix.Identity(4)
    mesh.data.transform(world)
    for obj in [o for o in bpy.data.objects if o is not mesh]:
        bpy.data.objects.remove(obj)
    before = tris(mesh)

    mesh.data.transform(rotation)
    lo, hi = box(mesh)
    center = (lo + hi) / 2
    if on_ground:
        center.z = lo.z
    mesh.data.transform(Matrix.Scale(length / max(hi - lo), 4) @ Matrix.Translation(-center))
    if target > 0:
        simplify(mesh, target)

    material = mesh.material_slots[0].material
    bsdf = next(n for n in material.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    for socket in ("Normal", "Metallic", "Roughness"):
        for link in list(bsdf.inputs[socket].links):
            material.node_tree.links.remove(link)
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Roughness"].default_value = 0.6
    image = bsdf.inputs["Base Color"].links[0].from_node.image
    image.scale(tex_size, tex_size)
    if tint:
        pixels = list(image.pixels)
        for i, value in enumerate(pixels):
            if i % 4 != 3:
                pixels[i] = value * tint[i % 4]
        image.pixels = pixels
    out_dir = os.path.join(OUT, folder)
    os.makedirs(out_dir, exist_ok=True)
    image.filepath_raw = os.path.join(out_dir, name + "_basecolor.png")
    image.file_format = "PNG"
    image.save()
    material.name = name
    mesh.name = name + "_Body"
    mesh.data.name = name + "_Body"
    bpy.context.view_layer.update()

    lo, hi = box(mesh)
    log("%s: %d -> %d üçgen, x %.2f..%.2f  y %.2f..%.2f  z %.2f..%.2f" % (name, before, tris(mesh), lo.x, hi.x, lo.y, hi.y, lo.z, hi.z))

    activate(mesh)
    bpy.ops.export_scene.fbx(
        filepath=os.path.join(out_dir, name + ".fbx"), use_selection=True, object_types={"MESH"},
        apply_unit_scale=True, bake_space_transform=True, axis_forward="-Z", axis_up="Y",
        mesh_smooth_type="FACE", add_leaf_bones=False, path_mode="STRIP",
    )
    render_close(name, mesh, hi - lo)


def camera(scene, location, target, lens, size):
    scene.render.resolution_x, scene.render.resolution_y = size
    data = bpy.data.cameras.new("Cam")
    data.lens = lens
    data.clip_end = 500.0
    cam = bpy.data.objects.new("Cam", data)
    scene.collection.objects.link(cam)
    cam.location = location
    cam.rotation_euler = (Vector(target) - Vector(location)).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam


def lighting(scene):
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 16
    scene.view_settings.view_transform = "Standard"
    scene.world = bpy.data.worlds.new("Sky")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.38, 0.63, 0.89, 1.0)
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy = 2.2
    scene.collection.objects.link(sun)
    sun.rotation_euler = Vector((0.32, -0.56, -0.77)).to_track_quat("-Z", "Y").to_euler()


def render_close(name, mesh, size):
    """Oyuncunun gördüğü yön: Blender +Y yüzü."""
    scene = bpy.context.scene
    lighting(scene)
    r = size.length * 2.2
    camera(scene, Vector((0.5, 1.0, 0.35)).normalized() * r, (0, 0, 0), 50, (700, 560))
    scene.render.filepath = os.path.join(PREVIEW, name + "_yakin.png")
    bpy.ops.render.render(write_still=True)


def render_scene():
    """Karakterin yanında oyundaki boylarıyla: arkadan, oyun kamerasına yakın."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    lighting(scene)
    bpy.ops.import_scene.fbx(filepath=WIZARD)
    bpy.context.view_layer.update()
    pink = bpy.data.materials.new("Karakter")
    pink.use_nodes = True
    pink.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.08, 0.1, 0.35, 1.0)
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            obj.data.materials.clear()
            obj.data.materials.append(pink)
    wizard_root = bpy.data.objects.new("KarakterKok", None)
    scene.collection.objects.link(wizard_root)
    wizard_root.scale = (0.8, 0.8, 0.8)
    for obj in bpy.data.objects:
        if obj.parent is None and obj is not wizard_root:
            obj.parent = wizard_root

    def prop(name, location, scale, rot_z=0.0):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=os.path.join(OUT, name + ".fbx"))
        new = [o for o in bpy.data.objects if o not in before]
        image = bpy.data.images.load(os.path.join(OUT, name + "_basecolor.png"), check_existing=True)
        material = bpy.data.materials.new(name + "Tex")
        material.use_nodes = True
        node = material.node_tree.nodes.new("ShaderNodeTexImage")
        node.image = image
        material.node_tree.links.new(node.outputs["Color"], material.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
        holder = bpy.data.objects.new("Kok", None)
        scene.collection.objects.link(holder)
        holder.location = location
        holder.scale = (scale, scale, scale)
        holder.rotation_euler = (0, 0, math.radians(rot_z))
        for obj in new:
            if obj.parent is None:
                obj.parent = holder
            if obj.type == "MESH":
                obj.data.materials.clear()
                obj.data.materials.append(material)

    # Unity (x, y, z) burada (-x, -z, y)
    for z in (5.0, 6.6, 8.2):
        prop("SpellBook", (0, -z, 1.0), 1.0)
    prop("Broom", (2.5, -9.0, 1.2), 0.8, 40)
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, -20, 0))
    floor = bpy.context.active_object
    floor.scale = (8.5, 70, 1)
    sand = bpy.data.materials.new("Kum")
    sand.use_nodes = True
    sand.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.7, 0.53, 0.27, 1.0)
    floor.data.materials.append(sand)
    camera(scene, (0, 5.3, 2.5), (0, -19.7, 1.46), 28, (960, 540))
    scene.render.filepath = os.path.join(PREVIEW, "sahne.png")
    bpy.ops.render.render(write_still=True)


def main():
    for prop in PROPS:
        if not ONLY or prop[6] == ONLY:
            convert(*prop)
    if WIZARD:
        render_scene()
    log("bitti")


try:
    main()
except Exception:
    log(traceback.format_exc())
