"""
Pannello di controllo per la configurazione e gestione della simulazione.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional
import math

from config.settings import (
    SimulationConfig,
    RoutingAlgorithm,
    ConflictResolution,
    TrafficPattern,
)


class ControlPanel(tk.Frame):
    """Pannello di controllo della simulazione."""

    def __init__(self, parent, on_start: Callable, on_stop: Callable,
                 on_step: Callable, on_reset: Callable,
                 on_config_change: Callable, **kwargs):
        super().__init__(parent, **kwargs)

        self._on_start = on_start
        self._on_stop = on_stop
        self._on_step = on_step
        self._on_reset = on_reset
        self._on_config_change = on_config_change

        self.configure(bg="#181825", padx=10, pady=10)

        self._build_ui()

    def _build_ui(self):
        """Costruisce l'interfaccia del pannello di controllo."""
        # Stile
        style = ttk.Style()
        style.configure("Control.TLabelframe", background="#181825", foreground="#cdd6f4")
        style.configure("Control.TLabelframe.Label", background="#181825", foreground="#cdd6f4")
        style.configure("Control.TLabel", background="#181825", foreground="#cdd6f4")
        style.configure("Control.TButton", padding=5)
        style.configure("Control.TScale", background="#181825")

        # === Sezione: Parametri di Rete ===
        network_frame = ttk.LabelFrame(
            self, text="⚙️ Parametri di Rete", style="Control.TLabelframe", padding=10
        )
        network_frame.pack(fill=tk.X, pady=(0, 10))

        # Numero di ingressi
        ttk.Label(network_frame, text="Dimensione rete (N):", style="Control.TLabel").grid(
            row=0, column=0, sticky="w", pady=2
        )
        self.var_num_inputs = tk.StringVar(value="8")
        self.combo_num_inputs = ttk.Combobox(
            network_frame,
            textvariable=self.var_num_inputs,
            values=["4", "8", "16", "32", "64"],
            state="readonly",
            width=10,
        )
        self.combo_num_inputs.grid(row=0, column=1, sticky="e", pady=2, padx=(10, 0))

        # Info stadi
        self.var_stages_info = tk.StringVar(value="Stadi: 3")
        ttk.Label(network_frame, textvariable=self.var_stages_info, style="Control.TLabel").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=2
        )
        self.combo_num_inputs.bind("<<ComboboxSelected>>", self._on_network_size_change)

        # === Sezione: Parametri di Traffico ===
        traffic_frame = ttk.LabelFrame(
            self, text="📡 Traffico", style="Control.TLabelframe", padding=10
        )
        traffic_frame.pack(fill=tk.X, pady=(0, 10))

        # Pattern di traffico
        ttk.Label(traffic_frame, text="Pattern:", style="Control.TLabel").grid(
            row=0, column=0, sticky="w", pady=2
        )
        self.var_traffic_pattern = tk.StringVar(value="uniform")
        self.combo_traffic = ttk.Combobox(
            traffic_frame,
            textvariable=self.var_traffic_pattern,
            values=[p.value for p in TrafficPattern if p != TrafficPattern.CUSTOM],
            state="readonly",
            width=15,
        )
        self.combo_traffic.grid(row=0, column=1, sticky="e", pady=2, padx=(10, 0))
        self.combo_traffic.bind("<<ComboboxSelected>>", self._on_traffic_change)

        # Tasso di generazione
        ttk.Label(traffic_frame, text="Tasso generazione:", style="Control.TLabel").grid(
            row=1, column=0, sticky="w", pady=2
        )
        self.var_gen_rate = tk.DoubleVar(value=0.5)
        self.scale_gen_rate = ttk.Scale(
            traffic_frame,
            from_=0.0,
            to=1.0,
            variable=self.var_gen_rate,
            orient=tk.HORIZONTAL,
            length=120,
            command=self._on_rate_change,
        )
        self.scale_gen_rate.grid(row=1, column=1, sticky="e", pady=2, padx=(10, 0))

        self.var_rate_label = tk.StringVar(value="0.50")
        ttk.Label(traffic_frame, textvariable=self.var_rate_label, style="Control.TLabel").grid(
            row=2, column=1, sticky="e", pady=0
        )

        # Hotspot destination (visibile solo per pattern hotspot)
        self.hotspot_frame = tk.Frame(traffic_frame, bg="#181825")
        ttk.Label(self.hotspot_frame, text="Hotspot dest:", style="Control.TLabel").pack(side=tk.LEFT)
        self.var_hotspot_dest = tk.StringVar(value="0")
        self.entry_hotspot = ttk.Entry(self.hotspot_frame, textvariable=self.var_hotspot_dest, width=5)
        self.entry_hotspot.pack(side=tk.LEFT, padx=(10, 0))

        ttk.Label(self.hotspot_frame, text="Frazione:", style="Control.TLabel").pack(side=tk.LEFT, padx=(10, 0))
        self.var_hotspot_frac = tk.StringVar(value="0.3")
        self.entry_hotspot_frac = ttk.Entry(self.hotspot_frame, textvariable=self.var_hotspot_frac, width=5)
        self.entry_hotspot_frac.pack(side=tk.LEFT, padx=(10, 0))

        # === Sezione: Risoluzione Conflitti ===
        conflict_frame = ttk.LabelFrame(
            self, text="⚡ Conflitti", style="Control.TLabelframe", padding=10
        )
        conflict_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(conflict_frame, text="Strategia:", style="Control.TLabel").grid(
            row=0, column=0, sticky="w", pady=2
        )
        self.var_conflict_res = tk.StringVar(value="drop")
        self.combo_conflict = ttk.Combobox(
            conflict_frame,
            textvariable=self.var_conflict_res,
            values=[c.value for c in ConflictResolution],
            state="readonly",
            width=15,
        )
        self.combo_conflict.grid(row=0, column=1, sticky="e", pady=2, padx=(10, 0))
        self.combo_conflict.bind("<<ComboboxSelected>>", self._on_conflict_change)

        # Buffer size (visibile solo per strategia buffer)
        self.buffer_frame = tk.Frame(conflict_frame, bg="#181825")
        ttk.Label(self.buffer_frame, text="Dim. buffer:", style="Control.TLabel").pack(side=tk.LEFT)
        self.var_buffer_size = tk.StringVar(value="4")
        self.entry_buffer = ttk.Entry(self.buffer_frame, textvariable=self.var_buffer_size, width=5)
        self.entry_buffer.pack(side=tk.LEFT, padx=(10, 0))

        # === Sezione: Simulazione ===
        sim_frame = ttk.LabelFrame(
            self, text="🎮 Simulazione", style="Control.TLabelframe", padding=10
        )
        sim_frame.pack(fill=tk.X, pady=(0, 10))

        # Numero cicli
        ttk.Label(sim_frame, text="Cicli:", style="Control.TLabel").grid(
            row=0, column=0, sticky="w", pady=2
        )
        self.var_num_cycles = tk.StringVar(value="1000")
        self.entry_cycles = ttk.Entry(sim_frame, textvariable=self.var_num_cycles, width=10)
        self.entry_cycles.grid(row=0, column=1, sticky="e", pady=2, padx=(10, 0))

        # Velocità animazione
        ttk.Label(sim_frame, text="Velocità (ms):", style="Control.TLabel").grid(
            row=1, column=0, sticky="w", pady=2
        )
        self.var_anim_speed = tk.IntVar(value=100)
        self.scale_speed = ttk.Scale(
            sim_frame,
            from_=10,
            to=1000,
            variable=self.var_anim_speed,
            orient=tk.HORIZONTAL,
            length=120,
        )
        self.scale_speed.grid(row=1, column=1, sticky="e", pady=2, padx=(10, 0))

        # === Pulsanti di Controllo ===
        btn_frame = tk.Frame(self, bg="#181825")
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        self.btn_start = ttk.Button(btn_frame, text="▶ Avvia", command=self._on_start_click)
        self.btn_start.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_step = ttk.Button(btn_frame, text="⏭ Step", command=self._on_step_click)
        self.btn_step.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_stop = ttk.Button(btn_frame, text="⏸ Pausa", command=self._on_stop_click, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_reset = ttk.Button(btn_frame, text="🔄 Reset", command=self._on_reset_click)
        self.btn_reset.pack(side=tk.LEFT, padx=(0, 5))

        # === Status Bar ===
        self.status_frame = tk.Frame(self, bg="#181825")
        self.status_frame.pack(fill=tk.X, pady=(10, 0))

        self.var_status = tk.StringVar(value="⏹ Pronto")
        self.lbl_status = ttk.Label(
            self.status_frame, textvariable=self.var_status,
            style="Control.TLabel", font=("Consolas", 10, "bold")
        )
        self.lbl_status.pack(anchor="w")

        self.var_cycle_info = tk.StringVar(value="Ciclo: 0 / 1000")
        ttk.Label(
            self.status_frame, textvariable=self.var_cycle_info, style="Control.TLabel"
        ).pack(anchor="w")

        # Progress bar
        self.progress = ttk.Progressbar(self.status_frame, length=200, mode="determinate")
        self.progress.pack(fill=tk.X, pady=(5, 0))

    def _on_network_size_change(self, event=None):
        """Gestisce il cambio di dimensione della rete."""
        n = int(self.var_num_inputs.get())
        stages = int(math.log2(n))
        self.var_stages_info.set(f"Stadi: {stages} | Switch/stadio: {n // 2}")

    def _on_traffic_change(self, event=None):
        """Gestisce il cambio di pattern di traffico."""
        pattern = self.var_traffic_pattern.get()
        if pattern == "hotspot":
            self.hotspot_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        else:
            self.hotspot_frame.grid_forget()

    def _on_conflict_change(self, event=None):
        """Gestisce il cambio di strategia di risoluzione conflitti."""
        strategy = self.var_conflict_res.get()
        if strategy == "buffer":
            self.buffer_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        else:
            self.buffer_frame.grid_forget()

    def _on_rate_change(self, value=None):
        """Aggiorna l'etichetta del tasso di generazione."""
        self.var_rate_label.set(f"{self.var_gen_rate.get():.2f}")

    def _on_start_click(self):
        """Gestisce il click su Avvia."""
        self.btn_start.configure(state=tk.DISABLED)
        self.btn_stop.configure(state=tk.NORMAL)
        self.btn_step.configure(state=tk.DISABLED)
        self.var_status.set("▶ In esecuzione...")
        self._on_start()

        def _on_stop_click(self):
        """Gestisce il click su Pausa."""
        self.btn_start.configure(state=tk.NORMAL)
        self.btn_stop.configure(state=tk.DISABLED)
        self.btn_step.configure(state=tk.NORMAL)
        self.var_status.set("⏸ In pausa")
        self._on_stop()

    def _on_step_click(self):
        """Gestisce il click su Step."""
        self.var_status.set("⏭ Step singolo")
        self._on_step()

    def _on_reset_click(self):
        """Gestisce il click su Reset."""
        self.btn_start.configure(state=tk.NORMAL)
        self.btn_stop.configure(state=tk.DISABLED)
        self.btn_step.configure(state=tk.NORMAL)
        self.var_status.set("⏹ Pronto")
        self.var_cycle_info.set("Ciclo: 0 / " + self.var_num_cycles.get())
        self.progress["value"] = 0
        self._on_reset()

    def get_config(self) -> SimulationConfig:
        """Costruisce un oggetto SimulationConfig dai valori correnti del pannello."""
        try:
            num_inputs = int(self.var_num_inputs.get())
            num_cycles = int(self.var_num_cycles.get())
            gen_rate = self.var_gen_rate.get()
            traffic_pattern = TrafficPattern(self.var_traffic_pattern.get())
            conflict_res = ConflictResolution(self.var_conflict_res.get())
            buffer_size = int(self.var_buffer_size.get())
            hotspot_dest = int(self.var_hotspot_dest.get())
            hotspot_frac = float(self.var_hotspot_frac.get())
            anim_speed = self.var_anim_speed.get()

            config = SimulationConfig(
                num_inputs=num_inputs,
                num_cycles=num_cycles,
                packet_generation_rate=gen_rate,
                traffic_pattern=traffic_pattern,
                conflict_resolution=conflict_res,
                buffer_size=buffer_size,
                hotspot_destination=hotspot_dest,
                hotspot_fraction=hotspot_frac,
                animation_speed_ms=anim_speed,
            )
            return config

        except (ValueError, TypeError) as e:
            messagebox.showerror(
                "Errore di Configurazione",
                f"Parametri non validi:\n{str(e)}"
            )
            return None

    def update_progress(self, current_cycle: int, total_cycles: int):
        """Aggiorna la barra di progresso e le informazioni sul ciclo."""
        self.var_cycle_info.set(f"Ciclo: {current_cycle} / {total_cycles}")
        progress_pct = (current_cycle / total_cycles * 100) if total_cycles > 0 else 0
        self.progress["value"] = progress_pct

    def mark_simulation_complete(self):
        """Segna la simulazione come completata."""
        self.btn_start.configure(state=tk.NORMAL)
        self.btn_stop.configure(state=tk.DISABLED)
        self.btn_step.configure(state=tk.NORMAL)
        self.var_status.set("✅ Simulazione completata")

    def set_controls_enabled(self, enabled: bool):
        """Abilita/disabilita i controlli di configurazione."""
        state = tk.NORMAL if enabled else tk.DISABLED
        self.combo_num_inputs.configure(state="readonly" if enabled else tk.DISABLED)
        self.combo_traffic.configure(state="readonly" if enabled else tk.DISABLED)
        self.combo_conflict.configure(state="readonly" if enabled else tk.DISABLED)
        self.entry_cycles.configure(state=state)