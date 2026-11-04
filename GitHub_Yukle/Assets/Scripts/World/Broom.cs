using UnityEngine;

namespace PembeBuyucu
{
    /// <summary>
    /// Süpürge toplanabilir nesnesi. Alınca oyuncu kısa süre uçar (PlayerController halleder).
    /// Resources/Models/Broom modelini kullanır, bulunamazsa basit bir çubuk ve fırça çizer.
    /// </summary>
    public class Broom : MonoBehaviour
    {
        public const string ModelPath = "Models/Broom";

        [SerializeField] private float spinSpeed = 90f;

        public static Broom Create(Transform parent, Material handleMaterial, Material bristleMaterial)
        {
            GameObject root = new GameObject("Broom");
            root.transform.SetParent(parent, false);

            GameObject prefab = Resources.Load<GameObject>(ModelPath);
            if (prefab != null)
            {
                Transform model = Instantiate(prefab, root.transform).transform;
                model.localPosition = Vector3.zero;
                model.localScale = Vector3.one * 0.8f;
                ModelPalette.Apply(model);
            }
            else
            {
                AddPart(root.transform, new Vector3(0f, 0f, 0f), new Vector3(0.2f, 0.2f, 2f), handleMaterial);
                AddPart(root.transform, new Vector3(0f, 0f, -1.1f), new Vector3(0.7f, 0.7f, 0.8f), bristleMaterial);
            }

            // Toplamayı kolaylaştırmak için tetikleyici görünen nesneden büyük.
            BoxCollider trigger = root.AddComponent<BoxCollider>();
            trigger.isTrigger = true;
            trigger.size = new Vector3(2f, 2f, 3f);

            Broom broom = root.AddComponent<Broom>();
            root.SetActive(false);
            return broom;
        }

        private void Update()
        {
            transform.Rotate(0f, spinSpeed * Time.deltaTime, 0f, Space.World);
        }

        public void Collect()
        {
            gameObject.SetActive(false);
        }

        private static void AddPart(Transform parent, Vector3 position, Vector3 scale, Material material)
        {
            GameObject part = GameObject.CreatePrimitive(PrimitiveType.Cube);
            part.name = "Part";
            part.transform.SetParent(parent, false);
            part.transform.localPosition = position;
            part.transform.localScale = scale;
            part.GetComponent<Renderer>().sharedMaterial = material;
            Destroy(part.GetComponent<Collider>());
        }
    }
}
