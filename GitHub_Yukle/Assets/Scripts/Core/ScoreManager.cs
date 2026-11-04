using UnityEngine;

namespace PembeBuyucu
{
    /// <summary>
    /// Skor = toplanan kristal sayısı. Portal da bu sayıya göre açılacak.
    /// Koşu bitince en yüksek kristal sayısını ve toplam kristali cihaza kaydeder.
    /// </summary>
    public class ScoreManager : MonoBehaviour
    {
        private const string HighScoreKey = "HighCrystals";
        private const string TotalCrystalsKey = "TotalCrystals";

        public static ScoreManager Instance { get; private set; }

        /// <summary>Bu koşuda toplanan kristal sayısı (yani skor).</summary>
        public int Crystals { get; private set; }
        public int HighScore { get; private set; }
        public int TotalCrystals { get; private set; }
        public bool IsNewHighScore { get; private set; }

        private void Awake()
        {
            Instance = this;
            HighScore = PlayerPrefs.GetInt(HighScoreKey, 0);
            TotalCrystals = PlayerPrefs.GetInt(TotalCrystalsKey, 0);
        }

        private void Start()
        {
            if (GameManager.Instance != null)
            {
                GameManager.Instance.RunEnded += OnRunEnded;
            }
        }

        private void OnDestroy()
        {
            if (GameManager.Instance != null)
            {
                GameManager.Instance.RunEnded -= OnRunEnded;
            }

            if (Instance == this)
            {
                Instance = null;
            }
        }

        public void AddCrystal()
        {
            if (GameManager.Instance == null || !GameManager.Instance.IsPlaying) return;

            Crystals++;
        }

        private void OnRunEnded()
        {
            IsNewHighScore = Crystals > HighScore;
            if (IsNewHighScore)
            {
                HighScore = Crystals;
                PlayerPrefs.SetInt(HighScoreKey, HighScore);
            }

            TotalCrystals += Crystals;
            PlayerPrefs.SetInt(TotalCrystalsKey, TotalCrystals);
            PlayerPrefs.Save();
        }
    }
}
