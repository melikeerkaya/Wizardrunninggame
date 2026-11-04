"""
Tripo'dan gelen iskeletli karakter (GLB) → Unity için FBX. Malzeme ve doku adları CHAR_NAME'den gelir.
- Fazladan nesneleri (Icosphere) ve Tripo'nun kendi animasyonlarını atar.
- Kemikleri Mixamo adlarına çevirir (Unity Humanoid eşlemesi kesin tutsun, Mixamo animasyonları oynasın).
  Tripo'da omurga sırası terstir: Hips → Spine02 → Spine01 → Spine.
- Kolları T duruşuna getirip bu duruşu dinlenme duruşu yapar (Humanoid animasyonları T duruşuna göre aktarır).
- 300 bin üçgeni WITCH_RATIO oranında sadeleştirir (ağırlıklar korunur). Tripo'nun doku yerleşimi çok parçalı olduğu için
  doğrudan sadeleştirmek yüzde doku yamaları bırakır; bu yüzden sade örgüye yeni UV açılır ve asıl örgünün rengi ile yüzey
  detayı (normal) Cycles ile WITCH_TEX_SIZE boyutlu yeni dokulara pişirilir.
- Renk ve normal dokularını PNG olarak WITCH_TEX klasörüne yazar, malzemeyi CHAR_NAME adıyla dışa aktarır.
- Kolları indirip bacakları açarak bir de koşu duruşu önizlemesi çizer: örgüdeki yırtıklar ancak hareket halinde görünür.
Çalıştırma: GLB_SRC, WITCH_FBX, WITCH_TEX, WITCH_PREVIEW, CHAR_NAME (ve isteğe bağlı WITCH_RATIO) ortam değişkenleriyle
blender -b -P convert_witch.py. Sonuç WITCH_PREVIEW/witch_log.txt dosyasına yazılır.
"""
import math
import os
import traceback

import bpy
from mathutils import Matrix, Vector

SRC = os.environ["GLB_SRC"]
FBX_PATH = os.environ["WITCH_FBX"]
TEX_DIR = os.environ["WITCH_TEX"]
PREVIEW_DIR = os.environ["WITCH_PREVIEW"]
NAME = os.environ.get("CHAR_NAME", "Witch")
RATIO = float(os.environ.get("WITCH_RATIO", "0.12"))
TEX_SIZE = int(os.environ.get("WITCH_TEX_SIZE", "2048"))
# "seams": asıl dokuyu koruyarak sadeleştir (dikiş noktaları korunur). "bake": yeni UV'ye pişir (bu modelin iç içe
# katmanları yüzünden yamalı çıktı, denemek için duruyor).
MODE = os.environ.get("WITCH_MODE", "seams")
# Dikiş noktalarını birleştirmenin ek maliyeti (Decimate "Weight"). Büyük değer = dikişler daha sıkı korunur.
SEAM_GUARD = float(os.environ.get("WITCH_SEAM_GUARD", "100"))
# Giysi ile altındaki beden arasındaki bu kadar (metre) dar boşluklarda beden yüzeyi silinir (0 = kapalı).
SKIN_GAP = float(os.environ.get("WITCH_SKIN_GAP", "0.004"))

RENAME = {
    "Hips": "Hips", "Spine02": "Spine", "Spine01": "Spine1", "Spine": "Spine2", "neck": "Neck", "Head": "Head",
    "head_end": "HeadTop_End",
}
for side in ("Left", "Right"):
    for part in ("Shoulder", "Arm", "ForeArm", "Hand", "UpLeg", "Leg", "Foot", "ToeBase"):
        RENAME[side + part] = side + part

lines = []


