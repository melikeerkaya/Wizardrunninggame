using System;
using UnityEngine;

namespace PembeBuyucu
{
    /// <summary>
    /// Karakterin otomatik koşusu, üç şeritte sağa/sola geçişi, zıplaması, kayması ve süpürge uçuşu.
    /// Hareket kodla yapılır (fizik motoru yok), çarpışma ise tetikleyici ile algılanır.
    /// Engele değmek koşuyu bitirir; bir engelin üstüne düşünce karakter yuvarlanıp devam eder, yükselirken takılınca sendeler.
    /// </summary>
    [RequireComponent(typeof(Rigidbody))]
    public class PlayerController : MonoBehaviour
    {
        private const int MaxLane = 1; // Şeritler: -1 (sol), 0 (orta), 1 (sağ)

        [Tooltip("Boş bırakılırsa sahnede otomatik bulunur.")]
        [SerializeField] private InputReader input;

        [Header("Koşu")]
        [SerializeField] private float startSpeed = 10f;
        [SerializeField] private float maxSpeed = 20f;
        [Tooltip("Saniye başına hız artışı.")]
        [SerializeField] private float acceleration = 0.07f;
        [Tooltip("Dünya değişince hız çarpanının saniyede ne kadar değişeceği.")]
        [SerializeField] private float speedFactorChangeRate = 0.5f;

        [Header("Şeritler")]
        [SerializeField] private float laneWidth = 2.5f;
        [SerializeField] private float laneChangeSpeed = 15f;

        [Header("Zıplama")]
        [SerializeField] private float jumpHeight = 2f;
        [SerializeField] private float gravity = 30f;

        [Header("Kayma")]
        [Tooltip("En uzun kayma süresi. Üstte engel kalmayınca bundan önce de kalkılır.")]
        [SerializeField] private float slideDuration = 0.6f;
        [Tooltip("En kısa kayma süresi. Bundan sonra üstte engel yoksa hemen ayağa kalkılır.")]
        [SerializeField] private float minSlideTime = 0.35f;
        [Tooltip("Kayarken çarpışma kapsülünün boyu. Zincirlerin altından geçmeye yetecek kadar alçak olmalı.")]
        [SerializeField] private float slideColliderHeight = 0.8f;
        [Tooltip("Havadayken kaymaya basılınca yere iniş hızı.")]
        [SerializeField] private float fastFallSpeed = 25f;

        [Header("Süpürge uçuşu")]
        [Tooltip("Havada geçirilen toplam süre (yükselme dahil).")]
        [SerializeField] private float flightDuration = 8f;
        [Tooltip("Uçarken zeminden yükseklik.")]
        [SerializeField] private float flightHeight = 4f;
        [Tooltip("Yerden havaya yükselme süresi (saniye).")]
        [SerializeField] private float riseTime = 1.2f;
        [Tooltip("Uçuş bitince yere alçalma süresi (saniye).")]
        [SerializeField] private float descendTime = 1.0f;
        [Tooltip("Yere indikten sonra engellerin çarpmadığı kısa süre (saniye).")]
        [SerializeField] private float landingGrace = 0.5f;

        [Header("Sendeleme")]
        [Tooltip("Havadayken engele değince karakterin sendelediği süre (saniye). Sendeleme animasyonu bu süreye uydurulur.")]
        [SerializeField] private float stumbleDuration = 1f;
        [Tooltip("Sendelemenin başında koşu hızının çarpanı. Süre boyunca 1'e döner.")]
        [SerializeField, Range(0f, 1f)] private float stumbleSpeedFactor = 0.6f;
        [Tooltip("Bu kadar saniye içinde ikinci kez sendelemek koşuyu bitirir (Subway Surfers'taki gibi).")]
        [SerializeField] private float stumbleWindow = 3f;
        [Tooltip("Sendeledikten sonra alçak engellerin sayılmadığı süre: aynı engelin ikinci kez çarpmasını önler.")]
        [SerializeField] private float stumbleGrace = 0.4f;

        [Header("Yuvarlanma")]
        [Tooltip("Engelin üstüne düşünce yuvarlanma süresi (saniye). Animasyon bu süreye uydurulur.")]
        [SerializeField] private float rollDuration = 0.9f;
        [Tooltip("Yuvarlanırken engelin üstüne çıkma hızı.")]
        [SerializeField] private float rollClimbSpeed = 8f;
        [Tooltip("Yere indikten bu kadar saniye içinde alçak engele değmek de üstüne inmek sayılır: engelin dibine inen yuvarlanır.")]
        [SerializeField] private float landingRollTime = 0.35f;

