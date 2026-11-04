using UnityEngine;
using UnityEngine.Animations;
using UnityEngine.Playables;

namespace PembeBuyucu
{
    /// <summary>
    /// Karakterin görünüşü ve animasyonu. Resources/PlayerCharacter varsa animasyonlu (Mixamo) karakteri yükler ve
    /// koşu, kayma, zıplama, sendeleme, yuvarlanma animasyonlarını oynatır. Yoksa Resources/Models/Wizard modelini yükler,
    /// parçalara renk verir ve kodla hareket ettirir: koşu, zıplama, kayma, süpürge uçuşu.
    /// İkisinde de şerit değiştirirken yana yatar, uçarken öne eğilir.
    /// Model bulunamazsa karakter eskisi gibi kapsül olarak kalır.
    /// Wizard modelinin parça adları "RenkAnahtarı_Parça" biçimindedir (bkz. Art/build_girl4.py).
    /// </summary>
    public class PlayerModel : MonoBehaviour
    {
        [SerializeField] private string resourcePath = "Models/Wizard";
        [SerializeField] private float modelScale = 0.95f;
        [Tooltip("Kamera karakterin yüzünü görüyorsa 0, arkasını görüyorsa 180 olmalı. Model ters bakıyorsa değeri değiştir.")]
        [SerializeField] private float modelYaw = 180f;

        [Header("Koşu animasyonu")]
        [SerializeField] private float cycleSpeed = 12f;
        [SerializeField] private float legSwing = 40f;
        [SerializeField] private float armSwing = 30f;
        [SerializeField] private float bobHeight = 0.06f;

        [Header("Şerit değiştirirken yatma")]
        [SerializeField] private float leanPerMeter = 12f;
        [SerializeField] private float maxLean = 20f;

        [Header("Sendeleme (sendeleme animasyonu yoksa)")]
        [Tooltip("Sendelerken öne kapaklanma açısı.")]
        [SerializeField] private float stumblePitch = 28f;
        [Tooltip("Sendelerken sağa sola yalpalama açısı.")]
        [SerializeField] private float stumbleWobble = 14f;

        [Header("Kayma")]
        [Tooltip("Kayarken gövdenin geriye yatma açısı.")]
        [SerializeField] private float slideBackLean = 45f;
        [Tooltip("Kayarken bacakların öne uzanma açısı. Bacaklar ters yöne gidiyorsa işaretini değiştir.")]
        [SerializeField] private float slideLegAngle = -50f;
        [Tooltip("Kayarken kolların açısı (dengede durmak için öne uzatılır).")]
        [SerializeField] private float slideArmAngle = -70f;
        [SerializeField] private float slideLift = 0.08f;
        [Tooltip("Eğilip doğrulma hızı. Büyük değer = daha çabuk doğrulur.")]
        [SerializeField] private float slideBlendSpeed = 20f;

        [Header("Ceket eteği")]
        [Tooltip("Bacak geriye gidince arka eteğin bacak açısının ne kadarı kadar savrulacağı.")]
        [SerializeField] private float skirtFollow = 0.8f;

        [Header("Animasyonlu karakter")]
        [Tooltip("Koşu, kayma ve zıplama animasyonları arasındaki geçiş süresi (saniye).")]
        [SerializeField] private float blendTime = 0.12f;

        // Karıştırıcıdaki animasyon sırası
        private const int RunInput = 0;
        private const int SlideInput = 1;
        private const int JumpInput = 2;
        private const int StandInput = 3;
        private const int StumbleInput = 4;
        private const int RollInput = 5;

        private PlayerController controller;
        private PlayerCharacter character;
        private PlayableGraph graph;
        private AnimationMixerPlayable mixer;
        private AnimationClipPlayable runClip, slideClip, jumpClip, stumbleClip, rollClip;
        private readonly float[] weights = new float[6];
        private bool wasSliding, wasAirborne, wasStumbling, wasRolling;
        private bool hasStumbleClip, hasRollClip;
        private float yaw;
        private Transform model;
        private Transform legL, legR, armL, armR;
        private Transform skirtBack;
        private Vector3 skirtOutward;
        private float skirtSign;
        private GameObject broom;
        private float cycle;
        private float lean;
        private float slideBlend;

