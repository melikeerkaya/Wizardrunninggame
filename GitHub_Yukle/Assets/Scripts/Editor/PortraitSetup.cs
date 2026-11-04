using UnityEditor;
using UnityEngine;

namespace PembeBuyucu
{
    /// <summary>
    /// Oyun Subway Surfers gibi dikey ekranda oynanır (arayüz 1080x1920'ye göre kurulu, kamera dikey ekrana göre ayarlı).
    /// Proje ayarını bir kez dikeye çeker; sonra elle değiştirilirse ellenmez.
    /// </summary>
    internal static class PortraitSetup
    {
        [InitializeOnLoadMethod]
        private static void Apply()
        {
            string key = "PembeBuyucu.PortraitSet." + Application.dataPath;
            if (EditorPrefs.GetBool(key)) return;

            PlayerSettings.defaultInterfaceOrientation = UIOrientation.Portrait;
            EditorPrefs.SetBool(key, true);
            Debug.Log("Oyun dikey ekrana ayarlandı (Player Settings > Resolution and Presentation > Default Orientation: Portrait).");
        }
    }
}