def activate(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def remove_covered_skin(mesh, arm):
    """Giysinin hemen altında kalan beden yüzeylerini siler. Dışa bakan (kemik ekseninden uzağa yönelen) bir yüzün
    SKIN_GAP kadar önünde başka bir yüzey varsa o yüz dışarıdan görünmez; koşarken eklem yerlerinde giysinin içinden
    çıkıp titreşir. Baş (yüz, saç, şapka) ve eller korunur. Örgü ve iskelet bu noktada dünya eksenlerindedir."""
    import bmesh
    from mathutils.bvhtree import BVHTree
    from mathutils.geometry import intersect_point_line

    segments = {}
    for bone in arm.data.bones:
        head = arm.matrix_world @ bone.head_local
        end = arm.matrix_world @ bone.children[0].head_local if bone.children else head
        segments[bone.name] = (head, end)
    names = {g.index: g.name for g in mesh.vertex_groups}
    protected = ("Neck", "Head", "HeadTop_End", "Hand")

    bm = bmesh.new()
    bm.from_mesh(mesh.data)
    bm.faces.ensure_lookup_table()
    bm.normal_update()
    deform = bm.verts.layers.deform.active
    tree = BVHTree.FromBMesh(bm)
    doomed = []
    for f in bm.faces:
        weights = {}
        for v in f.verts:
            for index, w in v[deform].items():
                weights[index] = weights.get(index, 0.0) + w
        if not weights:
            continue
        bone = names.get(max(weights, key=weights.get), "")
        if bone not in segments or bone.endswith(protected) or not bone.startswith("mixamorig:"):
            continue
        c = f.calc_center_median()
        a, b = segments[bone]
        axis = a
        if (b - a).length > 1e-6:
            t = min(max(intersect_point_line(c, a, b)[1], 0.0), 1.0)
            axis = a.lerp(b, t)
        if f.normal.dot(c - axis) <= 0:
            continue
        hit = tree.ray_cast(c + f.normal * 0.0003, f.normal, SKIN_GAP)
        if hit[2] is not None and hit[2] != f.index:
            doomed.append(f)
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    bm.to_mesh(mesh.data)
    bm.free()
    lines.append("removed %d covered skin faces (gap < %.3f m)" % (len(doomed), SKIN_GAP))


def decimate_keep_uv(mesh):
    """Doku dikişlerindeki (UV ada kenarları) noktaları koruyarak sadeleştirir; asıl doku aynen kullanılır.
    glTF'ten gelen özel normaller sadeleştirmeden sonra parlama izleri bıraktığı için silinir, yüzey yumuşak gölgelenir."""
    import bmesh

    bm = bmesh.new()
    bm.from_mesh(mesh.data)
    uv = bm.loops.layers.uv.active
    seam = set()
    for e in bm.edges:
        if len(e.link_loops) != 2:
            seam.update(v.index for v in e.verts)
            continue
        a, b = e.link_loops
        # İki yüzdeki aynı noktanın UV'si; komşu yüzde kenar ters yönde dolaşılır
        if (a[uv].uv - b.link_loop_next[uv].uv).length > 1e-5 or (a.link_loop_next[uv].uv - b[uv].uv).length > 1e-5:
            seam.update(v.index for v in e.verts)
    bm.free()
    group = mesh.vertex_groups.new(name="UVSeams")
    group.add(list(seam), 1.0, "REPLACE")

    # Asıl örgünün yumuşak normalleri sadeleştirmeden sonra geri aktarılır (yoksa yüzeyde parlak çizgiler kalır).
    original = mesh.copy()
    original.data = mesh.data.copy()
    bpy.context.scene.collection.objects.link(original)

    activate(mesh)
    dec = mesh.modifiers.new("Decimate", "DECIMATE")
    dec.ratio = RATIO
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
    lines.append("uv seam vertices=%d, decimated to %d tris" % (len(seam), sum(len(p.vertices) - 2 for p in mesh.data.polygons)))
    return mesh


def bake_low_poly(high):
    """Tripo'nun doku yerleşimi çok parçalı olduğu için örgüyü doğrudan sadeleştirmek dokuyu bozar. Bunun yerine:
    kopyayı sadeleştir, ona yeni UV aç, yüksek örgünün rengini ve yüzey detayını (normal) Cycles ile yeni dokulara pişir.
    Kemik ağırlıkları sadeleştirmede korunur. Yüksek örgü silinir, düşük örgü döndürülür."""
    scene = bpy.context.scene
    low = high.copy()
    low.data = high.data.copy()
    low.name = "witch"
    scene.collection.objects.link(low)
    activate(low)
    dec = low.modifiers.new("Decimate", "DECIMATE")
    dec.ratio = RATIO
    dec.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=dec.name)
    bpy.ops.mesh.customdata_custom_splitnormals_clear()
    bpy.ops.object.shade_smooth()
    while low.data.uv_layers:
        low.data.uv_layers.remove(low.data.uv_layers[0])
    low.data.uv_layers.new(name="UVMap")
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    # Sadeleştirme bazı üçgenleri ters çevirir: pişirmede siyah, oyunda delik olarak görünürler.
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003)
    bpy.ops.object.mode_set(mode="OBJECT")

    color = bpy.data.images.new(NAME + "_basecolor", TEX_SIZE, TEX_SIZE)
    normal = bpy.data.images.new(NAME + "_normal", TEX_SIZE, TEX_SIZE)
    normal.colorspace_settings.name = "Non-Color"
    mat = bpy.data.materials.new(NAME)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    color_node = nodes.new("ShaderNodeTexImage")
    color_node.image = color
    normal_node = nodes.new("ShaderNodeTexImage")
    normal_node.image = normal
    low.data.materials.clear()
    low.data.materials.append(mat)

    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 4
    bpy.ops.object.select_all(action="DESELECT")
    high.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    for node, kind in ((color_node, "DIFFUSE"), (normal_node, "NORMAL")):
        nodes.active = node
        bpy.ops.object.bake(type=kind, pass_filter={"COLOR"}, normal_space="TANGENT", use_selected_to_active=True,
                            cage_extrusion=0.02, max_ray_distance=0.06, margin=8)

    links.new(color_node.outputs["Color"], bsdf.inputs["Base Color"])
    normal_map = nodes.new("ShaderNodeNormalMap")
    links.new(normal_node.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = 0.6
    nodes.active = color_node
    bpy.data.objects.remove(high, do_unlink=True)
    lines.append("baked %dx%d colour and normal onto %d tris" % (TEX_SIZE, TEX_SIZE, sum(len(p.vertices) - 2 for p in low.data.polygons)))
    return low


def bounds(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in objs:
        ev = o.evaluated_get(dg)
        pts += [ev.matrix_world @ v.co for v in ev.data.vertices]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=SRC)
    for o in list(bpy.data.objects):
        if o.type != "ARMATURE" and not (o.type == "MESH" and o.parent is not None):
            bpy.data.objects.remove(o, do_unlink=True)
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    mesh = next(o for o in bpy.data.objects if o.type == "MESH")
    arm.animation_data_clear()
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
        pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()
    lines.append("source tris=%d" % sum(len(p.vertices) - 2 for p in mesh.data.polygons))

    for old, new in RENAME.items():
        bone = arm.data.bones.get(old)
        if bone is not None:
            bone.name = "mixamorig:" + new
    missing = [b.name for b in arm.data.bones if not b.name.startswith("mixamorig:")]
    groups = {g.name for g in mesh.vertex_groups}
    lines.append("not renamed: %s | vertex groups match bones: %s" % (
        missing, all(b.name in groups for b in arm.data.bones if b.use_deform and b.name.startswith("mixamorig:"))))

    # Kolları yatay (T) duruşa getir: önce üst kol, sonra ön kol, kemik başından döndürülür. Karakter -Y'ye bakar, sol kol +X'tedir.
    activate(arm)
    bpy.ops.object.mode_set(mode="POSE")
    for side, sign in (("Left", 1), ("Right", -1)):
        for upper, lower in (("Arm", "ForeArm"), ("ForeArm", "Hand")):
            pu = arm.pose.bones["mixamorig:%s%s" % (side, upper)]
            pl = arm.pose.bones["mixamorig:%s%s" % (side, lower)]
            d = (pl.head - pu.head).normalized()
            q = d.rotation_difference(Vector((sign, 0.0, 0.0)))
            h = pu.head.copy()
            pu.matrix = Matrix.Translation(h) @ q.to_matrix().to_4x4() @ Matrix.Translation(-h) @ pu.matrix
            bpy.context.view_layer.update()
    bpy.ops.object.mode_set(mode="OBJECT")

    # Duruşu örgüye uygula, sadeleştir, sonra aynı duruşu iskeletin dinlenme duruşu yap.
    activate(mesh)
    if mesh.data.shape_keys is not None:
        bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
    for mod in [m for m in mesh.modifiers if m.type == "ARMATURE"]:
        bpy.ops.object.modifier_apply(modifier=mod.name)
    if RATIO < 0.999:
        mesh = bake_low_poly(mesh) if MODE == "bake" else decimate_keep_uv(mesh)
    activate(arm)
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.select_all(action="SELECT")
    bpy.ops.pose.armature_apply(selected=False)
    bpy.ops.object.mode_set(mode="OBJECT")

    # Ölçeği (0.01) uygula: örgüyü ayır, ikisinin ölçeğini uygula, yeniden bağla.
    activate(mesh)
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    for obj in (arm, mesh):
        activate(obj)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    activate(mesh)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type="OBJECT", keep_transform=True)
    mod = mesh.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    bpy.context.view_layer.update()
    if SKIN_GAP > 0:
        remove_covered_skin(mesh, arm)

    lo, hi = bounds([mesh])
    head_top = (arm.matrix_world @ arm.data.bones["mixamorig:HeadTop_End"].head_local).z
    lines.append("result tris=%d  bounds lo=%s hi=%s  head top z=%.3f" % (
        sum(len(p.vertices) - 2 for p in mesh.data.polygons), tuple(round(v, 3) for v in lo), tuple(round(v, 3) for v in hi), head_top))
    for b in ("mixamorig:LeftArm", "mixamorig:LeftForeArm", "mixamorig:LeftHand", "mixamorig:RightHand"):
        lines.append("  %s rest head=%s" % (b, tuple(round(v, 3) for v in arm.matrix_world @ arm.data.bones[b].head_local)))

    # Dokular: renk ve normal PNG olarak; malzeme adı karakterin adı
    os.makedirs(TEX_DIR, exist_ok=True)
    material = mesh.data.materials[0]
    material.name = NAME
    for img in bpy.data.images:
        tag = "basecolor" if "basecolor" in img.name else "normal" if "normal" in img.name else None
        # Pişirme modunda yalnız pişirilen yeni dokular yazılır
        if tag is None or (MODE == "bake" and RATIO < 0.999 and not img.name.startswith(NAME + "_")):
            continue
        path = os.path.join(TEX_DIR, "%s_%s.png" % (NAME, tag))
        img.filepath_raw = path
        img.file_format = "PNG"
        img.save()
        lines.append("texture %s -> %s" % (img.name, path))

    # Önizleme: T duruşunda önden, yandan, arkadan
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "TEXTURE"
    scene.render.resolution_x, scene.render.resolution_y = 520, 600
    scene.world = bpy.data.worlds.new("W")
    scene.world.color = (0.25, 0.25, 0.28)
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    target = Vector((0, 0, (lo.z + hi.z) / 2))
    os.makedirs(PREVIEW_DIR, exist_ok=True)
    for name, loc in (("front", (0, -5.2, 1.0)), ("side", (5.2, 0, 1.0)), ("back", (0, 5.2, 1.2)), ("face", (0, -1.6, 1.42))):
        cam.location = loc
        look = Vector((0, 0, 1.4)) if name == "face" else target
        cam.data.lens = 70 if name == "face" else 50
        cam.rotation_euler = (look - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = os.path.join(PREVIEW_DIR, "%s_%s.png" % (NAME, name))
        bpy.ops.render.render(write_still=True)

    # Koşu duruşu: kollar aşağı, ön kollar bükük, bir bacak önde. Dışa aktarmadan önce geri alınır.
    activate(arm)
    bpy.ops.object.mode_set(mode="POSE")
    pose = (("LeftArm", "Y", 68), ("RightArm", "Y", -68), ("LeftForeArm", "X", -50), ("RightForeArm", "X", 50),
            ("LeftUpLeg", "X", -42), ("RightUpLeg", "X", 30), ("RightLeg", "X", 70), ("LeftLeg", "X", 25))
    for bone, axis, degrees in pose:
        pb = arm.pose.bones["mixamorig:" + bone]
        h = pb.head.copy()
        pb.matrix = Matrix.Translation(h) @ Matrix.Rotation(math.radians(degrees), 4, axis) @ Matrix.Translation(-h) @ pb.matrix
        bpy.context.view_layer.update()
    bpy.ops.object.mode_set(mode="OBJECT")
    for name, loc in (("pose_back", (0, 4.2, 1.5)), ("pose_side", (4.2, 1.2, 1.2))):
        cam.location = loc
        cam.data.lens = 70
        cam.rotation_euler = (target - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = os.path.join(PREVIEW_DIR, "%s_%s.png" % (NAME, name))
        bpy.ops.render.render(write_still=True)
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
        pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()

    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    mesh.select_set(True)
    os.makedirs(os.path.dirname(FBX_PATH), exist_ok=True)
    bpy.ops.export_scene.fbx(
        filepath=FBX_PATH, use_selection=True, object_types={"ARMATURE", "MESH"},
        apply_unit_scale=True, bake_space_transform=True, axis_forward="-Z", axis_up="Y",
        mesh_smooth_type="FACE", add_leaf_bones=False, bake_anim=False, use_armature_deform_only=False,
        path_mode="STRIP", embed_textures=False,
    )

    # Doğrulama: dışa aktarılan FBX'i yeniden aç, boyunu ve kemiklerini oku
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=FBX_PATH)
    arm2 = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    mesh2 = next(o for o in bpy.data.objects if o.type == "MESH")
    lo2, hi2 = bounds([mesh2])
    lines.append("reimported: armature scale=%s rot=%s bones=%d  bounds lo=%s hi=%s" % (
        tuple(round(v, 3) for v in arm2.scale), tuple(round(v, 3) for v in arm2.rotation_euler), len(arm2.data.bones),
        tuple(round(v, 3) for v in lo2), tuple(round(v, 3) for v in hi2)))
    return "OK"


try:
    lines.insert(0, main())
except Exception:
    lines.insert(0, "ERROR\n" + traceback.format_exc())
os.makedirs(PREVIEW_DIR, exist_ok=True)
with open(os.path.join(PREVIEW_DIR, "%s_log.txt" % NAME), "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
