"""
AutoFish Minecraft - Gestionnaire des fenetres overlay.
"""

import tkinter as tk
from typing import Optional, Callable, TYPE_CHECKING

from .ui_components import translate_color

if TYPE_CHECKING:
    from .app_state import AppState


class OverlayManager:
    """
    Gere les fenetres overlay (indicateur et affichage texte).

    Les overlays restent toujours au premier plan pour afficher
    l'etat de l'application.
    """

    def __init__(self, parent: tk.Tk, state: 'AppState', on_indicator_click: Callable):
        """
        Initialise le gestionnaire d'overlays.

        Args:
            parent: Fenetre parente Tkinter
            state: Etat de l'application
            on_indicator_click: Callback lors du clic sur l'indicateur
        """
        self.parent = parent
        self.state = state
        self.on_indicator_click = on_indicator_click

        # Variables Tkinter
        self.delay_label_var = tk.StringVar(value="Ready")

        # Fenetres
        self.indicator_window: Optional[tk.Toplevel] = None
        self.delay_label_window: Optional[tk.Toplevel] = None
        self.delay_label: Optional[tk.Label] = None

    def create(self):
        """Cree les fenetres overlay."""
        self._create_indicator()
        self._create_delay_label()

    def _create_indicator(self):
        """Cree l'indicateur de couleur."""
        self.indicator_window = tk.Toplevel(self.parent)
        self.indicator_window.overrideredirect(True)
        self.indicator_window.attributes("-topmost", True)
        self.indicator_window.attributes("-alpha", 0.8)
        self.indicator_window.geometry("20x20+5+5")
        self.indicator_window.configure(bg="red")
        self.indicator_window.bind("<Button-1>", lambda e: self.on_indicator_click())
        self._keep_indicator_on_top()

    def _create_delay_label(self):
        """Cree le label d'affichage transparent."""
        self.delay_label_window = tk.Toplevel(self.parent)
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
            fg=translate_color(self.state.display.text_color)
        )
        self.delay_label.pack()
        self._keep_text_on_top()

    def _keep_indicator_on_top(self):
        """Maintient l'indicateur au premier plan."""
        if self.indicator_window and self.indicator_window.winfo_exists():
            self.indicator_window.attributes("-topmost", True)
            self.indicator_window.lift()
            self.parent.after(1000, self._keep_indicator_on_top)

    def _keep_text_on_top(self):
        """Maintient le texte au premier plan."""
        if self.delay_label_window and self.delay_label_window.winfo_exists():
            self.delay_label_window.attributes("-topmost", True)
            self.delay_label_window.lift()
            self.parent.after(1000, self._keep_text_on_top)

    def update_indicator_color(self):
        """Met a jour la couleur de l'indicateur selon l'etat."""
        if self.state.is_completely_disabled:
            color = "grey"
        elif self.state.temp_pause_remaining > 0:
            color = "orange"
        elif self.state.is_paused:
            color = "red"
        elif self.state.is_inventory_open or self.state.is_chat_open:
            color = "#FFD700"  # Or/Jaune pour auto-pause
        else:
            color = "green"

        if self.indicator_window:
            self.indicator_window.configure(bg=color)

    def update_delay_text(self, text: str):
        """Met a jour le texte d'affichage."""
        self.delay_label_var.set(text)
        if self.delay_label:
            self.delay_label.config(fg=translate_color(self.state.display.text_color))

    def update_text_color(self):
        """Met a jour la couleur du texte."""
        if self.delay_label:
            self.delay_label.config(fg=translate_color(self.state.display.text_color))

    def destroy(self):
        """Detruit les fenetres overlay."""
        if self.indicator_window:
            self.indicator_window.destroy()
        if self.delay_label_window:
            self.delay_label_window.destroy()
