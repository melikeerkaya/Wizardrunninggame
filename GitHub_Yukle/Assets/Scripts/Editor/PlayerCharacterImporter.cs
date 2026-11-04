using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace PembeBuyucu
{
    /// <summary>
    /// Oyuncu karakterinin dosyalarını içe aktarır ve Resources/PlayerCharacter varlığına bağlar.
    /// Görünüş: Assets/Characters/Wizard/Wizard.fbx (Tripo büyücüsü, Art/convert_witch.py ile hazırlandı) varsa o,
    /// yoksa Mixamo Ch29 kızı (Ch29_Run.fbx). İkisi de Humanoid'dir, böylece aynı animasyonları oynatırlar.
    /// Animasyonlar: Assets/Characters/Ch29 altındaki Mixamo dosyaları. Dosya adının son parçası animasyonun adı olur
    /// (Ch29_Run → Run). Koşu döngüdür. İleri gidiş kök hareketi olarak kalır ve oyunda kullanılmaz (karakter yerinde
    /// koşar, ilerlemeyi PlayerController yapar); dikey hareket pozun içindedir.
    /// Her iki modelin dokularını ve URP malzemesini de kurar.
    /// </summary>
    public class PlayerCharacterImporter : AssetPostprocessor
    {
        private const string Folder = "Assets/Characters/Ch29/";
        private const string ModelFile = Folder + "Ch29_Run.fbx";
        private const string TextureFolder = Folder + "Textures";
        private const string MaterialFolder = Folder + "Materials";
        private const string WizardFolder = "Assets/Characters/Wizard/";
        private const string WizardFile = WizardFolder + "Wizard.fbx";
        private const string WizardMaterial = WizardFolder + "Materials/Wizard.mat";
        private const string CharacterAsset = "Assets/Resources/" + PlayerCharacter.ResourcePath + ".asset";
        // Düşük parlaklık: ince detaylı karakterde parlama noktaları hareket ederken kayan pikseller gibi görünür.
        private const float Smoothness = 0.15f;

        // Bu betik derlenmeden önce içe aktarılmış dosyalar bir kez yeniden içe aktarılır.
        private static readonly HashSet<string> Reimported = new HashSet<string>();

        private void OnPreprocessModel()
        {
            if (assetPath == WizardFile)
            {
                ModelImporter wizard = (ModelImporter)assetImporter;
                wizard.animationType = ModelImporterAnimationType.Human;
                wizard.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
                wizard.importAnimation = false;
                wizard.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;
                return;
            }

            if (!assetPath.StartsWith(Folder)) return;

            ModelImporter importer = (ModelImporter)assetImporter;
            importer.animationType = ModelImporterAnimationType.Human;
            importer.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
            importer.importAnimation = true;
            // Görünüş yalnız koşu dosyasından alınır; diğer dosyaların malzeme ve dokularına gerek yok.
            importer.materialImportMode = assetPath == ModelFile
                ? ModelImporterMaterialImportMode.ImportViaMaterialDescription
                : ModelImporterMaterialImportMode.None;
        }

        private void OnPreprocessAnimation()
        {
            if (!assetPath.StartsWith(Folder)) return;

            ModelImporter importer = (ModelImporter)assetImporter;
            string clipName = ClipName(assetPath);
            ModelImporterClipAnimation[] clips = importer.defaultClipAnimations;
            foreach (ModelImporterClipAnimation clip in clips)
            {
                clip.name = clipName;
                clip.loopTime = clipName == "Run";
                clip.lockRootRotation = true;
                clip.keepOriginalOrientation = true;
                clip.lockRootHeightY = true;
                clip.keepOriginalPositionY = true;
                clip.lockRootPositionXZ = false;
            }

            importer.clipAnimations = clips;
        }

        private static void OnPostprocessAllAssets(string[] imported, string[] deleted, string[] moved, string[] movedFrom)
        {
            bool changed = false;
            foreach (string path in imported)
            {
                if (!(path.StartsWith(Folder) || path.StartsWith(WizardFolder)) ||
                    !path.EndsWith(".fbx", System.StringComparison.OrdinalIgnoreCase)) continue;

                if (AssetImporter.GetAtPath(path) is ModelImporter importer &&
                    importer.animationType != ModelImporterAnimationType.Human && Reimported.Add(path))
                {
                    importer.SaveAndReimport();
                    continue;
                }

                changed = true;
            }

            if (changed)
            {
                EditorApplication.delayCall -= LinkCharacter;
                EditorApplication.delayCall += LinkCharacter;
                ScheduleLookSetup();
            }
        }

        // Dokular, dosyalar zaten içe aktarılmışken bu betik değişince de kurulsun diye her derlemeden sonra denetlenir.
        [InitializeOnLoadMethod]
        private static void ScheduleLookSetup()
        {
            EditorApplication.delayCall -= SetupLook;
            EditorApplication.delayCall += SetupLook;
            EditorApplication.delayCall -= LinkCharacter;
            EditorApplication.delayCall += LinkCharacter;
        }

        private static void SetupLook()
        {
            SetupCh29Look();
            SetupWizardLook();
        }

        // Mixamo dokuları FBX'in içine gömer ve Unity bunları malzemeye kendiliğinden bağlamaz: karakter dokusuz
        // (yüzsüz, kıyafetsiz) görünür. Dokuları ve malzemeyi bir kez klasörlere çıkarır, malzemeyi URP Lit olarak
        // bu dokularla kurarız. Her adım yapılmışsa atlanır.
        private static void SetupCh29Look()
        {
            if (!(AssetImporter.GetAtPath(ModelFile) is ModelImporter importer)) return;

            if (FindTexture("_Diffuse") == null)
            {
                EnsureFolder(TextureFolder);
                if (!importer.ExtractTextures(TextureFolder))
                {
                    Debug.LogWarning("PlayerCharacter: Ch29 dokuları FBX'ten çıkarılamadı.");
                    return;
                }

                AssetDatabase.Refresh();
            }

            MakeNormalMap(FindTexture("_Normal"));
            SmoothFiltering(FindTexture("_Diffuse"));

            if (!AssetDatabase.IsValidFolder(MaterialFolder) || AssetDatabase.FindAssets("t:Material", new[] { MaterialFolder }).Length == 0)
            {
                EnsureFolder(MaterialFolder);
                foreach (Object asset in AssetDatabase.LoadAllAssetsAtPath(ModelFile))
                {
                    if (asset is Material material)
                    {
                        AssetDatabase.ExtractAsset(material, MaterialFolder + "/" + material.name + ".mat");
                    }
                }

                AssetDatabase.WriteImportSettingsIfDirty(ModelFile);
                AssetDatabase.ImportAsset(ModelFile, ImportAssetOptions.ForceUpdate);
            }

            bool changed = false;
            foreach (string guid in AssetDatabase.FindAssets("t:Material", new[] { MaterialFolder }))
            {
                Material material = AssetDatabase.LoadAssetAtPath<Material>(AssetDatabase.GUIDToAssetPath(guid));
                changed |= ConfigureMaterial(material, FindTexture("_Diffuse"), FindTexture("_Normal"));
            }

            if (changed)
            {
                AssetDatabase.SaveAssets();
                Debug.Log("PlayerCharacter: Ch29 dokuları ve malzemesi kuruldu.");
            }
        }

        // Büyücünün dokuları dosya olarak gelir. Malzemeyi kendimiz kurar, FBX'teki malzemeyi ona yönlendiririz.
        private static void SetupWizardLook()
        {
            if (!(AssetImporter.GetAtPath(WizardFile) is ModelImporter importer)) return;

            Texture2D baseColor = AssetDatabase.LoadAssetAtPath<Texture2D>(WizardFolder + "Textures/Wizard_basecolor.png");
            Texture2D normal = AssetDatabase.LoadAssetAtPath<Texture2D>(WizardFolder + "Textures/Wizard_normal.png");
            Shader lit = Shader.Find("Universal Render Pipeline/Lit");
            if (baseColor == null || lit == null) return;

            MakeNormalMap(normal);
            SmoothFiltering(baseColor);

            Material material = AssetDatabase.LoadAssetAtPath<Material>(WizardMaterial);
            if (material == null)
            {
                EnsureFolder(WizardFolder + "Materials");
                material = new Material(lit);
                AssetDatabase.CreateAsset(material, WizardMaterial);
            }

            bool changed = ConfigureMaterial(material, baseColor, normal);
            if (changed)
            {
                AssetDatabase.SaveAssets();
            }

            // FBX'in kendi (gömülü) malzemeleri bu malzemeye yönlendirilir; yönlendirilenler artık gömülü sayılmaz.
            bool remapped = false;
            foreach (Object asset in AssetDatabase.LoadAllAssetsAtPath(WizardFile))
            {
                if (asset is Material embedded)
                {
                    importer.AddRemap(new AssetImporter.SourceAssetIdentifier(embedded), material);
                    remapped = true;
                }
            }

            if (remapped)
            {
                importer.SaveAndReimport();
            }

            if (changed || remapped)
            {
                Debug.Log("PlayerCharacter: büyücünün dokuları ve malzemesi kuruldu.");
            }
        }

        // URP Lit, opak, renk dokusu ve normal haritası bağlı. FBX'teki parlaklık ve saydamlık ayarları kullanılmaz.
        // Değişiklik yaptıysa true döner.
        private static bool ConfigureMaterial(Material material, Texture2D diffuse, Texture2D normal)
        {
            Shader lit = Shader.Find("Universal Render Pipeline/Lit");
            if (material == null || diffuse == null || lit == null) return false;

            if (material.shader == lit && material.GetTexture("_BaseMap") == diffuse && material.GetTexture("_BumpMap") == normal &&
                material.GetFloat("_Surface") == 0f && Mathf.Approximately(material.GetFloat("_Smoothness"), Smoothness)) return false;

            material.shader = lit;
            material.SetTexture("_BaseMap", diffuse);
            material.SetColor("_BaseColor", Color.white);
            material.SetTexture("_BumpMap", normal);
            SetKeyword(material, "_NORMALMAP", normal != null);
            material.SetFloat("_WorkflowMode", 1f);
            SetKeyword(material, "_SPECULAR_SETUP", false);
            SetKeyword(material, "_SPECGLOSSMAP", false);
            material.SetFloat("_Metallic", 0f);
            material.SetFloat("_Smoothness", Smoothness);
            material.SetFloat("_Surface", 0f);
            material.SetFloat("_Blend", 0f);
            material.SetFloat("_AlphaClip", 0f);
            material.SetFloat("_SrcBlend", 1f);
            material.SetFloat("_DstBlend", 0f);
            material.SetFloat("_SrcBlendAlpha", 1f);
            material.SetFloat("_DstBlendAlpha", 0f);
            material.SetFloat("_ZWrite", 1f);
            material.SetOverrideTag("RenderType", "Opaque");
            SetKeyword(material, "_SURFACE_TYPE_TRANSPARENT", false);
            SetKeyword(material, "_ALPHATEST_ON", false);
            material.renderQueue = -1;
            EditorUtility.SetDirty(material);
            return true;
        }

        private static void MakeNormalMap(Texture2D texture)
        {
            if (texture != null && AssetImporter.GetAtPath(AssetDatabase.GetAssetPath(texture)) is TextureImporter importer &&
                importer.textureType != TextureImporterType.NormalMap)
            {
                importer.textureType = TextureImporterType.NormalMap;
                importer.SaveAndReimport();
            }

            SmoothFiltering(texture);
        }

        // Üç doğrusal süzme ve anizotropi: karakter uzakta ve hareket halindeyken doku pikselleri kaymaz, titremez.
        private static void SmoothFiltering(Texture2D texture)
        {
            if (texture != null && AssetImporter.GetAtPath(AssetDatabase.GetAssetPath(texture)) is TextureImporter importer &&
                (importer.filterMode != FilterMode.Trilinear || importer.anisoLevel < 4 || !importer.mipmapEnabled))
            {
                importer.mipmapEnabled = true;
                importer.filterMode = FilterMode.Trilinear;
                importer.anisoLevel = 4;
                importer.SaveAndReimport();
            }
        }

        private static void SetKeyword(Material material, string keyword, bool on)
        {
            if (on)
            {
                material.EnableKeyword(keyword);
            }
            else
            {
                material.DisableKeyword(keyword);
            }
        }

        private static Texture2D FindTexture(string suffix)
        {
            if (!AssetDatabase.IsValidFolder(TextureFolder)) return null;

            foreach (string guid in AssetDatabase.FindAssets("t:Texture2D", new[] { TextureFolder }))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                if (Path.GetFileNameWithoutExtension(path).EndsWith(suffix)) return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            }

            return null;
        }

        private static void EnsureFolder(string path)
        {
            if (!AssetDatabase.IsValidFolder(path))
            {
                AssetDatabase.CreateFolder(Path.GetDirectoryName(path).Replace('\\', '/'), Path.GetFileName(path));
            }
        }

        private static void LinkCharacter()
        {
            GameObject model = AssetDatabase.LoadAssetAtPath<GameObject>(WizardFile);
            if (model == null)
            {
                model = AssetDatabase.LoadAssetAtPath<GameObject>(ModelFile);
            }

            AnimationClip run = LoadClip("Run");
            AnimationClip slide = LoadClip("Slide");
            AnimationClip jump = LoadClip("Jump");
            AnimationClip stumble = LoadClip("Stumble");
            AnimationClip roll = LoadClip("Roll");
            if (model == null || run == null) return;

            PlayerCharacter character = AssetDatabase.LoadAssetAtPath<PlayerCharacter>(CharacterAsset);
            if (character == null)
            {
                character = ScriptableObject.CreateInstance<PlayerCharacter>();
                AssetDatabase.CreateAsset(character, CharacterAsset);
            }
            else if (character.model == model && character.run == run && character.slide == slide && character.jump == jump &&
                     character.stumble == stumble && character.roll == roll)
            {
                return;
            }

            character.model = model;
            character.run = run;
            character.slide = slide;
            character.jump = jump;
            character.stumble = stumble;
            character.roll = roll;
            EditorUtility.SetDirty(character);
            AssetDatabase.SaveAssets();
            Debug.Log("PlayerCharacter: " + model.name + " modeli ve Ch29 animasyonları bağlandı.", character);
        }

        private static AnimationClip LoadClip(string clipName)
        {
            foreach (Object asset in AssetDatabase.LoadAllAssetsAtPath(Folder + "Ch29_" + clipName + ".fbx"))
            {
                if (asset is AnimationClip clip && clip.name == clipName) return clip;
            }

            return null;
        }

        private static string ClipName(string path)
        {
            string file = Path.GetFileNameWithoutExtension(path);
            return file.Substring(file.LastIndexOf('_') + 1);
        }
    }
}
