"""
Module de gestion des statistiques.
Gère le suivi et la persistance des statistiques de pêche.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from .config_manager import get_stats_file_path


class StatsManager:
    """
    Gestionnaire de statistiques avancées.

    Suit les clics, les poissons pêchés, les temps de réaction
    et d'autres métriques de performance.
    """

    def __init__(self, stats_file: Optional[str] = None):
        """
        Initialise le gestionnaire de statistiques.

        Args:
            stats_file: Chemin du fichier de statistiques (optionnel).
        """
        self.stats_file = stats_file or get_stats_file_path()
        self.stats = self._load_stats()

    def _default_stats(self) -> Dict[str, Any]:
        """
        Retourne les statistiques par défaut.

        Returns:
            Dictionnaire avec les valeurs par défaut.
        """
        return {
            'total_clicks': 0,
            'total_runtime': 0,
            'total_fish': 0,
            'best_session': 0,
            'sessions': [],
            'daily_stats': {},
            'hourly_distribution': [0] * 24,
            'success_rate': 0.0,
            'average_reaction_time': 0.0,
            'patterns_used': {}
        }

    def _load_stats(self) -> Dict[str, Any]:
        """
        Charge les statistiques depuis le fichier.

        Returns:
            Dictionnaire des statistiques.
        """
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
                    # S'assurer que toutes les clés existent
                    default = self._default_stats()
                    for key, value in default.items():
                        if key not in stats:
                            stats[key] = value
                    return stats
            except (json.JSONDecodeError, IOError) as e:
                logging.error(f"Erreur lors du chargement des stats: {e}")
                return self._default_stats()
        return self._default_stats()

    def save_stats(self) -> bool:
        """
        Sauvegarde les statistiques dans le fichier.

        Returns:
            True si la sauvegarde a réussi, False sinon.
        """
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            logging.error(f"Erreur lors de la sauvegarde des stats: {e}")
            return False

    def record_click(
        self,
        reaction_time: float,
        pattern: str,
        success: bool = True
    ) -> None:
        """
        Enregistre un clic et met à jour les statistiques.

        Args:
            reaction_time: Temps de réaction en secondes.
            pattern: Pattern comportemental utilisé.
            success: True si le clic a été réussi.
        """
        self.stats['total_clicks'] += 1

        if success:
            self.stats['total_fish'] += 1

        # Mise à jour de la moyenne de temps de réaction
        current_avg = self.stats.get('average_reaction_time', 0)
        n = self.stats['total_clicks']
        self.stats['average_reaction_time'] = \
            (current_avg * (n - 1) + reaction_time) / n

        # Enregistrer le pattern utilisé
        if pattern not in self.stats['patterns_used']:
            self.stats['patterns_used'][pattern] = 0
        self.stats['patterns_used'][pattern] += 1

        # Distribution horaire
        hour = datetime.now().hour
        self.stats['hourly_distribution'][hour] += 1

        # Stats quotidiennes
        today = datetime.now().strftime('%Y-%m-%d')
        if today not in self.stats['daily_stats']:
            self.stats['daily_stats'][today] = {
                'clicks': 0,
                'fish': 0,
                'runtime': 0
            }
        self.stats['daily_stats'][today]['clicks'] += 1
        if success:
            self.stats['daily_stats'][today]['fish'] += 1

        # Mise à jour du taux de succès
        if self.stats['total_clicks'] > 0:
            self.stats['success_rate'] = \
                (self.stats['total_fish'] / self.stats['total_clicks']) * 100

        self.save_stats()

    def get_session_stats(self) -> Dict[str, Any]:
        """
        Obtient les statistiques de la session actuelle.

        Returns:
            Dictionnaire avec les stats de session.
        """
        success_rate = 0.0
        if self.stats['total_clicks'] > 0:
            success_rate = \
                (self.stats['total_fish'] / self.stats['total_clicks']) * 100

        return {
            'clicks': self.stats['total_clicks'],
            'fish': self.stats['total_fish'],
            'success_rate': success_rate,
            'avg_reaction': self.stats['average_reaction_time'],
            'best_hour': self.get_best_hour(),
            'most_used_pattern': self.get_most_used_pattern()
        }

    def get_best_hour(self) -> str:
        """
        Trouve l'heure la plus productive.

        Returns:
            Chaîne décrivant l'heure la plus productive.
        """
        if not any(self.stats['hourly_distribution']):
            return "N/A"

        best_hour = self.stats['hourly_distribution'].index(
            max(self.stats['hourly_distribution'])
        )
        return f"{best_hour}h-{best_hour + 1}h"

    def get_most_used_pattern(self) -> str:
        """
        Trouve le pattern le plus utilisé.

        Returns:
            Nom du pattern le plus utilisé ou "N/A".
        """
        if not self.stats['patterns_used']:
            return "N/A"

        return max(
            self.stats['patterns_used'],
            key=self.stats['patterns_used'].get
        )

    def get_daily_summary(self, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtient le résumé d'une journée.

        Args:
            date: Date au format YYYY-MM-DD (aujourd'hui par défaut).

        Returns:
            Statistiques de la journée.
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        if date in self.stats['daily_stats']:
            return self.stats['daily_stats'][date]

        return {'clicks': 0, 'fish': 0, 'runtime': 0}

    def reset_stats(self) -> None:
        """Réinitialise toutes les statistiques."""
        self.stats = self._default_stats()
        self.save_stats()
        logging.info("Statistiques réinitialisées")

    def add_runtime(self, seconds: float) -> None:
        """
        Ajoute du temps d'exécution aux statistiques.

        Args:
            seconds: Nombre de secondes à ajouter.
        """
        self.stats['total_runtime'] += seconds

        today = datetime.now().strftime('%Y-%m-%d')
        if today in self.stats['daily_stats']:
            self.stats['daily_stats'][today]['runtime'] += seconds
