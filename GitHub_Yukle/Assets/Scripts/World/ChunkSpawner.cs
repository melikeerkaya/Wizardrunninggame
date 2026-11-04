using System.Collections.Generic;
using UnityEngine;

namespace PembeBuyucu
{
    /// <summary>
    /// Sonsuz yolu oluşturur: birkaç zemin parçasını (chunk) döngüye sokar,
    /// arkada kalan parçayı öne taşıyıp üzerine yeni engeller, kristaller ve süpürgeler yerleştirir.
    /// Her sırada en az bir şerit boş bırakılır, yani oyun her zaman geçilebilirdir.
    /// Kemerin hemen arkasındaki sırada aynı şeride engel konmaz: kemer kameradan arkasını kapatır, görülmeyen engele çarpılmasın.
    /// Çölde yol, kitap sayısına göre köprü ile kum arasında değişir; yeni parçalar ilerde üretildiği için geçiş önceden görünür.
    /// Portal açılınca yolun ilerisine portalı koyar ve çevresini boş bırakır.
    /// Dünya değişince renkleri, gökyüzünü ve engel sıklığını yeni dünyaya göre günceller.
    /// </summary>
    public class ChunkSpawner : MonoBehaviour
    {
        private const int LaneCount = 3;

        [Tooltip("Boş bırakılırsa sahnedeki PlayerController otomatik bulunur.")]
        [SerializeField] private PlayerController player;

        [Header("Zemin")]
        [SerializeField] private int chunkCount = 4;
        [SerializeField] private float chunkLength = 30f;
        [SerializeField] private float firstChunkStartZ = -10f;
        [Tooltip("Parça bu kadar geride kalınca öne taşınır.")]
        [SerializeField] private float recycleDistanceBehind = 10f;

        [Tooltip("Çölde yolun kum dokusuna karışan tonu: yol çevresindeki kumdan ayrılsın, oyuncu şeritleri görsün.")]
        [SerializeField] private Color desertRoadTint = new Color(0.94f, 0.88f, 0.8f);

        [Header("Köprü bölümü (çöl)")]
        [Tooltip("Köprü bölümleri, sırayla: x kitapta yol köprüye geçer, y kitapta kuma döner. x = 0 ise oyun köprüde başlar. Denemek için düşürebilirsin.")]
        [SerializeField] private Vector2Int[] bridgeSections = { new Vector2Int(0, 150), new Vector2Int(300, 450) };
        [SerializeField] private Color waterColor = new Color(0.2f, 0.72f, 0.78f);

        [Header("Sis (uzaktaki yolun aniden belirmesini gizler)")]
        [SerializeField] private float fogStart = 40f;
        [SerializeField] private float fogEnd = 110f;

        [Header("Engeller (sıklık dünyadan gelir)")]
        [Tooltip("Engel sıraları arasındaki mesafe.")]
        [SerializeField] private float rowSpacing = 10f;
        [Tooltip("Başlangıçta bu mesafeye kadar engel çıkmaz.")]
        [SerializeField] private float safeStartDistance = 25f;
        [SerializeField, Range(0f, 1f)] private float twoBlockedChance = 0.35f;
        [SerializeField, Range(0f, 1f)] private float tallChance = 0.4f;

        [Header("Kristaller")]
        [Tooltip("Başlangıçta bu mesafeye kadar kristal çıkmaz.")]
        [SerializeField] private float crystalSafeStartDistance = 15f;
        [SerializeField, Range(0f, 1f)] private float crystalLineChance = 0.7f;
        [SerializeField] private int crystalsPerLine = 3;
        [SerializeField] private float crystalSpacing = 1.6f;
        [SerializeField] private float crystalHeight = 1f;

        [Header("Süpürge")]
        [Tooltip("Her yol parçasında süpürge çıkma ihtimali.")]
        [SerializeField, Range(0f, 1f)] private float broomChance = 0.12f;
        [SerializeField] private float broomHeight = 1.2f;

        [Header("Havadaki kristaller (süpürge uçuşu)")]
        [Tooltip("Havadaki kristaller arasındaki mesafe.")]
        [SerializeField] private float airCrystalSpacing = 2.4f;
        [Tooltip("Kristal izi, her seferinde bu kadar kristal sonra yan şeride kayar.")]
        [SerializeField] private int airCrystalsPerLane = 4;

