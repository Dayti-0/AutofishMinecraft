"""
Module des composants UI personnalisés.
Contient les widgets graphiques réutilisables.
"""

import tkinter as tk
import collections
from typing import Optional


class VolumeGraphBar(tk.Canvas):
    """
    Widget graphique affichant l'historique du volume audio.

    Affiche une courbe de volume avec une ligne de seuil
    et un remplissage sous la courbe.
    """

    def __init__(
        self,
        master: Optional[tk.Widget] = None,
        width: int = 250,
        height: int = 120,
        history_size: int = 50,
        **kwargs
    ):
        """
        Initialise le graphique de volume.

        Args:
            master: Widget parent.
            width: Largeur du graphique.
            height: Hauteur du graphique.
            history_size: Nombre de valeurs à conserver.
            **kwargs: Arguments supplémentaires pour le Canvas.
        """
        super().__init__(master, **kwargs)
        self.configure(
            width=width,
            height=height,
            bg='white',
            highlightthickness=1
        )

        self._width = width
        self._height = height
        self._history_size = history_size
        self.history = collections.deque([0] * history_size, maxlen=history_size)
        self.threshold_value = 8.0

        # Couleurs
        self.line_color = '#4CAF50'
        self.fill_color = '#4CAF50'
        self.threshold_color = '#ff6666'
        self.grid_color = '#f0f0f0'

        self.draw()

    def add_value(self, value: float) -> None:
        """
        Ajoute une valeur à l'historique et redessine.

        Args:
            value: Valeur de volume (0-10).
        """
        self.history.append(value)
        self.draw()

    def set_threshold(self, threshold: float) -> None:
        """
        Définit le seuil et redessine.

        Args:
            threshold: Nouvelle valeur de seuil (0-10).
        """
        self.threshold_value = threshold
        self.draw()

    def draw(self) -> None:
        """Dessine le graphique complet."""
        self.delete("all")

        # Grille de fond
        self._draw_grid()

        # Ligne de seuil
        self._draw_threshold()

        # Courbe de volume
        self._draw_volume_curve()

    def _draw_grid(self) -> None:
        """Dessine la grille de fond."""
        grid_spacing = self._height // 5
        for i in range(5):
            y = i * grid_spacing
            self.create_line(
                0, y, self._width, y,
                fill=self.grid_color,
                width=1
            )

    def _draw_threshold(self) -> None:
        """Dessine la ligne de seuil."""
        threshold_y = self._height - (self.threshold_value * self._height / 10)
        self.create_line(
            0, threshold_y, self._width, threshold_y,
            fill=self.threshold_color,
            width=2,
            dash=(5, 2)
        )

    def _draw_volume_curve(self) -> None:
        """Dessine la courbe de volume."""
        if len(self.history) < 2:
            return

        # Calculer les points
        points = []
        point_spacing = self._width / (self._history_size - 1)

        for i, value in enumerate(self.history):
            x = i * point_spacing
            y = self._height - (value * self._height / 10)
            points.extend([x, y])

        if len(points) < 4:
            return

        # Courbe principale
        self.create_line(
            points,
            fill=self.line_color,
            width=2,
            smooth=True
        )

        # Zone de remplissage sous la courbe
        fill_points = [0, self._height] + points + [self._width, self._height]
        self.create_polygon(
            fill_points,
            fill=self.fill_color,
            stipple='gray50',
            outline=''
        )

    def clear(self) -> None:
        """Efface l'historique."""
        self.history = collections.deque(
            [0] * self._history_size,
            maxlen=self._history_size
        )
        self.draw()

    def set_colors(
        self,
        line_color: Optional[str] = None,
        fill_color: Optional[str] = None,
        threshold_color: Optional[str] = None
    ) -> None:
        """
        Définit les couleurs du graphique.

        Args:
            line_color: Couleur de la courbe.
            fill_color: Couleur de remplissage.
            threshold_color: Couleur de la ligne de seuil.
        """
        if line_color:
            self.line_color = line_color
        if fill_color:
            self.fill_color = fill_color
        if threshold_color:
            self.threshold_color = threshold_color
        self.draw()