        private int laneIndex;
        private float forwardSpeed;
        private float speedFactor = 1f;
        private float groundY;
        private float verticalVelocity;
        private bool isGrounded = true;
        private float flightTimeLeft;
        private float flightBlend;
        private float flightStartY;
        private float invulnerableUntil;
        private CapsuleCollider capsule;
        private float standHeight;
        private Vector3 standCenter;
        private float slideTimeLeft;
        private bool slideQueued;
        private float stumbleTimeLeft;
        private float lastStumbleTime = float.NegativeInfinity;
        private float lastAirborneTime = float.NegativeInfinity;
        private float rollTimeLeft;
        // Üstünden yuvarlanılan engel: geçilene kadar çarpmaz, üstü zemin sayılır.
        private Obstacle rollObstacle;
        private readonly Collider[] overheadHits = new Collider[8];

        /// <summary>Süpürge alındığında tetiklenir (süre yeniden başlasa bile).</summary>
        public event Action FlightStarted;

        /// <summary>Uçuş süresi dolup alçalma başladığında tetiklenir.</summary>
        public event Action FlightEnded;

        public float LaneWidth => laneWidth;
        public float FlightTimeLeft => flightTimeLeft;
        public bool IsFlying => flightTimeLeft > 0f;
        public bool IsGrounded => isGrounded;
        public bool IsSliding => slideTimeLeft > 0f;
        public float GroundY => groundY;
        public float FlightHeight => flightHeight;
        public float FlightDuration => flightDuration;
        public float RiseTime => riseTime;
        public float CurrentSpeed => forwardSpeed * speedFactor * Mathf.Lerp(1f, stumbleSpeedFactor, StumbleBlend);

        /// <summary>Sendeleme başında 1, bitince 0.</summary>
        public float StumbleBlend => stumbleDuration > 0f ? Mathf.Clamp01(stumbleTimeLeft / stumbleDuration) : 0f;

        public float StumbleDuration => stumbleDuration;

        public bool IsRolling => rollTimeLeft > 0f;
        public float RollDuration => rollDuration;

        /// <summary>0 = yerde, 1 = tam yükseklikte. Yükselirken ve alçalırken yumuşak değişir.</summary>
        public float FlightBlend => Mathf.SmoothStep(0f, 1f, flightBlend);

        /// <summary>Hedef şeride olan yatay uzaklık. Sağa gidilirken pozitiftir.</summary>
        public float LaneError => laneIndex * laneWidth - transform.position.x;

        private bool IsInvulnerable => IsFlying || flightBlend > 0f || Time.time < invulnerableUntil;

        private void Awake()
        {
            Rigidbody body = GetComponent<Rigidbody>();
            body.isKinematic = true;
            body.useGravity = false;

            forwardSpeed = startSpeed;
            groundY = transform.position.y;

            // Koşu orta şeritte başlar. Sahnedeki yer şeritte değilse karakter menüde yana yatık kalırdı
            // (PlayerModel şerit farkı kadar yatırır, menüdeyken de hareket edip farkı kapatmaz).
            transform.position = new Vector3(0f, groundY, transform.position.z);

            capsule = GetComponent<CapsuleCollider>();
            if (capsule != null)
            {
                standHeight = capsule.height;
                standCenter = capsule.center;
            }

            if (input == null)
            {
                input = FindFirstObjectByType<InputReader>();
            }

            // Karakter görünüşü sahnede ayrıca bir bileşen eklemeden gelir.
            if (!TryGetComponent<PlayerModel>(out _))
            {
                gameObject.AddComponent<PlayerModel>();
            }
        }

        private void Update()
        {
            if (input == null) return;
            if (GameManager.Instance == null || !GameManager.Instance.IsPlaying) return;

            float dt = Time.deltaTime;
            forwardSpeed = Mathf.Min(maxSpeed, forwardSpeed + acceleration * dt);
            speedFactor = Mathf.MoveTowards(speedFactor, GetWorldSpeedFactor(), speedFactorChangeRate * dt);
            stumbleTimeLeft = Mathf.Max(0f, stumbleTimeLeft - dt);

            UpdateFlightTimer(dt);
            UpdateSlideTimer(dt);
            UpdateRollTimer(dt);
            HandleLaneInput();
            HandleJumpInput();
            HandleSlideInput();
            Move(dt);
        }

        private static float GetWorldSpeedFactor()
        {
            WorldManager world = WorldManager.Instance;
            if (world == null || world.Current.speedMultiplier <= 0f) return 1f;

            return world.Current.speedMultiplier;
        }

        private void UpdateFlightTimer(float dt)
        {
            if (!IsFlying) return;

            flightTimeLeft -= dt;
            if (flightTimeLeft <= 0f)
            {
                flightTimeLeft = 0f;

                // Yere inişte, zıplamadan değil zeminden başlarız.
                flightStartY = groundY;
                FlightEnded?.Invoke();
            }
        }

