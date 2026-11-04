#if UNITY_EDITOR
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace PembeBuyucu
{
    /// <summary>
    /// Yalnız editörde, görüntü ve akıcılık sorunlarını incelemek için: Play'e basınca proje kökündeki Captures klasörüne
    /// ayarlar (ekran boyu, kalite, render ölçeği, kenar yumuşatma, kare süreleri) yazılır, ilk saniyelerdeki kare takılmaları
    /// Console'a düşer. SaveImages açılırsa ekran görüntüleri de alınır; bunlar oyunu takıldırdığı için normalde kapalıdır.
    /// Oyunun derlenmiş haline girmez.
    /// </summary>
    internal class DebugCapture : MonoBehaviour
    {
        private static readonly bool SaveImages = false;
        // Bu süreden uzun kareler ve bu saniyeye kadar yazılır.
        private const float SpikeSeconds = 0.04f;
        private const float SpikeWatchUntil = 30f;

        private string folder;
        private readonly StringBuilder info = new StringBuilder();
        private readonly List<float> frameTimes = new List<float>();
        private float startTime;

        private void Awake()
        {
            startTime = Time.realtimeSinceStartup;
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void Create()
        {
            if (FindFirstObjectByType<DebugCapture>() != null) return;

            GameObject go = new GameObject("DebugCapture");
            DontDestroyOnLoad(go);
            go.AddComponent<DebugCapture>();
        }

        private IEnumerator Start()
        {
            folder = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "Captures"));
            Directory.CreateDirectory(folder);
            if (SaveImages)
            {
                foreach (string old in Directory.GetFiles(folder))
                {
                    File.Delete(old);
                }
            }

            yield return new WaitForSeconds(1.5f);
            WriteSettings();
            if (SaveImages)
            {
                Shot("menu");
                yield return CloseUp("menu_closeup");
            }

            while (GameManager.Instance == null || !GameManager.Instance.IsPlaying)
            {
                yield return null;
            }

            yield return new WaitForSeconds(1f);
            if (SaveImages)
            {
                yield return Burst("run1", 4);
                yield return CloseUp("run_closeup");
            }

            float end = Time.unscaledTime + 3f;
            while (Time.unscaledTime < end && GameManager.Instance != null && GameManager.Instance.IsPlaying)
            {
                frameTimes.Add(Time.unscaledDeltaTime * 1000f);
                yield return null;
            }

            if (SaveImages)
            {
                yield return Burst("run2", 4);
            }

            WriteFrameTimes();
            File.WriteAllText(Path.Combine(folder, "info.txt"), info.ToString());
            Debug.Log("DebugCapture: görüntüler ve ayarlar " + folder + " klasörüne yazıldı.");
        }

        private void Update()
        {
            float now = Time.realtimeSinceStartup - startTime;
            if (now < SpikeWatchUntil && Time.unscaledDeltaTime > SpikeSeconds)
            {
                Debug.Log("Kare takılması: " + now.ToString("0.0") + ". sn, " + (Time.unscaledDeltaTime * 1000f).ToString("0") + " ms");
            }
        }

        private void Shot(string name)
        {
            ScreenCapture.CaptureScreenshot(Path.Combine(folder, name + ".png"));
        }

        // Art arda kareler: titreşen ya da kayan pikseller kareler arasındaki farkta görünür.
        private IEnumerator Burst(string name, int count)
        {
            for (int i = 0; i < count; i++)
            {
                Shot(name + "_" + i);
                yield return null;
            }
        }

        // Ana kameranın yerinden, dar açıyla karaktere bakan büyük çözünürlüklü görüntü.
        private IEnumerator CloseUp(string name)
        {
            yield return new WaitForEndOfFrame();
            Camera main = Camera.main;
            PlayerController player = FindFirstObjectByType<PlayerController>();
            if (main == null || player == null) yield break;

            GameObject go = new GameObject("CloseUpCamera");
            Camera cam = go.AddComponent<Camera>();
            cam.CopyFrom(main);
            cam.transform.SetPositionAndRotation(main.transform.position, main.transform.rotation);
            cam.transform.LookAt(player.transform.position + Vector3.up * 0.8f);
            cam.fieldOfView = 14f;
            RenderTexture rt = new RenderTexture(900, 1200, 24);
            var request = new RenderPipeline.StandardRequest { destination = rt };
            if (RenderPipeline.SupportsRenderRequest(cam, request))
            {
                RenderPipeline.SubmitRenderRequest(cam, request);
            }
            else
            {
                cam.targetTexture = rt;
                cam.Render();
                cam.targetTexture = null;
            }

            RenderTexture previous = RenderTexture.active;
            RenderTexture.active = rt;
            Texture2D tex = new Texture2D(rt.width, rt.height, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, rt.width, rt.height), 0, 0);
            tex.Apply();
            RenderTexture.active = previous;
            File.WriteAllBytes(Path.Combine(folder, name + ".png"), tex.EncodeToPNG());
            Destroy(tex);
            rt.Release();
            Destroy(rt);
            Destroy(go);
        }

        private void WriteSettings()
        {
            info.AppendLine("Screen: " + Screen.width + "x" + Screen.height + " (aspect " + ((float)Screen.width / Screen.height).ToString("0.000") + ")");
            info.AppendLine("Quality: " + QualitySettings.names[QualitySettings.GetQualityLevel()] + ", vSync " + QualitySettings.vSyncCount +
                            ", targetFrameRate " + Application.targetFrameRate);
            if (GraphicsSettings.currentRenderPipeline is UniversalRenderPipelineAsset urp)
            {
                info.AppendLine("URP asset: " + urp.name + ", renderScale " + urp.renderScale + ", MSAA " + urp.msaaSampleCount +
                                ", HDR " + urp.supportsHDR + ", shadowDistance " + urp.shadowDistance);
            }

            Camera main = Camera.main;
            if (main != null)
            {
                info.AppendLine("Camera: pos " + main.transform.position + ", euler " + main.transform.eulerAngles + ", fov " + main.fieldOfView +
                                ", allowMSAA " + main.allowMSAA + ", pixel size " + main.pixelWidth + "x" + main.pixelHeight);
                if (main.TryGetComponent<UniversalAdditionalCameraData>(out UniversalAdditionalCameraData data))
                {
                    info.AppendLine("Camera AA: " + data.antialiasing + ", post " + data.renderPostProcessing);
                }
            }

            PlayerController player = FindFirstObjectByType<PlayerController>();
            if (player != null && main != null)
            {
                Renderer[] renderers = player.GetComponentsInChildren<Renderer>().Where(r => r.enabled).ToArray();
                if (renderers.Length > 0)
                {
                    Bounds b = renderers[0].bounds;
                    foreach (Renderer r in renderers) b.Encapsulate(r.bounds);
                    Vector3 top = main.WorldToScreenPoint(new Vector3(b.center.x, b.max.y, b.center.z));
                    Vector3 bottom = main.WorldToScreenPoint(new Vector3(b.center.x, b.min.y, b.center.z));
                    info.AppendLine("Character: height " + b.size.y.ToString("0.00") + " units, on screen " + (top.y - bottom.y).ToString("0") +
                                    " px (" + ((top.y - bottom.y) / Screen.height * 100f).ToString("0.0") + "% of height), feet at " +
                                    (100f - bottom.y / Screen.height * 100f).ToString("0.0") + "% from top");
                    foreach (Renderer r in renderers)
                    {
                        info.AppendLine("  renderer " + r.name + " (" + r.GetType().Name + ") material " +
                                        (r.sharedMaterial != null ? r.sharedMaterial.name + " / " + r.sharedMaterial.shader.name : "none"));
                    }
                }
            }
        }

        private void WriteFrameTimes()
        {
            if (frameTimes.Count == 0) return;

            frameTimes.Sort();
            float average = frameTimes.Average();
            info.AppendLine("Frame time during run: avg " + average.ToString("0.0") + " ms (" + (1000f / average).ToString("0") + " fps), median " +
                            frameTimes[frameTimes.Count / 2].ToString("0.0") + " ms, worst " + frameTimes[frameTimes.Count - 1].ToString("0.0") +
                            " ms, frames " + frameTimes.Count);
        }
    }
}
#endif