        [Header("Portal")]
        [Tooltip("Portal, o an üretilmiş yolun bu kadar ilerisine konur.")]
        [SerializeField] private float portalOffset = 15f;
        [Tooltip("Portalın bu kadar önünde ve arkasında engel ve kristal çıkmaz.")]
        [SerializeField] private float portalClearRadius = 20f;

        [Header("Geçici renkler (sonra gerçek modellerle değişecek)")]
        [SerializeField] private Color crystalColor = new Color(0.3f, 0.9f, 1f);
        [SerializeField] private Color portalColor = new Color(0.8f, 0.3f, 1f);
        [SerializeField] private Color broomHandleColor = new Color(0.55f, 0.35f, 0.15f);
        [SerializeField] private Color broomBristleColor = new Color(0.95f, 0.8f, 0.3f);

        private readonly List<Chunk> chunks = new List<Chunk>();
        private readonly List<Crystal> airCrystals = new List<Crystal>();
        // Bir önceki sırada kemer olan şeritler.
        private readonly bool[] archInLastRow = new bool[LaneCount];
        // Üretilen son parçanın zemini ve sıradaki köprü bölümü.
        private RoadKind roadKind;
        private int bridgeStage;
        private WorldManager world;
        private ChunkMaterials materials;
        private Portal portal;
        private bool portalActive;
        private float portalZ;
        private float laneWidth;
        private float nextChunkStartZ;

        private void Awake()
        {
            if (player == null)
            {
                player = FindFirstObjectByType<PlayerController>();
            }

            if (player == null)
            {
                Debug.LogError("ChunkSpawner: Sahnede PlayerController bulunamadı.", this);
                enabled = false;
                return;
            }

            world = FindFirstObjectByType<WorldManager>();
            if (world == null)
            {
                world = new GameObject("WorldManager").AddComponent<WorldManager>();
            }

            laneWidth = player.LaneWidth;

            materials = new ChunkMaterials
            {
                Ground = MaterialFactory.Create(Color.white),
                Terrain = MaterialFactory.Create(Color.white),
                Water = MaterialFactory.Create(waterColor),
                LowObstacle = MaterialFactory.Create(Color.white),
                TallObstacle = MaterialFactory.Create(Color.white),
                Crystal = MaterialFactory.Create(crystalColor),
                BroomHandle = MaterialFactory.Create(broomHandleColor),
                BroomBristle = MaterialFactory.Create(broomBristleColor)
            };
            ApplyWorldLook(world.Current);

            float roadWidth = laneWidth * LaneCount + 1f;
            portal = Portal.Create(transform, roadWidth, MaterialFactory.Create(portalColor));

            nextChunkStartZ = firstChunkStartZ;

            Obstacle.Preload();
            ModelPalette.Preload(Broom.ModelPath);

            // Oyun köprüde başlıyorsa giriş parçası olmaz, yol baştan köprüdür.
            if (IsDesert && bridgeSections.Length > 0 && bridgeSections[0].x <= 0)
            {
                roadKind = RoadKind.Bridge;
            }

#if UNITY_EDITOR
            Debug.Log("Köprü bölümleri (kitap): " + string.Join(", ", System.Array.ConvertAll(bridgeSections, s => s.x + "-" + s.y)));
#endif

            for (int i = 0; i < chunkCount; i++)
            {
                Chunk chunk = new Chunk(transform, chunkLength, roadWidth, materials, i);
                chunk.SetSceneryVisible(IsDesert);
                chunk.MoveTo(nextChunkStartZ);
                Populate(chunk);
                chunks.Add(chunk);
                nextChunkStartZ += chunkLength;
            }

            world.PortalOpened += OnPortalOpened;
            world.WorldChanged += OnWorldChanged;
            player.FlightStarted += OnFlightStarted;
            player.FlightEnded += OnFlightEnded;
        }

        private void OnDestroy()
        {
            if (world != null)
            {
                world.PortalOpened -= OnPortalOpened;
                world.WorldChanged -= OnWorldChanged;
            }

            if (player != null)
            {
                player.FlightStarted -= OnFlightStarted;
                player.FlightEnded -= OnFlightEnded;
            }
        }