        private void Awake()
        {
            controller = GetComponent<PlayerController>();

            character = Resources.Load<PlayerCharacter>(PlayerCharacter.ResourcePath);
            if (character != null && (character.model == null || character.run == null))
            {
                character = null;
            }

            GameObject prefab = character != null ? character.model : Resources.Load<GameObject>(resourcePath);
            if (prefab == null)
            {
                Debug.LogWarning("PlayerModel: Resources/" + resourcePath + " bulunamadı, kapsül kullanılıyor.", this);
                enabled = false;
                return;
            }

            // Eski kapsül görünümünü kapat (çarpışma kutusu kalır).
            if (TryGetComponent<MeshRenderer>(out MeshRenderer capsule))
            {
                capsule.enabled = false;
            }

            yaw = character != null ? character.yaw : modelYaw;
            model = Instantiate(prefab, transform).transform;
            model.localPosition = Vector3.zero;
            model.localRotation = Quaternion.Euler(0f, yaw, 0f);
            model.localScale = Vector3.one * (character != null ? character.scale : modelScale);

            if (character != null)
            {
                SetupAnimation();
            }
            else
            {
                ModelPalette.Apply(model);
                FindParts();
            }

            CreateBroom();
        }

        // Animasyonlar bir karıştırıcıya bağlanır; hangisinin görüneceğini Update ağırlıklarla seçer.
        // Böylece ayrı bir Animator Controller dosyası gerekmez.
        private void SetupAnimation()
        {
            Animator animator = model.GetComponentInChildren<Animator>();
            if (animator == null)
            {
                animator = model.gameObject.AddComponent<Animator>();
            }

            // İlerlemeyi PlayerController yapar, karakter yerinde koşar.
            animator.applyRootMotion = false;

            AnimationClip jump = character.jump != null ? character.jump : character.run;
            graph = PlayableGraph.Create("PlayerModel");
            graph.SetTimeUpdateMode(DirectorUpdateMode.GameTime);
            mixer = AnimationMixerPlayable.Create(graph, weights.Length);
            runClip = AddClip(character.run, RunInput);
            slideClip = AddClip(character.slide != null ? character.slide : character.run, SlideInput);
            jumpClip = AddClip(jump, JumpInput);
            hasStumbleClip = character.stumble != null;
            stumbleClip = AddClip(hasStumbleClip ? character.stumble : character.run, StumbleInput);
            hasRollClip = character.roll != null;
            rollClip = AddClip(hasRollClip ? character.roll : character.run, RollInput);

            AnimationClipPlayable stand = AddClip(jump, StandInput);
            stand.SetTime(character.standPose);
            stand.SetSpeed(0);
            weights[StandInput] = 1f;
            mixer.SetInputWeight(StandInput, 1f);

            AnimationPlayableOutput.Create(graph, "Animation", animator).SetSourcePlayable(mixer);
            graph.Play();
        }

        private AnimationClipPlayable AddClip(AnimationClip clip, int input)
        {
            AnimationClipPlayable playable = AnimationClipPlayable.Create(graph, clip);
            graph.Connect(playable, 0, mixer, input);
            return playable;
        }

        private void OnDestroy()
        {
            if (graph.IsValid())
            {
                graph.Destroy();
            }
        }

        // Uçarken karakterin altında görünen süpürge. Karakterin modeline bağlı olduğu için onunla birlikte eğilir.
        private void CreateBroom()
        {
            GameObject prefab = Resources.Load<GameObject>(Broom.ModelPath);
            if (prefab == null) return;

            broom = Instantiate(prefab, model);
            broom.transform.localPosition = Vector3.zero;
            broom.transform.localRotation = Quaternion.identity;
            ModelPalette.Apply(broom.transform);
            broom.SetActive(false);
        }

