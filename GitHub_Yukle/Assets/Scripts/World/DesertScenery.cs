using System.Collections.Generic;
using UnityEngine;

namespace PembeBuyucu
{
    /// <summary>Bir yol parçasının zemini: kum, köprüye giriş, köprü ya da köprüden çıkış.</summary>
    public enum RoadKind
    {
        Sand,
        BridgeEntry,
        Bridge,
        BridgeExit
    }

    /// <summary>
    /// Çöl etabının yol kenarı: kum tepeleri ve üzerindeki harabeler, kaktüsler. Yalnızca görseldir, çarpışması yoktur.
    /// Kum tepeleri koddan üretilen örgülerdir; yol parçası boyunca tam tekrar eder, parçalar dikişsiz birleşir.
    /// Köprü bölümünde kum, yolun altında sulu bir vadiye iner; giriş ve çıkış parçalarında vadi yavaşça açılıp kapanır.
    /// Süsler her yol parçasında bir kez oluşturulur, parça öne taşınınca yerleri karışır (bkz. Art/convert_prop.py).
    /// </summary>
    public class DesertScenery
    {
        public const string SandTexturePath = "Models/Desert/Sand_basecolor";
        /// <summary>Kum dokusunun kendini tekrar ettiği uzunluk (metre).</summary>
        public const float SandTextureMeters = 6f;
        /// <summary>Giriş parçasında köprünün başladığı yer (parçanın başından metre).</summary>
        public const float BridgeEntryStart = 12f;
        /// <summary>Çıkış parçasında köprünün bittiği yer (parçanın başından metre).</summary>
        public const float BridgeExitEnd = 18f;

        private const float ValleyDepth = 5f;
        private const float WaterLevel = -4.2f;
        private const float RoadHalfWidth = 4.25f;

        private const string Folder = "Models/Desert/Scenery/";
        private const string Arch = Folder + "SceneArch";
        private const string Wall = Folder + "SceneWall";
        private const string Columns = Folder + "SceneColumns";
        private const string Stump = Folder + "SceneStump";
        private const string Cactus = Folder + "Cactus";
        private const string BarrelCactus = Folder + "BarrelCactus";
        private const string PricklyPear = Folder + "PricklyPear";
        private const string Palisade = Folder + "Palisade";
        private const string Palm = Folder + "Palm";

        // Yol kenarından dışarı doğru sıra sıra uzaklıklar: yakında sık, uzakta seyrek.
        private static readonly float[] Distances = { -0.05f, 1.5f, 3f, 5f, 7.5f, 10f, 13f, 17f, 22f, 28f, 35f, 44f, 55f, 68f, 85f };
        private const int Rows = 12;

        // Bir küme: bir ana parça ve dibindeki küçük bitkiler. Bitkinin yeri ana parçanın ortasına göre (x, z).
        private readonly struct Plant
        {
            public readonly string Path;
            public readonly float X;
            public readonly float Z;

            public Plant(string path, float x, float z)
            {
                Path = path;
                X = x;
                Z = z;
            }
        }

        private readonly struct ClusterKind
        {
            public readonly string Path;
            public readonly float MinDistance;
            public readonly float MaxDistance;
            public readonly Plant[] Plants;

            public ClusterKind(string path, float minDistance, float maxDistance, params Plant[] plants)
            {
                Path = path;
                MinDistance = minDistance;
                MaxDistance = maxDistance;
                Plants = plants;
            }
        }

        // Yakındaki kümeler. Uzaklık, yolun ortasından; kemer yola taşmasın diye yarı genişliği kadar açıkta durur.
        private static readonly ClusterKind[] NearKinds =
        {
            new ClusterKind(Arch, 8.5f, 13f, new Plant(BarrelCactus, -3.4f, 0.5f), new Plant(PricklyPear, 3.5f, 0.3f), new Plant(BarrelCactus, 3.1f, -0.6f)),
            new ClusterKind(Wall, 7.5f, 12f, new Plant(Cactus, 2.9f, 0.2f), new Plant(BarrelCactus, -2.7f, 0.6f)),
            new ClusterKind(Columns, 8f, 13f, new Plant(PricklyPear, 0.4f, 1.2f)),
            new ClusterKind(Stump, 6.5f, 11f, new Plant(BarrelCactus, -2f, 0.5f), new Plant(Cactus, 2.1f, -0.5f))
        };

