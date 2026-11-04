using UnityEngine;
using UnityEngine.InputSystem;

namespace PembeBuyucu
{
    /// <summary>
    /// Bütün girişleri (klavye, fare, dokunmatik) tek yerde toplar.
    /// Diğer scriptler yalnızca bu sınıfın özelliklerini okur.
    /// Her karede sıfırlanan "bu karede basıldı" değerleri verir.
    /// </summary>
    [DefaultExecutionOrder(-100)]
    public class InputReader : MonoBehaviour
    {
        [Tooltip("Kaydırma hareketinin sayılması için gereken en az mesafe (piksel).")]
        [SerializeField] private float swipeThreshold = 60f;

        private bool isSwiping;
        private Vector2 swipeStart;

        public bool LeftPressed { get; private set; }
        public bool RightPressed { get; private set; }
        public bool JumpPressed { get; private set; }
        public bool SlidePressed { get; private set; }
        public bool RestartPressed { get; private set; }
        public bool TapPressed { get; private set; }

        private void Update()
        {
            LeftPressed = false;
            RightPressed = false;
            JumpPressed = false;
            SlidePressed = false;
            RestartPressed = false;
            TapPressed = false;

            ReadKeyboard();
            ReadPointer();
        }

        private void ReadKeyboard()
        {
            Keyboard keyboard = Keyboard.current;
            if (keyboard == null) return;

            if (keyboard.aKey.wasPressedThisFrame || keyboard.leftArrowKey.wasPressedThisFrame)
            {
                LeftPressed = true;
            }

            if (keyboard.dKey.wasPressedThisFrame || keyboard.rightArrowKey.wasPressedThisFrame)
            {
                RightPressed = true;
            }

            if (keyboard.spaceKey.wasPressedThisFrame || keyboard.wKey.wasPressedThisFrame || keyboard.upArrowKey.wasPressedThisFrame)
            {
                JumpPressed = true;
            }

            if (keyboard.sKey.wasPressedThisFrame || keyboard.downArrowKey.wasPressedThisFrame)
            {
                SlidePressed = true;
            }

            if (keyboard.rKey.wasPressedThisFrame)
            {
                RestartPressed = true;
            }
        }

        // Pointer hem fareyi hem de dokunmatik ekranı kapsar.
        // Böylece mobil kontrolü bilgisayarda fare sürükleyerek de test edebiliriz.
        private void ReadPointer()
        {
            Pointer pointer = Pointer.current;
            if (pointer == null) return;

            if (pointer.press.wasPressedThisFrame)
            {
                TapPressed = true;
                isSwiping = true;
                swipeStart = pointer.position.ReadValue();
            }
            else if (isSwiping && pointer.press.isPressed)
            {
                Vector2 delta = pointer.position.ReadValue() - swipeStart;
                if (delta.magnitude >= swipeThreshold)
                {
                    if (Mathf.Abs(delta.x) > Mathf.Abs(delta.y))
                    {
                        if (delta.x < 0f) LeftPressed = true;
                        else RightPressed = true;
                    }
                    else if (delta.y > 0f)
                    {
                        JumpPressed = true;
                    }
                    else
                    {
                        SlidePressed = true;
                    }

                    isSwiping = false;
                }
            }

            if (pointer.press.wasReleasedThisFrame)
            {
                isSwiping = false;
            }
        }
    }
}
