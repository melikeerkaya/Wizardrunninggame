using UnityEngine;
using UnityEngine.Events;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem.UI;
using UnityEngine.UI;

namespace PembeBuyucu
{
    /// <summary>
    /// Oyun arayüzü: ana menü, oyun içi skor göstergesi ve oyun sonu ekranı.
    /// Canvas ve bütün öğeler çalışma anında kodla kurulur, sahnede ayrıca bir ayar gerekmez.
    /// Ekran düzeni oran (anchor) ile verildiği için hem yatay hem dikey ekranda çalışır.
    /// </summary>
    public class GameUI : MonoBehaviour
    {
        private static readonly Color PanelDim = new Color(0.1f, 0.05f, 0.15f, 0.7f);
        private static readonly Color ButtonColor = new Color(0.95f, 0.45f, 0.7f);
        private static readonly Color CrystalTextColor = new Color(0.4f, 0.95f, 1f);
        private static readonly Color HighlightColor = new Color(1f, 0.9f, 0.3f);

        [Tooltip("Boş bırakılırsa sahnede otomatik bulunur.")]
        [SerializeField] private ScoreManager score;

        private Font font;
        private GameObject menuPanel;
        private GameObject hudPanel;
        private GameObject gameOverPanel;

        private Text menuHighScoreText;
        private Text hudCrystalText;
        private Text hudWorldText;
        private Text hudFlightText;
        private Text bannerText;
        private PlayerController player;
        private int shownFlightTenths = -1;
        private Text overCrystalText;
        private Text overRecordText;

        private WorldManager world;
        private float bannerHideTime;
        private GameState? shownState;
        private int shownCrystals = -1;
        private int shownWorldKey = -1;

        private void Awake()
        {
            if (score == null)
            {
                score = FindFirstObjectByType<ScoreManager>();
            }

            font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");

            EnsureEventSystem();
            BuildCanvas();
        }

        private void Start()
        {
            // WorldManager bazen başka bir scriptin Awake'inde oluşturulur, bu yüzden Start'ta aranır.
            player = FindFirstObjectByType<PlayerController>();
            world = FindFirstObjectByType<WorldManager>();
            if (world != null)
            {
                world.PortalOpened += OnPortalOpened;
                world.WorldChanged += OnWorldChanged;
            }
        }

        private void OnDestroy()
        {
            if (world != null)
            {
                world.PortalOpened -= OnPortalOpened;
                world.WorldChanged -= OnWorldChanged;
            }
        }

        private void OnPortalOpened()
        {
            ShowBanner("PORTAL AÇILDI!");
        }

        private void OnWorldChanged(WorldData data)
        {
            ShowBanner("DÜNYA " + world.WorldNumber + ": " + data.name);
        }

        private void ShowBanner(string message)
        {
            bannerText.text = message;
            bannerText.gameObject.SetActive(true);
            bannerHideTime = Time.unscaledTime + 3f;
        }

        private string BuildWorldLabel()
        {
            if (world == null) return "";
            if (world.IsPortalOpen) return world.Current.name + "  -  PORTAL AÇIK!";
            if (!world.HasNextWorld) return world.Current.name;

            return world.Current.name + "  " + world.CrystalsInWorld + " / " + world.CrystalsNeeded;
        }

        private void Update()
        {
            if (score == null || GameManager.Instance == null) return;

            GameState state = GameManager.Instance.State;
            if (shownState != state)
            {
                shownState = state;
                ShowState(state);
            }

            if (state == GameState.Playing)
            {
                if (bannerText.gameObject.activeSelf && Time.unscaledTime >= bannerHideTime)
                {
                    bannerText.gameObject.SetActive(false);
                }

                int flightTenths = player != null ? Mathf.CeilToInt(player.FlightTimeLeft * 10f) : 0;
                if (shownFlightTenths != flightTenths)
                {
                    shownFlightTenths = flightTenths;
                    hudFlightText.text = flightTenths > 0 ? "SÜPÜRGE: " + (flightTenths / 10f).ToString("0.0") : "";
                }

                int worldKey = world == null ? 0 : world.WorldNumber * 2 + (world.IsPortalOpen ? 1 : 0);
                if (shownCrystals != score.Crystals || shownWorldKey != worldKey)
                {
                    shownCrystals = score.Crystals;
                    shownWorldKey = worldKey;
                    hudCrystalText.text = "Kristal: " + shownCrystals;
                    hudWorldText.text = BuildWorldLabel();
                }
            }
        }

