using System;
using UnityEngine;

namespace PembeBuyucu
{
    /// <summary>
    /// Bir dünyanın ayarları. Yeni dünya eklemek, WorldManager listesine bir satır eklemek kadar basittir.
    /// </summary>
    [Serializable]
    public class WorldData
    {
        public string name;

        [Tooltip("Bu dünyada, portalın açılması için toplanması gereken kristal sayısı.")]
        public int crystalsToOpenPortal;

        [Header("Görünüm")]
        public Color groundColor;
        public Color skyColor;
        public Color lowObstacleColor;
        public Color tallObstacleColor;

        [Header("Zorluk")]
        [Tooltip("Koşu hızının çarpanı. 1 = normal.")]
        public float speedMultiplier;

        [Tooltip("Her engel sırasının çıkma ihtimali (0-1).")]
        [Range(0f, 1f)] public float obstacleChance;

        public WorldData(string name, int crystalsToOpenPortal, Color groundColor, Color skyColor,
            Color lowObstacleColor, Color tallObstacleColor, float speedMultiplier, float obstacleChance)
        {
            this.name = name;
            this.crystalsToOpenPortal = crystalsToOpenPortal;
            this.groundColor = groundColor;
            this.skyColor = skyColor;
            this.lowObstacleColor = lowObstacleColor;
            this.tallObstacleColor = tallObstacleColor;
            this.speedMultiplier = speedMultiplier;
            this.obstacleChance = obstacleChance;
        }
    }
}