        private void FindParts()
        {
            legL = FindPart("Boot_BootL");
            legR = FindPart("Boot_BootR");
            armL = FindPart("Coat_SleeveL");
            armR = FindPart("Coat_SleeveR");

            skirtBack = FindPart("CoatBack_SkirtBack");
            if (skirtBack != null && skirtBack.TryGetComponent<MeshFilter>(out MeshFilter skirtMesh))
            {
                // Eteğin ortası dönme noktasının altında, sırt tarafındadır. Hangi yönün sırt olduğunu ve eteği
                // dışarı savuran dönüş yönünü modelin eksen düzeninden bağımsız olarak buradan çıkarırız.
                Vector3 center = skirtMesh.sharedMesh.bounds.center;
                skirtOutward = new Vector3(0f, 0f, center.z).normalized;
                skirtSign = Mathf.Sign(center.y * center.z);
            }
        }

        private Transform FindPart(string partName)
        {
            foreach (Transform t in model.GetComponentsInChildren<Transform>(true))
            {
                if (t.name == partName) return t;
            }

            return null;
        }

        private void Update()
        {
            bool playing = GameManager.Instance != null && GameManager.Instance.IsPlaying;
            // Süpürge, yükselirken ve alçalırken de görünür; havada olduğumuz sürece "uçuyor" sayılır.
            float flightBlend = controller.FlightBlend;
            bool flying = flightBlend > 0.01f;
            bool airborne = !controller.IsGrounded && !flying;
            float dt = Time.deltaTime;

            if (broom != null)
            {
                broom.SetActive(flying);
            }

            cycle += dt * (playing ? cycleSpeed : cycleSpeed * 0.15f);

            float bob;
            if (character != null)
            {
                UpdateAnimation(playing, flying, airborne, dt);
                // Koşu sallanması animasyonun içindedir; yalnız uçarken hafif süzülme eklenir.
                bob = flying ? Mathf.Sin(cycle * 0.4f) * bobHeight : 0f;
            }
            else
            {
                bob = UpdateLimbs(playing, flying, airborne, dt);
            }

            model.localPosition = new Vector3(0f, bob, 0f);

            // Şerit değiştirirken gittiği yöne yat.
            float targetLean = Mathf.Clamp(controller.LaneError * leanPerMeter, -maxLean, maxLean);
            lean = Mathf.Lerp(lean, targetLean, 10f * dt);
            // Uçarken öne eğilir, kayarken geriye yaslanır (animasyonlu karakterde kayma animasyonu zaten yaslanır).
            float pitch = 15f * flightBlend - slideBackLean * slideBlend;
            // Animasyon yoksa sendelerken önce öne kapaklanır, doğrulurken sönümlenerek yalpalar.
            float stumble = hasStumbleClip ? 0f : controller.StumbleBlend;
            pitch += stumblePitch * Mathf.Sin(stumble * Mathf.PI);
            float wobble = stumbleWobble * stumble * Mathf.Sin(stumble * Mathf.PI * 3f);
            // Önce karakter dönük hale getirilir, sonra eğim ve yatma oyuncunun eksenlerinde uygulanır.
            model.localRotation = Quaternion.Euler(pitch, 0f, lean + wobble) * Quaternion.Euler(0f, yaw, 0f);
        }

