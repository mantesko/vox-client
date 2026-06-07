import os
import sys
import time
import logging

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "client"))

from injector import TextInjector

def test_injection():
    print("====================================================")
    print("🔬 ТЕСТ ІНЖЕКТОРА: СЛАВА УКРАЇНІ")
    print("====================================================")

    # Ініціалізуємо інжектор
    injector = TextInjector()
    
    # Перевіряємо наявність необхідних утиліт
    print(f"\n📋 Утиліти:")
    print(f"  xclip: {'✅' if injector.has_xclip else '❌'}")
    print(f"  xdotool: {'✅' if injector.has_xdotool else '❌'}")
    
    if not injector.has_xclip or not injector.has_xdotool:
        print("\n⚠️  Встановіть відсутні утиліти:")
        if not injector.has_xclip:
            print("  sudo apt install xclip")
        if not injector.has_xdotool:
            print("  sudo apt install xdotool")
        return
    
    print("\n🚀 ВСТАВКА ФРАЗИ...")
    test_phrase = "Слава Україні! 🇺🇦"
    print(f"  Текст: {test_phrase}")
    
    # Викликаємо інжектор
    injector.inject(test_phrase)
    
    print("\n⏱️  Перевірте буфер обміну або активне вікно...")
    time.sleep(1)

    print("\n✅ Тест завершено.")
    print("====================================================")

if __name__ == "__main__":
    test_injection()