        private static readonly Mesh[] Terrains = new Mesh[4];
        private static float terrainLength;

        private class Cluster
        {
            public Transform Root;
            public float MinDistance;
            public float MaxDistance;
            public float Yaw;
        }

        private readonly GameObject root;
        private readonly GameObject water;
        private readonly MeshFilter ground;
        private readonly float length;
        private readonly List<Cluster> near = new List<Cluster>();
        private readonly List<Cluster> far = new List<Cluster>();
        private readonly List<Cluster> singles = new List<Cluster>();
        private readonly List<Cluster> palms = new List<Cluster>();
        private readonly List<Cluster> gates = new List<Cluster>();
        private RoadKind kind;

        public DesertScenery(Transform parent, float length, Material sand, Material waterMaterial, int index)
        {
            this.length = length;
            root = new GameObject("DesertScenery");
            root.transform.SetParent(parent, false);

            GameObject dunes = new GameObject("Dunes");
            dunes.transform.SetParent(root.transform, false);
            ground = dunes.AddComponent<MeshFilter>();
            ground.sharedMesh = GetTerrain(length, RoadKind.Sand);
            MeshRenderer renderer = dunes.AddComponent<MeshRenderer>();
            renderer.sharedMaterial = sand;
            renderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;

            water = GameObject.CreatePrimitive(PrimitiveType.Quad);
            water.name = "Water";
            water.transform.SetParent(root.transform, false);
            water.transform.localPosition = new Vector3(0f, WaterLevel, length * 0.5f);
            water.transform.localRotation = Quaternion.Euler(90f, 0f, 0f);
            water.transform.localScale = new Vector3(70f, length, 1f);
            Object.Destroy(water.GetComponent<Collider>());
            Renderer waterRenderer = water.GetComponent<Renderer>();
            waterRenderer.sharedMaterial = waterMaterial;
            waterRenderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            water.SetActive(false);

            // Her parçada iki yanda birer yakın küme; her tür yolda sırayla görünsün diye sıra parçaya göre değişir.
            AddCluster(NearKinds[index % NearKinds.Length], near);
            AddCluster(NearKinds[(index + 2) % NearKinds.Length], near);
            // Uzakta dev kemer ve duvar: ufuk çizgisini görseldeki gibi doldurur.
            AddCluster(new ClusterKind(index % 2 == 0 ? Arch : Wall, 24f, 42f), far, 1.5f);
            AddCluster(new ClusterKind(index % 2 == 0 ? Wall : Arch, 24f, 42f), far, 1.5f);

            // Yol kenarına serpilmiş tek bitkiler.
            string[] plants = { BarrelCactus, PricklyPear, Cactus, BarrelCactus };
            foreach (string plant in plants)
            {
                AddCluster(new ClusterKind(plant, 5.2f, 7f), singles);
            }

            // Köprü bölümü: vadi kıyısında palmiyeler, köprü ağzının iki yanında ahşap çit.
            AddCluster(new ClusterKind(Palm, 19f, 32f), palms);
            AddCluster(new ClusterKind(Palm, 19f, 32f), palms);
            AddCluster(new ClusterKind(Palisade, 7f, 7f), gates);
            AddCluster(new ClusterKind(Palisade, 7f, 7f), gates);

            SetKind(RoadKind.Sand);
        }

        public void SetVisible(bool visible)
        {
            root.SetActive(visible);
        }

        /// <summary>Zemini ve o zemine uyan süsleri seçer: yakın süsler kumda, palmiye ve çit köprü bölümünde görünür.</summary>
        public void SetKind(RoadKind newKind)
        {
            kind = newKind;
            bool sand = kind == RoadKind.Sand;
            ground.sharedMesh = GetTerrain(length, kind);
            water.SetActive(!sand);
            SetActive(near, sand);
            SetActive(singles, sand);
            SetActive(palms, !sand);
            SetActive(gates, kind == RoadKind.BridgeEntry || kind == RoadKind.BridgeExit);
            Shuffle();
        }