        private void StartFlight()
        {
            // Sıfırdan yükseliyorsak, yükselmeye şu anki yükseklikten başla (zıplarken alınmış olabilir).
            if (flightBlend <= 0f)
            {
                flightStartY = transform.position.y;
            }

            StopSlide();
            slideQueued = false;
            flightTimeLeft = flightDuration;
            isGrounded = false;
            verticalVelocity = 0f;
            FlightStarted?.Invoke();
        }

        private void HandleLaneInput()
        {
            if (input.LeftPressed)
            {
                laneIndex = Mathf.Max(-MaxLane, laneIndex - 1);
            }

            if (input.RightPressed)
            {
                laneIndex = Mathf.Min(MaxLane, laneIndex + 1);
            }
        }

        private void HandleJumpInput()
        {
            if (input.JumpPressed && isGrounded)
            {
                StopSlide();
                verticalVelocity = Mathf.Sqrt(2f * gravity * jumpHeight);
                isGrounded = false;
            }
        }

        // Yerdeyken hemen kayar. Havadayken hızla yere iner ve yere değince kaymaya başlar.
        private void HandleSlideInput()
        {
            if (!input.SlidePressed) return;
            if (IsFlying || flightBlend > 0f || IsRolling) return;

            if (isGrounded)
            {
                StartSlide();
            }
            else
            {
                slideQueued = true;
                verticalVelocity = Mathf.Min(verticalVelocity, -fastFallSpeed);
            }
        }

        private void UpdateSlideTimer(float dt)
        {
            if (!IsSliding) return;

            slideTimeLeft -= dt;
            bool minDone = slideDuration - slideTimeLeft >= minSlideTime;
            if (slideTimeLeft <= 0f || (minDone && !IsObstacleOverhead()))
            {
                StopSlide();
            }
        }

        // Ayağa kalksaydık kapsül bir engele (ör. zincire) değer miydi?
        private bool IsObstacleOverhead()
        {
            if (capsule == null) return false;

            Vector3 center = transform.TransformPoint(standCenter);
            float half = Mathf.Max(0f, standHeight * 0.5f - capsule.radius);
            int count = Physics.OverlapCapsuleNonAlloc(center + Vector3.up * half, center - Vector3.up * half,
                capsule.radius, overheadHits, ~0, QueryTriggerInteraction.Collide);

            for (int i = 0; i < count; i++)
            {
                if (overheadHits[i].TryGetComponent<Obstacle>(out _)) return true;
            }

            return false;
        }

        // Kayarken kapsül alçalır, tabanı yerde kalır. Zincirin altında ayağa kalkılırsa kapsül zincire değer.
        private void StartSlide()
        {
            slideTimeLeft = slideDuration;
            LowerCapsule();
        }

        private void LowerCapsule()
        {
            if (capsule == null) return;

            capsule.height = slideColliderHeight;
            capsule.center = standCenter - new Vector3(0f, (standHeight - slideColliderHeight) * 0.5f, 0f);
        }

        // Ayağa kalkar: kayma da yuvarlanma da biter.
        private void StopSlide()
        {
            slideTimeLeft = 0f;
            rollTimeLeft = 0f;
            if (capsule == null) return;

            capsule.height = standHeight;
            capsule.center = standCenter;
        }

        private void Move(float dt)
        {
            Vector3 position = transform.position;

            position.z += CurrentSpeed * dt;

            float targetX = laneIndex * laneWidth;
            position.x = Mathf.MoveTowards(position.x, targetX, laneChangeSpeed * dt);

            if (IsFlying || flightBlend > 0f)
            {
                // Yükselme ve alçalma süreye bağlı, yumuşak bir geçiştir.
                float direction = IsFlying ? 1f : -1f;
                float duration = IsFlying ? riseTime : descendTime;
                flightBlend = Mathf.Clamp01(flightBlend + direction * dt / duration);

                position.y = Mathf.Lerp(flightStartY, groundY + flightHeight, Mathf.SmoothStep(0f, 1f, flightBlend));

                if (!IsFlying && flightBlend <= 0f)
                {
                    position.y = groundY;
                    verticalVelocity = 0f;
                    isGrounded = true;
                    invulnerableUntil = Time.time + landingGrace;
                }
            }
            else if (!isGrounded)
            {
                float previousY = position.y;
                verticalVelocity -= gravity * dt;
                position.y += verticalVelocity * dt;

                float surface = RollSurface(position.z);
                if (surface > groundY && position.y <= surface)
                {
                    // Engelin üstünde yuvarlanıyor: üstüne çıkar, geçene kadar orada kalır.
                    position.y = Mathf.MoveTowards(previousY, surface, rollClimbSpeed * dt);
                    verticalVelocity = 0f;
                }
                else if (position.y <= groundY)
                {
                    position.y = groundY;
                    verticalVelocity = 0f;
                    isGrounded = true;

                    if (slideQueued)
                    {
                        slideQueued = false;
                        StartSlide();
                    }
                }
            }

            if (!isGrounded)
            {
                lastAirborneTime = Time.time;
            }

            transform.position = position;
        }

