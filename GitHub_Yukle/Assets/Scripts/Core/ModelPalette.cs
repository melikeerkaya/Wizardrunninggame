using System.Collections.Generic;
using UnityEngine;

namespace PembeBuyucu
{
    /// <summary>
    /// 3B modellerin renkleri. Modellerin parça adları "RenkAnahtarı_Parça" biçimindedir
    /// (bkz. Art/ klasöründeki Blender betikleri). Renkler burada kodla verilir,
    /// böylece Unity'nin malzeme dönüştürmesine bağlı kalmayız ve rengi tek yerden değiştirebiliriz.
    /// </summary>
    public static class ModelPalette
    {
        private static readonly Dictionary<string, Color> Colors = new Dictionary<string, Color>
        {
            // Büyücü kız (Art/build_girl4.py)
            { "Skin", new Color(1f, 0.75f, 0.62f) },
            { "Blush", new Color(0.96f, 0.52f, 0.5f) },
            { "Lip", new Color(0.86f, 0.42f, 0.42f) },
            { "Mouth", new Color(0.55f, 0.18f, 0.2f) },
            { "Sclera", new Color(0.98f, 0.96f, 0.94f) },
            { "Iris", new Color(0.52f, 0.25f, 0.17f) },
            { "Pupil", new Color(0.16f, 0.07f, 0.06f) },
            { "Shine", Color.white },
            { "Lash", new Color(0.2f, 0.09f, 0.08f) },
            { "Brow", new Color(0.38f, 0.17f, 0.14f) },
            { "Hair", new Color(0.8f, 0.4f, 0.42f) },
            { "HairLight", new Color(0.92f, 0.55f, 0.53f) },
            { "HairDark", new Color(0.6f, 0.27f, 0.32f) },
            { "Hat", new Color(0.86f, 0.42f, 0.53f) },
            { "HatDark", new Color(0.74f, 0.33f, 0.46f) },
            { "HatBand", new Color(0.33f, 0.21f, 0.27f) },
            { "HatGem", new Color(0.9f, 0.42f, 0.3f) },
            { "Brass", new Color(0.95f, 0.67f, 0.33f) },
            { "Coat", new Color(0.98f, 0.9f, 0.86f) },
            { "CoatBack", new Color(0.93f, 0.52f, 0.62f) },
            { "CoatTrim", new Color(0.78f, 0.33f, 0.44f) },
            { "Top", new Color(0.3f, 0.24f, 0.31f) },
            { "Shorts", new Color(0.34f, 0.27f, 0.33f) },
            { "Stocking", new Color(0.27f, 0.21f, 0.24f) },
            { "Leather", new Color(0.45f, 0.27f, 0.22f) },
            { "Boot", new Color(0.45f, 0.24f, 0.27f) },
            { "BootCuff", new Color(0.76f, 0.5f, 0.46f) },
            { "Sole", new Color(0.9f, 0.8f, 0.7f) },
            { "Glove", new Color(0.4f, 0.24f, 0.23f) },
            // Süpürge, küpler, palmiyeler ve kapı
            { "Gold", new Color(1f, 0.75f, 0f) },
            { "Cream", new Color(1f, 0.97f, 0.9f) },
            { "Wood", new Color(0.6f, 0.33f, 0.1f) },
            { "Band", new Color(1f, 0.15f, 0.55f) },
            { "Straw", new Color(1f, 0.78f, 0.1f) },
            { "StrawDark", new Color(0.95f, 0.5f, 0.05f) },
            { "Gem", new Color(0.55f, 0.25f, 1f) },
            { "Trunk", new Color(0.8f, 0.45f, 0.17f) },
            { "TrunkLight", new Color(0.86f, 0.53f, 0.22f) },
            { "Leaf", new Color(0.38f, 0.8f, 0.12f) },
            { "LeafDark", new Color(0.26f, 0.66f, 0.1f) },
            { "LeafLight", new Color(0.52f, 0.88f, 0.2f) },
            { "Coconut", new Color(0.45f, 0.27f, 0.12f) },
            { "Sandstone", new Color(0.88f, 0.58f, 0.4f) },
            { "SandstoneDark", new Color(0.78f, 0.48f, 0.32f) },
            { "SandstoneLight", new Color(0.94f, 0.68f, 0.48f) },
            { "SandstoneDeep", new Color(0.62f, 0.36f, 0.25f) },
            { "Dune", new Color(0.85f, 0.75f, 0.55f) },
            { "Iron", new Color(0.56f, 0.58f, 0.62f) },
            { "Bronze", new Color(0.8f, 0.55f, 0.22f) },
            { "BronzeDark", new Color(0.55f, 0.36f, 0.16f) },
            { "Sand", new Color(0.95f, 0.82f, 0.58f) },
            { "Clay", new Color(0.86f, 0.46f, 0.32f) },
            { "ClayDark", new Color(0.22f, 0.13f, 0.1f) },
            { "Earth", new Color(0.62f, 0.5f, 0.34f) },
            { "EarthDark", new Color(0.4f, 0.3f, 0.2f) },
            { "Plum", new Color(0.5f, 0.36f, 0.42f) },
            { "Turquoise", new Color(0.2f, 0.75f, 0.8f) },
            { "PotOrange", new Color(0.95f, 0.58f, 0.25f) }
        };

