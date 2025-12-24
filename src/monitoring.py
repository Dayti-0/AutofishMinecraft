"""
AutoFish Minecraft - Threads de monitoring.
"""

import time
import random
import logging
import threading
from typing import Callable, TYPE_CHECKING

from .audio_processing import get_app_volume, volume_to_db, db_to_normalized_scale
from .window_management import is_application_in_foreground

if TYPE_CHECKING:
    from .app_state import AppState
    from .calibration import AutoCalibrator


class VolumeMonitor:
    """
    Moniteur de volume audio.

    Detecte les pics de volume indiquant qu'un poisson a mordu.
    """

    def __init__(
        self,
        state: 'AppState',
        calibrator: 'AutoCalibrator',
        on_trigger: Callable,
        on_volume_update: Callable[[float], None]
    ):
        """
        Initialise le moniteur de volume.

        Args:
            state: Etat de l'application
            calibrator: Calibrateur automatique
            on_trigger: Callback quand un declenchement est detecte
            on_volume_update: Callback pour mise a jour du volume
        """
        self.state = state
        self.calibrator = calibrator
        self.on_trigger = on_trigger
        self.on_volume_update = on_volume_update
        self._thread = None

    def start(self):
        """Demarre le monitoring dans un thread."""
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def _monitor_loop(self):
        """Boucle principale de monitoring du volume."""
        while self.state.is_running:
            try:
                self._update_foreground_status()

                if not self.state.is_action_allowed():
                    time.sleep(0.05)
                    continue

                if not self.state.selected_app or not self.state.app_pid:
                    time.sleep(0.05)
                    continue

                volume = get_app_volume(self.state.selected_app)
                if volume is None:
                    time.sleep(0.05)
                    continue

                normalized = self._process_volume(volume)
                self.state.current_volume_level = normalized
                self.on_volume_update(normalized)

                # Mode calibration
                if self.calibrator.is_calibrating:
                    self._handle_calibration(normalized)
                    continue

                # Mise a jour historique et baseline
                self._update_baseline(normalized)

                # Detection de declenchement
                self._check_trigger(normalized)

                time.sleep(0.05)

            except Exception as e:
                logging.error(f"Erreur monitoring volume: {e}")
                time.sleep(1)

    def _update_foreground_status(self):
        """Met a jour le statut de focus de la fenetre."""
        if self.state.selected_app and self.state.app_pid:
            self.state.is_app_in_foreground = is_application_in_foreground(
                self.state.app_pid
            )

    def _process_volume(self, volume: float) -> float:
        """Convertit le volume en echelle normalisee."""
        db = volume_to_db(volume)
        return db_to_normalized_scale(db)

    def _handle_calibration(self, normalized: float):
        """Gere le mode calibration."""
        is_peak = (
            normalized > self.state.baseline_volume * 1.5 and
            normalized > 5.0
        )
        self.calibrator.add_sample(normalized, is_peak)
        time.sleep(0.05)

    def _update_baseline(self, normalized: float):
        """Met a jour l'historique et la baseline du volume."""
        self.state.volume_history.append(normalized)

        if len(self.state.volume_history) < 2:
            self.state.baseline_volume = normalized
        else:
            self.state.baseline_volume = (
                sum(self.state.volume_history) / len(self.state.volume_history)
            )

    def _check_trigger(self, normalized: float):
        """Verifie si un declenchement doit avoir lieu."""
        threshold = self.state.detection.threshold
        cooldown = self.state.detection.cooldown_period

        if normalized > threshold and normalized > self.state.baseline_volume * 1.2:
            current_time = time.time()

            if current_time - self.state.last_trigger_time > cooldown:
                self.state.trigger_count += 1

                if self.state.trigger_count >= 2:
                    self.state.last_trigger_time = current_time
                    self.state.last_catch_time = current_time  # Mise a jour du timestamp de prise
                    threading.Thread(target=self.on_trigger, daemon=True).start()
                    self.state.trigger_count = 0
        else:
            if self.state.trigger_count > 0:
                self.state.trigger_count -= 0.5


