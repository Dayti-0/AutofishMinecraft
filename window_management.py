"""
Module de gestion des fenêtres Windows.
Gère l'interaction avec les fenêtres des applications via l'API Windows.
"""

import logging
import psutil
import win32gui
import win32con
import win32process


def get_process_id_by_name(process_name: str) -> int:
    """
    Récupère le PID d'un processus à partir de son nom.

    Args:
        process_name: Nom du processus (ex: "javaw.exe").

    Returns:
        PID du processus ou None si non trouvé.
    """
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
            return proc.info['pid']
    return None


def is_application_in_foreground(pid: int) -> bool:
    """
    Vérifie si une application est au premier plan.

    Args:
        pid: PID du processus à vérifier.

    Returns:
        True si l'application est au premier plan, False sinon.
    """
    foreground_window = win32gui.GetForegroundWindow()
    _, foreground_pid = win32process.GetWindowThreadProcessId(foreground_window)
    return foreground_pid == pid


def get_hwnds_for_pid(pid: int) -> list:
    """
    Récupère les handles de fenêtre pour un PID donné.

    Args:
        pid: PID du processus.

    Returns:
        Liste des handles de fenêtre visibles et actifs.
    """
    def callback(hwnd, hwnds):
        if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
            _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
            if found_pid == pid:
                hwnds.append(hwnd)
        return True

    hwnds = []
    win32gui.EnumWindows(callback, hwnds)
    return hwnds


def bring_window_to_front(pid: int) -> bool:
    """
    Met la fenêtre d'une application au premier plan.

    Args:
        pid: PID du processus.

    Returns:
        True si réussi, False sinon.
    """
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


def get_window_rect(hwnd: int) -> tuple:
    """
    Récupère les dimensions client d'une fenêtre.

    Args:
        hwnd: Handle de la fenêtre.

    Returns:
        Tuple (left, top, right, bottom) des dimensions.
    """
    return win32gui.GetClientRect(hwnd)


def get_window_center(hwnd: int) -> tuple:
    """
    Calcule le centre d'une fenêtre.

    Args:
        hwnd: Handle de la fenêtre.

    Returns:
        Tuple (x, y) du centre de la fenêtre.
    """
    rect = get_window_rect(hwnd)
    center_x = (rect[2] - rect[0]) // 2
    center_y = (rect[3] - rect[1]) // 2
    return center_x, center_y
