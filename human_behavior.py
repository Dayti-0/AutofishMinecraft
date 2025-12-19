"""
Module de simulation du comportement humain.
Gère la randomisation réaliste des délais et positions de clic.
"""

import time
import random
import logging
import collections
import numpy as np
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Tuple


@dataclass
class HumanProfile:
    """
    Profil comportemental simulant un humain spécifique.

    Attributes:
        name: Nom du profil.
        reaction_speed: Vitesse de réaction (0.5=lent, 1.0=normal, 1.5=rapide).
        consistency: Cohérence des actions (0.0=erratique, 1.0=constant).
        fatigue_rate: Taux de fatigue (0.0=jamais fatigué, 1.0=fatigue rapide).
        concentration_level: Niveau de concentration (0.0=distrait, 1.0=concentré).
        rhythm_variation: Variation du rythme (0.0=robotique, 1.0=très varié).
    """
    name: str = "Default"
    reaction_speed: float = 1.0
    consistency: float = 0.5
    fatigue_rate: float = 0.5
    concentration_level: float = 0.6
    rhythm_variation: float = 0.5

    @classmethod
    def generate_random(cls, name: str = "Random") -> "HumanProfile":
        """
        Génère un profil humain aléatoire mais cohérent.

        Args:
            name: Nom à donner au profil.

        Returns:
            Un nouveau HumanProfile avec des valeurs aléatoires cohérentes.
        """
        reaction_speed = random.gauss(1.0, 0.2)
        consistency = random.betavariate(2, 2)

        # Les personnes rapides sont souvent moins consistantes
        if reaction_speed > 1.2:
            consistency *= 0.8

        fatigue_rate = random.betavariate(2, 3)
        concentration_level = random.betavariate(3, 2)
        rhythm_variation = 1.0 - (concentration_level * 0.5)

        return cls(
            name=name,
            reaction_speed=max(0.3, min(2.0, reaction_speed)),
            consistency=max(0.1, min(1.0, consistency)),
            fatigue_rate=max(0.0, min(1.0, fatigue_rate)),
            concentration_level=max(0.0, min(1.0, concentration_level)),
            rhythm_variation=max(0.1, min(1.0, rhythm_variation))
        )

    def to_dict(self) -> dict:
        """Convertit le profil en dictionnaire."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "HumanProfile":
        """Crée un profil à partir d'un dictionnaire."""
        return cls(**data)


