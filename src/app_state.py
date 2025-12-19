"""
AutoFish Minecraft - Gestion de l'etat de l'application.
"""

import time
import random
import collections
import tkinter as tk
from dataclasses import dataclass, field
from typing import Optional, Deque

from .config_manager import load_config


@dataclass
class DisplayOptions:
    """Options d'affichage de l'interface."""
    show_delay: bool = True
    show_volume: bool = True
    show_click_counter: bool = True
    show_rate: bool = True
    text_color: str = "Vert clair"


@dataclass
class DetectionParams:
    """Parametres de detection audio."""
    threshold: float = 8.0
    min_delay: float = 0.1
    max_delay: float = 1.5
    cooldown_period: float = 2.0
    post_action_delay: float = 0.75


@dataclass
class InactivityParams:
    """Parametres de gestion de l'inactivite."""
    base_delay: int = 7
    current_delay: float = 7.0
    trigger_count: int = 0


class AppState:
    """
    Classe centralisee pour gerer l'etat de l'application.

    Gere toutes les variables d'etat, les compteurs et les flags.
    """

    def __init__(self):
        """Initialise l'etat de l'application depuis la configuration."""
        self.config = load_config()

        # Flags d'etat principaux
        self.is_running: bool = True
        self.is_paused: bool = self.config.get("is_paused", False)
        self.is_completely_disabled: bool = self.config.get("is_completely_disabled", False)
        self.is_boost_mode: bool = self.config.get("is_boost_mode", False)

        # Auto-pause (inventaire/chat)
        self.is_inventory_open: bool = False
        self.is_chat_open: bool = False

        # Pause temporaire
        self.temp_pause_remaining: float = 0.0
        self.temp_pause_start: float = 0.0

        # Parametres de detection
        self.detection = DetectionParams(
            threshold=self.config.get("threshold", 8.0),
            min_delay=self.config.get("min_delay", 0.1),
            max_delay=self.config.get("max_delay", 1.5),
            post_action_delay=self.config.get("post_action_delay", 0.75)
        )

        # Inactivite
        inactivity_base = self.config.get("inactivity_base", 7)
        self.inactivity = InactivityParams(
            base_delay=inactivity_base,
            current_delay=random.uniform(inactivity_base - 2, inactivity_base + 2)
        )

        # Options d'affichage
        self.display = DisplayOptions(
            show_delay=self.config.get("show_delay", True),
            show_volume=self.config.get("show_volume", True),
            show_click_counter=self.config.get("show_click_counter", True),
            show_rate=self.config.get("show_rate", True),
            text_color=self.config.get("text_color", "Vert clair")
        )

        # Volume et detection
        self.volume_history: Deque[float] = collections.deque(maxlen=10)
        self.baseline_volume: float = 0.0
        self.trigger_count: int = 0
        self.last_trigger_time: float = 0.0
        self.current_volume_level: float = 0.0

        # Timing
        self.last_click_time: float = time.time()
        self.last_activity_time: float = time.time()
        self.start_time: float = time.time()

        # Compteurs
        self.click_counter: int = self.config.get("click_counter", 0)
        self.click_timestamps: Deque[float] = collections.deque()

        # Taux lisse
        self.last_rate: float = 0.0
        self.smoothing_alpha: float = 0.3

        # Pattern actuel
        self.current_pattern: str = "steady"

        # Application cible
        self.selected_app: str = self.config.get("selected_app", "")
        self.app_pid: Optional[int] = None
        self.is_app_in_foreground: bool = False

    def reset_inactivity(self):
        """Reinitialise les compteurs d'inactivite."""
        self.last_activity_time = time.time()
        self.inactivity.trigger_count = 0
        self.inactivity.current_delay = random.uniform(
            self.inactivity.base_delay - 2,
            self.inactivity.base_delay + 2
        )

    def update_activity(self):
        """Met a jour le timestamp de derniere activite."""
        self.last_click_time = time.time()
        self.last_activity_time = time.time()
        self.last_trigger_time = time.time()

    def is_action_allowed(self) -> bool:
        """Verifie si les actions automatiques sont autorisees."""
        return (
            not self.is_completely_disabled and
            not self.is_paused and
            self.temp_pause_remaining == 0 and
            not self.is_inventory_open and
            not self.is_chat_open
        )

    def get_display_rate(self) -> int:
        """Calcule le taux d'affichage lisse."""
        current_time = time.time()
        recent_clicks = [t for t in self.click_timestamps if current_time - t < 60]
        rate = len(recent_clicks)
        self.last_rate = self.smoothing_alpha * rate + (1 - self.smoothing_alpha) * self.last_rate
        return int(self.last_rate)

    def build_display_line(self, delay: float, volume: float, rate: int) -> str:
        """Construit la ligne d'affichage pour l'overlay."""
        parts = []
        if self.display.show_delay:
            parts.append(f"{delay:.2f}")
        if self.display.show_volume:
            parts.append(f"{volume:.1f}")
        if self.display.show_click_counter:
            parts.append(str(self.click_counter))
        if self.display.show_rate:
            parts.append(str(rate))
        return " | ".join(parts) if parts else "Ready"

    def to_config_dict(self) -> dict:
        """Convertit l'etat en dictionnaire de configuration."""
        return {
            "threshold": self.detection.threshold,
            "min_delay": self.detection.min_delay,
            "max_delay": self.detection.max_delay,
            "post_action_delay": self.detection.post_action_delay,
            "is_paused": self.is_paused,
            "is_completely_disabled": self.is_completely_disabled,
            "click_counter": self.click_counter,
            "inactivity_base": self.inactivity.base_delay,
            "selected_app": self.selected_app,
            "show_delay": self.display.show_delay,
            "show_volume": self.display.show_volume,
            "show_click_counter": self.display.show_click_counter,
            "show_rate": self.display.show_rate,
            "text_color": self.display.text_color,
            "is_boost_mode": self.is_boost_mode,
        }