        private void ShowState(GameState state)
        {
            menuPanel.SetActive(state == GameState.Menu);
            hudPanel.SetActive(state == GameState.Playing);
            gameOverPanel.SetActive(state == GameState.GameOver);

            if (state == GameState.Menu)
            {
                menuHighScoreText.text = "En çok kristal: " + score.HighScore;
            }
            else if (state == GameState.GameOver)
            {
                overCrystalText.text = "Kristal: " + score.Crystals;
                overRecordText.text = score.IsNewHighScore
                    ? "YENİ REKOR!"
                    : "En çok kristal: " + score.HighScore;
                overRecordText.color = score.IsNewHighScore ? HighlightColor : Color.white;
            }
        }

        // ---------- Kurulum ----------

        private static void EnsureEventSystem()
        {
            if (FindFirstObjectByType<EventSystem>() != null) return;

            // Projede yeni Input System kullanıldığı için StandaloneInputModule yerine bu modül gerekir.
            GameObject go = new GameObject("EventSystem");
            go.AddComponent<EventSystem>();
            go.AddComponent<InputSystemUIInputModule>().AssignDefaultActions();
        }

        private void BuildCanvas()
        {
            GameObject canvasObject = new GameObject("GameCanvas");
            canvasObject.transform.SetParent(transform, false);

            Canvas canvas = canvasObject.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;

            CanvasScaler scaler = canvasObject.AddComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1080f, 1920f);
            scaler.matchWidthOrHeight = 0.5f;

            canvasObject.AddComponent<GraphicRaycaster>();

            BuildMenu(canvasObject.transform);
            BuildHud(canvasObject.transform);
            BuildGameOver(canvasObject.transform);
        }

        private void BuildMenu(Transform parent)
        {
            menuPanel = CreatePanel(parent, "Menu", PanelDim);

            CreateText(menuPanel.transform, "Title", "PEMBE BÜYÜCÜ", 110, 0.68f, new Vector2(1000f, 160f));
            menuHighScoreText = CreateText(menuPanel.transform, "HighScore", "", 50, 0.55f, new Vector2(1000f, 80f));
            CreateButton(menuPanel.transform, "OYNA", 0.42f, new Vector2(360f, 130f), OnPlayClicked);
            CreateText(menuPanel.transform, "Hint",
                "A / D veya ok tuşları: şerit değiştir\nBoşluk: zıpla (mobilde kaydır)", 36, 0.28f, new Vector2(1000f, 120f));
        }

        private void BuildHud(Transform parent)
        {
            hudPanel = CreatePanel(parent, "Hud", null);

            hudCrystalText = CreateCornerText(hudPanel.transform, "Crystals", new Vector2(0f, 1f), new Vector2(40f, -40f), TextAnchor.UpperLeft, CrystalTextColor);
            hudWorldText = CreateCornerText(hudPanel.transform, "World", new Vector2(0f, 1f), new Vector2(40f, -110f), TextAnchor.UpperLeft, Color.white, 40);

            hudFlightText = CreateCornerText(hudPanel.transform, "Flight", new Vector2(0f, 1f), new Vector2(40f, -165f), TextAnchor.UpperLeft, HighlightColor, 44);

            bannerText = CreateText(hudPanel.transform, "Banner", "", 90, 0.78f, new Vector2(1000f, 140f));
            bannerText.color = HighlightColor;
            bannerText.gameObject.SetActive(false);
        }

        private void BuildGameOver(Transform parent)
        {
            gameOverPanel = CreatePanel(parent, "GameOver", PanelDim);

            CreateText(gameOverPanel.transform, "Title", "OYUN BİTTİ", 110, 0.70f, new Vector2(1000f, 160f));
            overCrystalText = CreateText(gameOverPanel.transform, "Crystals", "", 70, 0.57f, new Vector2(1000f, 100f));
            overRecordText = CreateText(gameOverPanel.transform, "Record", "", 50, 0.47f, new Vector2(1000f, 80f));
            CreateButton(gameOverPanel.transform, "TEKRAR OYNA", 0.30f, new Vector2(520f, 130f), OnRetryClicked);
            CreateText(gameOverPanel.transform, "Hint", "veya R tuşuna bas / ekrana dokun", 34, 0.22f, new Vector2(1000f, 60f));
        }

