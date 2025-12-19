import os
import time
import threading
import collections
import json
import logging
import numpy as np
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox
import psutil
import win32gui
import win32con
import win32api
import win32process
from pycaw.pycaw import AudioUtilities, IAudioMeterInformation
from comtypes import CLSCTX_ALL
from ctypes import POINTER, cast
from pynput import keyboard
from pynput.keyboard import Key
import random
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Optional, List, Tuple, Dict
import statistics

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

script_dir = os.path.dirname(os.path.realpath(__file__))
config_file = os.path.join(script_dir, "config.json")
stats_file = os.path.join(script_dir, "stats.json")

# ==========================================================================================
# CLASSES DE RANDOMISATION HUMAINE AVANCÉE
# ==========================================================================================

@dataclass
class HumanProfile:
    """Profil comportemental simulant un humain spécifique"""
    name: str = "Default"  # Nom du profil
    reaction_speed: float = 1.0  # Vitesse de base (0.5 = lent, 1.0 = normal, 1.5 = rapide)
    consistency: float = 0.5     # Cohérence (0.0 = erratique, 1.0 = très constant)
    fatigue_rate: float = 0.5   # Taux de fatigue (0.0 = jamais fatigué, 1.0 = fatigue rapide)
    concentration_level: float = 0.6  # Niveau de concentration (0.0 = distrait, 1.0 = très concentré)
    rhythm_variation: float = 0.5  # Variation du rythme (0.0 = robotique, 1.0 = très varié)
    
    @classmethod
    def generate_random(cls, name="Random"):
        """Génère un profil humain aléatoire mais cohérent"""
        reaction_speed = random.gauss(1.0, 0.2)
        consistency = random.betavariate(2, 2)
        
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


class HumanLikeRandomizer:
    """Système avancé de randomisation simulant le comportement humain"""
    
    def __init__(self, profile: Optional[HumanProfile] = None):
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
        
        self.behavior_patterns = {
            'steady': {'weight': 0.4, 'variation': 0.1},
            'accelerating': {'weight': 0.15, 'variation': 0.2},
            'decelerating': {'weight': 0.15, 'variation': 0.2},
            'erratic': {'weight': 0.1, 'variation': 0.4},
            'rhythmic': {'weight': 0.15, 'variation': 0.15},
            'tired': {'weight': 0.05, 'variation': 0.3}
        }
        
        logging.info(f"Profil '{self.profile.name}': V={self.profile.reaction_speed:.2f}, C={self.profile.consistency:.2f}")
    
    def get_fatigue_factor(self) -> float:
        """Calcule le facteur de fatigue actuel"""
        session_duration = time.time() - self.session_start
        base_fatigue = min(1.0, (session_duration / 3600) * self.profile.fatigue_rate)
        
        time_since_last = time.time() - self.last_action_time
        if time_since_last > 10:
            recovery = min(0.3, time_since_last / 60)
            base_fatigue = max(0, base_fatigue - recovery)
        
        self.fatigue_accumulator += 0.001 * self.profile.fatigue_rate
        self.fatigue_accumulator = min(0.5, self.fatigue_accumulator)
        
        return 1.0 + (base_fatigue + self.fatigue_accumulator) * 0.5
    
    def get_concentration_wave(self) -> float:
        """Simule les fluctuations de concentration"""
        current_time = time.time()
        
        primary_wave = np.sin(current_time / 120 + self.concentration_phase)
        secondary_wave = np.sin(current_time / 45) * 0.3
        micro_wave = np.sin(current_time / 8) * 0.1
        
        concentration = self.profile.concentration_level + \
                       (primary_wave * 0.2 + secondary_wave + micro_wave) * \
                       (1.0 - self.profile.concentration_level)
        
        return max(0.3, min(1.0, concentration))
    
    def get_micro_variations(self) -> float:
        """Génère des micro-variations réalistes"""
        current_time = time.time()
        
        v1 = np.sin(current_time * 2.3 + self.micro_rhythm_phase) * 0.02
        v2 = np.sin(current_time * 5.7) * 0.01
        v3 = np.sin(current_time * 11.3) * 0.005
        v4 = random.gauss(0, 0.01)
        
        return (v1 + v2 + v3 + v4) * self.profile.rhythm_variation
    
    def select_behavior_pattern(self) -> str:
        """Sélectionne un pattern comportemental de manière cohérente"""
        weights = []
        for pattern, info in self.behavior_patterns.items():
            weight = info['weight']
            
            if pattern == self.last_pattern_type:
                weight *= 0.3
                
            if pattern == 'steady' and self.profile.consistency > 0.7:
                weight *= 1.5
            elif pattern == 'erratic' and self.profile.consistency < 0.3:
                weight *= 1.5
            elif pattern == 'tired' and self.get_fatigue_factor() > 1.3:
                weight *= 2.0
                
            weights.append(weight)
        
        patterns = list(self.behavior_patterns.keys())
        selected = random.choices(patterns, weights=weights)[0]
        
        if selected != self.last_pattern_type:
            self.streak_counter = random.randint(3, 15)
            self.last_pattern_type = selected
        
        return selected
    
    def get_humanized_delay(self, min_delay: float, max_delay: float, 
                           context: Optional[Dict] = None, is_boost: bool = False) -> float:
        """Génère un délai avec comportement humain réaliste"""
        context = context or {}
        self.action_count += 1
        
        if self.streak_counter <= 0:
            pattern = self.select_behavior_pattern()
        else:
            pattern = self.last_pattern_type
            self.streak_counter -= 1
        
        base_mean = (min_delay + max_delay) / 2
        pattern_info = self.behavior_patterns[pattern]
        
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
            rhythm_base = base_mean + np.sin(self.action_count * 0.5) * (max_delay - min_delay) * 0.3
            delay = random.gauss(rhythm_base, base_mean * pattern_info['variation'])
        else:  # tired
            delay = random.gauss(max_delay * 0.9, base_mean * pattern_info['variation'])
        
        # Mode boost
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
        
        # Contraindre aux limites
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
    
    def get_click_position_variation(self, base_x: int, base_y: int, 
                                    window_rect: Tuple[int, int, int, int]) -> Tuple[int, int]:
        """Génère une position de clic avec variation humaine"""
        width = window_rect[2] - window_rect[0]
        height = window_rect[3] - window_rect[1]
        
        preferred_zone_x = width * 0.1
        preferred_zone_y = height * 0.1
        
        concentration = self.get_concentration_wave()
        max_deviation_x = preferred_zone_x * (2.0 - concentration)
        max_deviation_y = preferred_zone_y * (2.0 - concentration)
        
        if random.random() < 0.9:
            dx = random.gauss(0, max_deviation_x / 3)
            dy = random.gauss(0, max_deviation_y / 3)
        else:
            dx = random.gauss(0, max_deviation_x)
            dy = random.gauss(0, max_deviation_y)
        
        dx += random.gauss(0, 2) * (1.0 - self.profile.consistency)
        dy += random.gauss(0, 2) * (1.0 - self.profile.consistency)
        
        new_x = int(base_x + dx)
        new_y = int(base_y + dy)
        
        margin = 5
        new_x = max(margin, min(width - margin, new_x))
        new_y = max(margin, min(height - margin, new_y))
        
        return new_x, new_y


