"""
AutoFish Minecraft - Application principale.
Outil d'automatisation de peche pour Minecraft avec simulation de comportement humain.
"""

import time
import random
import logging
import threading
import tkinter as tk
from tkinter import messagebox

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

# Imports des modules locaux
from src import (
    load_config,
    save_config,
    get_running_applications,
    get_process_id_by_name,
    bring_window_to_front,
    HumanProfile,
    HumanLikeRandomizer,
    StatsManager,
    AutoCalibrator,
)
from src.app_state import AppState
from src.click_handler import ClickHandler
from src.monitoring import VolumeMonitor, InactivityMonitor, TempPauseMonitor
from src.keyboard_handler import KeyboardHandler
from src.overlay_manager import OverlayManager
from src.ui_builder import UIBuilder


class AutoFishApp(tk.Tk):
    """
    Application principale d'automatisation de peche.

    Orchestre les differents composants:
    - AppState: Gestion de l'etat
    - ClickHandler: Execution des clics
    - Monitors: Surveillance volume/inactivite
    - KeyboardHandler: Raccourcis clavier
    - OverlayManager: Fenetres overlay
    - UIBuilder: Interface utilisateur
    """

    def __init__(self):
        super().__init__()
        self._setup_window()
        self._init_components()
        self._build_interface()
        self._start_monitors()
        self._setup_closing()

        logging.info("Application AutoFish demarree")

    def _setup_window(self):
        """Configure la fenetre principale."""
        self.title("AutoFish Minecraft")
        self.geometry("480x600")
        self.configure(bg='#f0f0f0')
        self.resizable(False, False)

    def _init_components(self):
        """Initialise tous les composants."""
        # Etat de l'application
        self.state = AppState()

        # Profil humain
        self._init_human_profile()

        # Gestionnaires
        self.stats_manager = StatsManager()
        self.auto_calibrator = AutoCalibrator()

        # Gestionnaire de clics
        self.click_handler = ClickHandler(
            state=self.state,
            randomizer=self.randomizer,
            stats_manager=self.stats_manager,
            on_click_callback=self._on_click_performed
        )

        # Gestionnaire d'overlay
        self.overlay = OverlayManager(
            parent=self,
            state=self.state,
            on_indicator_click=self.toggle_pause
        )
        self.overlay.create()

        # Gestionnaire de clavier
        self.keyboard_handler = KeyboardHandler(
            state=self.state,
            on_toggle_pause=self.toggle_pause,
            on_toggle_disable=self.toggle_disable,
            on_temp_pause=self.start_temp_pause,
            on_test_click=self.test_click,
            on_state_change=self._update_indicator
        )
        self.keyboard_handler.start()

        # Moniteurs
        self.volume_monitor = VolumeMonitor(
            state=self.state,
            calibrator=self.auto_calibrator,
            on_trigger=self.click_handler.perform_double_right_click,
            on_volume_update=self._on_volume_update
        )

        self.inactivity_monitor = InactivityMonitor(
            state=self.state,
            calibrator=self.auto_calibrator,
            on_inactivity=self.click_handler.perform_single_right_click
        )

        self.temp_pause_monitor = TempPauseMonitor(
            state=self.state,
            on_pause_end=self._update_indicator
        )

    def _init_human_profile(self):
        """Initialise le profil humain et le randomizer."""
        human_profile_data = self.state.config.get("human_profile")
        if human_profile_data:
            self.human_profile = HumanProfile.from_dict(human_profile_data)
        else:
            self.human_profile = HumanProfile.generate_random("Default")

        self.randomizer = HumanLikeRandomizer(self.human_profile)

    def _build_interface(self):
        """Construit l'interface utilisateur."""
        callbacks = {
            'refresh_apps': self.refresh_applications,
            'select_app': self.select_application,
            'update_threshold': self._on_threshold_change,
            'update_delays': self._on_delays_change,
            'update_inactivity': self._on_inactivity_change,
            'start_calibration': self.start_auto_calibration,
            'generate_profile': self.generate_new_profile,
            'set_preset': self.set_preset_profile,
            'toggle_boost': self.toggle_boost,
            'reset_counter': self.reset_counter,
            'save_config': self.save_current_config,
        }

        self.ui = UIBuilder(self, self.state, callbacks)
        self.ui.build()

        # Charger les applications
        self.refresh_applications()
        if self.state.selected_app:
            self.ui.app_var.set(self.state.selected_app)
            self.select_application()

        # Mise a jour du profil
        self._update_profile_display()

        # Demarrer les mises a jour periodiques
        self._start_periodic_updates()

    def _start_monitors(self):
        """Demarre tous les threads de monitoring."""
        self.volume_monitor.start()
        self.inactivity_monitor.start()
        self.temp_pause_monitor.start()

        # Thread de sauvegarde auto
        threading.Thread(target=self._auto_save_loop, daemon=True).start()

    def _setup_closing(self):
        """Configure la gestion de la fermeture."""
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    # === Callbacks ===

    def _on_click_performed(self, display_line: str):
        """Callback appele apres chaque clic."""
        self.overlay.update_delay_text(display_line)
        self.save_current_config()

    def _on_volume_update(self, level: float):
        """Callback pour mise a jour du volume."""
        self.ui.update_volume_display(level)

    def _on_threshold_change(self, value):
        """Callback pour changement de seuil."""
        self.state.detection.threshold = float(value)
        self.ui.update_threshold_display(self.state.detection.threshold)

    def _on_delays_change(self, value):
        """Callback pour changement de delais."""
        min_delay = self.ui.min_delay_scale.get()
        max_delay = self.ui.max_delay_scale.get()

        if max_delay <= min_delay:
            max_delay = min_delay + 0.1
            self.ui.max_delay_scale.set(max_delay)

        self.state.detection.min_delay = min_delay
        self.state.detection.max_delay = max_delay
        self.ui.update_delay_display(min_delay, max_delay)

    def _on_inactivity_change(self, value):
        """Callback pour changement d'inactivite."""
        base = int(float(value))
        self.state.inactivity.base_delay = base
        self.state.inactivity.current_delay = random.uniform(base - 2, base + 2)
        self.ui.update_inactivity_display(base)
        self.save_current_config()

    def _update_indicator(self):
        """Met a jour l'indicateur d'etat."""
        self.overlay.update_indicator_color()

    # === Actions utilisateur ===

    def refresh_applications(self):
        """Rafraichit la liste des applications."""
        apps = get_running_applications()
        self.ui.update_apps_list(apps)
        logging.info(f"Applications trouvees: {apps}")

    def select_application(self):
        """Selectionne l'application cible."""
        app_name = self.ui.app_var.get()
        if not app_name:
            return

        self.state.app_pid = get_process_id_by_name(app_name)
        if self.state.app_pid:
            self.state.selected_app = app_name
            self.save_current_config()
            logging.info(f"Application selectionnee: {app_name} (PID: {self.state.app_pid})")

    def toggle_pause(self):
        """Bascule l'etat de pause."""
        self.state.is_paused = not self.state.is_paused
        self.state.reset_inactivity()
        self.save_current_config()
        self._update_indicator()
        logging.info(f"Etat: {'En pause' if self.state.is_paused else 'Actif'}")

    def toggle_disable(self):
        """Bascule l'etat completement desactive."""
        self.state.is_completely_disabled = not self.state.is_completely_disabled
        self.save_current_config()
        self._update_indicator()
        logging.info(f"Etat: {'Desactive' if self.state.is_completely_disabled else 'Active'}")

    def start_temp_pause(self, seconds: int):
        """Demarre une pause temporaire."""
        self.state.temp_pause_remaining = seconds
        self.state.temp_pause_start = time.time()
        self._update_indicator()
        logging.info(f"Pause temporaire de {seconds} secondes")

    def toggle_boost(self):
        """Active/desactive le mode boost."""
        self.state.is_boost_mode = not self.state.is_boost_mode
        self.ui.update_boost_button(self.state.is_boost_mode)
        self.save_current_config()
        logging.info(f"Mode Boost: {self.state.is_boost_mode}")

    def reset_counter(self):
        """Reinitialise le compteur de clics."""
        if messagebox.askyesno("Reset", "Reinitialiser le compteur ?"):
            self.state.click_counter = 0
            self.state.click_timestamps.clear()
            self.save_current_config()
            logging.info("Compteur reinitialise")

    def test_click(self):
        """Effectue un clic de test."""
        threading.Thread(
            target=self.click_handler.perform_single_right_click,
            daemon=True
        ).start()

    # === Profils ===

    def generate_new_profile(self):
        """Genere un nouveau profil aleatoire."""
        self.human_profile = HumanProfile.generate_random("Random")
        self.randomizer = HumanLikeRandomizer(self.human_profile)
        self.click_handler.randomizer = self.randomizer
        self._update_profile_display()
        self.save_current_config()

    def set_preset_profile(self, preset: str):
        """Applique un profil predefini."""
        profiles = {
            'fast': HumanProfile("Fast", 1.5, 0.7, 0.3, 0.8, 0.3),
            'normal': HumanProfile("Normal", 1.0, 0.5, 0.5, 0.6, 0.5),
            'slow': HumanProfile("Slow", 0.7, 0.3, 0.7, 0.4, 0.7)
        }

        if preset in profiles:
            self.human_profile = profiles[preset]
            self.randomizer = HumanLikeRandomizer(self.human_profile)
            self.click_handler.randomizer = self.randomizer
            self._update_profile_display()
            self.save_current_config()

    def _update_profile_display(self):
        """Met a jour l'affichage du profil."""
        text = (
            f"Profil: {self.human_profile.name}\n\n"
            f"Vitesse: {self.human_profile.reaction_speed:.1f}\n"
            f"Consistance: {self.human_profile.consistency:.1f}\n"
            f"Fatigue: {self.human_profile.fatigue_rate:.1f}\n"
            f"Concentration: {self.human_profile.concentration_level:.1f}\n"
            f"Variation: {self.human_profile.rhythm_variation:.1f}"
        )
        self.ui.profile_label.config(text=text)

    # === Calibration ===

    def start_auto_calibration(self):
        """Demarre l'auto-calibration."""
        if not self.ui.app_var.get():
            messagebox.showwarning("Erreur", "Selectionnez d'abord une application")
            return

        if not self.state.app_pid:
            messagebox.showwarning("Erreur", "Application non trouvee")
            return

        if bring_window_to_front(self.state.app_pid):
            logging.info(f"Application {self.ui.app_var.get()} mise au premier plan")

        self._show_calibration_window()

        self.auto_calibrator.start_calibration(
            self._on_calibration_complete,
            self._update_calibration_progress
        )

        self.ui.calibration_button.config(state='disabled')

    def _show_calibration_window(self):
        """Affiche la fenetre de calibration."""
        self.calibration_window = tk.Toplevel(self)
        self.calibration_window.title("Auto-Calibration en cours")
        self.calibration_window.geometry("400x200")
        self.calibration_window.configure(bg='#f0f0f0')
        self.calibration_window.resizable(False, False)
        self.calibration_window.attributes("-topmost", True)

        tk.Label(
            self.calibration_window, text="AUTO-CALIBRATION",
            font=('Arial', 14, 'bold'), bg='#f0f0f0'
        ).pack(pady=10)

        tk.Label(
            self.calibration_window,
            text="Pechez normalement pendant 30 secondes\n"
                 "Le script N'EFFECTUE PAS de clics pendant la calibration",
            font=('Arial', 10), bg='#f0f0f0'
        ).pack(pady=5)

        from tkinter import ttk
        self.calibration_progress_var = tk.IntVar(value=0)
        ttk.Progressbar(
            self.calibration_window,
            variable=self.calibration_progress_var,
            maximum=100, length=350
        ).pack(pady=10)

        self.calibration_time_var = tk.StringVar(value="Temps restant: 30s")
        tk.Label(
            self.calibration_window, textvariable=self.calibration_time_var,
            font=('Arial', 10), bg='#f0f0f0'
        ).pack(pady=5)

        tk.Button(
            self.calibration_window, text="Annuler",
            command=self._cancel_calibration,
            bg='#F44336', fg='white', width=10
        ).pack(pady=10)

    def _update_calibration_progress(self, progress: int, remaining: float):
        """Met a jour la progression de la calibration."""
        if hasattr(self, 'calibration_window') and self.calibration_window.winfo_exists():
            self.calibration_progress_var.set(progress)
            self.calibration_time_var.set(f"Temps restant: {int(remaining)}s")

    def _cancel_calibration(self):
        """Annule la calibration."""
        self.auto_calibrator.cancel()
        if hasattr(self, 'calibration_window'):
            self.calibration_window.destroy()
        self.ui.calibration_button.config(state='normal')

    def _on_calibration_complete(self, optimal_threshold):
        """Callback quand la calibration est terminee."""
        if hasattr(self, 'calibration_window'):
            self.calibration_window.destroy()

        self.ui.calibration_button.config(state='normal')

        if optimal_threshold:
            self.state.detection.threshold = optimal_threshold
            self.ui.threshold_scale.set(optimal_threshold)
            self.ui.update_threshold_display(optimal_threshold)
            self.save_current_config()

            messagebox.showinfo(
                "Calibration Reussie",
                f"Seuil optimal defini a {optimal_threshold:.1f}\n"
                f"Detecte {self.auto_calibrator.get_peak_count()} poissons"
            )
        else:
            messagebox.showwarning("Calibration", "Calibration echouee - pas assez de donnees")

    # === Mises a jour periodiques ===

    def _start_periodic_updates(self):
        """Demarre les mises a jour periodiques."""
        self._update_stats_display()

    def _update_stats_display(self):
        """Met a jour l'affichage des statistiques."""
        runtime = time.time() - self.state.start_time
        hours = int(runtime // 3600)
        minutes = int((runtime % 3600) // 60)

        recent_clicks = [t for t in self.state.click_timestamps if time.time() - t < 60]
        cpm = len(recent_clicks)

        session_stats = self.stats_manager.get_session_stats()

        text = f"""========================================
         STATISTIQUES AVANCEES
========================================

Poissons peches: {self.state.click_counter}
Temps session: {hours}h{minutes:02d}
Taux actuel: {cpm} /min
Taux succes: {session_stats['success_rate']:.1f}%

Meilleure heure: {session_stats['best_hour']}
Pattern favori: {session_stats['most_used_pattern']}
Reaction moy: {session_stats['avg_reaction']:.3f}s
Total historique: {session_stats['clicks']} clics"""

        self.ui.stats_text.delete(1.0, tk.END)
        self.ui.stats_text.insert(1.0, text)

        self.after(5000, self._update_stats_display)

    # === Sauvegarde ===

    def save_current_config(self):
        """Sauvegarde la configuration actuelle."""
        config = self.state.to_config_dict()
        config["human_profile"] = self.human_profile.to_dict()
        save_config(config)

    def _auto_save_loop(self):
        """Boucle de sauvegarde automatique."""
        while self.state.is_running:
            time.sleep(30)
            self.save_current_config()

    # === Fermeture ===

    def on_closing(self):
        """Gestion de la fermeture de l'application."""
        self.save_current_config()
        self.state.is_running = False

        self.keyboard_handler.stop()
        self.overlay.destroy()

        time.sleep(0.5)
        self.destroy()
        logging.info("Application fermee")


def main():
    """Point d'entree principal."""
    try:
        # Configuration DPI pour Windows 10/11
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        app = AutoFishApp()
        app.mainloop()

    except Exception as e:
        logging.critical(f"Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        input("Appuyez sur Entree pour fermer...")


if __name__ == "__main__":
    main()
