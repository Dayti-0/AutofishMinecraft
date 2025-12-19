"""
Module d'auto-calibration.
Gère la détection automatique du seuil optimal pour la pêche.
"""

import time
import logging
import numpy as np
from typing import Callable, Optional, List


class AutoCalibrator:
    """
    Système d'auto-calibration du seuil de détection.

    Collecte des échantillons audio pendant une période définie
    et calcule le seuil optimal basé sur les pics détectés.
    """

    def __init__(self, duration: int = 30):
        """
        Initialise le calibrateur.

        Args:
            duration: Durée de la calibration en secondes.
        """
        self.calibration_data: List[float] = []
        self.peak_values: List[float] = []
        self.is_calibrating: bool = False
        self.calibration_duration: int = duration
        self.callback: Optional[Callable] = None
        self.progress_callback: Optional[Callable] = None
        self.start_time: float = 0

    def start_calibration(
        self,
        callback: Callable[[Optional[float]], None],
        progress_callback: Optional[Callable[[int, float], None]] = None
    ) -> None:
        """
        Démarre la calibration.

        Args:
            callback: Fonction appelée à la fin avec le seuil optimal.
            progress_callback: Fonction appelée pour la progression (progress%, temps_restant).
        """
        self.calibration_data = []
        self.peak_values = []
        self.is_calibrating = True
        self.callback = callback
        self.progress_callback = progress_callback
        self.start_time = time.time()

        logging.info(
            f"Calibration démarrée - Pêchez normalement pendant "
            f"{self.calibration_duration} secondes"
        )

    def add_sample(self, volume_level: float, is_peak: bool = False) -> None:
        """
        Ajoute un échantillon de volume.

        Args:
            volume_level: Niveau de volume normalisé (0-10).
            is_peak: True si c'est un pic détecté (poisson qui mord).
        """
        if not self.is_calibrating:
            return

        self.calibration_data.append(volume_level)

        # Marquer les pics (quand un poisson mord)
        if is_peak:
            self.peak_values.append(volume_level)
            logging.info(f"Pic détecté pendant calibration: {volume_level:.1f}")

        # Mise à jour du progrès
        elapsed = time.time() - self.start_time
        progress = min(100, int((elapsed / self.calibration_duration) * 100))

        if self.progress_callback:
            remaining = max(0, self.calibration_duration - elapsed)
            self.progress_callback(progress, remaining)

        # Vérifier si la calibration est terminée
        if elapsed > self.calibration_duration:
            self.finish_calibration()

    def finish_calibration(self) -> None:
        """Termine la calibration et calcule le seuil optimal."""
        if not self.calibration_data:
            self.is_calibrating = False
            if self.callback:
                self.callback(None)
            return

        # Analyser les données
        data = np.array(self.calibration_data)

        if len(self.peak_values) >= 2:
            # Si on a détecté des pics, utiliser leur moyenne
            peaks = np.array(self.peak_values)
            min_peak = np.min(peaks)
            avg_peak = np.mean(peaks)

            # Le seuil optimal est légèrement en dessous du plus petit pic
            threshold = min_peak * 0.85  # 85% du pic minimum

            logging.info(
                f"Calibration avec {len(self.peak_values)} pics détectés"
            )
            logging.info(f"Pics: min={min_peak:.1f}, moy={avg_peak:.1f}")
        else:
            # Fallback: utiliser la méthode statistique
            mean = np.mean(data)
            std = np.std(data)

            # Les pics sont au-dessus de mean + 1.5*std
            threshold = mean + 1.5 * std

            logging.info("Calibration statistique (pas assez de pics)")
            logging.info(f"Moyenne={mean:.1f}, Écart-type={std:.1f}")

        # Arrondir à 0.1 près
        threshold = round(threshold, 1)

        # Limiter entre 4 et 9
        threshold = max(4.0, min(9.0, threshold))

        self.is_calibrating = False
        logging.info(f"Calibration terminée - Seuil optimal: {threshold}")

        if self.callback:
            self.callback(threshold)

    def cancel(self) -> None:
        """Annule la calibration en cours."""
        self.is_calibrating = False
        self.calibration_data = []
        self.peak_values = []
        logging.info("Calibration annulée")

    def get_progress(self) -> tuple:
        """
        Obtient la progression actuelle.

        Returns:
            Tuple (pourcentage, temps_restant).
        """
        if not self.is_calibrating:
            return (0, 0)

        elapsed = time.time() - self.start_time
        progress = min(100, int((elapsed / self.calibration_duration) * 100))
        remaining = max(0, self.calibration_duration - elapsed)

        return (progress, remaining)

    def get_sample_count(self) -> int:
        """
        Obtient le nombre d'échantillons collectés.

        Returns:
            Nombre d'échantillons.
        """
        return len(self.calibration_data)

    def get_peak_count(self) -> int:
        """
        Obtient le nombre de pics détectés.

        Returns:
            Nombre de pics.
        """
        return len(self.peak_values)
