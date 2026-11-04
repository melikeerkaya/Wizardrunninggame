using UnityEngine;

namespace PembeBuyucu
{
    /// <summary>
    /// Kamerayı karakterin arkasında tutar. Zıplarken kamera yukarı çıkmaz,
    /// şerit değiştirirken yumuşak biçimde yana kayar.
    /// Varsayılan duruş Subway Surfers'tan ölçüldü (dikey ekran, 60° görüş): kamera karakterin ~3 boyu yukarıda ve
    /// ~3.7 boyu geride, ~17° aşağı bakar; karakter ekranın alt kısmında, ekran yüksekliğinin ~%17'si kadar görünür.
    /// Süpürgeyle yükselirken kamera da yükselir, geriye çekilir ve görüş açısı genişler,
    /// böylece gerçekten havalanıyormuş gibi hissettirir.
    /// </summary>
    [RequireComponent(typeof(Camera))]
    public class CameraFollow : MonoBehaviour
    {
        [Tooltip("Boş bırakılırsa sahnedeki PlayerController otomatik bulunur.")]
        [SerializeField] private Transform target;

        [Tooltip("Karaktere göre yükseklik (y) ve geride durma mesafesi (z).")]
        [SerializeField] private Vector3 offset = new Vector3(0f, 4.5f, -5.3f);

        [Tooltip("Kameranın karakterin yanal hareketini ne kadar izleyeceği (0-1).")]
        [SerializeField, Range(0f, 1f)] private float sideFollow = 0.6f;
        [SerializeField] private float sideSmooth = 8f;

        [Tooltip("Kameranın karakterin ne kadar ilerisine baktığı.")]
        [SerializeField] private float lookAheadDistance = 6.3f;
        [SerializeField] private float lookHeight = 1f;

        [Header("Süpürge uçuşu")]
        [Tooltip("Uçarken kameranın ekstra yüksekliği.")]
        [SerializeField] private float flightLift = 4f;
        [Tooltip("Uçarken kameranın ekstra geri çekilmesi.")]
        [SerializeField] private float flightPullBack = 3f;
        [Tooltip("Uçarken bakış noktasının ekstra yüksekliği.")]
        [SerializeField] private float flightLookRaise = 2f;
        [Tooltip("Uçarken görüş açısının artışı (derece).")]
        [SerializeField] private float flightFovBoost = 14f;
        [Tooltip("Kameranın uçuşu geriden takip etme hızı. Küçük değer = daha gecikmeli, daha dramatik.")]
        [SerializeField] private float flightFollowSpeed = 3f;

        private PlayerController player;
        private Camera cam;
        private float baseFov;
        private float cameraBlend;

        private void Awake()
        {
            cam = GetComponent<Camera>();
            baseFov = cam.fieldOfView;

            player = FindFirstObjectByType<PlayerController>();
            if (target == null && player != null)
            {
                target = player.transform;
            }
        }

        private void LateUpdate()
        {
            if (target == null) return;

            // Kamera, oyuncunun yükselişini biraz geriden takip eder.
            float playerBlend = player != null ? player.FlightBlend : 0f;
            cameraBlend = Mathf.Lerp(cameraBlend, playerBlend, flightFollowSpeed * Time.deltaTime);

            Vector3 position = transform.position;
            float desiredX = target.position.x * sideFollow;

            position.x = Mathf.Lerp(position.x, desiredX, sideSmooth * Time.deltaTime);
            position.y = offset.y + flightLift * cameraBlend;
            position.z = target.position.z + offset.z - flightPullBack * cameraBlend;
            transform.position = position;

            float lookY = lookHeight + flightLookRaise * cameraBlend;
            transform.LookAt(new Vector3(position.x, lookY, target.position.z + lookAheadDistance));

            cam.fieldOfView = baseFov + flightFovBoost * cameraBlend;
        }
    }
}