class HumanLikeRandomizer:
    """
    Système avancé de randomisation simulant le comportement humain.

    Gère les délais, la fatigue, la concentration et les patterns comportementaux.
    """

    # Patterns comportementaux avec leurs poids et variations
    BEHAVIOR_PATTERNS = {
        'steady': {'weight': 0.4, 'variation': 0.1},
        'accelerating': {'weight': 0.15, 'variation': 0.2},
        'decelerating': {'weight': 0.15, 'variation': 0.2},
        'erratic': {'weight': 0.1, 'variation': 0.4},
        'rhythmic': {'weight': 0.15, 'variation': 0.15},
        'tired': {'weight': 0.05, 'variation': 0.3}
    }

    def __init__(self, profile: Optional[HumanProfile] = None):
        """
        Initialise le randomizer avec un profil humain.

        Args:
            profile: Profil humain à utiliser (génère un aléatoire si None).
        """
        self.profile = profile or HumanProfile.generate_random()
        self.session_start = time.time()
        self.action_count = 0
        self.last_delays = collections.deque(maxlen=20)
        self.micro_rhythm_phase = random.random() * 2 * np.pi
        self.concentration_phase = random.random() * 2 * np.pi
        self.fatigue_accumulator = 0.0
        self.last_action_time = time.time()
        self.streak_counter = 0
        self.last_pattern_type = None

        logging.info(
            f"Profil '{self.profile.name}': "
            f"V={self.profile.reaction_speed:.2f}, "
            f"C={self.profile.consistency:.2f}"
        )

    def get_fatigue_factor(self) -> float:
        """
        Calcule le facteur de fatigue actuel.

        La fatigue augmente avec le temps de session et diminue
        lors des périodes d'inactivité.

        Returns:
            Facteur de fatigue (1.0 = normal, >1.0 = fatigué).
        """
        session_duration = time.time() - self.session_start
        base_fatigue = min(1.0, (session_duration / 3600) * self.profile.fatigue_rate)

        # Récupération lors de l'inactivité
        time_since_last = time.time() - self.last_action_time
        if time_since_last > 10:
            recovery = min(0.3, time_since_last / 60)
            base_fatigue = max(0, base_fatigue - recovery)

        # Accumulation progressive de fatigue
        self.fatigue_accumulator += 0.001 * self.profile.fatigue_rate
        self.fatigue_accumulator = min(0.5, self.fatigue_accumulator)

        return 1.0 + (base_fatigue + self.fatigue_accumulator) * 0.5

    def get_concentration_wave(self) -> float:
        """
        Simule les fluctuations de concentration.

        Utilise des ondes sinusoïdales pour simuler les variations
        naturelles de l'attention humaine.

        Returns:
            Niveau de concentration (0.3 à 1.0).
        """
        current_time = time.time()

        # Onde principale (cycle de 2 minutes)
        primary_wave = np.sin(current_time / 120 + self.concentration_phase)
        # Onde secondaire (cycle de 45 secondes)
        secondary_wave = np.sin(current_time / 45) * 0.3
        # Micro-onde (cycle de 8 secondes)
        micro_wave = np.sin(current_time / 8) * 0.1

        concentration = self.profile.concentration_level + \
            (primary_wave * 0.2 + secondary_wave + micro_wave) * \
            (1.0 - self.profile.concentration_level)

        return max(0.3, min(1.0, concentration))

    def get_micro_variations(self) -> float:
        """
        Génère des micro-variations réalistes.

        Combine plusieurs fréquences pour créer une variation
        naturelle et non-périodique.

        Returns:
            Micro-variation à ajouter au délai.
        """
        current_time = time.time()

        v1 = np.sin(current_time * 2.3 + self.micro_rhythm_phase) * 0.02
        v2 = np.sin(current_time * 5.7) * 0.01
        v3 = np.sin(current_time * 11.3) * 0.005
        v4 = random.gauss(0, 0.01)

        return (v1 + v2 + v3 + v4) * self.profile.rhythm_variation

    def select_behavior_pattern(self) -> str:
        """
        Sélectionne un pattern comportemental de manière cohérente.

        Prend en compte le pattern précédent, le profil de l'utilisateur
        et le niveau de fatigue actuel.

        Returns:
            Nom du pattern sélectionné.
        """
        weights = []
        for pattern, info in self.BEHAVIOR_PATTERNS.items():
            weight = info['weight']

            # Éviter de répéter le même pattern
            if pattern == self.last_pattern_type:
                weight *= 0.3

            # Ajuster selon le profil
            if pattern == 'steady' and self.profile.consistency > 0.7:
                weight *= 1.5
            elif pattern == 'erratic' and self.profile.consistency < 0.3:
                weight *= 1.5
            elif pattern == 'tired' and self.get_fatigue_factor() > 1.3:
                weight *= 2.0

            weights.append(weight)

        patterns = list(self.BEHAVIOR_PATTERNS.keys())
        selected = random.choices(patterns, weights=weights)[0]

        if selected != self.last_pattern_type:
            self.streak_counter = random.randint(3, 15)
            self.last_pattern_type = selected

        return selected

    def get_humanized_delay(
        self,
        min_delay: float,
        max_delay: float,
        context: Optional[Dict] = None,
        is_boost: bool = False
    ) -> float:
        """
        Génère un délai avec comportement humain réaliste.

        Args:
            min_delay: Délai minimum en secondes.
            max_delay: Délai maximum en secondes.
            context: Contexte additionnel (urgent, repetition, etc.).
            is_boost: Active le mode boost (délais plus courts).

        Returns:
            Délai humanisé en secondes.
        """
        context = context or {}
        self.action_count += 1

        # Sélectionner ou continuer un pattern
        if self.streak_counter <= 0:
            pattern = self.select_behavior_pattern()
        else:
            pattern = self.last_pattern_type
            self.streak_counter -= 1

        base_mean = (min_delay + max_delay) / 2
        pattern_info = self.BEHAVIOR_PATTERNS[pattern]

        # Calculer le délai selon le pattern
        if pattern == 'steady':
            delay = random.gauss(base_mean, base_mean * pattern_info['variation'])
        elif pattern == 'accelerating':
            progress = min(1.0, self.streak_counter / 10)
            delay = max_delay - (max_delay - min_delay) * progress * 0.7
            delay += random.gauss(0, base_mean * pattern_info['variation'])
        elif pattern == 'decelerating':
            progress = min(1.0, self.streak_counter / 10)
            delay = min_delay + (max_delay - min_delay) * progress * 0.7
            delay += random.gauss(0, base_mean * pattern_info['variation'])
        elif pattern == 'erratic':
            delay = random.uniform(min_delay, max_delay)
            if random.random() < 0.2:
                delay *= random.choice([0.5, 1.8])
        elif pattern == 'rhythmic':
            rhythm_base = base_mean + np.sin(self.action_count * 0.5) * \
                (max_delay - min_delay) * 0.3
            delay = random.gauss(rhythm_base, base_mean * pattern_info['variation'])
        else:  # tired
            delay = random.gauss(max_delay * 0.9, base_mean * pattern_info['variation'])

        # Mode boost: délais plus courts
        if is_boost:
            if random.random() < 0.9:
                sub_range = min_delay + 0.2 * (max_delay - min_delay)
                delay = random.uniform(min_delay, sub_range)
            else:
                delay = random.uniform(min_delay, max_delay)

        # Appliquer les modificateurs
        delay *= self.profile.reaction_speed
        delay *= self.get_fatigue_factor()
        delay *= self.get_concentration_wave()
        delay += self.get_micro_variations()

        # Contexte
        if context.get('urgent'):
            delay *= 0.7
        if context.get('repetition', 0) > 10:
            delay *= 1.1

        # Contraindre aux limites avec légère flexibilité
        if delay < min_delay:
            if random.random() < 0.95:
                delay = min_delay + random.uniform(0, 0.05)
            else:
                delay = max(min_delay * 0.9, delay)
        elif delay > max_delay:
            if random.random() < 0.95:
                delay = max_delay - random.uniform(0, 0.05)
            else:
                delay = min(max_delay * 1.1, delay)

        self.last_delays.append(delay)
        self.last_action_time = time.time()

        return delay

    def get_click_position_variation(
        self,
        base_x: int,
        base_y: int,
        window_rect: Tuple[int, int, int, int]
    ) -> Tuple[int, int]:
        """
        Génère une position de clic avec variation humaine.

        Args:
            base_x: Position X de base.
            base_y: Position Y de base.
            window_rect: Rectangle de la fenêtre (left, top, right, bottom).

        Returns:
            Tuple (x, y) de la nouvelle position.
        """
        width = window_rect[2] - window_rect[0]
        height = window_rect[3] - window_rect[1]

        # Zone préférée autour du centre
        preferred_zone_x = width * 0.1
        preferred_zone_y = height * 0.1

        # Déviation basée sur la concentration
        concentration = self.get_concentration_wave()
        max_deviation_x = preferred_zone_x * (2.0 - concentration)
        max_deviation_y = preferred_zone_y * (2.0 - concentration)

        # Génération de la déviation (gaussienne)
        if random.random() < 0.9:
            dx = random.gauss(0, max_deviation_x / 3)
            dy = random.gauss(0, max_deviation_y / 3)
        else:
            dx = random.gauss(0, max_deviation_x)
            dy = random.gauss(0, max_deviation_y)

        # Micro-tremblements basés sur la consistance
        dx += random.gauss(0, 2) * (1.0 - self.profile.consistency)
        dy += random.gauss(0, 2) * (1.0 - self.profile.consistency)

        new_x = int(base_x + dx)
        new_y = int(base_y + dy)

        # Contraindre à l'intérieur de la fenêtre
        margin = 5
        new_x = max(margin, min(width - margin, new_x))
        new_y = max(margin, min(height - margin, new_y))

        return new_x, new_y

    def reset_session(self):
        """Réinitialise les compteurs de session."""
        self.session_start = time.time()
        self.action_count = 0
        self.fatigue_accumulator = 0.0
        self.last_delays.clear()
