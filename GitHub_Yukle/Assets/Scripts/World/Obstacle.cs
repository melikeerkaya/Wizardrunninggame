using System.Collections.Generic;
using UnityEngine;

namespace PembeBuyucu
{
    /// <summary>
    /// Engel işaretçisi. Oyuncu bu bileşene sahip bir tetikleyiciye değerse koşu biter.
    /// Alçak engeller karakterin beline gelir, üzerinden zıplanır: çömlek grupları (Resources/Models/Desert/Pots),
    /// devrik sütun, kırık taşlar ve kumdan çıkan bloklar (Resources/Models/Desert/Ruins). Aynı aile art arda gelmez.
    /// Yüksek engel taş kemerdir (Resources/Models/Desert/Archway): altından kayılır ya da iyi zamanlanmış zıplamayla üstünden
    /// aşılır. Şerit sınırlarında birer ayağı durur; çarpışma ayakları ve göğüs hizasından kemerin tepesine kadarını kapsar.
    /// Engelin üstüne düşen karakter yuvarlanıp devam eder (bkz. PlayerController).
    /// Alçak engelin çarpışma kutusu modelin sınırlarından hesaplanır, süsler (adında "Decor") sayılmaz.
    /// Model bulunamazsa engel düz blok olarak çizilir. Çarpışma kutuları ana nesnededir, görünüm alt nesnelerdedir.
    /// </summary>
    public class Obstacle : MonoBehaviour
    {
        // Alçak engel aileleri. Çömleklerin dört çeşidi kendi aralarında sırayla gelir (bkz. Art/build_pots.py, build_ruins.py).
        private static readonly string[][] LowFamilies =
        {
            new[]
            {
                "Models/Desert/Pots/PotAmphora",
                "Models/Desert/Pots/PotWide",
                "Models/Desert/Pots/PotGold",
                "Models/Desert/Pots/PotZigzag"
            },
            new[] { "Models/Desert/Ruins/FallenColumn" },
            new[] { "Models/Desert/Ruins/BrokenStones" },
            new[] { "Models/Desert/Ruins/SandBlocks" }
        };

        // Modeller engelin yüksekliğine göre bu orana ölçeklenir: çömlek grupları 1 birime (en büyük çömlek),
        // taşlar gerçek boyuna (Chunk.LowHeight) göre yapıldı.
        private static readonly float[] LowDesignHeights = { 1f, 0.8f, 0.8f, 0.8f };

        private static readonly HighLayout[] HighLayouts =
        {
            // Kemerin altı ortada 1.3'te, kapsülün kaydığı genişlikte ~1.18'de: ayaktaki karakter (~1.5 boy) çarpar, kayan
            // (~0.9) geçer. Taşın tepesi ~1.82'de, zıplamanın tepesinde kapsülün altı 2'de: iyi zamanlanırsa üstünden aşılır.
            // Bkz. Art/convert_archway.py.
            new HighLayout("Models/Desert/Archway", 1.15f, 1.82f, 0.44f, 0.7f, 0.44f, 1.6f)
        };

        // İnerken ayaklar bu yükseklikteyse (ölçek 1) karakter kemerin üstüne düşmüş sayılır, altındaysa kemere çarpmıştır.
        private const float HighLandOnHeight = 0.9f;

        // Yüksek engel modelleri 2 birimlik engel genişliğine göre yapıldı, ayakları x = ±1.25'te durur.
        private const float HighDesignWidth = 2f;
        private const float PillarX = 1.25f;
        // Model tek parça, ortak ayak gizlenemez: yan yana iki kemerin yüzleri titremesin diye biri biraz öne alınır.
        private const float OverlapOffset = 0.05f;

        // Alçak engelin kutusu görünen modelden bu kadar içeride kalır: kenara sürtünmek koşuyu bitirmesin.
        private const float LowSideInset = 0.08f;
        private const float LowTopInset = 0.04f;

        private static readonly Dictionary<string, GameObject> Prefabs = new Dictionary<string, GameObject>();
        // Her ailede sıradaki model.
        private static readonly int[] NextInFamily = new int[LowFamilies.Length];
        private static int lastLowFamily = -1;
        private static float lastHighRowZ = float.NaN;
        private static int lastHighLayout;

        private BoxCollider box;
        private BoxCollider leftPost;
        private BoxCollider rightPost;
        private Transform blockVisual;
        private Renderer blockRenderer;
        // Modeller ilk gerektiğinde kopyalanır; eksik model null olarak saklanır, her seferinde yeniden aranmaz.
        private readonly Dictionary<string, Variant> variants = new Dictionary<string, Variant>();
        private Variant active;
        private Transform archPlant;

        // Yan şeritteki kemerin yolun dışında kalan ayağının dibine konan küçük kaktüs (yalnız görsel).
        private const string ArchPlantPath = "Models/Desert/Scenery/BarrelCactus";
        private const float ArchPlantX = 2.05f;

        /// <summary>Üzerinden zıplanan alçak engel mi?</summary>
        public bool IsLow { get; private set; }

