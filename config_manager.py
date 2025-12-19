"""
Module de gestion de la configuration.
Gère le chargement et la sauvegarde des paramètres de l'application.
"""

import os
import json
import logging

# Répertoire du script
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
STATS_FILE = os.path.join(SCRIPT_DIR, "stats.json")

# Configuration par défaut
DEFAULT_CONFIG = {
    "threshold": 8.0,
    "min_delay": 0.1,
    "max_delay": 1.5,
    "is_paused": False,
    "is_completely_disabled": False,
    "click_counter": 0,
    "inactivity_base": 7,
    "selected_app": "",
    "show_delay": True,
    "show_volume": True,
    "show_click_counter": True,
    "show_rate": True,
    "text_color": "Vert clair",
    "is_boost_mode": False,
    "human_profile": None
}


def load_config() -> dict:
    """
    Charge la configuration depuis le fichier JSON.
    Retourne la configuration par défaut si le fichier n'existe pas.
    """
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                # Fusionner avec les valeurs par défaut pour les clés manquantes
                for key, value in DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value
                return config
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Erreur lors du chargement de la config: {e}")
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> bool:
    """
    Sauvegarde la configuration dans le fichier JSON.
    Retourne True en cas de succès, False sinon.
    """
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        logging.info("Configuration enregistrée")
        return True
    except IOError as e:
        logging.error(f"Erreur lors de la sauvegarde de la config: {e}")
        return False


def get_stats_file_path() -> str:
    """Retourne le chemin du fichier de statistiques."""
    return STATS_FILE


def get_config_file_path() -> str:
    """Retourne le chemin du fichier de configuration."""
    return CONFIG_FILE
