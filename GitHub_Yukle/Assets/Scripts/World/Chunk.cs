using System.Collections.Generic;
using UnityEngine;

namespace PembeBuyucu
{
    /// <summary>Bütün parçaların paylaştığı malzemeler. Rengi değişince hepsi birden değişir.</summary>
    public class ChunkMaterials
    {
        public Material Ground;
        public Material Terrain;
        public Material Water;
        public Material LowObstacle;
        public Material TallObstacle;
        public Material Crystal;
        public Material BroomHandle;
        public Material BroomBristle;
    }

    /// <summary>
    /// Yolun bir parçası: bir zemin bloğu, üzerindeki engeller ve yol kenarındaki çöl süsleri.
    /// Engeller her seferinde yeniden oluşturulmaz, havuzdan tekrar kullanılır.
    /// </summary>
    public class Chunk
    {
        public const float LowHeight = 0.8f; // Zıplayarak aşılabilir; Subway Surfers'taki gibi karakterin beline gelir
        public const float TallHeight = 2.2f; // Aşılamaz, şerit değiştirmek gerekir
        public const float ObstacleDepth = 1f;

        private const string BridgeSegmentPath = "Models/Desert/BridgeDeck";
        // Köprü parçaları art arda dizilir; model bu boya göre yapıldı (bkz. Art/convert_bridge.py).
        private const int BridgeSegments = 7;
        // Giriş ve çıkışta altında kum zemin durur: aynı yükseklikte olsalar yüzeyler titrerdi.
        private const float BridgeLift = 0.06f;

        private readonly Transform root;
        private readonly Renderer groundRenderer;
        private Transform[] bridgeSegments;
        private RoadKind roadKind;
        private readonly float length;
        private readonly ChunkMaterials materials;
        private Broom broom;
        private readonly DesertScenery scenery;
        private readonly List<Obstacle> pool = new List<Obstacle>();
        private readonly List<Crystal> crystalPool = new List<Crystal>();
        private int activeCount;
        private int activeCrystalCount;

        public float StartZ => root.position.z;
        public float EndZ => root.position.z + length;

        public Chunk(Transform parent, float length, float width, ChunkMaterials materials, int index)
        {
            this.length = length;
            this.materials = materials;

            root = new GameObject("Chunk").transform;
            root.SetParent(parent, false);

            GameObject ground = GameObject.CreatePrimitive(PrimitiveType.Cube);
            ground.name = "Ground";
            ground.transform.SetParent(root, false);
            ground.transform.localScale = new Vector3(width, 1f, length);
            ground.transform.localPosition = new Vector3(0f, -0.5f, length * 0.5f);
            groundRenderer = ground.GetComponent<Renderer>();
            groundRenderer.sharedMaterial = materials.Ground;

            // Zemin için çarpışma gerekmiyor, performans için kaldırıyoruz.
            Object.Destroy(ground.GetComponent<Collider>());

            scenery = new DesertScenery(root, length, materials.Terrain, materials.Water, index);
        }

        /// <summary>Parçanın zeminini seçer. Köprü parçaları ilk gerektiğinde oluşturulur.</summary>
        public void SetRoadKind(RoadKind kind)
        {
            roadKind = kind;
            if (kind != RoadKind.Sand && bridgeSegments == null)
            {
                CreateBridgeSegments();
            }

            // Köprü yoksa (model bulunamadıysa) yol kum olarak kalır.
            bool hasBridge = bridgeSegments != null;
            RoadKind shown = hasBridge ? kind : RoadKind.Sand;
            groundRenderer.enabled = shown != RoadKind.Bridge;
            scenery.SetKind(shown);
            if (!hasBridge) return;

            float segmentLength = length / BridgeSegments;
            for (int i = 0; i < BridgeSegments; i++)
            {
                float z = (i + 0.5f) * segmentLength;
                bool show = shown == RoadKind.Bridge || (shown == RoadKind.BridgeEntry && z >= DesertScenery.BridgeEntryStart) ||
                            (shown == RoadKind.BridgeExit && z <= DesertScenery.BridgeExitEnd);
                bridgeSegments[i].gameObject.SetActive(show);
            }
        }

        private void CreateBridgeSegments()
        {
            GameObject prefab = Resources.Load<GameObject>(BridgeSegmentPath);
            if (prefab == null) return;

            bridgeSegments = new Transform[BridgeSegments];
            float segmentLength = length / BridgeSegments;
            for (int i = 0; i < BridgeSegments; i++)
            {
                Transform segment = Object.Instantiate(prefab, root).transform;
                segment.localPosition = new Vector3(0f, BridgeLift, (i + 0.5f) * segmentLength);
                ModelPalette.Apply(segment);
                bridgeSegments[i] = segment;
            }
        }

        public void MoveTo(float z)
        {
            root.position = new Vector3(0f, 0f, z);
        }

        public void SetSceneryVisible(bool visible)
        {
            scenery.SetVisible(visible);
        }

        public void ClearObstacles()
        {
            for (int i = 0; i < activeCount; i++)
            {
                pool[i].gameObject.SetActive(false);
            }

            activeCount = 0;
        }

        public void SpawnObstacle(float x, float worldZ, float width, bool tall, bool sharedPillar)
        {
            Obstacle obstacle = GetFromPool();
            float height = tall ? TallHeight : LowHeight;

            obstacle.Place(new Vector3(x, 0f, worldZ), width, height, ObstacleDepth, tall,
                tall ? materials.TallObstacle : materials.LowObstacle, sharedPillar);
            if (roadKind != RoadKind.Sand)
            {
                obstacle.HideArchPlant();
            }

            obstacle.gameObject.SetActive(true);
        }

        public void ClearCrystals()
        {
            for (int i = 0; i < activeCrystalCount; i++)
            {
                crystalPool[i].gameObject.SetActive(false);
            }

            activeCrystalCount = 0;
        }

        public void SpawnCrystal(float x, float y, float worldZ)
        {
            Crystal crystal = GetCrystalFromPool();
            crystal.transform.position = new Vector3(x, y, worldZ);
            crystal.gameObject.SetActive(true);
        }

        public void ClearBroom()
        {
            if (broom != null)
            {
                broom.gameObject.SetActive(false);
            }
        }

        public void SpawnBroom(float x, float y, float worldZ)
        {
            if (broom == null)
            {
                broom = Broom.Create(root, materials.BroomHandle, materials.BroomBristle);
            }

            broom.transform.position = new Vector3(x, y, worldZ);
            broom.gameObject.SetActive(true);
        }

        private Crystal GetCrystalFromPool()
        {
            if (activeCrystalCount < crystalPool.Count)
            {
                return crystalPool[activeCrystalCount++];
            }

            Crystal crystal = Crystal.Create(root, materials.Crystal);
            crystalPool.Add(crystal);
            activeCrystalCount++;
            return crystal;
        }

        private Obstacle GetFromPool()
        {
            if (activeCount < pool.Count)
            {
                return pool[activeCount++];
            }

            Obstacle obstacle = Obstacle.Create(root);
            pool.Add(obstacle);
            activeCount++;
            return obstacle;
        }
    }
}
