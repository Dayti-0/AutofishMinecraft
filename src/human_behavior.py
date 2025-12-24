"""
Module de simulation du comportement humain.
Gère la randomisation réaliste des délais et positions de clic.
Version améliorée avec distribution log-normale, bruit de Perlin et mémoire contextuelle.
"""

import time
import random
import logging
import collections
import numpy as np
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Tuple, List


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


class PerlinNoise:
    """
    Générateur de bruit de Perlin pour variations organiques.
    Produit des variations douces et continues, plus naturelles que le random pur.
    """

    def __init__(self, seed: Optional[int] = None):
        """Initialise le générateur de bruit de Perlin."""
        self.seed = seed or random.randint(0, 1000000)
        np.random.seed(self.seed)
        self.p = np.arange(256, dtype=int)
        np.random.shuffle(self.p)
        self.p = np.concatenate([self.p, self.p])

    def fade(self, t: np.ndarray) -> np.ndarray:
        """Fonction de lissage 6t^5 - 15t^4 + 10t^3."""
        return t * t * t * (t * (t * 6 - 15) + 10)

    def lerp(self, a: float, b: float, t: float) -> float:
        """Interpolation linéaire."""
        return a + t * (b - a)

    def grad(self, hash_val: int, x: float) -> float:
        """Calcule le gradient."""
        return x if (hash_val & 1) == 0 else -x

    def noise(self, x: float) -> float:
        """
        Génère du bruit de Perlin 1D.

        Args:
            x: Position où évaluer le bruit.

        Returns:
            Valeur de bruit entre -1 et 1.
        """
        X = int(np.floor(x)) & 255
        x -= np.floor(x)
        u = self.fade(x)

        a = self.p[X]
        b = self.p[X + 1]

        return self.lerp(self.grad(a, x), self.grad(b, x - 1), u)


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

        # Nouvelles améliorations pour comportement ultra-réaliste
        self.perlin = PerlinNoise()
        self.perlin_offset = random.random() * 1000
        self.delay_memory: List[float] = []  # Mémoire des délais pour autocorrélation
        self.distraction_threshold = random.uniform(0.98, 0.995)  # Seuil de distraction
        self.last_distraction_time = time.time()
        self.micro_habits: Dict[str, float] = {}  # Micro-habitudes personnelles
        self.skill_improvement_rate = random.uniform(0.0001, 0.0005)  # Taux d'apprentissage
        self.action_quality = 0.5  # Qualité d'exécution (s'améliore avec le temps)

        logging.info(
            f"Profil '{self.profile.name}': "
            f"V={self.profile.reaction_speed:.2f}, "
            f"C={self.profile.consistency:.2f}, "
            f"Distraction={self.distraction_threshold:.3f}"
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

    def get_circadian_rhythm_factor(self) -> float:
        """
        Calcule le facteur basé sur le rythme circadien (heure de la journée).

        Les humains ont des performances variables selon l'heure:
        - Matin: réveil progressif
        - Midi-après-midi: pic de performance
        - Soir: fatigue croissante
        - Nuit: performance réduite

        Returns:
            Facteur multiplicateur (0.8 à 1.2).
        """
        now = datetime.now()
        hour = now.hour + now.minute / 60.0

        # Courbe circadienne basée sur l'heure
        if 6 <= hour < 9:  # Réveil
            return 1.0 + (hour - 6) / 3 * 0.1
        elif 9 <= hour < 14:  # Pic matinal
            return 0.95 - random.uniform(0, 0.1)
        elif 14 <= hour < 17:  # Après-midi
            return 1.0 + random.uniform(0, 0.15)
        elif 17 <= hour < 22:  # Soirée
            return 1.05 + (hour - 17) / 5 * 0.15
        else:  # Nuit
            return 1.2 + random.uniform(0, 0.3)

    def get_perlin_noise_variation(self) -> float:
        """
        Génère une variation basée sur le bruit de Perlin.

        Le bruit de Perlin produit des variations organiques et continues,
        simulant les fluctuations naturelles de performance humaine.

        Returns:
            Variation entre -0.15 et 0.15.
        """
        current_time = time.time() - self.session_start
        # Utiliser plusieurs octaves de bruit de Perlin
        noise1 = self.perlin.noise((current_time + self.perlin_offset) * 0.05) * 0.1
        noise2 = self.perlin.noise((current_time + self.perlin_offset) * 0.2) * 0.05
        return noise1 + noise2

    def check_distraction(self) -> bool:
        """
        Détermine si une distraction se produit.

        Simule les moments où l'attention se relâche (notification, pensée, etc.).

        Returns:
            True si une distraction se produit.
        """
        # Éviter les distractions trop fréquentes
        time_since_last = time.time() - self.last_distraction_time
        if time_since_last < 30:  # Au minimum 30s entre distractions
            return False

        # Probabilité de distraction inversement proportionnelle à la concentration
        distraction_prob = (1.0 - self.profile.concentration_level) * 0.05
        if random.random() < distraction_prob:
            self.last_distraction_time = time.time()
            return True

        return False

    def get_delay_from_memory(self, base_delay: float) -> float:
        """
        Utilise la mémoire des délais précédents pour créer une autocorrélation.

        Les humains ont tendance à répéter des patterns similaires inconsciemment.

        Args:
            base_delay: Délai de base calculé.

        Returns:
            Délai ajusté basé sur la mémoire.
        """
        if not self.delay_memory:
            return base_delay

        # Calculer la moyenne pondérée des derniers délais
        recent_delays = list(self.delay_memory)[-5:]
        weights = [0.4, 0.25, 0.2, 0.1, 0.05][:len(recent_delays)]
        weights = weights[::-1]  # Les plus récents ont plus de poids

        memory_influence = sum(d * w for d, w in zip(recent_delays, weights)) / sum(weights)

        # Mélanger le délai de base avec l'influence de la mémoire
        consistency_factor = self.profile.consistency
        return base_delay * (1 - consistency_factor * 0.3) + memory_influence * consistency_factor * 0.3

    def apply_skill_progression(self) -> float:
        """
        Simule l'amélioration progressive des compétences.

        Avec la pratique, les temps de réaction s'améliorent légèrement.

        Returns:
            Facteur de réduction du délai (0.95 à 1.0).
        """
        # La qualité s'améliore lentement jusqu'à un plateau
        self.action_quality = min(1.0, self.action_quality + self.skill_improvement_rate)

        # Réduction maximale de 5% du délai après beaucoup de pratique
        improvement = (self.action_quality - 0.5) * 0.1
        return 1.0 - improvement

    def get_lognormal_delay(self, mean: float, variation: float) -> float:
        """
        Génère un délai suivant une distribution log-normale.

        Les temps de réaction humains suivent mieux une distribution log-normale
        qu'une distribution normale, car ils sont bornés à gauche (>0) et ont
        une queue longue vers la droite (délais occasionnels très longs).

        Args:
            mean: Délai moyen souhaité.
            variation: Variation relative (0.1 = 10%).

        Returns:
            Délai généré selon distribution log-normale.
        """
        # Paramètres de la log-normale pour obtenir la moyenne souhaitée
        sigma = np.sqrt(np.log(1 + variation**2))
        mu = np.log(mean) - sigma**2 / 2

        return np.random.lognormal(mu, sigma)

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
        Génère un délai avec comportement humain ultra-réaliste.

        Version améliorée utilisant:
        - Distribution log-normale (temps de réaction humains réels)
        - Bruit de Perlin (variations organiques)
        - Mémoire contextuelle (autocorrélation)
        - Distractions aléatoires
        - Rythme circadien
        - Progression des compétences

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

        # AMÉLIORATION 1: Utiliser distribution log-normale au lieu de gaussienne
        # Les temps de réaction humains suivent cette distribution
        if pattern == 'steady':
            delay = self.get_lognormal_delay(base_mean, pattern_info['variation'])
        elif pattern == 'accelerating':
            progress = min(1.0, self.streak_counter / 10)
            target_mean = max_delay - (max_delay - min_delay) * progress * 0.7
            delay = self.get_lognormal_delay(target_mean, pattern_info['variation'])
        elif pattern == 'decelerating':
            progress = min(1.0, self.streak_counter / 10)
            target_mean = min_delay + (max_delay - min_delay) * progress * 0.7
            delay = self.get_lognormal_delay(target_mean, pattern_info['variation'])
        elif pattern == 'erratic':
            # Pour erratic, garder une distribution uniforme mais avec pics occasionnels
            delay = random.uniform(min_delay, max_delay)
            if random.random() < 0.15:
                delay *= random.choice([0.6, 1.9])
        elif pattern == 'rhythmic':
            rhythm_base = base_mean + np.sin(self.action_count * 0.5) * \
                (max_delay - min_delay) * 0.3
            delay = self.get_lognormal_delay(max(min_delay, rhythm_base), pattern_info['variation'] * 0.8)
        else:  # tired
            delay = self.get_lognormal_delay(max_delay * 0.9, pattern_info['variation'] * 1.2)

        # Mode boost: délais plus courts mais toujours réalistes
        if is_boost:
            if random.random() < 0.85:
                boost_mean = min_delay + 0.25 * (max_delay - min_delay)
                delay = self.get_lognormal_delay(boost_mean, 0.15)
            else:
                delay = self.get_lognormal_delay(base_mean * 0.7, 0.2)

        # AMÉLIORATION 2: Appliquer la mémoire contextuelle (autocorrélation)
        delay = self.get_delay_from_memory(delay)

        # AMÉLIORATION 3: Bruit de Perlin pour variations organiques
        perlin_variation = self.get_perlin_noise_variation()
        delay *= (1.0 + perlin_variation)

        # AMÉLIORATION 4: Rythme circadien (heure de la journée)
        circadian_factor = self.get_circadian_rhythm_factor()
        delay *= circadian_factor

        # AMÉLIORATION 5: Progression des compétences
        skill_factor = self.apply_skill_progression()
        delay *= skill_factor

        # Appliquer les modificateurs classiques
        delay *= self.profile.reaction_speed
        delay *= self.get_fatigue_factor()
        delay *= self.get_concentration_wave()
        delay += self.get_micro_variations()

        # AMÉLIORATION 6: Distractions aléatoires
        if self.check_distraction():
            distraction_delay = random.uniform(0.5, 2.5)
            delay += distraction_delay
            logging.info(f"💭 Distraction: +{distraction_delay:.2f}s")

        # Contexte
        if context.get('urgent'):
            delay *= random.uniform(0.65, 0.75)
        if context.get('repetition', 0) > 10:
            # Fatigue mentale sur actions répétitives
            repetition_factor = 1.0 + (context.get('repetition', 0) - 10) * 0.01
            delay *= min(1.3, repetition_factor)

        # Contraindre aux limites avec flexibilité humaine
        # Un humain peut occasionnellement dépasser les limites
        if delay < min_delay:
            if random.random() < 0.90:
                # La plupart du temps, respecter le minimum
                delay = min_delay + random.uniform(0, 0.08)
            else:
                # Rarement, être légèrement plus rapide
                delay = max(min_delay * 0.85, delay)
        elif delay > max_delay:
            if random.random() < 0.92:
                # Souvent, respecter le maximum
                delay = max_delay - random.uniform(0, 0.1)
            else:
                # Parfois, être un peu plus lent (distraction légère)
                delay = min(max_delay * 1.15, delay)

        # AMÉLIORATION 7: Enregistrer dans la mémoire pour autocorrélation future
        self.delay_memory.append(delay)
        if len(self.delay_memory) > 50:
            self.delay_memory.pop(0)

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
        self.delay_memory.clear()
        self.action_quality = 0.5
        self.last_distraction_time = time.time()

        # Régénérer certains paramètres aléatoires pour varier les sessions
        self.perlin = PerlinNoise()
        self.perlin_offset = random.random() * 1000
        self.distraction_threshold = random.uniform(0.98, 0.995)

        logging.info(f"🔄 Session réinitialisée - Nouveau profil de variation généré")
