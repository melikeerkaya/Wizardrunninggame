using UnityEngine;

namespace PembeBuyucu
{
    /// <summary>
    /// Sonraki dünyaya açılan portal: yolun iki yanında sütun, üstünde kiriş.
    /// Yolun tamamını kapladığı için kaçılamaz, oyuncu içinden geçince dünya değişir.
    /// Şimdilik basit bir çerçeve; gerçek model sonra gelecek.
    /// </summary>
    public class Portal : MonoBehaviour
    {
        private const float Height = 5f;

        public static Portal Create(Transform parent, float roadWidth, Material material)
        {
            GameObject root = new GameObject("Portal");
            root.transform.SetParent(parent, false);

            float half = roadWidth * 0.5f;
            AddPart(root.transform, new Vector3(-half, Height * 0.5f, 0f), new Vector3(1f, Height, 1f), material);
            AddPart(root.transform, new Vector3(half, Height * 0.5f, 0f), new Vector3(1f, Height, 1f), material);
            AddPart(root.transform, new Vector3(0f, Height + 0.5f, 0f), new Vector3(roadWidth + 1f, 1f, 1f), material);

            BoxCollider trigger = root.AddComponent<BoxCollider>();
            trigger.isTrigger = true;
            trigger.center = new Vector3(0f, Height * 0.5f, 0f);
            trigger.size = new Vector3(roadWidth, Height, 1.5f);

            Portal portal = root.AddComponent<Portal>();
            root.SetActive(false);
            return portal;
        }

        public void Show(float z)
        {
            transform.position = new Vector3(0f, 0f, z);
            gameObject.SetActive(true);
        }

        public void Hide()
        {
            gameObject.SetActive(false);
        }

        private static void AddPart(Transform parent, Vector3 position, Vector3 scale, Material material)
        {
            GameObject part = GameObject.CreatePrimitive(PrimitiveType.Cube);
            part.name = "Frame";
            part.transform.SetParent(parent, false);
            part.transform.localPosition = position;
            part.transform.localScale = scale;
            part.GetComponent<Renderer>().sharedMaterial = material;
            Destroy(part.GetComponent<Collider>());
        }
    }
}