        private void OnTriggerEnter(Collider other)
        {
            if (GameManager.Instance == null || !GameManager.Instance.IsPlaying) return;

            if (other.TryGetComponent<Crystal>(out Crystal crystal))
            {
                // Havadaki kristaller yalnızca uçarken, yerdekiler yalnızca havada değilken toplanır.
                bool canCollect = crystal.IsAerial ? IsFlying : flightBlend <= 0f;
                if (canCollect)
                {
                    crystal.Collect();
                }

                return;
            }

            if (other.TryGetComponent<Broom>(out Broom broom))
            {
                broom.Collect();
                StartFlight();
                return;
            }

            if (other.TryGetComponent<Portal>(out Portal portal))
            {
                portal.Hide();

                if (WorldManager.Instance != null)
                {
                    WorldManager.Instance.EnterNextWorld();
                }

                return;
            }

            if (other.TryGetComponent<Obstacle>(out Obstacle obstacle) && !IsInvulnerable && obstacle != rollObstacle)
            {
#if UNITY_EDITOR
                Debug.Log("Engel teması: " + (obstacle.IsLow ? "alçak" : "yüksek") + ", havada " + !isGrounded + ", yükseklik " +
                          (transform.position.y - groundY).ToString("0.00") + ", dikey hız " + verticalVelocity.ToString("0.0") +
                          ", inişten beri " + (Time.time - lastAirborneTime).ToString("0.00") + " sn, yuvarlanıyor " + IsRolling);
#endif
                HitObstacle(obstacle);
            }
        }

        // Alçak engel: üstüne düşmek, dibine inmek ya da yuvarlanırken değmek yuvarlatır; yükselirken takılmak sendeletir.
        // Yüksek engel: ayaklar yeterince yukarıdayken inerek değmek yuvarlatır, yükselerek değmek sendeletir.
        // Yerde koşarak alçak engele girmek, kemere alttan çarpmak koşuyu bitirir.
        private void HitObstacle(Obstacle obstacle)
        {
            bool falling = !isGrounded && verticalVelocity <= 0f;
            if (obstacle.IsLow)
            {
                bool justLanded = isGrounded && Time.time - lastAirborneTime < landingRollTime;
                if (falling || justLanded || IsRolling)
                {
                    StartRoll(obstacle);
                }
                else if (!isGrounded)
                {
                    Stumble();
                }
                else
                {
                    GameManager.Instance.EndRun();
                }

                return;
            }

            if (!isGrounded && transform.position.y - groundY >= obstacle.LandOnHeight)
            {
                if (falling)
                {
                    StartRoll(obstacle);
                }
                else
                {
                    Stumble();
                }

                return;
            }

            GameManager.Instance.EndRun();
        }

        private void StartRoll(Obstacle obstacle)
        {
            rollObstacle = obstacle;
            rollTimeLeft = rollDuration;
            slideTimeLeft = 0f;
            slideQueued = false;
            isGrounded = false;
            verticalVelocity = Mathf.Min(verticalVelocity, 0f);
            LowerCapsule();
        }

        private void UpdateRollTimer(float dt)
        {
            if (rollObstacle != null && transform.position.z > rollObstacle.transform.position.z + rollObstacle.RollHalfDepth + 1f)
            {
                rollObstacle = null;
            }

            if (!IsRolling) return;

            rollTimeLeft -= dt;
            if (rollTimeLeft > 0f) return;

            // Bir kemerin altındayken ayağa kalkılmaz.
            if (IsObstacleOverhead())
            {
                rollTimeLeft = 0.05f;
            }
            else
            {
                StopSlide();
            }
        }

        // Yuvarlanılan engelin üstündeyken zeminin yüksekliği, değilse gerçek zemin.
        private float RollSurface(float z)
        {
            if (rollObstacle == null) return groundY;

            float reach = rollObstacle.RollHalfDepth + (capsule != null ? capsule.radius : 0f);
            return Mathf.Abs(z - rollObstacle.transform.position.z) < reach ? groundY + rollObstacle.RollTop : groundY;
        }

        // Yükselirken engele takılmak koşuyu bitirmez, karakter sendeler. Kısa sürede ikincisi koşuyu bitirir.
        private void Stumble()
        {
            float sinceLast = Time.time - lastStumbleTime;
            if (sinceLast < stumbleGrace) return;

            if (sinceLast < stumbleWindow)
            {
                GameManager.Instance.EndRun();
                return;
            }

            lastStumbleTime = Time.time;
            stumbleTimeLeft = stumbleDuration;
        }
    }
}
