using UnityEngine;

namespace PembeBuyucu
{
    /// <summary>
    /// Animasyonlu oyuncu karakteri: Mixamo modeli ve koşu, kayma, zıplama animasyonları.
    /// Resources/PlayerCharacter varlığı, editörde Assets/Characters/Ch29 dosyaları içe aktarılınca kendiliğinden
    /// doldurulur (bkz. Editor/PlayerCharacterImporter.cs). Bu varlık yoksa oyun eski Wizard modelini kullanır.
    /// Animasyon zamanları saniyedir; Mixamo 30 kare/sn olduğu için N. kare (N - 1) / 30 saniyedir.
    /// </summary>
    public class PlayerCharacter : ScriptableObject
    {
        public const string ResourcePath = "PlayerCharacter";

        public GameObject model;
        public AnimationClip run;
        public AnimationClip slide;
        public AnimationClip jump;
        public AnimationClip stumble;
        public AnimationClip roll;

        [Header("Yerleşim")]
        [Tooltip("Subway Surfers oranı: baş hizası şerit genişliğinin ~0.57'si. Büyücünün başı 1.77'de, 2.5'lik şeritte 0.8 ile ~1.41 olur (şapkanın ucu ~1.64).")]
        public float scale = 0.8f;

        [Tooltip("Model koşu yönüne (+Z) bakıyorsa 0. Mixamo modelleri +Z'ye bakar.")]
        public float yaw;

        [Header("Animasyon zamanları (saniye)")]
        [Tooltip("Kayma başlayınca kayma animasyonunun başlatılacağı an (karakterin yere inmeye başladığı kare).")]
        public float slideStart = 0.1f;

        [Tooltip("Kayma uzarsa animasyon bu anda bekletilir (yerde kayarken).")]
        public float slideHold = 0.7f;

        [Tooltip("Zıplayınca animasyonun başlatılacağı an (ayakların yerden kesilmeye başladığı kare).")]
        public float jumpTakeoff = 0.67f;

        [Tooltip("Havada uzun kalınırsa animasyon bu anda bekletilir (yere inmeden hemen önce).")]
        public float jumpHold = 1.33f;

        [Tooltip("Oyun başlamadan ve süpürgede dururken kullanılan duruş: zıplama animasyonunun bu anı.")]
        public float standPose;

        [Tooltip("Yuvarlanma animasyonunun başlatılacağı an (ayakların yere değdiği kare).")]
        public float rollStart = 0.07f;

        [Tooltip("Yuvarlanma animasyonunun bittiği sayılan an (karakterin doğrulduğu kare).")]
        public float rollEnd = 1.45f;

        [Header("Koşu hızı")]
        [Tooltip("Koşu animasyonunun hızı = oyundaki koşu hızı x bu değer (aşağıdaki sınırlar içinde).")]
        public float runAnimPerSpeed = 0.12f;

        public float runAnimMin = 1.1f;
        public float runAnimMax = 1.8f;
    }
}
