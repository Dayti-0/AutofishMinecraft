"""
AutoFish Minecraft - Gestionnaire de clics.
"""

import time
import random
import logging
from typing import Optional, Callable, TYPE_CHECKING

import win32gui
import win32con
import win32api

from .window_management import get_process_id_by_name, get_hwnds_for_pid
from .human_behavior import HumanLikeRandomizer

if TYPE_CHECKING:
    from .app_state import AppState
    from .stats_manager import StatsManager


class ClickHandler:
    """
    Gere les clics automatiques avec simulation de comportement humain.

    Responsable de:
    - L'execution des clics droits
    - La variation de position des clics
    - Les delais humanises
    """

    def __init__(
        self,
        state: 'AppState',
        randomizer: HumanLikeRandomizer,
        stats_manager: 'StatsManager',
        on_click_callback: Optional[Callable] = None
    ):
        """
        Initialise le gestionnaire de clics.

        Args:
            state: Etat de l'application
            randomizer: Randomizer pour comportement humain
            stats_manager: Gestionnaire de statistiques
            on_click_callback: Callback appele apres chaque clic
        """
        self.state = state
        self.randomizer = randomizer
        self.stats_manager = stats_manager
        self.on_click_callback = on_click_callback

    def _get_window_handle(self) -> Optional[int]:
        """Recupere le handle de la fenetre cible."""
        if not self.state.app_pid:
            self.state.app_pid = get_process_id_by_name(self.state.selected_app)

        if not self.state.app_pid:
            return None

        hwnds = get_hwnds_for_pid(self.state.app_pid)
        return hwnds[0] if hwnds else None

    def _get_click_position(self, hwnd: int, base_x: Optional[int] = None, base_y: Optional[int] = None) -> tuple:
        """Calcule une position de clic avec variation."""
        rect = win32gui.GetClientRect(hwnd)

        if base_x is None:
            base_x = (rect[2] - rect[0]) // 2
        if base_y is None:
            base_y = (rect[3] - rect[1]) // 2

        return self.randomizer.get_click_position_variation(base_x, base_y, rect)

    def _send_right_click(self, hwnd: int, x: int, y: int):
        """Envoie un clic droit a la fenetre."""
        lParam = win32api.MAKELONG(x, y)
        win32gui.PostMessage(hwnd, win32con.WM_RBUTTONDOWN, win32con.MK_RBUTTON, lParam)
        time.sleep(random.uniform(0.01, 0.03))
        win32gui.PostMessage(hwnd, win32con.WM_RBUTTONUP, 0, lParam)

    def perform_double_right_click(self, increment_counter: bool = True):
        """
        Effectue deux clics droits avec delai humanise.

        Utilise pour attraper un poisson (premier clic) et relancer (second clic).
        """
        try:
            # Reinitialiser les compteurs d'inactivite
            self.state.reset_inactivity()

            hwnd = self._get_window_handle()
            if not hwnd:
                return

            rect = win32gui.GetClientRect(hwnd)
            x, y = self._get_click_position(hwnd)

            # Premier delai humanise
            context = {'urgent': self.state.current_volume_level > self.state.detection.threshold * 1.2}
            delay1 = self.randomizer.get_humanized_delay(
                self.state.detection.min_delay,
                self.state.detection.max_delay,
                context,
                self.state.is_boost_mode
            )

            self.state.current_pattern = self.randomizer.last_pattern_type or "steady"

            logging.info(
                f"Clic apres {delay1:.2f}s a ({x},{y}), volume: {self.state.current_volume_level:.1f}"
            )
            time.sleep(delay1)

            # Premier clic
            self._send_right_click(hwnd, x, y)

            # Deuxieme clic apres delai
            delay2 = random.uniform(0.5, 0.7)
            time.sleep(delay2)

            x2, y2 = self._get_click_position(hwnd, x, y)
            self._send_right_click(hwnd, x2, y2)

            # Attendre le delai post-action
            time.sleep(self.state.detection.post_action_delay)

            # Mettre a jour les timestamps
            self.state.update_activity()

            if increment_counter:
                self._record_click(delay1, self.state.current_pattern)

        except Exception as e:
            logging.error(f"Erreur lors des clics: {e}")

    def perform_single_right_click(self, increment_counter: bool = True):
        """
        Effectue un seul clic droit avec delai humanise.

        Utilise pour le relancement apres inactivite.
        """
        try:
            # Reinitialiser les compteurs d'inactivite
            self.state.reset_inactivity()

            hwnd = self._get_window_handle()
            if not hwnd:
                return

            x, y = self._get_click_position(hwnd)

            delay = self.randomizer.get_humanized_delay(
                self.state.detection.min_delay,
                self.state.detection.max_delay,
                {},
                self.state.is_boost_mode
            )
            time.sleep(delay)

            self._send_right_click(hwnd, x, y)

            self.state.last_click_time = time.time()
            self.state.last_activity_time = time.time()

            if increment_counter:
                self._record_click(delay, "inactivity")

            logging.info(f"Clic unique a ({x},{y})")

        except Exception as e:
            logging.error(f"Erreur clic unique: {e}")

    def _record_click(self, delay: float, pattern: str):
        """Enregistre un clic dans les statistiques."""
        self.state.click_counter += 1
        self.state.click_timestamps.append(time.time())
        self.stats_manager.record_click(delay, pattern, True)

        if self.on_click_callback:
            rate = self.state.get_display_rate()
            volume = self.state.current_volume_level
            display_line = self.state.build_display_line(delay, volume, rate)
            self.on_click_callback(display_line)
