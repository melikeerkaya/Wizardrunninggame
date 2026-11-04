using System;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace PembeBuyucu
{
    public enum GameState
    {
        Menu,
        Playing,
        GameOver
    }

    /// <summary>
    /// Oyunun durumunu (menü / oynuyor / bitti) tutar ve yeniden başlatmayı yönetir.
    /// Sahnede tek bir tane olmalı.
    /// </summary>
    public class GameManager : MonoBehaviour
    {
        // Yeniden başlatınca menüyü atlayıp doğrudan koşuya geçmek için.
        private static bool skipMenuOnLoad;

        public static GameManager Instance { get; private set; }

        [Tooltip("Boş bırakılırsa sahnede otomatik bulunur.")]
        [SerializeField] private InputReader input;

        [Tooltip("Oyun bittikten sonra yeniden başlatma girişinin kabul edileceği bekleme süresi (saniye).")]
        [SerializeField] private float restartDelay = 0.5f;

        private float gameOverTime;

        public GameState State { get; private set; } = GameState.Menu;
        public bool IsPlaying => State == GameState.Playing;

        /// <summary>Koşu bittiğinde bir kez tetiklenir.</summary>
        public event Action RunEnded;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics()
        {
            skipMenuOnLoad = false;
        }

        private void Awake()
        {
            Instance = this;
            State = skipMenuOnLoad ? GameState.Playing : GameState.Menu;
            skipMenuOnLoad = false;
            Time.timeScale = 1f;

            if (input == null)
            {
                input = FindFirstObjectByType<InputReader>();
            }
        }

        private void OnDestroy()
        {
            if (Instance == this)
            {
                Instance = null;
            }
        }

        private void Update()
        {
            if (input == null) return;

            if (State == GameState.Menu)
            {
                if (input.JumpPressed)
                {
                    StartRun();
                }
            }
            else if (State == GameState.GameOver)
            {
                if (input.RestartPressed || input.TapPressed)
                {
                    TryRestart();
                }
            }
        }

        /// <summary>Menüden koşuyu başlatır.</summary>
        public void StartRun()
        {
            if (State != GameState.Menu) return;

            State = GameState.Playing;
        }

        /// <summary>Koşuyu bitirir. Birden fazla çağrılırsa yalnızca ilki geçerli olur.</summary>
        public void EndRun()
        {
            if (State != GameState.Playing) return;

            State = GameState.GameOver;
            gameOverTime = Time.unscaledTime;
            RunEnded?.Invoke();
        }

        /// <summary>Oyun bittiyse ve bekleme süresi geçtiyse sahneyi baştan yükler.</summary>
        public void TryRestart()
        {
            if (State != GameState.GameOver) return;
            if (Time.unscaledTime - gameOverTime < restartDelay) return;

            // Sahne Build Profiles > Scene List içinde olmalı.
            skipMenuOnLoad = true;
            SceneManager.LoadScene(SceneManager.GetActiveScene().buildIndex);
        }
    }
}