class InactivityMonitor:
    """
    Moniteur d'inactivite.

    Declenche un clic automatique si aucune activite n'est detectee.
    """

    def __init__(
        self,
        state: 'AppState',
        calibrator: 'AutoCalibrator',
        on_inactivity: Callable
    ):
        """
        Initialise le moniteur d'inactivite.

        Args:
            state: Etat de l'application
            calibrator: Calibrateur automatique
            on_inactivity: Callback lors d'inactivite detectee
        """
        self.state = state
        self.calibrator = calibrator
        self.on_inactivity = on_inactivity
        self._thread = None

    def start(self):
        """Demarre le monitoring dans un thread."""
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def _monitor_loop(self):
        """Boucle principale de verification d'inactivite."""
        while self.state.is_running:
            try:
                if not self._should_check_inactivity():
                    time.sleep(1)
                    continue

                time_since_last = time.time() - self.state.last_activity_time

                if time_since_last > self.state.inactivity.current_delay:
                    self.state.inactivity.trigger_count += 1

                    if self.state.inactivity.trigger_count >= 2:
                        logging.info(
                            f"Inactivite detectee ({time_since_last:.1f}s) - Clic automatique"
                        )
                        threading.Thread(target=self.on_inactivity, daemon=True).start()
                        self._reset_inactivity_delay()
                else:
                    self.state.inactivity.trigger_count = 0

                time.sleep(1)

            except Exception as e:
                logging.error(f"Erreur inactivite: {e}")
                time.sleep(5)

    def _should_check_inactivity(self) -> bool:
        """Verifie si l'inactivite doit etre surveillee."""
        return (
            self.state.is_action_allowed() and
            not self.calibrator.is_calibrating
        )

    def _reset_inactivity_delay(self):
        """Reinitialise le delai d'inactivite."""
        base = self.state.inactivity.base_delay
        self.state.inactivity.current_delay = random.uniform(base - 2, base + 2)
        self.state.inactivity.trigger_count = 0


class TempPauseMonitor:
    """
    Moniteur de pause temporaire.

    Gere le compte a rebours de la pause temporaire.
    """

    def __init__(self, state: 'AppState', on_pause_end: Callable):
        """
        Initialise le moniteur de pause temporaire.

        Args:
            state: Etat de l'application
            on_pause_end: Callback quand la pause se termine
        """
        self.state = state
        self.on_pause_end = on_pause_end
        self._thread = None

    def start(self):
        """Demarre le monitoring dans un thread."""
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def _monitor_loop(self):
        """Boucle de gestion de la pause temporaire."""
        while self.state.is_running:
            if self.state.temp_pause_remaining > 0:
                elapsed = time.time() - self.state.temp_pause_start
                self.state.temp_pause_remaining = max(0, 15 - elapsed)

                if self.state.temp_pause_remaining == 0:
                    self.on_pause_end()

            time.sleep(0.5)


class AutoCastMonitor:
    """
    Moniteur d'auto-cast.

    Declenche automatiquement un recast si aucune prise n'est detectee apres un certain delai.
    """

    def __init__(
        self,
        state: 'AppState',
        calibrator: 'AutoCalibrator',
        on_auto_cast: Callable
    ):
        """
        Initialise le moniteur d'auto-cast.

        Args:
            state: Etat de l'application
            calibrator: Calibrateur automatique
            on_auto_cast: Callback lors du declenchement de l'auto-cast
        """
        self.state = state
        self.calibrator = calibrator
        self.on_auto_cast = on_auto_cast
        self._thread = None

    def start(self):
        """Demarre le monitoring dans un thread."""
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def _monitor_loop(self):
        """Boucle principale de verification de l'auto-cast."""
        while self.state.is_running:
            try:
                if not self._should_check_auto_cast():
                    time.sleep(1)
                    continue

                time_since_last_catch = time.time() - self.state.last_catch_time

                if time_since_last_catch > self.state.auto_cast.current_delay:
                    logging.info(
                        f"Aucune prise depuis {time_since_last_catch:.1f}s - Auto-cast"
                    )
                    threading.Thread(target=self.on_auto_cast, daemon=True).start()
                    self._reset_auto_cast_delay()

                time.sleep(1)

            except Exception as e:
                logging.error(f"Erreur auto-cast: {e}")
                time.sleep(5)

    def _should_check_auto_cast(self) -> bool:
        """Verifie si l'auto-cast doit etre surveille."""
        return (
            self.state.auto_cast.enabled and
            self.state.is_action_allowed() and
            not self.calibrator.is_calibrating
        )

    def _reset_auto_cast_delay(self):
        """Reinitialise le delai d'auto-cast."""
        base = self.state.auto_cast.base_delay
        self.state.auto_cast.current_delay = random.uniform(base - 2, base + 2)
        self.state.last_catch_time = time.time()