# ==========================================================================================
# GESTIONNAIRE DE STATISTIQUES AVANCÉES
# ==========================================================================================

class StatsManager:
    """Gestionnaire de statistiques avancées"""
    
    def __init__(self):
        self.stats_file = stats_file
        self.load_stats()
        
    def load_stats(self):
        """Charge les statistiques"""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r') as f:
                    self.stats = json.load(f)
            except:
                self.stats = self.default_stats()
        else:
            self.stats = self.default_stats()
    
    def default_stats(self):
        """Statistiques par défaut"""
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
    
    def save_stats(self):
        """Sauvegarde les statistiques"""
        try:
            with open(self.stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except:
            pass
    
    def record_click(self, reaction_time, pattern, success=True):
        """Enregistre un clic"""
        self.stats['total_clicks'] += 1
        if success:
            self.stats['total_fish'] += 1
        
        # Mise à jour de la moyenne de réaction
        current_avg = self.stats.get('average_reaction_time', 0)
        n = self.stats['total_clicks']
        self.stats['average_reaction_time'] = (current_avg * (n-1) + reaction_time) / n
        
        # Enregistrer le pattern
        if pattern not in self.stats['patterns_used']:
            self.stats['patterns_used'][pattern] = 0
        self.stats['patterns_used'][pattern] += 1
        
        # Distribution horaire
        hour = datetime.now().hour
        self.stats['hourly_distribution'][hour] += 1
        
        # Stats quotidiennes
        today = datetime.now().strftime('%Y-%m-%d')
        if today not in self.stats['daily_stats']:
            self.stats['daily_stats'][today] = {'clicks': 0, 'fish': 0, 'runtime': 0}
        self.stats['daily_stats'][today]['clicks'] += 1
        if success:
            self.stats['daily_stats'][today]['fish'] += 1
        
        self.save_stats()
    
    def get_session_stats(self):
        """Obtient les stats de la session actuelle"""
        return {
            'clicks': self.stats['total_clicks'],
            'fish': self.stats['total_fish'],
            'success_rate': (self.stats['total_fish'] / self.stats['total_clicks'] * 100) if self.stats['total_clicks'] > 0 else 0,
            'avg_reaction': self.stats['average_reaction_time'],
            'best_hour': self.get_best_hour(),
            'most_used_pattern': self.get_most_used_pattern()
        }
    
    def get_best_hour(self):
        """Trouve l'heure la plus productive"""
        if not any(self.stats['hourly_distribution']):
            return "N/A"
        best_hour = self.stats['hourly_distribution'].index(max(self.stats['hourly_distribution']))
        return f"{best_hour}h-{best_hour+1}h"
    
    def get_most_used_pattern(self):
        """Trouve le pattern le plus utilisé"""
        if not self.stats['patterns_used']:
            return "N/A"
        return max(self.stats['patterns_used'], key=self.stats['patterns_used'].get)


# ==========================================================================================
# SYSTÈME D'AUTO-CALIBRATION AMÉLIORÉ
# ==========================================================================================

class AutoCalibrator:
    """Système d'auto-calibration du seuil"""
    
    def __init__(self):
        self.calibration_data = []
        self.peak_values = []  # Valeurs lors des pics détectés
        self.is_calibrating = False
        self.calibration_duration = 30  # 30 secondes pour avoir plusieurs poissons
        self.callback = None
        self.progress_callback = None
        
    def start_calibration(self, callback, progress_callback=None):
        """Démarre la calibration"""
        self.calibration_data = []
        self.peak_values = []
        self.is_calibrating = True
        self.callback = callback
        self.progress_callback = progress_callback
        self.start_time = time.time()
        logging.info("Calibration démarrée - Pêchez normalement pendant 30 secondes")
        
    def add_sample(self, volume_level, is_peak=False):
        """Ajoute un échantillon de volume"""
        if self.is_calibrating:
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
    
    def finish_calibration(self):
        """Termine la calibration et calcule le seuil optimal"""
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
            
            logging.info(f"Calibration avec {len(self.peak_values)} pics détectés")
            logging.info(f"Pics: min={min_peak:.1f}, moy={avg_peak:.1f}")
        else:
            # Fallback: utiliser la méthode statistique
            mean = np.mean(data)
            std = np.std(data)
            
            # Les pics sont au-dessus de mean + 1.5*std
            threshold = mean + 1.5 * std
            
            logging.info(f"Calibration statistique (pas assez de pics)")
            logging.info(f"Moyenne={mean:.1f}, Écart-type={std:.1f}")
        
        # Arrondir à 0.1 près
        threshold = round(threshold, 1)
        
        # Limiter entre 4 et 9
        threshold = max(4.0, min(9.0, threshold))
        
        self.is_calibrating = False
        logging.info(f"Calibration terminée - Seuil optimal: {threshold}")
        
        if self.callback:
            self.callback(threshold)


# ==========================================================================================
# FONCTIONS UTILITAIRES
# ==========================================================================================

def load_config():
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            return json.load(f)
    return {}

def save_config(config):
    with open(config_file, "w") as f:
        json.dump(config, f, indent=4)
    logging.info(f"Configuration enregistrée")

def get_running_applications():
    apps = set()
    for session in AudioUtilities.GetAllSessions():
        if session.Process and session.Process.name() not in ["System", "Registry", "svchost.exe", "RuntimeBroker.exe"]:
            apps.add(session.Process.name())
    return sorted(list(apps))

def get_app_volume(process_name):
    sessions = AudioUtilities.GetAllSessions()
    for session in sessions:
        if session.Process and session.Process.name() == process_name:
            audio_meter = session._ctl.QueryInterface(IAudioMeterInformation)
            return audio_meter.GetPeakValue()
    return None

def volume_to_db(volume):
    if volume == 0:
        return -100
    return 20 * np.log10(volume)

def db_to_normalized_scale(db):
    return max(0, min(10, (db + 50) / 6))

def get_process_id_by_name(process_name):
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
            return proc.info['pid']
    return None

def is_application_in_foreground(pid):
    foreground_window = win32gui.GetForegroundWindow()
    _, foreground_pid = win32process.GetWindowThreadProcessId(foreground_window)
    return foreground_pid == pid

def get_hwnds_for_pid(pid):
    def callback(hwnd, hwnds):
        if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
            _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
            if found_pid == pid:
                hwnds.append(hwnd)
        return True
    hwnds = []
    win32gui.EnumWindows(callback, hwnds)
    return hwnds

def bring_window_to_front(pid):
    """Met la fenêtre de l'application au premier plan"""
    try:
        hwnds = get_hwnds_for_pid(pid)
        if hwnds:
            hwnd = hwnds[0]
            # Restaurer la fenêtre si elle est minimisée
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            # Mettre au premier plan
            win32gui.SetForegroundWindow(hwnd)
            return True
    except Exception as e:
        logging.error(f"Erreur lors de la mise au premier plan: {e}")
    return False


# ==========================================================================================
# BARRE DE VOLUME AVEC GRAPHIQUE
# ==========================================================================================

class VolumeGraphBar(tk.Canvas):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(width=250, height=120, bg='white', highlightthickness=1)
        self.history = collections.deque([0] * 50, maxlen=50)
        self.threshold_line = None
        self.threshold_value = 8.0
        self.draw()
    
    def add_value(self, value):
        """Ajoute une valeur à l'historique"""
        self.history.append(value)
        self.draw()
    
    def set_threshold(self, threshold):
        """Définit le seuil"""
        self.threshold_value = threshold
        self.draw()
    
    def draw(self):
        """Dessine le graphique"""
        self.delete("all")
        
        # Grille de fond
        for i in range(5):
            y = i * 24
            self.create_line(0, y, 250, y, fill='#f0f0f0', width=1)
        
        # Ligne de seuil
        threshold_y = 120 - (self.threshold_value * 12)
        self.create_line(0, threshold_y, 250, threshold_y, fill='#ff6666', width=2, dash=(5, 2))
        
        # Courbe de volume
        if len(self.history) > 1:
            points = []
            for i, value in enumerate(self.history):
                x = i * 5
                y = 120 - (value * 12)
                points.extend([x, y])
            
            if len(points) > 4:
                # Courbe principale
                self.create_line(points, fill='#4CAF50', width=2, smooth=True)
                
                # Zone de remplissage sous la courbe
                fill_points = [0, 120] + points + [250, 120]
                self.create_polygon(fill_points, fill='#4CAF50', stipple='gray50', outline='')


# ==========================================================================================
# CLASSE PRINCIPALE - VERSION SIMPLIFIÉE
# ==========================================================================================

class VolumeAnalyzerSimplified(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Analyseur de Volume - Version Simplifiée")
        self.geometry("480x600")
        self.configure(bg='#f0f0f0')
        self.resizable(False, False)

        # Charger la configuration
        config = load_config()

        # Gestionnaires
        self.stats_manager = StatsManager()
        self.auto_calibrator = AutoCalibrator()

        # Variables principales
        self.app_var = tk.StringVar()
        self.threshold = config.get("threshold", 8.0)
        self.current_level_var = tk.StringVar(value="Niveau: 0.0")
        self.delay_display_var = tk.StringVar(value="0.10 - 0.50s")

        self.is_running = True
        self.is_paused = config.get("is_paused", False)
        self.is_completely_disabled = config.get("is_completely_disabled", False)

        self.volume_history = collections.deque(maxlen=10)
        self.baseline_volume = 0
        self.trigger_count = 0
        self.last_trigger_time = 0
        self.cooldown_period = 2
        self.last_click_time = time.time()
        self.last_activity_time = time.time()

        self.min_delay = config.get("min_delay", 0.1)
        self.max_delay = config.get("max_delay", 1.5)

        self.indicator_window = None
        self.delay_label_window = None
        self.current_color = "red"
        self.delay_label_var = tk.StringVar(value="Ready")

        self.click_timestamps = collections.deque()
        self.click_counter = config.get("click_counter", 0)
        self.start_time = time.time()

        self.is_app_in_foreground = False
        self.app_pid = None

        self.inactivity_base = config.get("inactivity_base", 7)
        self.inactivity_delay = random.uniform(self.inactivity_base - 2, self.inactivity_base + 2)
        self.inactivity_trigger_count = 0

        self.selected_app = config.get("selected_app", "")

        self.last_rate = 0
        self.alpha = 0.3

        # Variables d'affichage
        self.show_delay = tk.BooleanVar(value=config.get("show_delay", True))
        self.show_volume = tk.BooleanVar(value=config.get("show_volume", True))
        self.show_click_counter = tk.BooleanVar(value=config.get("show_click_counter", True))
        self.show_rate = tk.BooleanVar(value=config.get("show_rate", True))

        # Couleurs
        self.colors_map = {
            "Rouge": "red", "Vert": "green", "Bleu": "blue", "Orange": "orange",
            "Violet": "purple", "Cyan": "cyan", "Rose": "magenta", "Jaune": "yellow",
            "Vert clair": "lime", "Marron": "brown", "Gris": "grey", "Blanc": "white"
        }
        self.text_color_var = tk.StringVar(value=config.get("text_color", "Vert clair"))
        self.is_boost_mode = config.get("is_boost_mode", False)

        # Pause temporaire
        self.temp_pause_remaining = 0
        self.temp_pause_start = 0

        # Volume pour la détection
        self.current_volume_level = 0
        
        # Variables de calibration
        self.calibration_window = None
        self.calibration_progress_var = None
        self.calibration_time_var = None

        # Profil humain et randomizer
        human_profile_data = config.get("human_profile")
        if human_profile_data:
            self.human_profile = HumanProfile(**human_profile_data)
        else:
            self.human_profile = HumanProfile.generate_random("Default")
        
        self.randomizer = HumanLikeRandomizer(self.human_profile)
        self.current_pattern = "steady"  # Pour les stats

        # Construction de l'interface
        self.create_widgets()

        # Créer l'indicateur de pixel (carré en haut à gauche) TOUJOURS AU PREMIER PLAN
        self.create_pixel_indicator()

        # Créer l'affichage du délai SANS FOND
        self.create_delay_label()

        # Listener clavier (F8, F9, F10, F11)
        self.setup_keyboard_listener()

        # Threads de monitoring
        self.volume_thread = threading.Thread(target=self.monitor_volume, daemon=True)
        self.volume_thread.start()

        self.inactivity_thread = threading.Thread(target=self.check_inactivity, daemon=True)
        self.inactivity_thread.start()

        self.temp_pause_thread = threading.Thread(target=self.handle_temp_pause, daemon=True)
        self.temp_pause_thread.start()

        # Sauvegarde automatique
        self.auto_save_thread = threading.Thread(target=self.auto_save, daemon=True)
        self.auto_save_thread.start()

        # Mise à jour de l'affichage
        self.update_pixel_color()

        # Gestion de la fermeture
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        logging.info("Application Simplifiée démarrée")

    def create_widgets(self):
        """Crée tous les widgets de l'interface"""
        
        # Notebook pour organiser
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # === Onglet Principal ===
        main_tab = tk.Frame(notebook, bg='#f0f0f0')
        notebook.add(main_tab, text="Principal")

        # Application
        app_frame = tk.LabelFrame(main_tab, text="Application", font=('Arial', 9, 'bold'), 
                                 bg='#f0f0f0', padx=5, pady=3)
        app_frame.pack(fill=tk.X, padx=5, pady=3)

        app_controls = tk.Frame(app_frame, bg='#f0f0f0')
        app_controls.pack()

        self.app_combo = ttk.Combobox(app_controls, textvariable=self.app_var, width=20, state='readonly')
        self.app_combo.pack(side=tk.LEFT, padx=2)

        tk.Button(app_controls, text="↻", command=self.refresh_applications,
                 bg='#4CAF50', fg='white', width=3, height=1).pack(side=tk.LEFT, padx=1)
        tk.Button(app_controls, text="OK", command=self.select_application,
                 bg='#2196F3', fg='white', width=3, height=1).pack(side=tk.LEFT, padx=1)

        # Graphique de volume amélioré
        volume_frame = tk.LabelFrame(main_tab, text="Analyse Audio", font=('Arial', 9, 'bold'), 
                                    bg='#f0f0f0', padx=5, pady=3)
        volume_frame.pack(fill=tk.X, padx=5, pady=3)

        self.volume_graph = VolumeGraphBar(volume_frame)
        self.volume_graph.pack(pady=3)

        tk.Label(volume_frame, textvariable=self.current_level_var,
                font=('Arial', 8), bg='#f0f0f0').pack()

        # Seuil
        threshold_frame = tk.Frame(main_tab, bg='#f0f0f0')
        threshold_frame.pack(fill=tk.X, padx=5, pady=3)

        tk.Label(threshold_frame, text="Seuil:", font=('Arial', 9), bg='#f0f0f0').pack(side=tk.LEFT)
        self.threshold_scale = tk.Scale(threshold_frame, from_=0, to=10, resolution=0.1,
                                       orient=tk.HORIZONTAL, length=180, command=self.update_threshold,
                                       bg='#f0f0f0', highlightbackground='#f0f0f0', showvalue=False)
        self.threshold_scale.set(self.threshold)
        self.threshold_scale.pack(side=tk.LEFT, padx=3)
        self.threshold_label = tk.Label(threshold_frame, text=f"{self.threshold:.1f}", 
                                       font=('Arial', 9, 'bold'), bg='#f0f0f0')
        self.threshold_label.pack(side=tk.LEFT)

        # Délais
        delay_frame = tk.Frame(main_tab, bg='#f0f0f0')
        delay_frame.pack(fill=tk.X, padx=5, pady=3)

        tk.Label(delay_frame, text="Min:", font=('Arial', 9), bg='#f0f0f0').pack(side=tk.LEFT)
        self.min_delay_scale = tk.Scale(delay_frame, from_=0, to=5, resolution=0.01,
                                       orient=tk.HORIZONTAL, length=80, command=self.update_delays,
                                       bg='#f0f0f0', highlightbackground='#f0f0f0', showvalue=False)
        self.min_delay_scale.set(self.min_delay)
        self.min_delay_scale.pack(side=tk.LEFT, padx=2)

        tk.Label(delay_frame, text="Max:", font=('Arial', 9), bg='#f0f0f0').pack(side=tk.LEFT)
        self.max_delay_scale = tk.Scale(delay_frame, from_=0, to=10, resolution=0.01,
                                       orient=tk.HORIZONTAL, length=80, command=self.update_delays,
                                       bg='#f0f0f0', highlightbackground='#f0f0f0', showvalue=False)
        self.max_delay_scale.set(self.max_delay)
        self.max_delay_scale.pack(side=tk.LEFT, padx=2)

        tk.Label(delay_frame, textvariable=self.delay_display_var,
                font=('Arial', 8), bg='#f0f0f0').pack(side=tk.LEFT, padx=5)

        # Statistiques améliorées
        stats_frame = tk.LabelFrame(main_tab, text="Statistiques", font=('Arial', 9, 'bold'), 
                                   bg='#f0f0f0', padx=5, pady=3)
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=3)

        self.stats_text = tk.Text(stats_frame, height=8, width=50, bg='#ffffff',
                                 font=('Consolas', 8), relief=tk.FLAT, borderwidth=1)
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        self.update_stats_display()

        # === Onglet Profils (SIMPLIFIÉ) ===
        profiles_tab = tk.Frame(notebook, bg='#f0f0f0')
        notebook.add(profiles_tab, text="Profils")

        # Bouton de calibration en haut
        self.calibration_button = tk.Button(profiles_tab, text="🎯 AUTO-CALIBRATION",
                                           command=self.start_auto_calibration,
                                           bg='#FF9800', fg='white', font=('Arial', 11, 'bold'),
                                           width=25, height=2)
        self.calibration_button.pack(pady=15)

        # Profil actuel
        current_frame = tk.LabelFrame(profiles_tab, text="Profil Actuel", 
                                     font=('Arial', 10, 'bold'), bg='#f0f0f0')
        current_frame.pack(fill=tk.X, padx=10, pady=10)

        self.profile_label = tk.Label(current_frame, text="", font=('Arial', 9), bg='#f0f0f0')
        self.profile_label.pack(pady=10)
        self.update_profile_display()

        # Boutons de presets
        profile_preset_frame = tk.LabelFrame(profiles_tab, text="Profils Prédéfinis", 
                                            font=('Arial', 10, 'bold'), bg='#f0f0f0')
        profile_preset_frame.pack(fill=tk.X, padx=10, pady=10)

        profile_preset_buttons = tk.Frame(profile_preset_frame, bg='#f0f0f0')
        profile_preset_buttons.pack(pady=10)

        tk.Button(profile_preset_buttons, text="🎲 Aléatoire", command=self.generate_new_profile,
                 bg='#00BCD4', fg='white', width=12, height=2, font=('Arial', 9)).pack(side=tk.LEFT, padx=5)
        tk.Button(profile_preset_buttons, text="⚡ Rapide", command=lambda: self.set_preset_profile('fast'),
                 bg='#8BC34A', fg='white', width=12, height=2, font=('Arial', 9)).pack(side=tk.LEFT, padx=5)
        tk.Button(profile_preset_buttons, text="⚖️ Normal", command=lambda: self.set_preset_profile('normal'),
                 bg='#3F51B5', fg='white', width=12, height=2, font=('Arial', 9)).pack(side=tk.LEFT, padx=5)
        tk.Button(profile_preset_buttons, text="🐌 Lent", command=lambda: self.set_preset_profile('slow'),
                 bg='#795548', fg='white', width=12, height=2, font=('Arial', 9)).pack(side=tk.LEFT, padx=5)

        # === Onglet Options ===
        options_tab = tk.Frame(notebook, bg='#f0f0f0')
        notebook.add(options_tab, text="Options")

        # Affichage
        display_frame = tk.LabelFrame(options_tab, text="Affichage", font=('Arial', 9, 'bold'), 
                                     bg='#f0f0f0', padx=5, pady=5)
        display_frame.pack(fill=tk.X, padx=5, pady=5)

        display_grid = tk.Frame(display_frame, bg='#f0f0f0')
        display_grid.pack()

        tk.Checkbutton(display_grid, text="Délai", variable=self.show_delay, bg='#f0f0f0',
                      command=self.save_current_config).grid(row=0, column=0, sticky='w')
        tk.Checkbutton(display_grid, text="Volume", variable=self.show_volume, bg='#f0f0f0',
                      command=self.save_current_config).grid(row=0, column=1, sticky='w')
        tk.Checkbutton(display_grid, text="Compteur", variable=self.show_click_counter, bg='#f0f0f0',
                      command=self.save_current_config).grid(row=1, column=0, sticky='w')
        tk.Checkbutton(display_grid, text="Taux", variable=self.show_rate, bg='#f0f0f0',
                      command=self.save_current_config).grid(row=1, column=1, sticky='w')

        # Couleur texte
        color_frame = tk.Frame(options_tab, bg='#f0f0f0')
        color_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(color_frame, text="Couleur texte:", font=('Arial', 9), bg='#f0f0f0').pack(side=tk.LEFT)
        color_combo = ttk.Combobox(color_frame, textvariable=self.text_color_var,
                                  values=list(self.colors_map.keys()), width=12, state='readonly')
        color_combo.pack(side=tk.LEFT, padx=5)
        color_combo.bind('<<ComboboxSelected>>', lambda e: self.save_current_config())

        # Boutons d'action (sans Test)
        action_frame = tk.Frame(options_tab, bg='#f0f0f0')
        action_frame.pack(fill=tk.X, padx=5, pady=10)

        self.boost_button = tk.Button(action_frame, text="🚀 Boost: OFF", 
                                     command=self.toggle_boost, bg='#9C27B0', fg='white', 
                                     width=15, height=2, font=('Arial', 9))
        self.boost_button.pack(side=tk.LEFT, padx=10)

        tk.Button(action_frame, text="🔄 Reset Compteur", command=self.reset_counter,
                 bg='#607D8B', fg='white', width=15, height=2, font=('Arial', 9)).pack(side=tk.LEFT, padx=10)

        # Info touches
        info_frame = tk.Frame(self, bg='#e0e0e0', height=30)
        info_frame.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Label(info_frame, text="F8: Pause | F9: Off | F10: Pause 15s | F11: Test rapide",
                font=('Arial', 8), bg='#e0e0e0').pack(pady=2)

        # Rafraîchir les applications au démarrage
        self.refresh_applications()
        if self.selected_app:
            self.app_var.set(self.selected_app)
            self.select_application()

    def create_pixel_indicator(self):
        """Crée l'indicateur de pixel TOUJOURS AU PREMIER PLAN"""
        self.indicator_window = tk.Toplevel(self)
        self.indicator_window.overrideredirect(True)
        self.indicator_window.attributes("-topmost", True)
        self.indicator_window.attributes("-alpha", 0.8)
        self.indicator_window.geometry("20x20+5+5")
        self.indicator_window.configure(bg="red")
        self.indicator_window.bind("<Button-1>", self.toggle_pause_from_indicator)
        
        # Forcer le carré à rester au premier plan
        self.keep_indicator_on_top()

    def keep_indicator_on_top(self):
        """Force l'indicateur à rester au premier plan"""
        if self.indicator_window and self.indicator_window.winfo_exists():
            self.indicator_window.attributes("-topmost", True)
            self.indicator_window.lift()
            self.after(1000, self.keep_indicator_on_top)

    def create_delay_label(self):
        """Crée l'affichage du délai TRANSPARENT et TOUJOURS AU PREMIER PLAN"""
        self.delay_label_window = tk.Toplevel(self)
        self.delay_label_window.overrideredirect(True)
        self.delay_label_window.attributes("-topmost", True)
        self.delay_label_window.attributes("-alpha", 1.0)
        self.delay_label_window.geometry("+30+5")
        
        # Rendre le fond transparent
        self.delay_label_window.attributes('-transparentcolor', 'black')
        self.delay_label_window.configure(bg='black')
        
        self.delay_label = tk.Label(
            self.delay_label_window, 
            textvariable=self.delay_label_var,
            font=('Arial', 11, 'bold'),
            bg='black',
            fg=self.colors_map.get(self.text_color_var.get(), 'lime')
        )
        self.delay_label.pack()
        
        self.keep_text_on_top()

    def keep_text_on_top(self):
        """Force le texte à rester au premier plan"""
        if self.delay_label_window and self.delay_label_window.winfo_exists():
            self.delay_label_window.attributes("-topmost", True)
            self.delay_label_window.lift()
            self.after(1000, self.keep_text_on_top)

    def setup_keyboard_listener(self):
        """Configure le listener de touches F8, F9, F10, F11"""
        def on_press(key):
            try:
                if key == keyboard.Key.f8:
                    self.toggle_pause()
                elif key == keyboard.Key.f9:
                    self.toggle_disable()
                elif key == keyboard.Key.f10:
                    self.start_temp_pause(15)
                elif key == keyboard.Key.f11:
                    self.test_click()
            except:
                pass

        self.keyboard_listener = keyboard.Listener(on_press=on_press)
        self.keyboard_listener.start()

    def start_auto_calibration(self):
        """Démarre l'auto-calibration avec fenêtre de progrès"""
        if not self.app_var.get():
            messagebox.showwarning("Erreur", "Sélectionnez d'abord une application")
            return
        
        if not self.app_pid:
            messagebox.showwarning("Erreur", "Application non trouvée")
            return
        
        # Mettre la fenêtre cible au premier plan
        if bring_window_to_front(self.app_pid):
            logging.info(f"Application {self.app_var.get()} mise au premier plan")
        
        # Créer la fenêtre de progrès
        self.calibration_window = tk.Toplevel(self)
        self.calibration_window.title("Auto-Calibration en cours")
        self.calibration_window.geometry("400x200")
        self.calibration_window.configure(bg='#f0f0f0')
        self.calibration_window.resizable(False, False)
        self.calibration_window.attributes("-topmost", True)
        
        # Titre
        tk.Label(self.calibration_window, text="🎯 AUTO-CALIBRATION", 
                font=('Arial', 14, 'bold'), bg='#f0f0f0').pack(pady=10)
        
        # Instructions
        tk.Label(self.calibration_window, 
                text="Pêchez normalement pendant 30 secondes\nLe script N'EFFECTUE PAS de clics pendant la calibration",
                font=('Arial', 10), bg='#f0f0f0').pack(pady=5)
        
        # Barre de progression
        self.calibration_progress_var = tk.IntVar(value=0)
        progress_bar = ttk.Progressbar(self.calibration_window, 
                                       variable=self.calibration_progress_var,
                                       maximum=100, length=350)
        progress_bar.pack(pady=10)
        
        # Temps restant
        self.calibration_time_var = tk.StringVar(value="Temps restant: 30s")
        tk.Label(self.calibration_window, textvariable=self.calibration_time_var,
                font=('Arial', 10), bg='#f0f0f0').pack(pady=5)
        
        # Bouton Annuler
        tk.Button(self.calibration_window, text="Annuler", 
                 command=self.cancel_calibration,
                 bg='#F44336', fg='white', width=10).pack(pady=10)
        
        # Démarrer la calibration
        self.auto_calibrator.start_calibration(
            self.on_calibration_complete, 
            self.update_calibration_progress
        )
        
        # Désactiver le bouton de calibration pendant le processus
        self.calibration_button.config(state='disabled')

    def update_calibration_progress(self, progress, remaining):
        """Met à jour la progression de la calibration"""
        if self.calibration_window and self.calibration_window.winfo_exists():
            self.calibration_progress_var.set(progress)
            self.calibration_time_var.set(f"Temps restant: {int(remaining)}s")
    
    def cancel_calibration(self):
        """Annule la calibration en cours"""
        self.auto_calibrator.is_calibrating = False
        if self.calibration_window:
            self.calibration_window.destroy()
            self.calibration_window = None
        self.calibration_button.config(state='normal')
        logging.info("Calibration annulée")

    def on_calibration_complete(self, optimal_threshold):
        """Appelé quand la calibration est terminée"""
        if self.calibration_window:
            self.calibration_window.destroy()
            self.calibration_window = None
        
        self.calibration_button.config(state='normal')
        
        if optimal_threshold:
            self.threshold = optimal_threshold
            self.threshold_scale.set(optimal_threshold)
            self.volume_graph.set_threshold(optimal_threshold)
            self.save_current_config()
            
            # Message de succès
            messagebox.showinfo("Calibration Réussie", 
                              f"✅ Seuil optimal défini à {optimal_threshold:.1f}\n"
                              f"Détecté {len(self.auto_calibrator.peak_values)} poissons")
        else:
            messagebox.showwarning("Calibration", "Calibration échouée - pas assez de données")

    def test_click(self):
        """Test de clic (F11)"""
        threading.Thread(target=self.perform_single_right_click, daemon=True).start()

    def monitor_volume(self):
        """Thread principal de monitoring du volume
        Les clics sont envoyés même si la fenêtre est en arrière-plan (PostMessage)"""
        while self.is_running:
            try:
                if not self.is_completely_disabled and not self.is_paused and self.temp_pause_remaining == 0:
                    app_name = self.app_var.get()
                    if app_name and self.app_pid:
                        self.is_app_in_foreground = is_application_in_foreground(self.app_pid)
                        
                        volume = get_app_volume(app_name)
                        if volume is not None:
                            db = volume_to_db(volume)
                            normalized = db_to_normalized_scale(db)
                            
                            # Stocker le niveau actuel
                            self.current_volume_level = normalized
                            
                            # Mise à jour du graphique
                            self.volume_graph.add_value(normalized)
                            self.current_level_var.set(f"Niveau: {normalized:.1f}")
                            
                            # Auto-calibration - collecter les données SANS déclencher de clics
                            if self.auto_calibrator.is_calibrating:
                                # Détecter si c'est un pic (poisson qui mord)
                                is_peak = (normalized > self.baseline_volume * 1.5 and 
                                         normalized > 5.0)  # Seuil minimum pour considérer comme pic
                                self.auto_calibrator.add_sample(normalized, is_peak)
                                
                                # NE PAS effectuer de clics pendant la calibration
                                continue  # Passer au prochain cycle sans déclencher
                            
                            # Historique pour calcul de moyenne
                            self.volume_history.append(normalized)
                            if len(self.volume_history) < 2:
                                self.baseline_volume = normalized
                            else:
                                self.baseline_volume = sum(self.volume_history) / len(self.volume_history)
                            
                            # Détection normale (seulement si pas en calibration)
                            # Les clics sont envoyés même si la fenêtre est en arrière-plan
                            if not self.auto_calibrator.is_calibrating:
                                if normalized > self.threshold and normalized > self.baseline_volume * 1.2:
                                    current_time = time.time()
                                    
                                    if current_time - self.last_trigger_time > self.cooldown_period:
                                        self.trigger_count += 1
                                        
                                        if self.trigger_count >= 2:
                                            threading.Thread(target=self.perform_right_clicks, daemon=True).start()
                                            self.last_trigger_time = current_time
                                            self.trigger_count = 0
                                else:
                                    if self.trigger_count > 0:
                                        self.trigger_count -= 0.5
                
                time.sleep(0.05)
                
            except Exception as e:
                logging.error(f"Erreur monitoring volume: {e}")
                time.sleep(1)

    def check_inactivity(self):
        """Thread de vérification d'inactivité"""
        while self.is_running:
            try:
                # Pas de clics d'inactivité pendant la calibration
                if (not self.is_completely_disabled and not self.is_paused and 
                    self.temp_pause_remaining == 0 and not self.auto_calibrator.is_calibrating):
                    
                    time_since_last = time.time() - self.last_activity_time
                    
                    # Envoyer les clics d'inactivité même si la fenêtre est en arrière-plan
                    if time_since_last > self.inactivity_delay:
                        self.inactivity_trigger_count += 1
                        if self.inactivity_trigger_count >= 2:
                            threading.Thread(target=self.perform_single_right_click, daemon=True).start()
                            self.inactivity_delay = random.uniform(self.inactivity_base - 2, 
                                                                  self.inactivity_base + 2)
                            self.inactivity_trigger_count = 0
                
                time.sleep(1)
                
            except Exception as e:
                logging.error(f"Erreur inactivité: {e}")
                time.sleep(5)

    def update_stats_display(self):
        """Met à jour l'affichage des statistiques avancées"""
        runtime = time.time() - self.start_time
        hours = int(runtime // 3600)
        minutes = int((runtime % 3600) // 60)
        
        recent_clicks = [t for t in self.click_timestamps if time.time() - t < 60]
        cpm = len(recent_clicks)
        
        # Stats de la session
        session_stats = self.stats_manager.get_session_stats()
        
        text = f"""╔══════════════════════════════════════╗
║         STATISTIQUES AVANCÉES        ║
╚══════════════════════════════════════╝

🎣 Poissons pêchés: {self.click_counter}
⏱️ Temps session: {hours}h{minutes:02d}
📊 Taux actuel: {cpm} /min
✨ Taux succès: {session_stats['success_rate']:.1f}%

📈 Meilleure heure: {session_stats['best_hour']}
🎯 Pattern favori: {session_stats['most_used_pattern']}
⚡ Réaction moy: {session_stats['avg_reaction']:.3f}s
🔥 Total historique: {session_stats['clicks']} clics"""
        
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(1.0, text)
        
        self.after(5000, self.update_stats_display)

    def toggle_pause(self):
        """Bascule l'état de pause (F8)"""
        self.is_paused = not self.is_paused
        self.save_current_config()
        self.update_pixel_color()
        logging.info(f"État: {'En pause' if self.is_paused else 'Actif'}")

    def toggle_pause_from_indicator(self, event):
        """Bascule la pause depuis le clic sur l'indicateur"""
        self.toggle_pause()

    def toggle_disable(self):
        """Bascule l'état complètement désactivé (F9)"""
        self.is_completely_disabled = not self.is_completely_disabled
        self.save_current_config()
        self.update_pixel_color()
        logging.info(f"État: {'Désactivé' if self.is_completely_disabled else 'Activé'}")

    def start_temp_pause(self, seconds):
        """Démarre une pause temporaire (F10)"""
        self.temp_pause_remaining = seconds
        self.temp_pause_start = time.time()
        self.update_pixel_color()
        logging.info(f"Pause temporaire de {seconds} secondes")

    def handle_temp_pause(self):
        """Gère la pause temporaire"""
        while self.is_running:
            if self.temp_pause_remaining > 0:
                elapsed = time.time() - self.temp_pause_start
                self.temp_pause_remaining = max(0, 15 - elapsed)
                if self.temp_pause_remaining == 0:
                    self.update_pixel_color()
            time.sleep(0.5)

    def toggle_boost(self):
        """Active/désactive le mode boost"""
        self.is_boost_mode = not self.is_boost_mode
        self.boost_button.config(text=f"🚀 Boost: {'ON' if self.is_boost_mode else 'OFF'}")
        self.save_current_config()
        logging.info(f"Mode Boost: {self.is_boost_mode}")

    def reset_counter(self):
        """Réinitialise le compteur de clics"""
        if messagebox.askyesno("Reset", "Réinitialiser le compteur ?"):
            self.click_counter = 0
            self.click_timestamps.clear()
            self.save_current_config()
            self.update_stats_display()
            logging.info("Compteur réinitialisé")

    def generate_new_profile(self):
        """Génère un nouveau profil humain aléatoire"""
        self.human_profile = HumanProfile.generate_random("Random")
        self.randomizer = HumanLikeRandomizer(self.human_profile)
        self.update_profile_display()
        self.save_current_config()

    def set_preset_profile(self, preset):
        """Applique un profil prédéfini"""
        profiles = {
            'fast': HumanProfile("Fast", 1.5, 0.7, 0.3, 0.8, 0.3),
            'normal': HumanProfile("Normal", 1.0, 0.5, 0.5, 0.6, 0.5),
            'slow': HumanProfile("Slow", 0.7, 0.3, 0.7, 0.4, 0.7)
        }
        
        if preset in profiles:
            self.human_profile = profiles[preset]
            self.randomizer = HumanLikeRandomizer(self.human_profile)
            self.update_profile_display()
            self.save_current_config()

    def update_profile_display(self):
        """Met à jour l'affichage du profil"""
        text = (f"Profil: {self.human_profile.name}\n\n"
               f"Vitesse: {self.human_profile.reaction_speed:.1f}\n"
               f"Consistance: {self.human_profile.consistency:.1f}\n"
               f"Fatigue: {self.human_profile.fatigue_rate:.1f}\n"
               f"Concentration: {self.human_profile.concentration_level:.1f}\n"
               f"Variation: {self.human_profile.rhythm_variation:.1f}")
        self.profile_label.config(text=text)

    def refresh_applications(self):
        """Rafraîchit la liste des applications"""
        apps = get_running_applications()
        self.app_combo['values'] = apps
        logging.info(f"Applications trouvées: {apps}")

    def select_application(self):
        """Sélectionne l'application"""
        app_name = self.app_var.get()
        if not app_name:
            return
        
        self.app_pid = get_process_id_by_name(app_name)
        if self.app_pid:
            self.selected_app = app_name
            self.save_current_config()
            logging.info(f"Application sélectionnée: {app_name} (PID: {self.app_pid})")

    def update_threshold(self, value):
        """Met à jour le seuil"""
        self.threshold = float(value)
        self.threshold_label.config(text=f"{self.threshold:.1f}")
        self.volume_graph.set_threshold(self.threshold)

    def update_delays(self, value):
        """Met à jour les délais"""
        self.min_delay = self.min_delay_scale.get()
        self.max_delay = self.max_delay_scale.get()
        
        if self.max_delay <= self.min_delay:
            self.max_delay = self.min_delay + 0.1
            self.max_delay_scale.set(self.max_delay)
        
        self.delay_display_var.set(f"{self.min_delay:.2f} - {self.max_delay:.2f}s")

    def translated_color(self):
        """Retourne la couleur traduite pour tkinter"""
        return self.colors_map.get(self.text_color_var.get(), "lime")

    def perform_right_clicks(self, increment_counter=True):
        """Effectue les clics droits avec randomisation humaine"""
        try:
            app_name = self.app_var.get()
            if not self.app_pid:
                self.app_pid = get_process_id_by_name(app_name)
            if not self.app_pid:
                return
            
            hwnds = get_hwnds_for_pid(self.app_pid)
            if not hwnds:
                return
            hwnd = hwnds[0]

            # Position avec variation
            rect = win32gui.GetClientRect(hwnd)
            base_x = (rect[2] - rect[0]) // 2
            base_y = (rect[3] - rect[1]) // 2
            x, y = self.randomizer.get_click_position_variation(base_x, base_y, rect)
            lParam = win32api.MAKELONG(x, y)

            # Premier délai humanisé
            volume_exceeded = self.current_volume_level
            context = {'urgent': volume_exceeded > self.threshold * 1.2}
            delay1 = self.randomizer.get_humanized_delay(self.min_delay, self.max_delay, 
                                                        context, self.is_boost_mode)
            
            # Pattern actuel pour les stats
            self.current_pattern = self.randomizer.last_pattern_type or "steady"
            
            logging.info(f"Clic après {delay1:.2f}s à ({x},{y}), volume: {volume_exceeded:.1f}")
            time.sleep(delay1)

            # Premier clic
            win32gui.PostMessage(hwnd, win32con.WM_RBUTTONDOWN, win32con.MK_RBUTTON, lParam)
            time.sleep(random.uniform(0.01, 0.03))
            win32gui.PostMessage(hwnd, win32con.WM_RBUTTONUP, 0, lParam)

            # Deuxième clic
            delay2 = random.uniform(0.5, 0.7)
            time.sleep(delay2)

            x2, y2 = self.randomizer.get_click_position_variation(x, y, rect)
            lParam2 = win32api.MAKELONG(x2, y2)

            win32gui.PostMessage(hwnd, win32con.WM_RBUTTONDOWN, win32con.MK_RBUTTON, lParam2)
            time.sleep(random.uniform(0.01, 0.03))
            win32gui.PostMessage(hwnd, win32con.WM_RBUTTONUP, 0, lParam2)

            self.last_click_time = time.time()
            self.last_activity_time = time.time()

            if increment_counter:
                self.click_counter += 1
                self.click_timestamps.append(time.time())
                
                # Enregistrer dans les stats
                self.stats_manager.record_click(delay1, self.current_pattern, True)
                
                # Mise à jour de l'affichage
                rate = self.get_display_rate()
                line = self.build_display_line(delay1, volume_exceeded, rate)
                self.delay_label_var.set(line)
                
                if self.delay_label:
                    tk_color = self.translated_color()
                    self.delay_label.config(fg=tk_color)

                self.save_current_config()

        except Exception as e:
            logging.error(f"Erreur lors des clics: {e}")

    def perform_single_right_click(self, increment_counter=True):
        """Effectue un seul clic droit"""
        try:
            app_name = self.app_var.get()
            if not self.app_pid:
                self.app_pid = get_process_id_by_name(app_name)
            if not self.app_pid:
                return
            
            hwnds = get_hwnds_for_pid(self.app_pid)
            if not hwnds:
                return
            hwnd = hwnds[0]

            rect = win32gui.GetClientRect(hwnd)
            base_x = (rect[2] - rect[0]) // 2
            base_y = (rect[3] - rect[1]) // 2
            x, y = self.randomizer.get_click_position_variation(base_x, base_y, rect)
            lParam = win32api.MAKELONG(x, y)

            delay = self.randomizer.get_humanized_delay(self.min_delay, self.max_delay, 
                                                       {}, self.is_boost_mode)
            time.sleep(delay)

            win32gui.PostMessage(hwnd, win32con.WM_RBUTTONDOWN, win32con.MK_RBUTTON, lParam)
            time.sleep(random.uniform(0.01, 0.03))
            win32gui.PostMessage(hwnd, win32con.WM_RBUTTONUP, 0, lParam)

            self.last_click_time = time.time()
            self.last_activity_time = time.time()

            if increment_counter:
                self.click_counter += 1
                self.click_timestamps.append(time.time())
                self.stats_manager.record_click(delay, "inactivity", True)
                
                # Affichage normal sans "TEST"
                rate = self.get_display_rate()
                volume_level = self.current_volume_level
                line = self.build_display_line(delay, volume_level, rate)
                self.delay_label_var.set(line)
                
                if self.delay_label:
                    tk_color = self.translated_color()
                    self.delay_label.config(fg=tk_color)
                
                self.save_current_config()

            logging.info(f"Clic unique à ({x},{y})")

        except Exception as e:
            logging.error(f"Erreur clic unique: {e}")

    def get_display_rate(self):
        """Calcule le taux d'affichage"""
        current_time = time.time()
        recent_clicks = [t for t in self.click_timestamps if current_time - t < 60]
        rate = len(recent_clicks)
        self.last_rate = self.alpha * rate + (1 - self.alpha) * self.last_rate
        return int(self.last_rate)

    def build_display_line(self, delay1, volume_exceeded, rate):
        """Construit la ligne d'affichage"""
        parts = []
        if self.show_delay.get():
            parts.append(f"{delay1:.2f}")
        if self.show_volume.get():
            parts.append(f"{volume_exceeded:.1f}")
        if self.show_click_counter.get():
            parts.append(str(self.click_counter))
        if self.show_rate.get():
            parts.append(str(rate))
        return " | ".join(parts) if parts else "Ready"

    def update_pixel_color(self):
        """Met à jour la couleur de l'indicateur pixel"""
        if self.is_completely_disabled:
            self.current_color = "grey"
        elif self.temp_pause_remaining > 0:
            self.current_color = "orange"
        elif self.is_paused:
            self.current_color = "red"
        else:
            self.current_color = "green"

        if self.indicator_window:
            self.indicator_window.configure(bg=self.current_color)

    def save_current_config(self):
        """Sauvegarde la configuration actuelle"""
        config = {
            "threshold": self.threshold,
            "min_delay": self.min_delay,
            "max_delay": self.max_delay,
            "is_paused": self.is_paused,
            "is_completely_disabled": self.is_completely_disabled,
            "click_counter": self.click_counter,
            "inactivity_base": self.inactivity_base,
            "selected_app": self.app_var.get(),
            "show_delay": self.show_delay.get(),
            "show_volume": self.show_volume.get(),
            "show_click_counter": self.show_click_counter.get(),
            "show_rate": self.show_rate.get(),
            "text_color": self.text_color_var.get(),
            "is_boost_mode": self.is_boost_mode,
            "human_profile": asdict(self.human_profile)
        }
        save_config(config)

    def auto_save(self):
        """Sauvegarde automatique périodique"""
        while self.is_running:
            time.sleep(30)
            self.save_current_config()

    def on_closing(self):
        """Gestion de la fermeture"""
        self.save_current_config()
        self.is_running = False
        
        if hasattr(self, 'keyboard_listener'):
            self.keyboard_listener.stop()
        
        if self.indicator_window:
            self.indicator_window.destroy()
        if self.delay_label_window:
            self.delay_label_window.destroy()
        
        time.sleep(0.5)
        self.destroy()
        logging.info("Application fermée")


if __name__ == "__main__":
    try:
        # Pour Windows 10/11, permettre les couleurs transparentes
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass
        
        app = VolumeAnalyzerSimplified()
        app.mainloop()
    except Exception as e:
        logging.critical(f"Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        input("Appuyez sur Entrée pour fermer...")