        // Animasyonlu karakter: kayma ve zıplama başladığı an kendi animasyonları baştan oynar;
        // oyun başlamadan ve süpürgedeyken ayakta duruş, diğer zamanlar koşu görünür.
        private void UpdateAnimation(bool playing, bool flying, bool airborne, float dt)
        {
            bool sliding = controller.IsSliding;
            if (sliding && !wasSliding)
            {
                slideClip.SetTime(character.slideStart);
                slideClip.SetSpeed(1);
            }

            if (airborne && !wasAirborne)
            {
                jumpClip.SetTime(character.jumpTakeoff);
                jumpClip.SetSpeed(1);
            }

            // Sendeleme animasyonu baştan oynar ve sendeleme süresine sığacak hızda biter.
            bool stumbling = hasStumbleClip && controller.StumbleBlend > 0f;
            if (stumbling && !wasStumbling)
            {
                stumbleClip.SetTime(0);
                stumbleClip.SetSpeed(character.stumble.length / controller.StumbleDuration);
            }

            // Yuvarlanma animasyonu ayaklar yere değerken başlar ve yuvarlanma süresine sığacak hızda biter.
            bool rolling = hasRollClip && controller.IsRolling;
            if (rolling && !wasRolling)
            {
                rollClip.SetTime(character.rollStart);
                rollClip.SetSpeed((character.rollEnd - character.rollStart) / controller.RollDuration);
            }

            wasSliding = sliding;
            wasAirborne = airborne;
            wasStumbling = stumbling;
            wasRolling = rolling;

            // Kayma ya da havada kalma uzarsa animasyon yerde kayarken ve inişten hemen önce bekletilir.
            if (slideClip.GetTime() >= character.slideHold)
            {
                slideClip.SetSpeed(0);
            }

            if (jumpClip.GetTime() >= character.jumpHold)
            {
                jumpClip.SetSpeed(0);
            }

            runClip.SetSpeed(Mathf.Clamp(controller.CurrentSpeed * character.runAnimPerSpeed, character.runAnimMin, character.runAnimMax));

            int active = !playing || flying ? StandInput : sliding ? SlideInput : rolling ? RollInput : stumbling ? StumbleInput :
                airborne ? JumpInput : RunInput;
            float step = blendTime > 0f ? dt / blendTime : 1f;
            float sum = 0f;
            for (int i = 0; i < weights.Length; i++)
            {
                weights[i] = Mathf.MoveTowards(weights[i], i == active ? 1f : 0f, step);
                sum += weights[i];
            }

            for (int i = 0; i < weights.Length; i++)
            {
                mixer.SetInputWeight(i, weights[i] / sum);
            }
        }

        // Wizard modeli: kollar ve bacaklar kodla sallanır. Modelin yukarı-aşağı oynamasını döndürür.
        private float UpdateLimbs(bool playing, bool flying, bool airborne, float dt)
        {
            float swing = Mathf.Sin(cycle);

            float legAngle = playing && controller.IsGrounded ? swing * legSwing : 0f;
            float armAngle = playing && controller.IsGrounded ? -swing * armSwing : 0f;

            slideBlend = Mathf.MoveTowards(slideBlend, controller.IsSliding ? 1f : 0f, slideBlendSpeed * dt);

            if (slideBlend > 0f)
            {
                SetLimbs(slideLegAngle * slideBlend, slideLegAngle * slideBlend, slideArmAngle * slideBlend, slideArmAngle * slideBlend);
            }
            else if (airborne)
            {
                legAngle = 35f;
                armAngle = -50f;
                SetLimbs(legAngle, -legAngle * 0.4f, armAngle, armAngle);
            }
            else if (flying)
            {
                SetLimbs(8f, -8f, 20f, 20f);
            }
            else
            {
                SetLimbs(legAngle, -legAngle, armAngle, -armAngle);
            }

            UpdateSkirt();

            // Koşarken hafif zıplama, uçarken sallanma.
            float bob = playing && controller.IsGrounded ? Mathf.Abs(swing) * bobHeight : 0f;
            if (flying)
            {
                bob = Mathf.Sin(cycle * 0.4f) * bobHeight;
            }

            bob *= 1f - slideBlend;
            return bob + slideLift * slideBlend;
        }

        private void SetLimbs(float legLeft, float legRight, float armLeft, float armRight)
        {
            SetPitch(legL, legLeft);
            SetPitch(legR, legRight);
            SetPitch(armL, armLeft);
            SetPitch(armR, armRight);
        }

        // Bacak geriye gidince arka etek de o yöne savrulur, böylece bacak ceketin içinden çıkmaz.
        private void UpdateSkirt()
        {
            if (skirtBack == null) return;

            float push = Mathf.Max(LegPush(legL), LegPush(legR));
            float angle = Mathf.Asin(Mathf.Clamp01(push)) * Mathf.Rad2Deg * skirtFollow;
            skirtBack.localRotation = Quaternion.Euler(skirtSign * angle, 0f, 0f);
        }

        // Ayağın eteğe (sırta) doğru gidişi: 0 = dik ya da öne, 1 = tam yatay geriye.
        private float LegPush(Transform leg)
        {
            if (leg == null) return 0f;

            return Vector3.Dot(leg.localRotation * Vector3.down, skirtOutward);
        }

        private static void SetPitch(Transform part, float degrees)
        {
            if (part != null)
            {
                part.localRotation = Quaternion.Euler(degrees, 0f, 0f);
            }
        }
    }
}