        // Süpürge alınınca, uçuş boyunca gidilecek yolun üstüne havada bir kristal izi çizer.
        // İz yan şeritlere kayarak ilerler, oyuncu da şerit değiştirerek onları toplar.
        private void OnFlightStarted()
        {
            HideAirCrystals();

            float speed = player.CurrentSpeed;
            float startZ = player.transform.position.z + speed * player.RiseTime * 0.6f;
            float endZ = player.transform.position.z + speed * (player.FlightDuration - 1f);
            float y = player.GroundY + player.FlightHeight;

            int lane = Random.Range(0, LaneCount);
            int count = 0;
            for (float z = startZ; z < endZ; z += airCrystalSpacing)
            {
                if (count > 0 && count % airCrystalsPerLane == 0)
                {
                    lane = Mathf.Clamp(lane + (Random.value < 0.5f ? -1 : 1), 0, LaneCount - 1);
                }

                SpawnAirCrystal(count, (lane - 1) * laneWidth, y, z);
                count++;
            }
        }

        private void OnFlightEnded()
        {
            HideAirCrystals();
        }

        private void SpawnAirCrystal(int index, float x, float y, float z)
        {
            if (index >= airCrystals.Count)
            {
                Crystal crystal = Crystal.Create(transform, materials.Crystal);
                crystal.IsAerial = true;
                airCrystals.Add(crystal);
            }

            Crystal air = airCrystals[index];
            air.transform.position = new Vector3(x, y, z);
            air.gameObject.SetActive(true);
        }

        private void HideAirCrystals()
        {
            foreach (Crystal crystal in airCrystals)
            {
                crystal.gameObject.SetActive(false);
            }
        }

        private void Update()
        {
            while (chunks.Count > 0 && chunks[0].EndZ < player.transform.position.z - recycleDistanceBehind)
            {
                Chunk chunk = chunks[0];
                chunks.RemoveAt(0);

                chunk.MoveTo(nextChunkStartZ);
                Populate(chunk);
                chunks.Add(chunk);
                nextChunkStartZ += chunkLength;
            }
        }

        private void OnPortalOpened()
        {
            // Köprü sürüyorsa portal, köprünün çıkış parçasından sonraki kuma konur.
            int bridgeChunksLeft = roadKind == RoadKind.BridgeEntry ? 2 : roadKind == RoadKind.Bridge ? 1 : 0;
            portalZ = nextChunkStartZ + bridgeChunksLeft * chunkLength + portalOffset;
            portalActive = true;
            portal.Show(portalZ);
        }

        private void OnWorldChanged(WorldData data)
        {
            portalActive = false;
            portal.Hide();
            ApplyWorldLook(data);
            roadKind = RoadKind.Sand;
            foreach (Chunk chunk in chunks)
            {
                chunk.SetRoadKind(RoadKind.Sand);
                chunk.SetSceneryVisible(IsDesert);
            }
        }

        // Bir sonraki yol parçasının zemini: kum -> giriş -> köprü -> çıkış -> kum.
        private RoadKind NextRoadKind()
        {
            int crystals = ScoreManager.Instance != null ? ScoreManager.Instance.Crystals : 0;
            switch (roadKind)
            {
                case RoadKind.BridgeEntry:
                    return RoadKind.Bridge;
                case RoadKind.Bridge:
                    if (crystals < bridgeSections[bridgeStage].y) return RoadKind.Bridge;

                    bridgeStage++;
                    return RoadKind.BridgeExit;
                case RoadKind.BridgeExit:
                    return RoadKind.Sand;
                default:
                    return IsDesert && bridgeStage < bridgeSections.Length && crystals >= bridgeSections[bridgeStage].x
                        ? RoadKind.BridgeEntry
                        : RoadKind.Sand;
            }
        }

        // Kum zemin ve yol kenarı süsleri yalnız ilk dünyada (Çöl Diyarı).
        private bool IsDesert => world.WorldNumber == 1;

