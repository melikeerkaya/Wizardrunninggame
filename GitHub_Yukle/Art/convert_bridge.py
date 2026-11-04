"""
Köprü parçası (plank-bridge-segment.glb) -> Resources/Models/Desert/BridgeDeck.fbx ve BridgeDeck_basecolor.png.
Model bir kişilik dar bir köprüdür, oyunun yolu 8.5 birim geniştir. Bu yüzden dokuz dilim gibi esnetilir:
- Tahtalar x yönünde yolun genişliğine uzatılır; kenardaki direk ve halatlar ölçekte kalır, yolun dışında durur.
- Parçanın boyu tam BRIDGE_LENGTH'tir (yol parçasına 7 tane sığar), art arda dikişsiz dizilir.
- Güvertenin üstü y=0'dadır (oyuncu yürür), direklerin alt ucu aşağıdaki vadinin suyuna kadar uzatılır.
Örgü sadeleştirilir, normaller yeniden hesaplanır; renk dokusu kodla bağlanır (ModelPalette).
Çalıştırma: BRIDGE_GLB, BRIDGE_FBX, BRIDGE_TEX, BRIDGE_PREVIEW ortam değişkenleriyle blender -b -P convert_bridge.py
"""
import math
import os
import traceback

import bpy
from mathutils import Matrix, Vector

GLB = os.environ["BRIDGE_GLB"]
FBX = os.environ["BRIDGE_FBX"]
TEX = os.environ["BRIDGE_TEX"]
PREVIEW = os.environ["BRIDGE_PREVIEW"]

BRIDGE_LENGTH = 30.0 / 7.0
ROAD_EDGE = 4.35  # Yolun yarı genişliği (4.25) ve tahtaların ondan biraz taşan payı
INNER_X = 0.66  # Bu genişliğe kadar yalnız tahta vardır, esneyen dilim budur
LEG_END = -6.0  # Direklerin alt ucu (suyun altı)
LEG_Z = 0.2  # Modelde bu yüksekliğin altında yalnız direkler kalır
TARGET_TRIS = 1500
TEX_SIZE = 1024

lines = []


def log(text):
    lines.append(str(text))
    os.makedirs(PREVIEW, exist_ok=True)
    with open(os.path.join(PREVIEW, "bridge_log.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def tris(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


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
    log("girdi %d üçgen" % tris(mesh))
    # Güvertenin üstü: halatların başladığı yüksekliğin (~0.74) altındaki en yüksek nokta; direklerin içindekiler sayılmaz.
    deck = max(v.co.z for v in mesh.data.vertices if v.co.z < 0.7 and abs(v.co.x) < 0.7)
    planks = [abs(v.co.x) for v in mesh.data.vertices if abs(v.co.z - deck) < 0.03]
    log("güverte üstü z=%.3f, tahta yarı genişliği %.3f" % (deck, max(planks)))

    # Sadeleştirme esnetmeden önce yapılır: yoksa uzayan tahtalarda küçük hata büyür.
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = mesh
    dec = mesh.modifiers.new("Decimate", "DECIMATE")
    dec.ratio = TARGET_TRIS / tris(mesh)
    dec.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=dec.name)
    log("sade %d üçgen" % tris(mesh))

    vertices = mesh.data.vertices
    legs = [v.co for v in vertices if v.co.z < LEG_Z]
    log("bacak noktası %d, en küçük |x| %.3f" % (len(legs), min(abs(p.x) for p in legs)))
    ys = [v.co.y for v in vertices]
    length = max(ys) - min(ys)
    scale = BRIDGE_LENGTH / length
    stretch = ROAD_EDGE / INNER_X
    leg_top = (LEG_Z - deck) * scale
    for v in vertices:
        x, y, z = v.co
        side = -1.0 if x < 0 else 1.0
        ax = abs(x)
        nx = ax * stretch if ax <= INNER_X else ROAD_EDGE + (ax - INNER_X) * scale
        nz = (z - deck) * scale if z >= LEG_Z else LEG_END + (leg_top - LEG_END) * (z / LEG_Z)
        v.co = Vector((side * nx, y * scale, nz))
    mesh.data.update()

    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))

    material = mesh.material_slots[0].material
    bsdf = next(n for n in material.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    for socket in ("Normal", "Metallic", "Roughness"):
        for link in list(bsdf.inputs[socket].links):
            material.node_tree.links.remove(link)
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Roughness"].default_value = 0.7
    image = bsdf.inputs["Base Color"].links[0].from_node.image
    image.scale(TEX_SIZE, TEX_SIZE)
    os.makedirs(os.path.dirname(TEX), exist_ok=True)
    image.filepath_raw = TEX
    image.file_format = "PNG"
    image.save()
    material.name = "BridgeDeck"
    mesh.name = "BridgeDeck_Body"
    mesh.data.name = "BridgeDeck_Body"
    bpy.context.view_layer.update()

    points = [v.co for v in mesh.data.vertices]
    log("sonuç %d üçgen, x %.2f..%.2f  y %.2f..%.2f  z %.2f..%.2f" % (
        tris(mesh), min(p.x for p in points), max(p.x for p in points), min(p.y for p in points), max(p.y for p in points),
        min(p.z for p in points), max(p.z for p in points)))

    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    os.makedirs(os.path.dirname(FBX), exist_ok=True)
    bpy.ops.export_scene.fbx(
        filepath=FBX, use_selection=True, object_types={"MESH"},
        apply_unit_scale=True, bake_space_transform=True, axis_forward="-Z", axis_up="Y",
        mesh_smooth_type="FACE", add_leaf_bones=False, path_mode="STRIP",
    )
    log("bitti")


try:
    main()
except Exception:
    log(traceback.format_exc())