        /// <summary>Yüksek engelde, inerken ayaklar en az bu yükseklikteyse engele üstten değilmiş sayılır.</summary>
        public float LandOnHeight { get; private set; }

        /// <summary>Üstünde yuvarlanırken karakterin ayaklarının durduğu yükseklik.</summary>
        public float RollTop { get; private set; }

        /// <summary>Engelin koşu yönündeki yarı kalınlığı.</summary>
        public float RollHalfDepth { get; private set; }

        private readonly struct HighLayout
        {
            public readonly string Path;
            public readonly float OverheadBottom;
            public readonly float OverheadTop;
            public readonly float OverheadDepth;
            public readonly float PostWidth;
            public readonly float PostDepth;
            public readonly float PostTop;

            public HighLayout(string path, float overheadBottom, float overheadTop, float overheadDepth, float postWidth,
                float postDepth, float postTop)
            {
                Path = path;
                OverheadBottom = overheadBottom;
                OverheadTop = overheadTop;
                OverheadDepth = overheadDepth;
                PostWidth = postWidth;
                PostDepth = postDepth;
                PostTop = postTop;
            }
        }

        private class Variant
        {
            public Transform Model;
            // Alçak engelde görünen gövdenin sınırları (ölçek 1).
            public Bounds Body;
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics()
        {
            Prefabs.Clear();
            System.Array.Clear(NextInFamily, 0, NextInFamily.Length);
            lastLowFamily = -1;
            lastHighRowZ = float.NaN;
        }

        /// <summary>Bütün engel modellerini önceden yükler (bkz. ModelPalette.Preload).</summary>
        public static void Preload()
        {
            foreach (string[] family in LowFamilies)
            {
                foreach (string path in family)
                {
                    ModelPalette.Preload(path);
                }
            }

            foreach (HighLayout layout in HighLayouts)
            {
                ModelPalette.Preload(layout.Path);
            }

            ModelPalette.Preload(ArchPlantPath);
        }

        public static Obstacle Create(Transform parent)
        {
            GameObject go = new GameObject("Obstacle");
            go.transform.SetParent(parent, true);

            // Üç kutu da aynı nesnede: oyuncu hangisine değerse değsin Obstacle bileşenini bulur.
            Obstacle obstacle = go.AddComponent<Obstacle>();
            obstacle.box = AddTrigger(go);
            obstacle.leftPost = AddTrigger(go);
            obstacle.rightPost = AddTrigger(go);

            GameObject block = GameObject.CreatePrimitive(PrimitiveType.Cube);
            block.name = "Block";
            block.transform.SetParent(go.transform, false);
            Destroy(block.GetComponent<Collider>());
            obstacle.blockVisual = block.transform;
            obstacle.blockRenderer = block.GetComponent<Renderer>();

            return obstacle;
        }

        private static BoxCollider AddTrigger(GameObject go)
        {
            BoxCollider collider = go.AddComponent<BoxCollider>();
            collider.isTrigger = true;
            return collider;
        }

        public void Place(Vector3 groundPosition, float width, float height, float depth, bool tall, Material blockMaterial,
            bool sharedPillar)
        {
            transform.position = groundPosition;
            IsLow = !tall;
            LandOnHeight = height;
            RollTop = height;
            RollHalfDepth = depth * 0.5f;

            if (active != null)
            {
                active.Model.gameObject.SetActive(false);
            }

            leftPost.enabled = false;
            rightPost.enabled = false;

            active = tall ? PlaceHigh(groundPosition.z, width, sharedPillar) : PlaceLow(height);
            UpdateArchPlant(tall && active != null, groundPosition.x);
            blockVisual.gameObject.SetActive(active == null);
            if (active != null) return;

            box.center = new Vector3(0f, height * 0.5f, 0f);
            box.size = new Vector3(width, height, depth);
            blockVisual.localScale = new Vector3(width, height, depth);
            blockVisual.localPosition = new Vector3(0f, height * 0.5f, 0f);
            blockRenderer.sharedMaterial = blockMaterial;
        }

        private Variant PlaceLow(float height)
        {
            // Bir önceki aile dışındakilerden biri seçilir. Modeli olmayan aile atlanır.
            int count = LowFamilies.Length;
            int first = lastLowFamily < 0 ? Random.Range(0, count) : Random.Range(0, count - 1);
            if (lastLowFamily >= 0 && first >= lastLowFamily) first++;

            for (int i = 0; i < count; i++)
            {
                int family = (first + i) % count;
                string[] paths = LowFamilies[family];
                Variant variant = GetVariant(paths[NextInFamily[family] % paths.Length], false);
                if (variant == null) continue;

                lastLowFamily = family;
                NextInFamily[family]++;

                // Aynı tür de hep aynı durmasın diye model bazen ters çevrilir.
                bool flip = Random.value < 0.5f;
                float scale = height / LowDesignHeights[family];
                variant.Model.localScale = Vector3.one * scale;
                variant.Model.localRotation = Quaternion.Euler(0f, flip ? 180f : 0f, 0f);
                variant.Model.gameObject.SetActive(true);

                Bounds body = variant.Body;
                float side = flip ? -1f : 1f;
                float top = body.max.y * scale - LowTopInset;
                box.center = new Vector3(body.center.x * scale * side, top * 0.5f, body.center.z * scale * side);
                box.size = new Vector3(body.size.x * scale - 2f * LowSideInset, top, body.size.z * scale - 2f * LowSideInset);
                RollTop = body.max.y * scale;
                RollHalfDepth = box.size.z * 0.5f;
                return variant;
            }

            return null;
        }

