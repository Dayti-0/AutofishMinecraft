"""
AutoFish Minecraft - Application principale.
Outil d'automatisation de pêche pour Minecraft avec simulation de comportement humain.
"""

import os
import time
import random
import logging
import threading
import collections
import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import asdict

import win32gui
import win32con
import win32api
from pynput import keyboard

# Imports des modules locaux
from src import (
    load_config,
    save_config,
    get_running_applications,
    get_app_volume,
    volume_to_db,
    db_to_normalized_scale,
    get_process_id_by_name,
    is_application_in_foreground,
    get_hwnds_for_pid,
    bring_window_to_front,
    HumanProfile,
    HumanLikeRandomizer,
    StatsManager,
    AutoCalibrator,
    VolumeGraphBar,
    get_color_list,
    translate_color
)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)


class AutoFishApp(tk.Tk):
    """
    Application principale d'automatisation de pêche.

    Gère l'interface utilisateur, la détection audio et les clics automatiques.
    """

    def __init__(self):
        super().__init__()
        self.title("AutoFish Minecraft")
        self.geometry("480x600")
        self.configure(bg='#f0f0f0')
        self.resizable(False, False)

        # Charger la configuration
        self.config = load_config()

        # Gestionnaires
        self.stats_manager = StatsManager()
        self.auto_calibrator = AutoCalibrator()

        # Initialiser les variables
        self._init_variables()

        # Initialiser le profil humain
        self._init_human_profile()

        # Construction de l'interface
        self._create_widgets()

        # Créer les overlays
        self._create_overlays()

        # Configuration du clavier
        self._setup_keyboard_listener()

        # Démarrer les threads
        self._start_threads()

        # Mise à jour initiale
        self.update_pixel_color()

        # Gestion de la fermeture
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        logging.info("Application AutoFish démarrée")

    def _init_variables(self):
        """Initialise toutes les variables de l'application."""
        # Variables Tkinter
        self.app_var = tk.StringVar()
        self.current_level_var = tk.StringVar(value="Niveau: 0.0")
        self.delay_display_var = tk.StringVar(value="0.10 - 0.50s")
        self.delay_label_var = tk.StringVar(value="Ready")

        # Variables d'affichage
        self.show_delay = tk.BooleanVar(value=self.config.get("show_delay", True))
        self.show_volume = tk.BooleanVar(value=self.config.get("show_volume", True))
        self.show_click_counter = tk.BooleanVar(value=self.config.get("show_click_counter", True))
        self.show_rate = tk.BooleanVar(value=self.config.get("show_rate", True))
        self.text_color_var = tk.StringVar(value=self.config.get("text_color", "Vert clair"))

        # État de l'application
        self.is_running = True
        self.is_paused = self.config.get("is_paused", False)
        self.is_completely_disabled = self.config.get("is_completely_disabled", False)
        self.is_boost_mode = self.config.get("is_boost_mode", False)

        # Paramètres de détection
        self.threshold = self.config.get("threshold", 8.0)
        self.min_delay = self.config.get("min_delay", 0.1)
        self.max_delay = self.config.get("max_delay", 1.5)

        # Volume et détection
        self.volume_history = collections.deque(maxlen=10)
        self.baseline_volume = 0
        self.trigger_count = 0
        self.last_trigger_time = 0
        self.cooldown_period = 2
        self.post_action_delay = self.config.get("post_action_delay", 0.75)
        self.current_volume_level = 0

        # Timing
        self.last_click_time = time.time()
        self.last_activity_time = time.time()
        self.start_time = time.time()

        # Inactivité
        self.inactivity_base = self.config.get("inactivity_base", 7)
        self.inactivity_delay = random.uniform(self.inactivity_base - 2, self.inactivity_base + 2)
        self.inactivity_trigger_count = 0

        # Compteurs
        self.click_counter = self.config.get("click_counter", 0)
        self.click_timestamps = collections.deque()

        # Application cible
        self.selected_app = self.config.get("selected_app", "")
        self.app_pid = None
        self.is_app_in_foreground = False

        # Pause temporaire
        self.temp_pause_remaining = 0
        self.temp_pause_start = 0

        # Auto-pause pour inventaire et chat (seulement quand fenêtre au premier plan)
        self.is_inventory_open = False
        self.is_chat_open = False

        # Taux lissé
        self.last_rate = 0
        self.alpha = 0.3

        # Pattern actuel
        self.current_pattern = "steady"

        # Fenêtres overlay
        self.indicator_window = None
        self.delay_label_window = None
        self.calibration_window = None

    def _init_human_profile(self):
        """Initialise le profil humain et le randomizer."""
        human_profile_data = self.config.get("human_profile")
        if human_profile_data:
            self.human_profile = HumanProfile.from_dict(human_profile_data)
        else:
            self.human_profile = HumanProfile.generate_random("Default")

        self.randomizer = HumanLikeRandomizer(self.human_profile)

    def _create_widgets(self):
        """Crée tous les widgets de l'interface."""
        # Notebook pour organiser les onglets
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Créer les onglets
        self._create_main_tab(notebook)
        self._create_profiles_tab(notebook)
        self._create_options_tab(notebook)

        # Barre d'info en bas
        self._create_info_bar()

        # Charger les applications
        self.refresh_applications()
        if self.selected_app:
            self.app_var.set(self.selected_app)
            self.select_application()

    def _create_main_tab(self, notebook):
        """Crée l'onglet principal."""
        main_tab = tk.Frame(notebook, bg='#f0f0f0')
        notebook.add(main_tab, text="Principal")

        # Section Application
        app_frame = tk.LabelFrame(
            main_tab, text="Application",
            font=('Arial', 9, 'bold'), bg='#f0f0f0', padx=5, pady=3
        )
        app_frame.pack(fill=tk.X, padx=5, pady=3)

        app_controls = tk.Frame(app_frame, bg='#f0f0f0')
        app_controls.pack()

        self.app_combo = ttk.Combobox(
            app_controls, textvariable=self.app_var,
            width=20, state='readonly'
        )
        self.app_combo.pack(side=tk.LEFT, padx=2)

        tk.Button(
            app_controls, text="↻", command=self.refresh_applications,
            bg='#4CAF50', fg='white', width=3, height=1
        ).pack(side=tk.LEFT, padx=1)

        tk.Button(
            app_controls, text="OK", command=self.select_application,
            bg='#2196F3', fg='white', width=3, height=1
        ).pack(side=tk.LEFT, padx=1)

        # Section Analyse Audio
        volume_frame = tk.LabelFrame(
            main_tab, text="Analyse Audio",
            font=('Arial', 9, 'bold'), bg='#f0f0f0', padx=5, pady=3
        )
        volume_frame.pack(fill=tk.X, padx=5, pady=3)

        self.volume_graph = VolumeGraphBar(volume_frame)
        self.volume_graph.pack(pady=3)

        tk.Label(
            volume_frame, textvariable=self.current_level_var,
            font=('Arial', 8), bg='#f0f0f0'
        ).pack()

        # Section Seuil
        threshold_frame = tk.Frame(main_tab, bg='#f0f0f0')
        threshold_frame.pack(fill=tk.X, padx=5, pady=3)

        tk.Label(
            threshold_frame, text="Seuil:",
            font=('Arial', 9), bg='#f0f0f0'
        ).pack(side=tk.LEFT)

        self.threshold_scale = tk.Scale(
            threshold_frame, from_=0, to=10, resolution=0.1,
            orient=tk.HORIZONTAL, length=180, command=self.update_threshold,
            bg='#f0f0f0', highlightbackground='#f0f0f0', showvalue=False
        )
        self.threshold_scale.set(self.threshold)
        self.threshold_scale.pack(side=tk.LEFT, padx=3)

        self.threshold_label = tk.Label(
            threshold_frame, text=f"{self.threshold:.1f}",
            font=('Arial', 9, 'bold'), bg='#f0f0f0'
        )
        self.threshold_label.pack(side=tk.LEFT)

        # Section Délais
        delay_frame = tk.Frame(main_tab, bg='#f0f0f0')
        delay_frame.pack(fill=tk.X, padx=5, pady=3)

        tk.Label(
            delay_frame, text="Min:",
            font=('Arial', 9), bg='#f0f0f0'
        ).pack(side=tk.LEFT)

        self.min_delay_scale = tk.Scale(
            delay_frame, from_=0, to=5, resolution=0.01,
            orient=tk.HORIZONTAL, length=80, command=self.update_delays,
            bg='#f0f0f0', highlightbackground='#f0f0f0', showvalue=False
        )
        self.min_delay_scale.set(self.min_delay)
        self.min_delay_scale.pack(side=tk.LEFT, padx=2)

        tk.Label(
            delay_frame, text="Max:",
            font=('Arial', 9), bg='#f0f0f0'
        ).pack(side=tk.LEFT)

        self.max_delay_scale = tk.Scale(
            delay_frame, from_=0, to=10, resolution=0.01,
            orient=tk.HORIZONTAL, length=80, command=self.update_delays,
            bg='#f0f0f0', highlightbackground='#f0f0f0', showvalue=False
        )
        self.max_delay_scale.set(self.max_delay)
        self.max_delay_scale.pack(side=tk.LEFT, padx=2)

        tk.Label(
            delay_frame, textvariable=self.delay_display_var,
            font=('Arial', 8), bg='#f0f0f0'
        ).pack(side=tk.LEFT, padx=5)

        # Section Inactivité
        inactivity_frame = tk.Frame(main_tab, bg='#f0f0f0')
        inactivity_frame.pack(fill=tk.X, padx=5, pady=3)

        tk.Label(
            inactivity_frame, text="Clic si inactif:",
            font=('Arial', 9), bg='#f0f0f0'
        ).pack(side=tk.LEFT)

        self.inactivity_scale = tk.Scale(
            inactivity_frame, from_=3, to=30, resolution=1,
            orient=tk.HORIZONTAL, length=120, command=self.update_inactivity,
            bg='#f0f0f0', highlightbackground='#f0f0f0', showvalue=False
        )
        self.inactivity_scale.set(self.inactivity_base)
        self.inactivity_scale.pack(side=tk.LEFT, padx=3)

        self.inactivity_label = tk.Label(
            inactivity_frame, text=f"{self.inactivity_base}s (±2s)",
            font=('Arial', 9, 'bold'), bg='#f0f0f0'
        )
        self.inactivity_label.pack(side=tk.LEFT)

        # Section Statistiques
        stats_frame = tk.LabelFrame(
            main_tab, text="Statistiques",
            font=('Arial', 9, 'bold'), bg='#f0f0f0', padx=5, pady=3
        )
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=3)

        self.stats_text = tk.Text(
            stats_frame, height=8, width=50, bg='#ffffff',
            font=('Consolas', 8), relief=tk.FLAT, borderwidth=1
        )
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        self.update_stats_display()

    def _create_profiles_tab(self, notebook):
        """Crée l'onglet des profils."""
        profiles_tab = tk.Frame(notebook, bg='#f0f0f0')
        notebook.add(profiles_tab, text="Profils")

        # Bouton de calibration
        self.calibration_button = tk.Button(
            profiles_tab, text="🎯 AUTO-CALIBRATION",
            command=self.start_auto_calibration,
            bg='#FF9800', fg='white', font=('Arial', 11, 'bold'),
            width=25, height=2
        )
        self.calibration_button.pack(pady=15)

        # Profil actuel
        current_frame = tk.LabelFrame(
            profiles_tab, text="Profil Actuel",
            font=('Arial', 10, 'bold'), bg='#f0f0f0'
        )
        current_frame.pack(fill=tk.X, padx=10, pady=10)

        self.profile_label = tk.Label(
            current_frame, text="", font=('Arial', 9), bg='#f0f0f0'
        )
        self.profile_label.pack(pady=10)
        self.update_profile_display()

        # Boutons de presets
        preset_frame = tk.LabelFrame(
            profiles_tab, text="Profils Prédéfinis",
            font=('Arial', 10, 'bold'), bg='#f0f0f0'
        )
        preset_frame.pack(fill=tk.X, padx=10, pady=10)

        preset_buttons = tk.Frame(preset_frame, bg='#f0f0f0')
        preset_buttons.pack(pady=10)

        presets = [
            ("🎲 Aléatoire", self.generate_new_profile, '#00BCD4'),
            ("⚡ Rapide", lambda: self.set_preset_profile('fast'), '#8BC34A'),
            ("⚖️ Normal", lambda: self.set_preset_profile('normal'), '#3F51B5'),
            ("🐌 Lent", lambda: self.set_preset_profile('slow'), '#795548')
        ]

        for text, command, color in presets:
            tk.Button(
                preset_buttons, text=text, command=command,
                bg=color, fg='white', width=12, height=2, font=('Arial', 9)
            ).pack(side=tk.LEFT, padx=5)

    def _create_options_tab(self, notebook):
        """Crée l'onglet des options."""
        options_tab = tk.Frame(notebook, bg='#f0f0f0')
        notebook.add(options_tab, text="Options")

        # Section Affichage
        display_frame = tk.LabelFrame(
            options_tab, text="Affichage",
            font=('Arial', 9, 'bold'), bg='#f0f0f0', padx=5, pady=5
        )
        display_frame.pack(fill=tk.X, padx=5, pady=5)

        display_grid = tk.Frame(display_frame, bg='#f0f0f0')
        display_grid.pack()

        options = [
            ("Délai", self.show_delay, 0, 0),
            ("Volume", self.show_volume, 0, 1),
            ("Compteur", self.show_click_counter, 1, 0),
            ("Taux", self.show_rate, 1, 1)
        ]

        for text, var, row, col in options:
            tk.Checkbutton(
                display_grid, text=text, variable=var, bg='#f0f0f0',
                command=self.save_current_config
            ).grid(row=row, column=col, sticky='w')

        # Section Couleur
        color_frame = tk.Frame(options_tab, bg='#f0f0f0')
        color_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(
            color_frame, text="Couleur texte:",
            font=('Arial', 9), bg='#f0f0f0'
        ).pack(side=tk.LEFT)

        color_combo = ttk.Combobox(
            color_frame, textvariable=self.text_color_var,
            values=get_color_list(), width=12, state='readonly'
        )
        color_combo.pack(side=tk.LEFT, padx=5)
        color_combo.bind('<<ComboboxSelected>>', lambda e: self.save_current_config())

        # Section Actions
        action_frame = tk.Frame(options_tab, bg='#f0f0f0')
        action_frame.pack(fill=tk.X, padx=5, pady=10)

        self.boost_button = tk.Button(
            action_frame, text=f"🚀 Boost: {'ON' if self.is_boost_mode else 'OFF'}",
            command=self.toggle_boost, bg='#9C27B0', fg='white',
            width=15, height=2, font=('Arial', 9)
        )
        self.boost_button.pack(side=tk.LEFT, padx=10)

        tk.Button(
            action_frame, text="🔄 Reset Compteur",
            command=self.reset_counter, bg='#607D8B', fg='white',
            width=15, height=2, font=('Arial', 9)
        ).pack(side=tk.LEFT, padx=10)

    def _create_info_bar(self):
        """Crée la barre d'information en bas."""
        info_frame = tk.Frame(self, bg='#e0e0e0', height=40)
        info_frame.pack(fill=tk.X, side=tk.BOTTOM)

        tk.Label(
            info_frame,
            text="F8: Pause | F9: Off | F10: Pause 15s | F11: Test",
            font=('Arial', 8), bg='#e0e0e0'
        ).pack(pady=0)

        tk.Label(
            info_frame,
            text="Auto-pause: E (inventaire) | T / : (chat) - si fenêtre active",
            font=('Arial', 7), bg='#e0e0e0', fg='#666666'
        ).pack(pady=0)

    def _create_overlays(self):
        """Crée les fenêtres overlay."""
        # Indicateur pixel
        self.indicator_window = tk.Toplevel(self)
        self.indicator_window.overrideredirect(True)
        self.indicator_window.attributes("-topmost", True)
        self.indicator_window.attributes("-alpha", 0.8)
        self.indicator_window.geometry("20x20+5+5")
        self.indicator_window.configure(bg="red")
        self.indicator_window.bind("<Button-1>", lambda e: self.toggle_pause())
        self._keep_indicator_on_top()

        # Label de délai transparent
        self.delay_label_window = tk.Toplevel(self)
        self.delay_label_window.overrideredirect(True)
        self.delay_label_window.attributes("-topmost", True)
        self.delay_label_window.attributes("-alpha", 1.0)
        self.delay_label_window.geometry("+30+5")
        self.delay_label_window.attributes('-transparentcolor', 'black')
        self.delay_label_window.configure(bg='black')

        self.delay_label = tk.Label(
            self.delay_label_window,
            textvariable=self.delay_label_var,
            font=('Arial', 11, 'bold'),
            bg='black',
            fg=translate_color(self.text_color_var.get())
        )
        self.delay_label.pack()
        self._keep_text_on_top()

    def _keep_indicator_on_top(self):
        """Maintient l'indicateur au premier plan."""
        if self.indicator_window and self.indicator_window.winfo_exists():
            self.indicator_window.attributes("-topmost", True)
            self.indicator_window.lift()
            self.after(1000, self._keep_indicator_on_top)

    def _keep_text_on_top(self):
        """Maintient le texte au premier plan."""
        if self.delay_label_window and self.delay_label_window.winfo_exists():
            self.delay_label_window.attributes("-topmost", True)
            self.delay_label_window.lift()
            self.after(1000, self._keep_text_on_top)

    def _setup_keyboard_listener(self):
        """Configure le listener clavier."""
        def on_press(key):
            try:
                # Touches de contrôle globales (fonctionnent toujours)
                if key == keyboard.Key.f8:
                    self.toggle_pause()
                elif key == keyboard.Key.f9:
                    self.toggle_disable()
                elif key == keyboard.Key.f10:
                    self.start_temp_pause(15)
                elif key == keyboard.Key.f11:
                    self.test_click()

                # Auto-pause pour inventaire/chat (seulement si fenêtre au premier plan)
                # Si la fenêtre est en arrière-plan, on ne pause pas car le bot peut continuer
                elif self.is_app_in_foreground:
                    # Touche E - Toggle inventaire
                    if hasattr(key, 'char') and key.char and key.char.lower() == 'e':
                        if self.is_inventory_open:
                            self.is_inventory_open = False
                            logging.info("Inventaire fermé - Auto-pause désactivée")
                        else:
                            self.is_inventory_open = True
                            logging.info("Inventaire ouvert - Auto-pause activée")
                        self.update_pixel_color()

                    # Touches T, / ou : - Ouverture du chat
                    elif hasattr(key, 'char') and key.char and key.char.lower() in ('t', '/', ':'):
                        self.is_chat_open = True
                        logging.info("Chat ouvert - Auto-pause activée")
                        self.update_pixel_color()

                    # Touche Escape - Ferme inventaire ET chat
                    elif key == keyboard.Key.esc:
                        if self.is_inventory_open or self.is_chat_open:
                            self.is_inventory_open = False
                            self.is_chat_open = False
                            logging.info("Inventaire/Chat fermé (Escape) - Auto-pause désactivée")
                            self.update_pixel_color()

                    # Touche Enter - Ferme le chat seulement
                    elif key == keyboard.Key.enter:
                        if self.is_chat_open:
                            self.is_chat_open = False
                            logging.info("Chat fermé (Enter) - Auto-pause désactivée")
                            self.update_pixel_color()

            except Exception:
                pass

        self.keyboard_listener = keyboard.Listener(on_press=on_press)
        self.keyboard_listener.start()

    def _start_threads(self):
        """Démarre les threads de monitoring."""
        threading.Thread(target=self.monitor_volume, daemon=True).start()
        threading.Thread(target=self.check_inactivity, daemon=True).start()
        threading.Thread(target=self.handle_temp_pause, daemon=True).start()
        threading.Thread(target=self.auto_save, daemon=True).start()

    # === Méthodes de gestion des applications ===

    def refresh_applications(self):
        """Rafraîchit la liste des applications."""
        apps = get_running_applications()
        self.app_combo['values'] = apps
        logging.info(f"Applications trouvées: {apps}")

    def select_application(self):
        """Sélectionne l'application cible."""
        app_name = self.app_var.get()
        if not app_name:
            return

        self.app_pid = get_process_id_by_name(app_name)
        if self.app_pid:
            self.selected_app = app_name
            self.save_current_config()
            logging.info(f"Application sélectionnée: {app_name} (PID: {self.app_pid})")

    # === Méthodes de monitoring ===

    def monitor_volume(self):
        """Thread principal de monitoring du volume."""
        while self.is_running:
            try:
                # Toujours mettre à jour le statut du focus de la fenêtre
                app_name = self.app_var.get()
                if app_name and self.app_pid:
                    self.is_app_in_foreground = is_application_in_foreground(self.app_pid)

                # Vérifier si on doit exécuter les actions
                # Note: is_inventory_open et is_chat_open ne bloquent que si fenêtre au premier plan
                if (not self.is_completely_disabled and
                        not self.is_paused and
                        self.temp_pause_remaining == 0 and
                        not self.is_inventory_open and
                        not self.is_chat_open):

                    if app_name and self.app_pid:

                        volume = get_app_volume(app_name)
                        if volume is not None:
                            db = volume_to_db(volume)
                            normalized = db_to_normalized_scale(db)
                            self.current_volume_level = normalized

                            # Mise à jour du graphique
                            self.volume_graph.add_value(normalized)
                            self.current_level_var.set(f"Niveau: {normalized:.1f}")

                            # Mode calibration
                            if self.auto_calibrator.is_calibrating:
                                is_peak = (normalized > self.baseline_volume * 1.5 and
                                           normalized > 5.0)
                                self.auto_calibrator.add_sample(normalized, is_peak)
                                time.sleep(0.05)
                                continue

                            # Historique et baseline
                            self.volume_history.append(normalized)
                            if len(self.volume_history) < 2:
                                self.baseline_volume = normalized
                            else:
                                self.baseline_volume = sum(self.volume_history) / len(self.volume_history)

                            # Détection de déclenchement
                            if normalized > self.threshold and normalized > self.baseline_volume * 1.2:
                                current_time = time.time()

                                if current_time - self.last_trigger_time > self.cooldown_period:
                                    self.trigger_count += 1

                                    if self.trigger_count >= 2:
                                        # Bloquer immédiatement les nouveaux triggers
                                        self.last_trigger_time = current_time
                                        threading.Thread(
                                            target=self.perform_right_clicks,
                                            daemon=True
                                        ).start()
                                        # Note: last_trigger_time sera aussi mis à jour à la FIN
                                        # de perform_right_clicks() avec le post_action_delay
                                        self.trigger_count = 0
                            else:
                                if self.trigger_count > 0:
                                    self.trigger_count -= 0.5

                time.sleep(0.05)

            except Exception as e:
                logging.error(f"Erreur monitoring volume: {e}")
                time.sleep(1)

    def check_inactivity(self):
        """Thread de vérification d'inactivité."""
        while self.is_running:
            try:
                if (not self.is_completely_disabled and
                        not self.is_paused and
                        self.temp_pause_remaining == 0 and
                        not self.is_inventory_open and
                        not self.is_chat_open and
                        not self.auto_calibrator.is_calibrating):

                    time_since_last = time.time() - self.last_activity_time

                    if time_since_last > self.inactivity_delay:
                        self.inactivity_trigger_count += 1
                        if self.inactivity_trigger_count >= 2:
                            logging.info(f"Inactivité détectée ({time_since_last:.1f}s) - Clic automatique")
                            threading.Thread(
                                target=self.perform_single_right_click,
                                daemon=True
                            ).start()
                            self.inactivity_delay = random.uniform(
                                self.inactivity_base - 2,
                                self.inactivity_base + 2
                            )
                            self.inactivity_trigger_count = 0
                    else:
                        # Réinitialiser le compteur si une activité récente a eu lieu
                        self.inactivity_trigger_count = 0

                time.sleep(1)

            except Exception as e:
                logging.error(f"Erreur inactivité: {e}")
                time.sleep(5)

    def handle_temp_pause(self):
        """Gère la pause temporaire."""
        while self.is_running:
            if self.temp_pause_remaining > 0:
                elapsed = time.time() - self.temp_pause_start
                self.temp_pause_remaining = max(0, 15 - elapsed)
                if self.temp_pause_remaining == 0:
                    self.update_pixel_color()
            time.sleep(0.5)

    # === Méthodes d'action ===

    def perform_right_clicks(self, increment_counter=True):
        """Effectue les clics droits avec randomisation humaine."""
        try:
            # Réinitialiser immédiatement les compteurs d'inactivité pour éviter
            # les déclenchements en parallèle pendant l'exécution des clics
            self.last_activity_time = time.time()
            self.inactivity_trigger_count = 0

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
            delay1 = self.randomizer.get_humanized_delay(
                self.min_delay, self.max_delay, context, self.is_boost_mode
            )

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

            # Attendre le délai post-action avant de réactiver la détection
            # Cela évite les faux déclenchements dus aux sons juste après la pêche
            time.sleep(self.post_action_delay)

            self.last_click_time = time.time()
            self.last_activity_time = time.time()
            # Mettre à jour last_trigger_time ICI (après les actions) pour que le cooldown
            # commence après la fin des clics, pas avant
            self.last_trigger_time = time.time()

            if increment_counter:
                self.click_counter += 1
                self.click_timestamps.append(time.time())
                self.stats_manager.record_click(delay1, self.current_pattern, True)

                rate = self._get_display_rate()
                line = self._build_display_line(delay1, volume_exceeded, rate)
                self.delay_label_var.set(line)

                if self.delay_label:
                    self.delay_label.config(fg=translate_color(self.text_color_var.get()))

                self.save_current_config()

        except Exception as e:
            logging.error(f"Erreur lors des clics: {e}")

    def perform_single_right_click(self, increment_counter=True):
        """Effectue un seul clic droit."""
        try:
            # Réinitialiser immédiatement les compteurs d'inactivité
            self.last_activity_time = time.time()
            self.inactivity_trigger_count = 0

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

            delay = self.randomizer.get_humanized_delay(
                self.min_delay, self.max_delay, {}, self.is_boost_mode
            )
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

                rate = self._get_display_rate()
                volume_level = self.current_volume_level
                line = self._build_display_line(delay, volume_level, rate)
                self.delay_label_var.set(line)

                if self.delay_label:
                    self.delay_label.config(fg=translate_color(self.text_color_var.get()))

                self.save_current_config()

            logging.info(f"Clic unique à ({x},{y})")

        except Exception as e:
            logging.error(f"Erreur clic unique: {e}")

    def test_click(self):
        """Effectue un clic de test."""
        threading.Thread(target=self.perform_single_right_click, daemon=True).start()

    # === Méthodes d'interface ===

    def update_threshold(self, value):
        """Met à jour le seuil."""
        self.threshold = float(value)
        self.threshold_label.config(text=f"{self.threshold:.1f}")
        self.volume_graph.set_threshold(self.threshold)

    def update_delays(self, value):
        """Met à jour les délais."""
        self.min_delay = self.min_delay_scale.get()
        self.max_delay = self.max_delay_scale.get()

        if self.max_delay <= self.min_delay:
            self.max_delay = self.min_delay + 0.1
            self.max_delay_scale.set(self.max_delay)

        self.delay_display_var.set(f"{self.min_delay:.2f} - {self.max_delay:.2f}s")

    def update_inactivity(self, value):
        """Met à jour le délai d'inactivité."""
        self.inactivity_base = int(float(value))
        self.inactivity_label.config(text=f"{self.inactivity_base}s (±2s)")
        # Recalculer le délai d'inactivité avec la nouvelle base
        self.inactivity_delay = random.uniform(
            self.inactivity_base - 2,
            self.inactivity_base + 2
        )
        self.save_current_config()

    def update_stats_display(self):
        """Met à jour l'affichage des statistiques."""
        runtime = time.time() - self.start_time
        hours = int(runtime // 3600)
        minutes = int((runtime % 3600) // 60)

        recent_clicks = [t for t in self.click_timestamps if time.time() - t < 60]
        cpm = len(recent_clicks)

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

    def update_profile_display(self):
        """Met à jour l'affichage du profil."""
        text = (
            f"Profil: {self.human_profile.name}\n\n"
            f"Vitesse: {self.human_profile.reaction_speed:.1f}\n"
            f"Consistance: {self.human_profile.consistency:.1f}\n"
            f"Fatigue: {self.human_profile.fatigue_rate:.1f}\n"
            f"Concentration: {self.human_profile.concentration_level:.1f}\n"
            f"Variation: {self.human_profile.rhythm_variation:.1f}"
        )
        self.profile_label.config(text=text)

    def update_pixel_color(self):
        """Met à jour la couleur de l'indicateur."""
        if self.is_completely_disabled:
            color = "grey"
        elif self.temp_pause_remaining > 0:
            color = "orange"
        elif self.is_paused:
            color = "red"
        elif self.is_inventory_open or self.is_chat_open:
            color = "#FFD700"  # Or/Jaune pour auto-pause (inventaire/chat)
        else:
            color = "green"

        if self.indicator_window:
            self.indicator_window.configure(bg=color)

    # === Méthodes de contrôle ===

    def toggle_pause(self):
        """Bascule l'état de pause."""
        self.is_paused = not self.is_paused

        # Réinitialiser le timer d'inactivité pour éviter un clic immédiat à la reprise
        self.last_activity_time = time.time()
        self.inactivity_trigger_count = 0
        self.inactivity_delay = random.uniform(
            self.inactivity_base - 2,
            self.inactivity_base + 2
        )

        self.save_current_config()
        self.update_pixel_color()
        logging.info(f"État: {'En pause' if self.is_paused else 'Actif'}")

    def toggle_disable(self):
        """Bascule l'état complètement désactivé."""
        self.is_completely_disabled = not self.is_completely_disabled
        self.save_current_config()
        self.update_pixel_color()
        logging.info(f"État: {'Désactivé' if self.is_completely_disabled else 'Activé'}")

    def start_temp_pause(self, seconds):
        """Démarre une pause temporaire."""
        self.temp_pause_remaining = seconds
        self.temp_pause_start = time.time()
        self.update_pixel_color()
        logging.info(f"Pause temporaire de {seconds} secondes")

    def toggle_boost(self):
        """Active/désactive le mode boost."""
        self.is_boost_mode = not self.is_boost_mode
        self.boost_button.config(text=f"🚀 Boost: {'ON' if self.is_boost_mode else 'OFF'}")
        self.save_current_config()
        logging.info(f"Mode Boost: {self.is_boost_mode}")

    def reset_counter(self):
        """Réinitialise le compteur de clics."""
        if messagebox.askyesno("Reset", "Réinitialiser le compteur ?"):
            self.click_counter = 0
            self.click_timestamps.clear()
            self.save_current_config()
            self.update_stats_display()
            logging.info("Compteur réinitialisé")

    # === Méthodes de profil ===

    def generate_new_profile(self):
        """Génère un nouveau profil aléatoire."""
        self.human_profile = HumanProfile.generate_random("Random")
        self.randomizer = HumanLikeRandomizer(self.human_profile)
        self.update_profile_display()
        self.save_current_config()

    def set_preset_profile(self, preset):
        """Applique un profil prédéfini."""
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

    # === Méthodes de calibration ===

    def start_auto_calibration(self):
        """Démarre l'auto-calibration."""
        if not self.app_var.get():
            messagebox.showwarning("Erreur", "Sélectionnez d'abord une application")
            return

        if not self.app_pid:
            messagebox.showwarning("Erreur", "Application non trouvée")
            return

        if bring_window_to_front(self.app_pid):
            logging.info(f"Application {self.app_var.get()} mise au premier plan")

        # Fenêtre de progrès
        self.calibration_window = tk.Toplevel(self)
        self.calibration_window.title("Auto-Calibration en cours")
        self.calibration_window.geometry("400x200")
        self.calibration_window.configure(bg='#f0f0f0')
        self.calibration_window.resizable(False, False)
        self.calibration_window.attributes("-topmost", True)

        tk.Label(
            self.calibration_window, text="🎯 AUTO-CALIBRATION",
            font=('Arial', 14, 'bold'), bg='#f0f0f0'
        ).pack(pady=10)

        tk.Label(
            self.calibration_window,
            text="Pêchez normalement pendant 30 secondes\n"
                 "Le script N'EFFECTUE PAS de clics pendant la calibration",
            font=('Arial', 10), bg='#f0f0f0'
        ).pack(pady=5)

        self.calibration_progress_var = tk.IntVar(value=0)
        progress_bar = ttk.Progressbar(
            self.calibration_window,
            variable=self.calibration_progress_var,
            maximum=100, length=350
        )
        progress_bar.pack(pady=10)

        self.calibration_time_var = tk.StringVar(value="Temps restant: 30s")
        tk.Label(
            self.calibration_window, textvariable=self.calibration_time_var,
            font=('Arial', 10), bg='#f0f0f0'
        ).pack(pady=5)

        tk.Button(
            self.calibration_window, text="Annuler",
            command=self.cancel_calibration,
            bg='#F44336', fg='white', width=10
        ).pack(pady=10)

        self.auto_calibrator.start_calibration(
            self.on_calibration_complete,
            self.update_calibration_progress
        )

        self.calibration_button.config(state='disabled')

    def update_calibration_progress(self, progress, remaining):
        """Met à jour la progression de la calibration."""
        if self.calibration_window and self.calibration_window.winfo_exists():
            self.calibration_progress_var.set(progress)
            self.calibration_time_var.set(f"Temps restant: {int(remaining)}s")

    def cancel_calibration(self):
        """Annule la calibration."""
        self.auto_calibrator.cancel()
        if self.calibration_window:
            self.calibration_window.destroy()
            self.calibration_window = None
        self.calibration_button.config(state='normal')

    def on_calibration_complete(self, optimal_threshold):
        """Appelé quand la calibration est terminée."""
        if self.calibration_window:
            self.calibration_window.destroy()
            self.calibration_window = None

        self.calibration_button.config(state='normal')

        if optimal_threshold:
            self.threshold = optimal_threshold
            self.threshold_scale.set(optimal_threshold)
            self.volume_graph.set_threshold(optimal_threshold)
            self.save_current_config()

            messagebox.showinfo(
                "Calibration Réussie",
                f"✅ Seuil optimal défini à {optimal_threshold:.1f}\n"
                f"Détecté {self.auto_calibrator.get_peak_count()} poissons"
            )
        else:
            messagebox.showwarning("Calibration", "Calibration échouée - pas assez de données")

    # === Méthodes utilitaires ===

    def _get_display_rate(self):
        """Calcule le taux d'affichage lissé."""
        current_time = time.time()
        recent_clicks = [t for t in self.click_timestamps if current_time - t < 60]
        rate = len(recent_clicks)
        self.last_rate = self.alpha * rate + (1 - self.alpha) * self.last_rate
        return int(self.last_rate)

    def _build_display_line(self, delay, volume, rate):
        """Construit la ligne d'affichage."""
        parts = []
        if self.show_delay.get():
            parts.append(f"{delay:.2f}")
        if self.show_volume.get():
            parts.append(f"{volume:.1f}")
        if self.show_click_counter.get():
            parts.append(str(self.click_counter))
        if self.show_rate.get():
            parts.append(str(rate))
        return " | ".join(parts) if parts else "Ready"

    def save_current_config(self):
        """Sauvegarde la configuration actuelle."""
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
            "human_profile": self.human_profile.to_dict()
        }
        save_config(config)

    def auto_save(self):
        """Sauvegarde automatique périodique."""
        while self.is_running:
            time.sleep(30)
            self.save_current_config()

    def on_closing(self):
        """Gestion de la fermeture de l'application."""
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


def main():
    """Point d'entrée principal."""
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
        input("Appuyez sur Entrée pour fermer...")


if __name__ == "__main__":
    main()