class PixelIndicator(tk.Toplevel):
    """
    Indicateur visuel de statut sous forme de carré coloré.

    Reste toujours au premier plan et peut être cliqué.
    """

    # Couleurs de statut
    COLORS = {
        'active': 'green',
        'paused': 'red',
        'temp_pause': 'orange',
        'disabled': 'grey'
    }

    def __init__(
        self,
        master: tk.Widget,
        size: int = 20,
        position: tuple = (5, 5),
        on_click: Optional[callable] = None
    ):
        """
        Initialise l'indicateur.

        Args:
            master: Widget parent.
            size: Taille du carré en pixels.
            position: Position (x, y) sur l'écran.
            on_click: Fonction appelée lors d'un clic.
        """
        super().__init__(master)

        self._size = size
        self._position = position
        self._on_click = on_click
        self._current_status = 'paused'
        self._keep_on_top_job = None

        # Configuration de la fenêtre
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.8)
        self.geometry(f"{size}x{size}+{position[0]}+{position[1]}")
        self.configure(bg=self.COLORS['paused'])

        # Bind du clic
        if on_click:
            self.bind("<Button-1>", lambda e: on_click())

        # Démarrer le maintien au premier plan
        self._keep_on_top()

    def set_status(self, status: str) -> None:
        """
        Change le statut et la couleur de l'indicateur.

        Args:
            status: Un de 'active', 'paused', 'temp_pause', 'disabled'.
        """
        if status in self.COLORS:
            self._current_status = status
            self.configure(bg=self.COLORS[status])

    def get_status(self) -> str:
        """
        Obtient le statut actuel.

        Returns:
            Statut actuel.
        """
        return self._current_status

    def _keep_on_top(self) -> None:
        """Force l'indicateur à rester au premier plan."""
        if self.winfo_exists():
            self.attributes("-topmost", True)
            self.lift()
            self._keep_on_top_job = self.after(1000, self._keep_on_top)

    def destroy(self) -> None:
        """Détruit l'indicateur proprement."""
        if self._keep_on_top_job:
            self.after_cancel(self._keep_on_top_job)
        super().destroy()


class TransparentLabel(tk.Toplevel):
    """
    Label flottant avec fond transparent.

    Utilisé pour afficher des informations en overlay.
    """

    def __init__(
        self,
        master: tk.Widget,
        text_var: tk.StringVar,
        position: tuple = (30, 5),
        font: tuple = ('Arial', 11, 'bold'),
        fg_color: str = 'lime'
    ):
        """
        Initialise le label transparent.

        Args:
            master: Widget parent.
            text_var: Variable StringVar liée au texte.
            position: Position (x, y) sur l'écran.
            font: Police de caractères.
            fg_color: Couleur du texte.
        """
        super().__init__(master)

        self._position = position
        self._keep_on_top_job = None

        # Configuration de la fenêtre
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 1.0)
        self.geometry(f"+{position[0]}+{position[1]}")

        # Rendre le fond transparent
        self.attributes('-transparentcolor', 'black')
        self.configure(bg='black')

        # Créer le label
        self.label = tk.Label(
            self,
            textvariable=text_var,
            font=font,
            bg='black',
            fg=fg_color
        )
        self.label.pack()

        # Démarrer le maintien au premier plan
        self._keep_on_top()

    def set_color(self, color: str) -> None:
        """
        Change la couleur du texte.

        Args:
            color: Nouvelle couleur.
        """
        self.label.config(fg=color)

    def _keep_on_top(self) -> None:
        """Force le label à rester au premier plan."""
        if self.winfo_exists():
            self.attributes("-topmost", True)
            self.lift()
            self._keep_on_top_job = self.after(1000, self._keep_on_top)

    def destroy(self) -> None:
        """Détruit le label proprement."""
        if self._keep_on_top_job:
            self.after_cancel(self._keep_on_top_job)
        super().destroy()


# Mapping des couleurs françaises vers les couleurs tkinter
COLORS_MAP = {
    "Rouge": "red",
    "Vert": "green",
    "Bleu": "blue",
    "Orange": "orange",
    "Violet": "purple",
    "Cyan": "cyan",
    "Rose": "magenta",
    "Jaune": "yellow",
    "Vert clair": "lime",
    "Marron": "brown",
    "Gris": "grey",
    "Blanc": "white"
}


def get_color_list() -> list:
    """
    Obtient la liste des noms de couleurs disponibles.

    Returns:
        Liste des noms de couleurs en français.
    """
    return list(COLORS_MAP.keys())


def translate_color(french_name: str) -> str:
    """
    Traduit un nom de couleur français en nom tkinter.

    Args:
        french_name: Nom de la couleur en français.

    Returns:
        Nom de la couleur pour tkinter.
    """
    return COLORS_MAP.get(french_name, "lime")