        private static void SetActive(List<Cluster> clusters, bool active)
        {
            foreach (Cluster cluster in clusters)
            {
                cluster.Root.gameObject.SetActive(active);
            }
        }

        /// <summary>Süslere yeni yer verir; aynı parça tekrar geldiğinde yol kenarı aynı görünmesin.</summary>
        public void Shuffle()
        {
            // Çiftler karşılıklı yanlara düşer: yolun iki yanı da boş kalmaz.
            PlacePair(near);
            PlacePair(far);
            PlacePair(palms);
            foreach (Cluster single in singles)
            {
                Place(single, Random.value < 0.5f ? 1f : -1f, Random.Range(1f, length - 1f));
            }

            // Çitler köprü ağzının hemen kum tarafında, yolun iki yanında durur.
            float gateZ = kind == RoadKind.BridgeExit ? BridgeExitEnd + 2f : BridgeEntryStart - 2f;
            for (int i = 0; i < gates.Count; i++)
            {
                Place(gates[i], i == 0 ? 1f : -1f, gateZ);
                gates[i].Root.localRotation = Quaternion.identity;
            }
        }

        private void PlacePair(List<Cluster> pair)
        {
            bool flip = Random.value < 0.5f;
            for (int i = 0; i < pair.Count; i++)
            {
                Place(pair[i], (i % 2 == 0) == flip ? 1f : -1f, Random.Range(1f, length - 1f));
            }
        }

        private void Place(Cluster cluster, float side, float z)
        {
            float x = side * Random.Range(cluster.MinDistance, cluster.MaxDistance);
            cluster.Root.localPosition = new Vector3(x, Height(x, z, length, kind), z);
            cluster.Root.localRotation = Quaternion.Euler(0f, cluster.Yaw + Random.Range(-14f, 14f), 0f);
        }

        private void AddCluster(ClusterKind clusterKind, List<Cluster> list, float scale = 1f)
        {
            GameObject prefab = Resources.Load<GameObject>(clusterKind.Path);
            if (prefab == null) return;

            Transform cluster = new GameObject("Cluster").transform;
            cluster.SetParent(root.transform, false);
            cluster.localScale = Vector3.one * scale;
            AddModel(prefab, cluster, Vector3.zero, 0f);
            foreach (Plant plant in clusterKind.Plants)
            {
                GameObject plantPrefab = Resources.Load<GameObject>(plant.Path);
                if (plantPrefab != null)
                {
                    AddModel(plantPrefab, cluster, new Vector3(plant.X, 0f, plant.Z), Random.Range(0f, 360f));
                }
            }

            bool roundPlant = clusterKind.Plants.Length == 0 && (clusterKind.Path.Contains("Cactus") || clusterKind.Path == Palm);
            list.Add(new Cluster
            {
                Root = cluster,
                MinDistance = clusterKind.MinDistance,
                MaxDistance = clusterKind.MaxDistance,
                Yaw = roundPlant ? Random.Range(0f, 360f) : 0f
            });
        }

        private static void AddModel(GameObject prefab, Transform parent, Vector3 position, float yaw)
        {
            Transform model = Object.Instantiate(prefab, parent).transform;
            model.localPosition = position;
            model.localRotation = Quaternion.Euler(0f, yaw, 0f);
            ModelPalette.Apply(model);
        }

        // Vadinin o noktadaki açıklığı: 0 = kum, 1 = tam vadi. Giriş ve çıkışta yumuşak değişir, parça sınırlarında eğimi sıfırdır.
        private static float ValleyBlend(RoadKind kind, float z, float length)
        {
            switch (kind)
            {
                case RoadKind.Bridge:
                    return 1f;
                case RoadKind.BridgeEntry:
                    return Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(BridgeEntryStart, length, z));
                case RoadKind.BridgeExit:
                    return Mathf.SmoothStep(1f, 0f, Mathf.InverseLerp(0f, BridgeExitEnd, z));
                default:
                    return 0f;
            }
        }