        private Variant PlaceHigh(float rowZ, float width, bool sharedPillar)
        {
            int first = rowZ == lastHighRowZ ? lastHighLayout : Random.Range(0, HighLayouts.Length);

            for (int i = 0; i < HighLayouts.Length; i++)
            {
                int index = (first + i) % HighLayouts.Length;
                HighLayout layout = HighLayouts[index];
                Variant variant = GetVariant(layout.Path, true);
                if (variant == null) continue;

                lastHighRowZ = rowZ;
                lastHighLayout = index;

                float scale = width / HighDesignWidth;
                variant.Model.localScale = Vector3.one * scale;
                variant.Model.localPosition = new Vector3(0f, 0f, sharedPillar ? OverlapOffset : 0f);
                variant.Model.gameObject.SetActive(true);

                float bottom = layout.OverheadBottom * scale;
                float top = layout.OverheadTop * scale;
                LandOnHeight = HighLandOnHeight * scale;
                RollTop = top;
                RollHalfDepth = layout.OverheadDepth * scale * 0.5f;
                box.center = new Vector3(0f, (bottom + top) * 0.5f, 0f);
                box.size = new Vector3(width, top - bottom, layout.OverheadDepth * scale);

                // Ayaklar da çarpar: şerit değiştirirken taşın içinden geçilmez.
                Vector3 postSize = new Vector3(layout.PostWidth, layout.PostTop, layout.PostDepth) * scale;
                rightPost.enabled = true;
                rightPost.center = new Vector3(PillarX * scale, postSize.y * 0.5f, 0f);
                rightPost.size = postSize;
                leftPost.enabled = !sharedPillar;
                leftPost.center = new Vector3(-PillarX * scale, postSize.y * 0.5f, 0f);
                leftPost.size = postSize;
                return variant;
            }

            return null;
        }

        /// <summary>Köprüde kemerin dış ayağının yanı boşluktur, kaktüs havada kalmasın.</summary>
        public void HideArchPlant()
        {
            if (archPlant != null)
            {
                archPlant.gameObject.SetActive(false);
            }
        }

        private void UpdateArchPlant(bool isArch, float laneX)
        {
            bool show = isArch && !Mathf.Approximately(laneX, 0f);
            if (show && archPlant == null)
            {
                GameObject prefab = Resources.Load<GameObject>(ArchPlantPath);
                if (prefab == null) return;

                archPlant = Instantiate(prefab, transform).transform;
                ModelPalette.Apply(archPlant);
            }

            if (archPlant == null) return;

            archPlant.gameObject.SetActive(show);
            if (show)
            {
                archPlant.localPosition = new Vector3(Mathf.Sign(laneX) * ArchPlantX, 0f, 0.2f);
                archPlant.localRotation = Quaternion.Euler(0f, Random.Range(0f, 360f), 0f);
            }
        }

        private Variant GetVariant(string path, bool tall)
        {
            if (variants.TryGetValue(path, out Variant cached)) return cached;

            if (!Prefabs.TryGetValue(path, out GameObject prefab))
            {
                prefab = Resources.Load<GameObject>(path);
                Prefabs[path] = prefab;
            }

            Variant variant = null;
            if (prefab != null)
            {
                Transform model = Instantiate(prefab, transform).transform;
                model.localPosition = Vector3.zero;
                ModelPalette.Apply(model);
                variant = new Variant
                {
                    Model = model,
                    Body = tall ? new Bounds() : MeasureBody(model)
                };
                model.gameObject.SetActive(false);
            }

            variants[path] = variant;
            return variant;
        }

        // Modelin kendi uzayındaki sınırları. Havuzdaki engel kapalıyken de çalışsın diye Renderer.bounds değil mesh kullanılır.
        private static Bounds MeasureBody(Transform model)
        {
            Bounds bounds = new Bounds();
            bool any = false;
            foreach (MeshFilter filter in model.GetComponentsInChildren<MeshFilter>(true))
            {
                if (filter.sharedMesh == null || filter.name.Contains("Decor")) continue;

                Bounds mesh = filter.sharedMesh.bounds;
                for (int i = 0; i < 8; i++)
                {
                    Vector3 corner = mesh.center + Vector3.Scale(mesh.extents,
                        new Vector3((i & 1) == 0 ? -1f : 1f, (i & 2) == 0 ? -1f : 1f, (i & 4) == 0 ? -1f : 1f));
                    Vector3 point = model.InverseTransformPoint(filter.transform.TransformPoint(corner));
                    if (any)
                    {
                        bounds.Encapsulate(point);
                    }
                    else
                    {
                        bounds = new Bounds(point, Vector3.zero);
                        any = true;
                    }
                }
            }

            return bounds;
        }
    }
}