        // Düz renk yerine kendi dokusunu kullanan parçalar: anahtar ve dokunun Resources yolu.
        private static readonly Dictionary<string, string> Textures = new Dictionary<string, string>
        {
            { "Archway", "Models/Desert/Archway_basecolor" },
            { "Broom", "Models/Broom_basecolor" },
            { "SpellBook", "Models/SpellBook_basecolor" },
            { "SceneArch", "Models/Desert/Scenery/SceneArch_basecolor" },
            { "SceneWall", "Models/Desert/Scenery/SceneWall_basecolor" },
            { "SceneColumns", "Models/Desert/Scenery/SceneColumns_basecolor" },
            { "SceneStump", "Models/Desert/Scenery/SceneStump_basecolor" },
            { "Cactus", "Models/Desert/Scenery/Cactus_basecolor" },
            { "BarrelCactus", "Models/Desert/Scenery/BarrelCactus_basecolor" },
            { "PricklyPear", "Models/Desert/Scenery/PricklyPear_basecolor" },
            { "Palisade", "Models/Desert/Scenery/Palisade_basecolor" },
            { "Palm", "Models/Desert/Scenery/Palm_basecolor" },
            { "BridgeDeck", "Models/Desert/BridgeDeck_basecolor" }
        };

        // Aynı renk anahtarı için tek malzeme paylaşılır (hem performans hem tutarlılık için).
        private static readonly Dictionary<string, Material> Materials = new Dictionary<string, Material>();

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics()
        {
            Materials.Clear();
        }

        /// <summary>Modeli, dokularını ve malzemelerini önceden yükler: koşu sırasında ilk gerektiğinde diskten okunup oyunu
        /// takıldırmasın. Geçici kopya hemen silinir.</summary>
        public static void Preload(string path)
        {
            GameObject prefab = Resources.Load<GameObject>(path);
            if (prefab == null) return;

            GameObject copy = Object.Instantiate(prefab);
            Apply(copy.transform);
            Object.Destroy(copy);
        }

        /// <summary>Modelin bütün parçalarına adlarındaki anahtara göre renk verir.</summary>
        public static void Apply(Transform model)
        {
            foreach (Renderer part in model.GetComponentsInChildren<Renderer>(true))
            {
                string key = part.name.Split('_')[0];
                if (!Materials.TryGetValue(key, out Material material) || material == null)
                {
                    material = CreateMaterial(key);
                    if (material == null) continue;

                    Materials[key] = material;
                }

                part.sharedMaterial = material;
            }
        }

        private static Material CreateMaterial(string key)
        {
            if (Colors.TryGetValue(key, out Color color)) return MaterialFactory.Create(color);
            if (!Textures.TryGetValue(key, out string path)) return null;

            Texture2D texture = Resources.Load<Texture2D>(path);
            if (texture == null) return null;

            Material material = MaterialFactory.Create(Color.white);
            material.mainTexture = texture;
            return material;
        }
    }
}