        // Malzemeler bütün parçalarda ortak olduğu için renk anında hepsinde değişir.
        private void ApplyWorldLook(WorldData data)
        {
            Texture2D sand = IsDesert ? Resources.Load<Texture2D>(DesertScenery.SandTexturePath) : null;
            Vector2 sandScale = new Vector2(
                (laneWidth * LaneCount + 1f) / DesertScenery.SandTextureMeters, chunkLength / DesertScenery.SandTextureMeters);
            materials.Ground.mainTexture = sand;
            materials.Ground.color = sand != null ? desertRoadTint : data.groundColor;
            materials.Ground.mainTextureScale = sandScale;
            materials.Terrain.mainTexture = sand;
            materials.Terrain.mainTextureScale = sandScale;
            materials.LowObstacle.color = data.lowObstacleColor;
            materials.TallObstacle.color = data.tallObstacleColor;

            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.Linear;
            RenderSettings.fogStartDistance = fogStart;
            RenderSettings.fogEndDistance = fogEnd;
            RenderSettings.fogColor = data.skyColor;

            Camera cam = Camera.main;
            if (cam != null)
            {
                cam.clearFlags = CameraClearFlags.SolidColor;
                cam.backgroundColor = data.skyColor;
            }
        }

        private bool IsInPortalZone(float z)
        {
            return portalActive && Mathf.Abs(z - portalZ) < portalClearRadius;
        }

        private void Populate(Chunk chunk)
        {
            chunk.ClearObstacles();

            roadKind = NextRoadKind();
            chunk.SetRoadKind(roadKind);

            float obstacleChance = world.Current.obstacleChance;

            int rows = Mathf.Max(1, Mathf.FloorToInt(chunkLength / rowSpacing));
            for (int row = 0; row < rows; row++)
            {
                float rowZ = chunk.StartZ + (row + 0.5f) * rowSpacing;

                if (rowZ < safeStartDistance || IsInPortalZone(rowZ) || Random.value > obstacleChance)
                {
                    System.Array.Clear(archInLastRow, 0, LaneCount);
                    continue;
                }

                // Bir şerit her zaman boş kalır, diğerlerinden biri veya ikisi engellenir.
                int freeLane = Random.Range(0, LaneCount);
                int blockedA = (freeLane + 1) % LaneCount;
                int blockedB = (freeLane + 2) % LaneCount;
                bool useA = !archInLastRow[blockedA];
                bool useB = !archInLastRow[blockedB];
                if (useA && useB && Random.value >= twoBlockedChance)
                {
                    useA = Random.value < 0.5f;
                    useB = !useA;
                }

                bool tallA = useA && Random.value < tallChance;
                bool tallB = useB && Random.value < tallChance;
                // Yan yana iki kemer ortak sınıra iki ayak koyar; sağdaki ortak ayağı soldakine bırakır.
                bool shared = tallA && tallB && Mathf.Abs(blockedA - blockedB) == 1;
                if (useA) SpawnInLane(chunk, blockedA, rowZ, tallA, shared && blockedA > blockedB);
                if (useB) SpawnInLane(chunk, blockedB, rowZ, tallB, shared && blockedB > blockedA);

                System.Array.Clear(archInLastRow, 0, LaneCount);
                archInLastRow[blockedA] = tallA;
                archInLastRow[blockedB] = tallB;
            }

            PopulatePickups(chunk, rows);
        }

        // Kristal sıraları ve süpürge, engel sıralarının tam ortasına (iki sıra arasına) konur.
        // Böylece hiçbiri engelin içine denk gelmez. Süpürge çıkacaksa o sıradaki kristallerin yerini alır.
        private void PopulatePickups(Chunk chunk, int rows)
        {
            chunk.ClearCrystals();
            chunk.ClearBroom();

            int broomRow = Random.value < broomChance ? Random.Range(0, rows) : -1;

            for (int row = 0; row < rows; row++)
            {
                float lineZ = chunk.StartZ + row * rowSpacing;

                if (lineZ < crystalSafeStartDistance) continue;
                if (IsInPortalZone(lineZ)) continue;

                float x = (Random.Range(0, LaneCount) - 1) * laneWidth;

                if (row == broomRow)
                {
                    chunk.SpawnBroom(x, broomHeight, lineZ);
                    continue;
                }

                if (Random.value > crystalLineChance) continue;

                float firstZ = lineZ - (crystalsPerLine - 1) * 0.5f * crystalSpacing;
                for (int i = 0; i < crystalsPerLine; i++)
                {
                    chunk.SpawnCrystal(x, crystalHeight, firstZ + i * crystalSpacing);
                }
            }
        }

        private void SpawnInLane(Chunk chunk, int laneSlot, float worldZ, bool tall, bool sharedPillar)
        {
            float x = (laneSlot - 1) * laneWidth;
            chunk.SpawnObstacle(x, worldZ, laneWidth * 0.8f, tall, sharedPillar);
        }
    }
}
