import subprocess
import logging
import config

logger = logging.getLogger("VoxInjector")

class TextInjector:
    def __init__(self):
        # Перевірка наявності необхідних утиліт
        self.has_xclip = self._has_command("xclip")
        self.has_xdotool = self._has_command("xdotool")
        if not self.has_xclip:
            logger.error("Утиліту 'xclip' не знайдено! Встановіть її: sudo apt install xclip")

    def inject(self, text: str):
        if not text: 
            return
            
        logger.info(f"Інжектуємо текст: {text[:50]}...")
        
        try:
            # 1. Запис у буфер обміну через xclip
            if self.has_xclip:
                subprocess.run(['xclip', '-selection', 'clipboard'], input=text.encode('utf-8'), check=True)
            else:
                # Fallback, якщо немає xclip (може не працювати для довгих текстів)
                import pyperclip
                pyperclip.copy(text)
                
            # 2. Емуляція вставки через Ctrl+V
            if self.has_xdotool:
                subprocess.run(["xdotool", "key", "--clearmodifiers", "ctrl+v"], check=True)
                
                # 3. Додатковий Enter, якщо увімкнено AUTO_ENTER
                if getattr(config, 'AUTO_ENTER', False):
                    logger.info("Надсилаємо Enter (AUTO_ENTER=True)")
                    subprocess.run(["xdotool", "key", "Return"], check=True)
            else:
                logger.error("Утиліту 'xdotool' не знайдено! Неможливо імітувати вставку.")
                
        except Exception as e:
            logger.error(f"Помилка інжекції: {e}")

    def _has_command(self, cmd: str) -> bool:
        try:
            subprocess.run(["which", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return True
        except: 
            return False