        // ---------- Düğmeler ----------

        private static void OnPlayClicked()
        {
            if (GameManager.Instance != null)
            {
                GameManager.Instance.StartRun();
            }
        }

        private static void OnRetryClicked()
        {
            if (GameManager.Instance != null)
            {
                GameManager.Instance.TryRestart();
            }
        }

        // ---------- Yardımcılar ----------

        private static GameObject CreatePanel(Transform parent, string name, Color? background)
        {
            GameObject go = new GameObject(name, typeof(RectTransform));
            go.transform.SetParent(parent, false);

            RectTransform rect = go.GetComponent<RectTransform>();
            rect.anchorMin = Vector2.zero;
            rect.anchorMax = Vector2.one;
            rect.offsetMin = Vector2.zero;
            rect.offsetMax = Vector2.zero;

            if (background.HasValue)
            {
                go.AddComponent<Image>().color = background.Value;
            }

            return go;
        }

        // Ekranın yatay ortasında, yüksekliğin verilen oranına (0-1) yerleştirilen metin.
        private Text CreateText(Transform parent, string name, string content, int size, float heightRatio, Vector2 boxSize)
        {
            Text text = CreateTextObject(parent, name, content, size, TextAnchor.MiddleCenter, Color.white);

            RectTransform rect = text.rectTransform;
            rect.anchorMin = rect.anchorMax = new Vector2(0.5f, heightRatio);
            rect.pivot = new Vector2(0.5f, 0.5f);
            rect.sizeDelta = boxSize;
            rect.anchoredPosition = Vector2.zero;
            return text;
        }

        // Ekranın bir köşesine yaslanan metin (skor göstergesi için).
        private Text CreateCornerText(Transform parent, string name, Vector2 corner, Vector2 offset, TextAnchor alignment, Color color, int size = 56)
        {
            Text text = CreateTextObject(parent, name, "", size, alignment, color);

            RectTransform rect = text.rectTransform;
            rect.anchorMin = rect.anchorMax = corner;
            rect.pivot = corner;
            rect.sizeDelta = new Vector2(500f, 100f);
            rect.anchoredPosition = offset;
            return text;
        }

        private Text CreateTextObject(Transform parent, string name, string content, int size, TextAnchor alignment, Color color)
        {
            GameObject go = new GameObject(name, typeof(RectTransform));
            go.transform.SetParent(parent, false);

            Text text = go.AddComponent<Text>();
            text.font = font;
            text.fontSize = size;
            text.fontStyle = FontStyle.Bold;
            text.alignment = alignment;
            text.color = color;
            text.text = content;
            text.horizontalOverflow = HorizontalWrapMode.Overflow;
            text.verticalOverflow = VerticalWrapMode.Overflow;
            text.raycastTarget = false;
            return text;
        }

        private void CreateButton(Transform parent, string label, float heightRatio, Vector2 size, UnityAction onClick)
        {
            GameObject go = new GameObject(label + " Button", typeof(RectTransform));
            go.transform.SetParent(parent, false);

            RectTransform rect = go.GetComponent<RectTransform>();
            rect.anchorMin = rect.anchorMax = new Vector2(0.5f, heightRatio);
            rect.pivot = new Vector2(0.5f, 0.5f);
            rect.sizeDelta = size;
            rect.anchoredPosition = Vector2.zero;

            Image image = go.AddComponent<Image>();
            image.color = ButtonColor;

            Button button = go.AddComponent<Button>();
            button.targetGraphic = image;
            button.onClick.AddListener(onClick);

            Text text = CreateTextObject(go.transform, "Label", label, 56, TextAnchor.MiddleCenter, Color.white);
            RectTransform textRect = text.rectTransform;
            textRect.anchorMin = Vector2.zero;
            textRect.anchorMax = Vector2.one;
            textRect.offsetMin = Vector2.zero;
            textRect.offsetMax = Vector2.zero;
        }
    }
}
