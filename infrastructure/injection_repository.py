import subprocess
import logging
from typing import Optional
from ..domain.entities import TextInjectionRepository

logger = logging.getLogger("InjectionRepository")

class X11TextInjectionRepository(TextInjectionRepository):
    """Text injection implementation for X11 systems"""
    
    def __init__(self):
        self._has_xclip = self._check_command_availability("xclip")
        self._has_xdotool = self._check_command_availability("xdotool")
        
        if not self._has_xclip:
            logger.error("xclip utility not found! Install it: sudo apt install xclip")
        if not self._has_xdotool:
            logger.error("xdotool utility not found! Install it: sudo apt install xdotool")
    
    def inject_text(self, text: str) -> None:
        """Inject text using clipboard and keyboard simulation"""
        if not text or not self.is_available():
            return
            
        logger.info(f"Injecting text: {text[:50]}...")
        
        try:
            # Copy to clipboard using xclip
            if self._has_xclip:
                subprocess.run(
                    ['xclip', '-selection', 'clipboard'], 
                    input=text.encode('utf-8'), 
                    check=True
                )
            else:
                # Fallback to pyperclip
                import pyperclip
                pyperclip.copy(text)
            
            # Simulate Ctrl+V using xdotool
            if self._has_xdotool:
                subprocess.run(
                    ["xdotool", "key", "--clearmodifiers", "ctrl+v"], 
                    check=True
                )
                
        except Exception as e:
            logger.error(f"Text injection failed: {e}")
    
    def is_available(self) -> bool:
        """Check if text injection is available"""
        return self._has_xclip and self._has_xdotool
    
    def _check_command_availability(self, command: str) -> bool:
        """Check if system command is available"""
        try:
            subprocess.run(
                ["which", command], 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL, 
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False
