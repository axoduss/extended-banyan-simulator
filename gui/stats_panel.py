"""
Pannello delle statistiche e grafici della simulazione.
"""
import tkinter as tk
from tkinter import ttk
from typing import List, Optional
import math

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from core.metrics import AggregateMetrics, MetricsCollector


class StatsPanel(tk.Frame):
    """Pannello per la visualizzazione delle statistiche e dei grafici."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(bg="#181825")

        self._metrics_collector: Optional[MetricsCollector] = None
        self._aggregate_metrics: Optional[AggregateMetrics] = None

        self._build_ui()

    def _build_ui(self):
        """Costruisce l'interfaccia del pannello statistiche."""
        # Notebook con tab
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Tab 1: Metriche in tempo reale
        self.realtime_frame = tk.Frame(self.notebook, bg="#181825")
        self.notebook.add(self.realtime_frame, text="📊 Tempo Reale")

        # Tab 2: Grafici
        self.charts_frame = tk.Frame(self.notebook, bg="#181825")
        self.notebook.add(self.charts_frame, text="📈 Grafici")

        # Tab 3: Dettaglio Switch
        self.switch_frame = tk.Frame(self.notebook, bg="#181825")
        self.notebook.add(self.switch_frame, text="🔲 Switch")

        # Tab 4: Riepilogo Finale
        self.summary_frame = tk.Frame(self.notebook, bg="#181825")
        self.notebook.add(self.summary_frame, text="📋 Riepilogo")

        # Costruisci contenuto tab
        self._build_realtime_tab()
        self._build_charts_tab()
        self._build_switch_tab()
        self._build_summary_tab()

    def _build_realtime_tab(self):
        """Costruisce il tab delle metriche in tempo reale."""
        # Frame con griglia di metriche
        metrics_grid = tk.Frame(self.realtime_frame, bg="#181825")
        metrics_grid.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.realtime_vars = {}
        metrics_definitions = [
            ("cycle", "Ciclo Corrente", "0"),
            ("throughput", "Throughput", "0.000"),
            ("avg_latency", "Latenza Media", "0.00"),
            ("packets_generated", "Pacchetti Generati", "0"),
            ("packets_delivered", "Pacchetti Consegnati", "0"),
            ("packets_dropped", "Pacchetti Scartati", "0"),
            ("packets_in_transit", "In Transito", "0"),
            ("packets_buffered", "Bufferizzati", "0"),
            ("conflicts", "Conflitti (ciclo)", "0"),
            ("total_conflicts", "Conflitti Totali", "0"),
            ("delivery_rate", "Tasso Consegna", "0.00%"),
            ("drop_rate", "Tasso Scarto", "0.00%"),
        ]

        for idx, (key, label, default) in enumerate(metrics_definitions):
            row = idx // 3
            col = idx % 3

            cell_frame = tk.Frame(metrics_grid, bg="#1e1e2e", padx=10, pady=8,
                                  highlightbackground="#313244", highlightthickness=1)
            cell_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

            tk.Label(
                cell_frame, text=label, bg="#1e1e2e", fg="#a6adc8",
                font=("Segoe UI", 9)
            ).pack(anchor="w")

            var = tk.StringVar(value=default)
            self.realtime_vars[key] = var
            tk.Label(
                cell_frame, textvariable=var, bg="#1e1e2e", fg="#cdd6f4",
                font=("Consolas", 14, "bold")
            ).pack(anchor="w")

        # Configura griglia
        for col in range(3):
            metrics_grid.grid_columnconfigure(col, weight=1)

    def _build_charts_tab(self):
        """Costruisce il tab dei grafici."""
        if not HAS_MATPLOTLIB:
            tk.Label(
                self.charts_frame,
                text="⚠️ matplotlib non disponibile.\nInstalla con: pip install matplotlib",
                bg="#181825", fg="#f38ba8", font=("Segoe UI", 12)
            ).pack(expand=True)
            return

        # Figura matplotlib con 4 subplot
        self.fig = Figure(figsize=(10, 6), dpi=80, facecolor="#181825")
        self.fig.subplots_adjust(hspace=0.4, wspace=0.3)

        # Subplot
        self.ax_throughput = self.fig.add_subplot(2, 2, 1)
        self.ax_latency = self.fig.add_subplot(2, 2, 2)
        self.ax_conflicts = self.fig.add_subplot(2, 2, 3)
        self.ax_delivery = self.fig.add_subplot(2, 2, 4)

        self._style_axes()

        # Canvas matplotlib in tkinter
        self.chart_canvas = FigureCanvasTkAgg(self.fig, master=self.charts_frame)
        self.chart_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Pulsante refresh
        btn_frame = tk.Frame(self.charts_frame, bg="#181825")
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(btn_frame, text="🔄 Aggiorna Grafici", command=self.refresh_charts).pack(side=tk.RIGHT)

    def _style_axes(self):
        """Applica lo stile scuro agli assi."""
        for ax in [self.ax_throughput, self.ax_latency, self.ax_conflicts, self.ax_delivery]:
            ax.set_facecolor("#1e1e2e")
            ax.tick_params(colors="#a6adc8", labelsize=8)
            ax.spines["bottom"].set_color("#585b70")
            ax.spines["top"].set_color("#585b70")
            ax.spines["left"].set_color("#585b70")
            ax.spines["right"].set_color("#585b70")
            ax.xaxis.label.set_color("#a6adc8")
            ax.yaxis.label.set_color("#a6adc8")
            ax.title.set_color("#cdd6f4")

        self.ax_throughput.set_title("Throughput", fontsize=10)
        self.ax_throughput.set_xlabel("Ciclo")
        self.ax_throughput.set_ylabel("Throughput")

        self.ax_latency.set_title("Latenza Media", fontsize=10)
        self.ax_latency.set_xlabel("Ciclo")
        self.ax_latency.set_ylabel("Cicli")

        self.ax_conflicts.set_title("Conflitti per Ciclo", fontsize=10)
        self.ax_conflicts.set_xlabel("Ciclo")
        self.ax_conflicts.set_ylabel("Conflitti")

        self.ax_delivery.set_title("Consegne per Ciclo", fontsize=10)
        self.ax_delivery.set_xlabel("Ciclo")
        self.ax_delivery.set_ylabel("Pacchetti")

    def _build_switch_tab(self):
        """Costruisce il tab con i dettagli degli switch."""
        # Treeview per i dati degli switch
        columns = ("stage", "position", "processed", "conflicts", "dropped",
                   "buffered", "utilization", "conflict_rate")
        
        self.switch_tree = ttk.Treeview(
            self.switch_frame, columns=columns, show="headings", height=15
        )

        headers = {
            "stage": "Stadio",
            "position": "Posizione",
            "processed": "Processati",
            "conflicts": "Conflitti",
            "dropped": "Scartati",
            "buffered": "Bufferizzati",
            "utilization": "Utilizzo %",
            "conflict_rate": "Tasso Conflitti",
        }

        for col, header in headers.items():
            self.switch_tree.heading(col, text=header)
            self.switch_tree.column(col, width=90, anchor="center")

        # Scrollbar
        scrollbar = ttk.Scrollbar(self.switch_frame, orient=tk.VERTICAL,
                                  command=self.switch_tree.yview)
        self.switch_tree.configure(yscrollcommand=scrollbar.set)

        self.switch_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10, padx=(0, 10))

    def _build_summary_tab(self):
        """Costruisce il tab del riepilogo finale."""
        self.summary_text = tk.Text(
            self.summary_frame,
            bg="#1e1e2e",
            fg="#cdd6f4",
            font=("Consolas", 10),
            wrap=tk.WORD,
            padx=15,
            pady=15,
            state=tk.DISABLED,
        )
        self.summary_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def set_metrics_collector(self, collector: MetricsCollector):
        """Imposta il collector delle metriche."""
        self._metrics_collector = collector

    def update_realtime(self, cycle_data: dict):
        """Aggiorna le metriche in tempo reale."""
        for key, value in cycle_data.items():
            if key in self.realtime_vars:
                self.realtime_vars[key].set(str(value))

        def refresh_charts(self):
        """Aggiorna i grafici con i dati correnti."""
        if not HAS_MATPLOTLIB or self._metrics_collector is None:
            return

        # Pulisci assi
        for ax in [self.ax_throughput, self.ax_latency, self.ax_conflicts, self.ax_delivery]:
            ax.clear()

        self._style_axes()

        # Dati
        throughput_data = self._metrics_collector.get_throughput_series()
        latency_data = self._metrics_collector.get_latency_series()
        conflict_data = self._metrics_collector.get_conflict_series()
        delivery_data = self._metrics_collector.get_delivery_series()

        # Throughput
        if throughput_data:
            window = max(1, min(50, len(throughput_data) // 5))
            smoothed = self._moving_average(throughput_data, window)
            self.ax_throughput.plot(
                smoothed, color="#89b4fa", linewidth=1.2, label="Throughput"
            )
            self.ax_throughput.axhline(
                y=sum(throughput_data) / len(throughput_data),
                color="#f9e2af", linestyle="--", linewidth=0.8, label="Media"
            )
            self.ax_throughput.legend(fontsize=7, facecolor="#1e1e2e",
                                     edgecolor="#585b70", labelcolor="#cdd6f4")
            self.ax_throughput.set_ylim(bottom=0)

        # Latenza
        if latency_data:
            window = max(1, min(50, len(latency_data) // 5))
            smoothed = self._moving_average(latency_data, window)
            self.ax_latency.plot(
                smoothed, color="#a6e3a1", linewidth=1.2, label="Latenza Media"
            )
            self.ax_latency.legend(fontsize=7, facecolor="#1e1e2e",
                                   edgecolor="#585b70", labelcolor="#cdd6f4")
            self.ax_latency.set_ylim(bottom=0)

        # Conflitti
        if conflict_data:
            window = max(1, min(50, len(conflict_data) // 5))
            smoothed = self._moving_average(conflict_data, window)
            self.ax_conflicts.plot(
                smoothed, color="#f38ba8", linewidth=1.2, label="Conflitti"
            )
            self.ax_conflicts.fill_between(
                range(len(smoothed)), smoothed, alpha=0.2, color="#f38ba8"
            )
            self.ax_conflicts.legend(fontsize=7, facecolor="#1e1e2e",
                                     edgecolor="#585b70", labelcolor="#cdd6f4")
            self.ax_conflicts.set_ylim(bottom=0)

        # Consegne
        if delivery_data:
            window = max(1, min(50, len(delivery_data) // 5))
            smoothed = self._moving_average(delivery_data, window)
            self.ax_delivery.plot(
                smoothed, color="#cba6f7", linewidth=1.2, label="Consegne"
            )
            self.ax_delivery.legend(fontsize=7, facecolor="#1e1e2e",
                                    edgecolor="#585b70", labelcolor="#cdd6f4")
            self.ax_delivery.set_ylim(bottom=0)

        self.fig.tight_layout(pad=2.0)
        self.chart_canvas.draw()

    def update_switch_table(self, switch_stats: List[List[dict]]):
        """Aggiorna la tabella degli switch."""
        # Pulisci tabella
        for item in self.switch_tree.get_children():
            self.switch_tree.delete(item)

        # Popola
        for stage_stats in switch_stats:
            for sw_stat in stage_stats:
                self.switch_tree.insert("", tk.END, values=(
                    sw_stat["stage"],
                    sw_stat["position"],
                    sw_stat["packets_processed"],
                    sw_stat["conflicts"],
                    sw_stat["packets_dropped"],
                    sw_stat["packets_buffered"],
                    f"{sw_stat['utilization'] * 100:.1f}%",
                    f"{sw_stat['conflict_rate']:.3f}",
                ))

    def update_summary(self, metrics: AggregateMetrics):
        """Aggiorna il riepilogo finale."""
        self.summary_text.configure(state=tk.NORMAL)
        self.summary_text.delete("1.0", tk.END)

        summary = self._format_summary(metrics)
        self.summary_text.insert(tk.END, summary)
        self.summary_text.configure(state=tk.DISABLED)

    def _format_summary(self, m: AggregateMetrics) -> str:
        """Formatta il riepilogo delle metriche aggregate."""
        lines = [
            "=" * 60,
            "       RIEPILOGO SIMULAZIONE RETE BANYAN",
            "=" * 60,
            "",
            "─── GENERALE ───────────────────────────────────────────",
            f"  Cicli totali:              {m.total_cycles:>10}",
            f"  Pacchetti generati:        {m.total_packets_generated:>10}",
            f"  Pacchetti consegnati:      {m.total_packets_delivered:>10}",
            f"  Pacchetti scartati:        {m.total_packets_dropped:>10}",
            f"  Pacchetti deflessi:        {m.total_packets_deflected:>10}",
            f"  Conflitti totali:          {m.total_conflicts:>10}",
            "",
            "─── THROUGHPUT ─────────────────────────────────────────",
            f"  Throughput medio:          {m.avg_throughput:>10.4f}",
            f"  Throughput massimo:        {m.max_throughput:>10.4f}",
            f"  Throughput minimo:         {m.min_throughput:>10.4f}",
            "",
            "─── LATENZA ────────────────────────────────────────────",
            f"  Latenza media:             {m.avg_latency:>10.2f} cicli",
            f"  Latenza mediana:           {m.median_latency:>10.2f} cicli",
            f"  Latenza minima:            {str(m.min_latency):>10}",
            f"  Latenza massima:           {str(m.max_latency):>10}",
            f"  Deviazione standard:       {m.latency_std_dev:>10.2f}",
            f"  95° percentile:            {m.latency_percentile_95:>10.2f}",
            f"  99° percentile:            {m.latency_percentile_99:>10.2f}",
            "",
            "─── TASSI ──────────────────────────────────────────────",
            f"  Tasso di consegna:         {m.delivery_rate * 100:>9.2f}%",
            f"  Tasso di scarto:           {m.drop_rate * 100:>9.2f}%",
            f"  Tasso conflitti/ciclo:     {m.conflict_rate:>10.3f}",
            "",
            "─── UTILIZZO SWITCH ────────────────────────────────────",
            f"  Utilizzo medio:            {m.avg_switch_utilization * 100:>9.2f}%",
            f"  Utilizzo massimo:          {m.max_switch_utilization * 100:>9.2f}%",
            f"  Utilizzo minimo:           {m.min_switch_utilization * 100:>9.2f}%",
            "",
            "─── FAIRNESS ───────────────────────────────────────────",
            f"  Indice di Jain:            {m.jain_fairness_index:>10.4f}",
            "",
            "=" * 60,
        ]
        return "\n".join(lines)

    @staticmethod
    def _moving_average(data: List[float], window: int) -> List[float]:
        """Calcola la media mobile di una serie di dati."""
        if not data or window <= 0:
            return data
        if window == 1:
            return data

        result = []
        for i in range(len(data)):
            start = max(0, i - window + 1)
            subset = data[start:i + 1]
            result.append(sum(subset) / len(subset))
        return result

    def reset(self):
        """Reset del pannello statistiche."""
        # Reset metriche real-time
        for var in self.realtime_vars.values():
            var.set("0")

        # Reset grafici
        if HAS_MATPLOTLIB and hasattr(self, 'fig'):
            for ax in [self.ax_throughput, self.ax_latency, self.ax_conflicts, self.ax_delivery]:
                ax.clear()
            self._style_axes()
            self.chart_canvas.draw()

        # Reset tabella switch
        for item in self.switch_tree.get_children():
            self.switch_tree.delete(item)

        # Reset summary
        self.summary_text.configure(state=tk.NORMAL)
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.configure(state=tk.DISABLED)

        self._metrics_collector = None
        self._aggregate_metrics = None