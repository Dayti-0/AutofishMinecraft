"""
AutoFish Minecraft - Constructeur d'interface utilisateur.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, Any, TYPE_CHECKING

from .ui_components import VolumeGraphBar, get_color_list

if TYPE_CHECKING:
    from .app_state import AppState


class UIBuilder:
    """
    Construit l'interface utilisateur de l'application.

    Separe la logique de creation des widgets de la logique metier.
    """

    def __init__(self, parent: tk.Tk, state: 'AppState', callbacks: Dict[str, Callable]):
        """
        Initialise le constructeur d'interface.

        Args:
            parent: Fenetre parente Tkinter
            state: Etat de l'application
            callbacks: Dictionnaire des callbacks pour les actions
        """
        self.parent = parent
        self.state = state
        self.callbacks = callbacks

        # Variables Tkinter
        self.app_var = tk.StringVar()
        self.current_level_var = tk.StringVar(value="Niveau: 0.0")
        self.delay_display_var = tk.StringVar(
            value=f"{state.detection.min_delay:.2f} - {state.detection.max_delay:.2f}s"
        )

        # Variables d'affichage liees a l'etat
        self.show_delay = tk.BooleanVar(value=state.display.show_delay)
        self.show_volume = tk.BooleanVar(value=state.display.show_volume)
        self.show_click_counter = tk.BooleanVar(value=state.display.show_click_counter)
        self.show_rate = tk.BooleanVar(value=state.display.show_rate)
        self.text_color_var = tk.StringVar(value=state.display.text_color)

        # Widgets references
        self.app_combo = None
        self.volume_graph = None
        self.threshold_scale = None
        self.threshold_label = None
        self.min_delay_scale = None
        self.max_delay_scale = None
        self.inactivity_scale = None
        self.inactivity_label = None
        self.auto_cast_scale = None
        self.auto_cast_label = None
        self.stats_text = None
        self.profile_label = None
        self.calibration_button = None
        self.boost_button = None

    def build(self):
        """Construit l'interface complete."""
        notebook = ttk.Notebook(self.parent)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self._create_main_tab(notebook)
        self._create_profiles_tab(notebook)
        self._create_options_tab(notebook)
        self._create_info_bar()

    def _create_main_tab(self, notebook: ttk.Notebook):
        """Cree l'onglet principal."""
        main_tab = tk.Frame(notebook, bg='#f0f0f0')
        notebook.add(main_tab, text="Principal")

        self._create_app_section(main_tab)
        self._create_volume_section(main_tab)
        self._create_threshold_section(main_tab)
        self._create_delay_section(main_tab)
        self._create_inactivity_section(main_tab)
        self._create_auto_cast_section(main_tab)
        self._create_stats_section(main_tab)

    def _create_app_section(self, parent: tk.Frame):
        """Cree la section de selection d'application."""
        app_frame = tk.LabelFrame(
            parent, text="Application",
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
            app_controls, text="<", command=self.callbacks['refresh_apps'],
            bg='#4CAF50', fg='white', width=3, height=1
        ).pack(side=tk.LEFT, padx=1)

        tk.Button(
            app_controls, text="OK", command=self.callbacks['select_app'],
            bg='#2196F3', fg='white', width=3, height=1
        ).pack(side=tk.LEFT, padx=1)

    def _create_volume_section(self, parent: tk.Frame):
        """Cree la section d'analyse audio."""
        volume_frame = tk.LabelFrame(
            parent, text="Analyse Audio",
            font=('Arial', 9, 'bold'), bg='#f0f0f0', padx=5, pady=3
        )
        volume_frame.pack(fill=tk.X, padx=5, pady=3)

        self.volume_graph = VolumeGraphBar(volume_frame)
        self.volume_graph.pack(pady=3)

        tk.Label(
            volume_frame, textvariable=self.current_level_var,
            font=('Arial', 8), bg='#f0f0f0'
        ).pack()

    def _create_threshold_section(self, parent: tk.Frame):
        """Cree la section de reglage du seuil."""
        threshold_frame = tk.Frame(parent, bg='#f0f0f0')
        threshold_frame.pack(fill=tk.X, padx=5, pady=3)

        tk.Label(
            threshold_frame, text="Seuil:",
            font=('Arial', 9), bg='#f0f0f0'
        ).pack(side=tk.LEFT)

        self.threshold_scale = tk.Scale(
            threshold_frame, from_=0, to=10, resolution=0.1,
            orient=tk.HORIZONTAL, length=180,
            command=self.callbacks['update_threshold'],
            bg='#f0f0f0', highlightbackground='#f0f0f0', showvalue=False
        )
        self.threshold_scale.set(self.state.detection.threshold)
        self.threshold_scale.pack(side=tk.LEFT, padx=3)

        self.threshold_label = tk.Label(
            threshold_frame, text=f"{self.state.detection.threshold:.1f}",
            font=('Arial', 9, 'bold'), bg='#f0f0f0'
        )
        self.threshold_label.pack(side=tk.LEFT)

    def _create_delay_section(self, parent: tk.Frame):
        """Cree la section de reglage des delais."""
        delay_frame = tk.Frame(parent, bg='#f0f0f0')
        delay_frame.pack(fill=tk.X, padx=5, pady=3)

        tk.Label(
            delay_frame, text="Min:",
            font=('Arial', 9), bg='#f0f0f0'
        ).pack(side=tk.LEFT)

        self.min_delay_scale = tk.Scale(
            delay_frame, from_=0, to=5, resolution=0.01,
            orient=tk.HORIZONTAL, length=80,
            command=self.callbacks['update_delays'],
            bg='#f0f0f0', highlightbackground='#f0f0f0', showvalue=False
        )
        self.min_delay_scale.set(self.state.detection.min_delay)
        self.min_delay_scale.pack(side=tk.LEFT, padx=2)

        tk.Label(
            delay_frame, text="Max:",
            font=('Arial', 9), bg='#f0f0f0'
        ).pack(side=tk.LEFT)

        self.max_delay_scale = tk.Scale(
            delay_frame, from_=0, to=10, resolution=0.01,
            orient=tk.HORIZONTAL, length=80,
            command=self.callbacks['update_delays'],
            bg='#f0f0f0', highlightbackground='#f0f0f0', showvalue=False
        )
        self.max_delay_scale.set(self.state.detection.max_delay)
        self.max_delay_scale.pack(side=tk.LEFT, padx=2)

        tk.Label(
            delay_frame, textvariable=self.delay_display_var,
            font=('Arial', 8), bg='#f0f0f0'
        ).pack(side=tk.LEFT, padx=5)

    def _create_inactivity_section(self, parent: tk.Frame):
        """Cree la section de reglage de l'inactivite."""
        inactivity_frame = tk.Frame(parent, bg='#f0f0f0')
        inactivity_frame.pack(fill=tk.X, padx=5, pady=3)

        tk.Label(
            inactivity_frame, text="Clic si inactif:",
            font=('Arial', 9), bg='#f0f0f0'
        ).pack(side=tk.LEFT)

        self.inactivity_scale = tk.Scale(
            inactivity_frame, from_=3, to=30, resolution=1,
            orient=tk.HORIZONTAL, length=120,
            command=self.callbacks['update_inactivity'],
            bg='#f0f0f0', highlightbackground='#f0f0f0', showvalue=False
        )
        self.inactivity_scale.set(self.state.inactivity.base_delay)
        self.inactivity_scale.pack(side=tk.LEFT, padx=3)

        self.inactivity_label = tk.Label(
            inactivity_frame,
            text=f"{self.state.inactivity.base_delay}s (+/-2s)",
            font=('Arial', 9, 'bold'), bg='#f0f0f0'
        )
        self.inactivity_label.pack(side=tk.LEFT)

    def _create_auto_cast_section(self, parent: tk.Frame):
        """Cree la section de reglage de l'auto-cast."""
        auto_cast_frame = tk.Frame(parent, bg='#f0f0f0')
        auto_cast_frame.pack(fill=tk.X, padx=5, pady=3)

        tk.Label(
            auto_cast_frame, text="Auto-cast si pas de prise:",
            font=('Arial', 9), bg='#f0f0f0'
        ).pack(side=tk.LEFT)

        self.auto_cast_scale = tk.Scale(
            auto_cast_frame, from_=5, to=60, resolution=1,
            orient=tk.HORIZONTAL, length=120,
            command=self.callbacks['update_auto_cast'],
            bg='#f0f0f0', highlightbackground='#f0f0f0', showvalue=False
        )
        self.auto_cast_scale.set(self.state.auto_cast.base_delay)
        self.auto_cast_scale.pack(side=tk.LEFT, padx=3)

        self.auto_cast_label = tk.Label(
            auto_cast_frame,
            text=f"{self.state.auto_cast.base_delay}s (+/-2s)",
            font=('Arial', 9, 'bold'), bg='#f0f0f0'
        )
        self.auto_cast_label.pack(side=tk.LEFT)

    def _create_stats_section(self, parent: tk.Frame):
        """Cree la section des statistiques."""
        stats_frame = tk.LabelFrame(
            parent, text="Statistiques",
            font=('Arial', 9, 'bold'), bg='#f0f0f0', padx=5, pady=3
        )
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=3)

        self.stats_text = tk.Text(
            stats_frame, height=8, width=50, bg='#ffffff',
            font=('Consolas', 8), relief=tk.FLAT, borderwidth=1
        )
        self.stats_text.pack(fill=tk.BOTH, expand=True)

    def _create_profiles_tab(self, notebook: ttk.Notebook):
        """Cree l'onglet des profils."""
        profiles_tab = tk.Frame(notebook, bg='#f0f0f0')
        notebook.add(profiles_tab, text="Profils")

        self.calibration_button = tk.Button(
            profiles_tab, text="AUTO-CALIBRATION",
            command=self.callbacks['start_calibration'],
            bg='#FF9800', fg='white', font=('Arial', 11, 'bold'),
            width=25, height=2
        )
        self.calibration_button.pack(pady=15)

        current_frame = tk.LabelFrame(
            profiles_tab, text="Profil Actuel",
            font=('Arial', 10, 'bold'), bg='#f0f0f0'
        )
        current_frame.pack(fill=tk.X, padx=10, pady=10)

        self.profile_label = tk.Label(
            current_frame, text="", font=('Arial', 9), bg='#f0f0f0'
        )
        self.profile_label.pack(pady=10)

        preset_frame = tk.LabelFrame(
            profiles_tab, text="Profils Predefinis",
            font=('Arial', 10, 'bold'), bg='#f0f0f0'
        )
        preset_frame.pack(fill=tk.X, padx=10, pady=10)

        preset_buttons = tk.Frame(preset_frame, bg='#f0f0f0')
        preset_buttons.pack(pady=10)

        presets = [
            ("Aleatoire", self.callbacks['generate_profile'], '#00BCD4'),
            ("Rapide", lambda: self.callbacks['set_preset']('fast'), '#8BC34A'),
            ("Normal", lambda: self.callbacks['set_preset']('normal'), '#3F51B5'),
            ("Lent", lambda: self.callbacks['set_preset']('slow'), '#795548')
        ]

        for text, command, color in presets:
            tk.Button(
                preset_buttons, text=text, command=command,
                bg=color, fg='white', width=12, height=2, font=('Arial', 9)
            ).pack(side=tk.LEFT, padx=5)

    def _create_options_tab(self, notebook: ttk.Notebook):
        """Cree l'onglet des options."""
        options_tab = tk.Frame(notebook, bg='#f0f0f0')
        notebook.add(options_tab, text="Options")

        display_frame = tk.LabelFrame(
            options_tab, text="Affichage",
            font=('Arial', 9, 'bold'), bg='#f0f0f0', padx=5, pady=5
        )
        display_frame.pack(fill=tk.X, padx=5, pady=5)

        display_grid = tk.Frame(display_frame, bg='#f0f0f0')
        display_grid.pack()

        options = [
            ("Delai", self.show_delay, 0, 0),
            ("Volume", self.show_volume, 0, 1),
            ("Compteur", self.show_click_counter, 1, 0),
            ("Taux", self.show_rate, 1, 1)
        ]

        for text, var, row, col in options:
            tk.Checkbutton(
                display_grid, text=text, variable=var, bg='#f0f0f0',
                command=self._sync_display_options
            ).grid(row=row, column=col, sticky='w')

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
        color_combo.bind('<<ComboboxSelected>>', lambda e: self._sync_display_options())

        action_frame = tk.Frame(options_tab, bg='#f0f0f0')
        action_frame.pack(fill=tk.X, padx=5, pady=10)

        boost_text = f"Boost: {'ON' if self.state.is_boost_mode else 'OFF'}"
        self.boost_button = tk.Button(
            action_frame, text=boost_text,
            command=self.callbacks['toggle_boost'], bg='#9C27B0', fg='white',
            width=15, height=2, font=('Arial', 9)
        )
        self.boost_button.pack(side=tk.LEFT, padx=10)

        tk.Button(
            action_frame, text="Reset Compteur",
            command=self.callbacks['reset_counter'], bg='#607D8B', fg='white',
            width=15, height=2, font=('Arial', 9)
        ).pack(side=tk.LEFT, padx=10)

    def _create_info_bar(self):
        """Cree la barre d'information en bas."""
        info_frame = tk.Frame(self.parent, bg='#e0e0e0', height=40)
        info_frame.pack(fill=tk.X, side=tk.BOTTOM)

        tk.Label(
            info_frame,
            text="F8: Pause | F9: Off | F10: Pause 15s | F11: Test",
            font=('Arial', 8), bg='#e0e0e0'
        ).pack(pady=0)

        tk.Label(
            info_frame,
            text="Auto-pause: E (inventaire) | T / : (chat) - si fenetre active",
            font=('Arial', 7), bg='#e0e0e0', fg='#666666'
        ).pack(pady=0)

    def _sync_display_options(self):
        """Synchronise les options d'affichage avec l'etat."""
        self.state.display.show_delay = self.show_delay.get()
        self.state.display.show_volume = self.show_volume.get()
        self.state.display.show_click_counter = self.show_click_counter.get()
        self.state.display.show_rate = self.show_rate.get()
        self.state.display.text_color = self.text_color_var.get()

        if 'save_config' in self.callbacks:
            self.callbacks['save_config']()

    def update_apps_list(self, apps: list):
        """Met a jour la liste des applications."""
        self.app_combo['values'] = apps

    def update_volume_display(self, level: float):
        """Met a jour l'affichage du niveau de volume."""
        self.current_level_var.set(f"Niveau: {level:.1f}")
        self.volume_graph.add_value(level)

    def update_threshold_display(self, value: float):
        """Met a jour l'affichage du seuil."""
        self.threshold_label.config(text=f"{value:.1f}")
        self.volume_graph.set_threshold(value)

    def update_delay_display(self, min_val: float, max_val: float):
        """Met a jour l'affichage des delais."""
        self.delay_display_var.set(f"{min_val:.2f} - {max_val:.2f}s")

    def update_inactivity_display(self, value: int):
        """Met a jour l'affichage de l'inactivite."""
        self.inactivity_label.config(text=f"{value}s (+/-2s)")

    def update_auto_cast_display(self, value: int):
        """Met a jour l'affichage de l'auto-cast."""
        self.auto_cast_label.config(text=f"{value}s (+/-2s)")

    def update_boost_button(self, is_boost: bool):
        """Met a jour le bouton boost."""
        self.boost_button.config(text=f"Boost: {'ON' if is_boost else 'OFF'}")
