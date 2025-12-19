"""
Module de traitement audio.
Gère la détection et l'analyse du volume des applications.
"""

import numpy as np
from pycaw.pycaw import AudioUtilities, IAudioMeterInformation
from comtypes import CLSCTX_ALL


def get_running_applications() -> list:
    """
    Récupère la liste des applications en cours d'exécution qui produisent du son.

    Returns:
        Liste triée des noms d'applications audio actives.
    """
    apps = set()
    excluded_apps = {"System", "Registry", "svchost.exe", "RuntimeBroker.exe"}

    for session in AudioUtilities.GetAllSessions():
        if session.Process and session.Process.name() not in excluded_apps:
            apps.add(session.Process.name())

    return sorted(list(apps))


def get_app_volume(process_name: str) -> float:
    """
    Récupère le niveau de volume actuel d'une application.

    Args:
        process_name: Nom du processus de l'application.

    Returns:
        Niveau de volume (0.0 à 1.0) ou None si l'application n'est pas trouvée.
    """
    sessions = AudioUtilities.GetAllSessions()
    for session in sessions:
        if session.Process and session.Process.name() == process_name:
            audio_meter = session._ctl.QueryInterface(IAudioMeterInformation)
            return audio_meter.GetPeakValue()
    return None


def volume_to_db(volume: float) -> float:
    """
    Convertit un volume linéaire en décibels.

    Args:
        volume: Niveau de volume linéaire (0.0 à 1.0).

    Returns:
        Valeur en décibels (-100 pour silence, 0 pour volume max).
    """
    if volume == 0:
        return -100
    return 20 * np.log10(volume)


def db_to_normalized_scale(db: float) -> float:
    """
    Convertit une valeur en décibels vers une échelle normalisée 0-10.

    Args:
        db: Valeur en décibels.

    Returns:
        Valeur normalisée entre 0 et 10.
    """
    return max(0, min(10, (db + 50) / 6))


def get_normalized_volume(process_name: str) -> float:
    """
    Récupère le volume normalisé (0-10) d'une application.

    Args:
        process_name: Nom du processus de l'application.

    Returns:
        Volume normalisé (0-10) ou None si l'application n'est pas trouvée.
    """
    volume = get_app_volume(process_name)
    if volume is not None:
        db = volume_to_db(volume)
        return db_to_normalized_scale(db)
    return None
