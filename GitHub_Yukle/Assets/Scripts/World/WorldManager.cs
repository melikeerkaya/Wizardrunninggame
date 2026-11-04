using System;
using System.Collections.Generic;
using UnityEngine;

namespace PembeBuyucu
{
    /// <summary>
    /// Dünyaların listesini ve şu anki dünyayı tutar.
    /// Bir dünyada yeterli kristal toplanınca portalın açıldığını duyurur,
    /// oyuncu portala girince sonraki dünyaya geçer.
    /// Sahnede tek bir tane olmalı. Eksikse ChunkSpawner varsayılan değerlerle kendisi oluşturur.
    /// </summary>
    public class WorldManager : MonoBehaviour
    {
        public static WorldManager Instance { get; private set; }

        [SerializeField] private List<WorldData> worlds = CreateDefaultWorlds();

        private int index;
        private int crystalsAtWorldStart;
        private float runTime;

        /// <summary>Gereken kristal toplanınca, portal açıldığında bir kez tetiklenir.</summary>
        public event Action PortalOpened;

        /// <summary>Oyuncu portaldan geçip yeni dünyaya girince tetiklenir.</summary>
        public event Action<WorldData> WorldChanged;

        public WorldData Current => worlds[index];
        public int WorldNumber => index + 1;
        public bool HasNextWorld => index < worlds.Count - 1;
        public bool IsPortalOpen { get; private set; }
        public int CrystalsNeeded => Current.crystalsToOpenPortal;

        public int CrystalsInWorld =>
            ScoreManager.Instance != null ? ScoreManager.Instance.Crystals - crystalsAtWorldStart : 0;

        private void Awake()
        {
            Instance = this;

            if (worlds == null || worlds.Count == 0)
            {
                worlds = CreateDefaultWorlds();
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
            if (GameManager.Instance == null || !GameManager.Instance.IsPlaying) return;

            runTime += Time.deltaTime;

            if (IsPortalOpen || !HasNextWorld) return;

            if (CrystalsInWorld >= CrystalsNeeded)
            {
                IsPortalOpen = true;
                Debug.Log("Portal açıldı: " + Mathf.RoundToInt(runTime) + " sn, " + CrystalsInWorld + " kristal (" + Current.name + ")");
                PortalOpened?.Invoke();
            }
        }

        /// <summary>Oyuncu portala girince çağrılır.</summary>
        public void EnterNextWorld()
        {
            if (!IsPortalOpen || !HasNextWorld) return;

            index++;
            IsPortalOpen = false;
            crystalsAtWorldStart = ScoreManager.Instance != null ? ScoreManager.Instance.Crystals : 0;
            WorldChanged?.Invoke(Current);
        }

        private static List<WorldData> CreateDefaultWorlds()
        {
            // Engel renkleri bütün dünyalarda aynı: turuncu = zıpla, kırmızı = şerit değiştir.
            // İlk dünyanın (Çöl Diyarı) hedefi 600, diğerleri şimdilik test için 30. Son dünyada portal yok, hedefi kullanılmaz.
            Color low = new Color(0.95f, 0.55f, 0.2f);
            Color tall = new Color(0.8f, 0.2f, 0.25f);

            return new List<WorldData>
            {
                new WorldData("ÇÖL", 600, new Color(0.85f, 0.75f, 0.55f), new Color(0.65f, 0.82f, 0.95f), low, tall, 1f, 0.75f),
                new WorldData("ORMAN", 30, new Color(0.35f, 0.6f, 0.3f), new Color(0.6f, 0.8f, 0.7f), low, tall, 1.05f, 0.78f),
                new WorldData("BUZUL", 30, new Color(0.85f, 0.93f, 0.98f), new Color(0.75f, 0.88f, 0.97f), low, tall, 1.1f, 0.8f),
                new WorldData("SU DÜNYASI", 30, new Color(0.2f, 0.5f, 0.7f), new Color(0.3f, 0.75f, 0.85f), low, tall, 1.15f, 0.83f),
                new WorldData("GÖKYÜZÜ ZİRVESİ", 30, new Color(0.95f, 0.85f, 0.95f), new Color(0.75f, 0.7f, 0.95f), low, tall, 1.2f, 0.85f)
            };
        }
    }
}
