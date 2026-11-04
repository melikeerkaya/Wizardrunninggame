"""
Çöl kumu dokusu: Resources/Models/Desert/Sand_basecolor.png. Rüzgârın çizdiği dalgalı kum izleri ve geniş ton lekeleri.
Her yöne kusursuz tekrar eder (bütün dalgalar dokunun boyuna tam katlıdır), oyunda 6 metrede bir tekrarlanır.
Işık dokuya hafifçe işlenmiştir: normal haritası gerekmez, telefonda ucuzdur. Karşıtlık düşük tutuldu ki engeller öne çıksın.
Çalıştırma: SAND_TEX ortam değişkeniyle blender -b -P build_sand.py
"""
import math
import os

import bpy
import numpy as np

PATH = os.environ["SAND_TEX"]
SIZE = 1024
BASE = np.array((0.87, 0.74, 0.53))
LIGHT = np.array((0.95, 0.84, 0.63))
DARK = np.array((0.74, 0.59, 0.39))

v, u = np.meshgrid(np.arange(SIZE) / SIZE, np.arange(SIZE) / SIZE, indexing="ij")
tau = 2 * math.pi


def waves(items):
    return sum(a * np.sin(tau * (fu * u + fv * v) + p) for a, fu, fv, p in items)


# Sırtları kıvrıltan yavaş dalgalar; her biri dokunun boyuna tam kat olduğu için dikiş oluşmaz
bend = waves(((0.45, 1, 1, 0.3), (0.28, 2, -1, 1.7), (0.12, 3, 2, 4.1)))
phase = 9.0 * v + 1.0 * u + bend
# Rüzgâr izi: bir yanı dik, bir yanı yatık sırt (testere dişine yakın)
ripple = np.sin(tau * phase) + 0.35 * np.sin(2 * tau * phase + 0.8)
ripple /= np.abs(ripple).max()
fine = waves(((0.5, 7, 21, 0.4), (0.35, -11, 27, 2.0), (0.25, 17, 33, 5.0))) / 1.1
patches = waves(((0.6, 1, 0, 1.0), (0.5, 0, 1, 2.3), (0.35, 1, -1, 4.2), (0.25, 2, 2, 0.6))) / 1.7

shade = 0.16 * ripple + 0.06 * fine + 0.22 * patches
color = np.empty((SIZE, SIZE, 3))
for i in range(3):
    up = np.clip(shade, 0, 1)[..., None][..., 0]
    down = np.clip(-shade, 0, 1)
    color[..., i] = BASE[i] + (LIGHT[i] - BASE[i]) * up + (DARK[i] - BASE[i]) * down

pixels = np.ones((SIZE, SIZE, 4), dtype=np.float32)
pixels[..., :3] = np.clip(color, 0, 1)
image = bpy.data.images.new("Sand", SIZE, SIZE, alpha=False)
image.colorspace_settings.name = "Non-Color"  # Değerler zaten sRGB, olduğu gibi yazılsın
image.pixels.foreach_set(pixels.flatten())
os.makedirs(os.path.dirname(PATH), exist_ok=True)
image.filepath_raw = PATH
image.file_format = "PNG"
image.save()
