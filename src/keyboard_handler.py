"""
AutoFish Minecraft - Gestionnaire de clavier.
"""

import logging
from typing import Callable, TYPE_CHECKING

from pynput import keyboard

if TYPE_CHECKING:
    from .app_state import AppState


class KeyboardHandler:
    """
    Gere les raccourcis clavier globaux et l'auto-pause.

    Raccourcis:
    - F8: Basculer pause
    - F9: Activer/desactiver completement
    - F10: Pause temporaire 15s
    - F11: Clic de test
    - E: Toggle inventaire (si fenetre active)
    - T, /, :: Ouvrir chat (si fenetre active)
    - Escape: Fermer inventaire/chat
    - Enter: Fermer chat
    """

    def __init__(
        self,
        state: 'AppState',
        on_toggle_pause: Callable,
        on_toggle_disable: Callable,
        on_temp_pause: Callable[[int], None],
        on_test_click: Callable,
        on_state_change: Callable
    ):
        """
        Initialise le gestionnaire de clavier.

        Args:
            state: Etat de l'application
            on_toggle_pause: Callback pour basculer la pause
            on_toggle_disable: Callback pour activer/desactiver
            on_temp_pause: Callback pour pause temporaire
            on_test_click: Callback pour clic de test
            on_state_change: Callback quand l'etat change
        """
        self.state = state
        self.on_toggle_pause = on_toggle_pause
        self.on_toggle_disable = on_toggle_disable
        self.on_temp_pause = on_temp_pause
        self.on_test_click = on_test_click
        self.on_state_change = on_state_change
        self._listener = None

    def start(self):
        """Demarre le listener clavier."""
        self._listener = keyboard.Listener(on_press=self._on_key_press)
        self._listener.start()

    def stop(self):
        """Arrete le listener clavier."""
        if self._listener:
            self._listener.stop()

    def _on_key_press(self, key):
        """Gere les appuis de touches."""
        try:
            # Touches de controle globales
            if key == keyboard.Key.f8:
                self.on_toggle_pause()
            elif key == keyboard.Key.f9:
                self.on_toggle_disable()
            elif key == keyboard.Key.f10:
                self.on_temp_pause(15)
            elif key == keyboard.Key.f11:
                self.on_test_click()

            # Auto-pause pour inventaire/chat (seulement si fenetre au premier plan)
            elif self.state.is_app_in_foreground:
                self._handle_game_keys(key)

        except Exception:
            pass

    def _handle_game_keys(self, key):
        """Gere les touches liees au jeu."""
        # Si le chat est ouvert, seuls Escape et Enter sont pris en compte
        if self.state.is_chat_open:
            if key == keyboard.Key.esc:
                self._close_all_menus()
            elif self._is_enter_key(key):
                self._close_chat()
            # Ignorer toutes les autres touches (y compris t, /, :)
            return

        # Touche E - Toggle inventaire
        if self._is_char_key(key, 'e'):
            self._toggle_inventory()

        # Touches T, / ou : - Ouverture du chat (seulement si chat pas deja ouvert)
        elif self._is_char_key(key, 't', '/', ':'):
            self._open_chat()

        # Touche Escape - Ferme inventaire ET chat
        elif key == keyboard.Key.esc:
            self._close_all_menus()

        # Touche Enter - Ferme le chat seulement
        elif self._is_enter_key(key):
            self._close_chat()

    def _is_char_key(self, key, *chars) -> bool:
        """Verifie si la touche correspond a un caractere."""
        if hasattr(key, 'char') and key.char:
            return key.char.lower() in chars
        return False

    def _is_enter_key(self, key) -> bool:
        """Verifie si la touche est Enter (toutes variantes)."""
        # Touche Enter standard
        if key == keyboard.Key.enter:
            return True
        # Caracteres retour chariot/nouvelle ligne (pave numerique ou autres claviers)
        if hasattr(key, 'char') and key.char in ('\r', '\n'):
            return True
        return False

    def _toggle_inventory(self):
        """Bascule l'etat de l'inventaire."""
        if self.state.is_inventory_open:
            self.state.is_inventory_open = False
            logging.info("Inventaire ferme - Auto-pause desactivee")
        else:
            self.state.is_inventory_open = True
            logging.info("Inventaire ouvert - Auto-pause activee")
        self.on_state_change()

    def _open_chat(self):
        """Ouvre le chat."""
        self.state.is_chat_open = True
        logging.info("Chat ouvert - Auto-pause activee")
        self.on_state_change()

    def _close_all_menus(self):
        """Ferme l'inventaire et le chat."""
        if self.state.is_inventory_open or self.state.is_chat_open:
            self.state.is_inventory_open = False
            self.state.is_chat_open = False
            logging.info("Inventaire/Chat ferme (Escape) - Auto-pause desactivee")
            self.on_state_change()

    def _close_chat(self):
        """Ferme le chat."""
        if self.state.is_chat_open:
            self.state.is_chat_open = False
            logging.info("Chat ferme (Enter) - Auto-pause desactivee")
            self.on_state_change()