        /// <summary>Zeminin yüksekliği. Yolun kenarında sıfırdır, dışa doğru yükselir; z yönünde parça boyunca tam tekrar eder.
        /// Vadide yolun yakını suyun altına iner, uzakta yine kum tepeleri başlar.</summary>
        public static float Height(float x, float z, float length, RoadKind kind)
        {
            float side = x < 0f ? -1f : 1f;
            float d = Mathf.Max(0f, Mathf.Abs(x) - RoadHalfWidth);
            float wave = 2f * Mathf.PI * z / length;
            float rise = Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(1.5f, 22f, d));
            float dunes = 1.4f + 0.8f * Mathf.Sin(2f * wave + d * 0.14f + side * 1.3f) + 0.5f * Mathf.Sin(wave - d * 0.09f + side * 0.7f);
            float far = d / 85f;
            float height = rise * dunes + far * far * 7f;

            float valley = ValleyBlend(kind, z, length) * (1f - Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(8f, 28f, d)));
            return Mathf.Lerp(height, -ValleyDepth, valley);
        }

        private static Mesh GetTerrain(float length, RoadKind kind)
        {
            if (!Mathf.Approximately(terrainLength, length))
            {
                System.Array.Clear(Terrains, 0, Terrains.Length);
                terrainLength = length;
            }

            int index = (int)kind;
            if (Terrains[index] != null) return Terrains[index];

            var vertices = new List<Vector3>();
            var normals = new List<Vector3>();
            var uvs = new List<Vector2>();
            var triangles = new List<int>();
            foreach (float side in new[] { 1f, -1f })
            {
                int start = vertices.Count;
                int columns = Distances.Length;
                for (int c = 0; c < columns; c++)
                {
                    for (int r = 0; r <= Rows; r++)
                    {
                        float x = side * (RoadHalfWidth + Distances[c]);
                        float z = length * r / Rows;
                        float y = Height(x, z, length, kind);
                        // Kumda yol kenarı yolun biraz altından başlar, arada çizgi kalmaz.
                        vertices.Add(new Vector3(x, c == 0 && ValleyBlend(kind, z, length) <= 0f ? -0.02f : y, z));
                        normals.Add(TerrainNormal(x, z, length, kind));
                        // Yolun dokusuyla aynı ölçek: yolun genişliği ve uzunluğu 0-1 sayılır.
                        uvs.Add(new Vector2((x + RoadHalfWidth) / (RoadHalfWidth * 2f), z / length));
                    }
                }

                for (int c = 0; c < columns - 1; c++)
                {
                    for (int r = 0; r < Rows; r++)
                    {
                        int a = start + c * (Rows + 1) + r;
                        int up = a + 1;
                        int outer = a + Rows + 1;
                        int both = outer + 1;
                        if (side > 0f)
                        {
                            triangles.AddRange(new[] { a, up, outer, outer, up, both });
                        }
                        else
                        {
                            triangles.AddRange(new[] { a, outer, up, outer, both, up });
                        }
                    }
                }
            }

            Mesh terrain = new Mesh { name = "Dunes" + kind };
            terrain.SetVertices(vertices);
            terrain.SetNormals(normals);
            terrain.SetUVs(0, uvs);
            terrain.SetTriangles(triangles, 0);
            terrain.RecalculateBounds();
            Terrains[index] = terrain;
            return terrain;
        }

        // Dikişlerde gölge kırılmasın diye normal, örgüden değil yükseklik işlevinden hesaplanır.
        private static Vector3 TerrainNormal(float x, float z, float length, RoadKind kind)
        {
            const float step = 0.25f;
            float dx = Height(x + step, z, length, kind) - Height(x - step, z, length, kind);
            float dz = Height(x, z + step, length, kind) - Height(x, z - step, length, kind);
            return new Vector3(-dx, 2f * step, -dz).normalized;
        }
    }
}
