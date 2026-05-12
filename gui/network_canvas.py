"""
Canvas per la visualizzazione grafica della rete Banyan.
"""
import tkinter as tk
from tkinter import Canvas
from typing import List, Dict, Optional, Tuple
import math


class NetworkCanvas(tk.Frame):
    """Widget per la visualizzazione della topologia della rete Banyan."""

    # Colori
    COLORS = {
        "background": "#1e1e2e",
        "switch_idle": "#45475a",
        "switch_active": "#89b4fa",
        "switch_conflict": "#f38ba8",
        "switch_border": "#cdd6f4",
        "connection": "#585b70",
        "connection_active": "#a6e3a1",
        "packet_transit": "#f9e2af",
        "packet_delivered": "#a6e3