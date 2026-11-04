using UnityEngine;

namespace PembeBuyucu
{
    /// <summary>
    /// Düz renkli malzeme üretir. Varsayılan URP malzemesinin kopyasını alıp rengini değiştirir.
    /// Shader.Find kullanmıyoruz, böylece telefona çıkarken shader eksik kalmaz.
    /// </summary>
    public static class MaterialFactory
    {
        public static Material Create(Color color)
        {
            GameObject temp = GameObject.CreatePrimitive(PrimitiveType.Cube);
            Material material = new Material(temp.GetComponent<Renderer>().sharedMaterial);
            Object.Destroy(temp);

            material.color = color;
            return material;
        }
    }
}
