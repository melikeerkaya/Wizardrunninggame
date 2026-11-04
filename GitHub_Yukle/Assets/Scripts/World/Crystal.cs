using UnityEngine;

namespace PembeBuyucu
{
    /// <summary>
    /// Toplanabilir kristal. Oyuncu değince kaybolur ve skora eklenir.
    /// Görünüşü büyü kitabıdır (Resources/Models/SpellBook, bkz. Art/convert_prop.py); model bulunamazsa eğik küp çizilir.
    /// Kendi etrafında döner, böylece yolda daha kolay fark edilir.
    /// Havadaki kristaller (IsAerial) yalnızca süpürgeyle uçarken, yerdekiler yalnızca yerdeyken toplanır.
    /// </summary>
    public class Crystal : MonoBehaviour
    {
        public const string ModelPath = "Models/SpellBook";

        // Toplamayı kolaylaştırmak için tetikleyici görünen nesneden biraz büyük.
        private const float TriggerSize = 1.2f;

        [SerializeField] private float spinSpeed = 120f;

        /// <summary>Süpürge uçuşu sırasında havada çıkan kristal mi?</summary>
        public bool IsAerial { get; set; }

        public static Crystal Create(Transform parent, Material material)
        {
            GameObject prefab = Resources.Load<GameObject>(ModelPath);
            if (prefab == null) return CreateCube(parent, material);

            GameObject root = new GameObject("Crystal");
            root.transform.SetParent(parent, true);

            Transform model = Instantiate(prefab, root.transform).transform;
            model.localPosition = Vector3.zero;
            ModelPalette.Apply(model);

            BoxCollider trigger = root.AddComponent<BoxCollider>();
            trigger.isTrigger = true;
            trigger.size = Vector3.one * TriggerSize;

            return root.AddComponent<Crystal>();
        }

        // Eğik küp, dönerken elmas gibi görünür.
        private static Crystal CreateCube(Transform parent, Material material)
        {
            GameObject go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = "Crystal";
            go.transform.SetParent(parent, true);
            go.transform.localScale = Vector3.one * 0.6f;
            go.transform.rotation = Quaternion.Euler(35f, 0f, 45f);
            go.GetComponent<Renderer>().sharedMaterial = material;

            BoxCollider box = go.GetComponent<BoxCollider>();
            box.isTrigger = true;
            box.size = Vector3.one * (TriggerSize / 0.6f);

            return go.AddComponent<Crystal>();
        }

        private void Update()
        {
            transform.Rotate(0f, spinSpeed * Time.deltaTime, 0f, Space.World);
        }

        public void Collect()
        {
            gameObject.SetActive(false);

            if (ScoreManager.Instance != null)
            {
                ScoreManager.Instance.AddCrystal();
            }
        }
    }
}
