"""
Applicazione principale GUI del simulatore di rete Banyan.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import queue
from typing import Optional

from config.settings import SimulationConfig
from core.network import BanyanNetwork
from core.metrics import AggregateMetrics
from .network_canvas import NetworkCanvas
from .control_panel import ControlPanel
from .stats_panel import StatsPanel


class BanyanSimulatorApp:
    """Applicazione principale del simulatore."""

    APP_TITLE = "🔀 Simulatore Rete Banyan"
    APP_VERSION = "1.0.0"
    MIN_WIDTH = 1280
    MIN_HEIGHT = 800

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{self.APP_TITLE} v{self.APP_VERSION}")
        self.root.geometry(f"{self.MIN_WIDTH}x{self.MIN_HEIGHT}")
        self.root.minsize(self.MIN_WIDTH, self.MIN_HEIGHT)
        self.root.configure(bg="#11111b")

        # Stato
        self._network: Optional[BanyanNetwork] = None
        self._simulation_thread: Optional[threading.Thread] = None
        self._is_running: bool = False
        self._is_paused: bool = False
        self._update_queue: queue.Queue = queue.Queue()
        self._animation_job: Optional[str] = None

        # Configurazione iniziale
        self._config = SimulationConfig()

        # Costruisci UI
        self._build_menu()
        self._build_layout()

        # Inizializza la rete
        self._initialize_network()

        # Avvia il loop di aggiornamento GUI
        self._process_update_queue()

    def _build_menu(self):
        """Costruisce la barra dei menu."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Menu File
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Esporta Metriche...", command=self._export_metrics)
        file_menu.add_command(label="Esporta Rete (PS)...", command=self._export_network)
        file_menu.add_separator()
        file_menu.add_command(label="Esci", command=self._on_close)

        # Menu Simulazione
        sim_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Simulazione", menu=sim_menu)
        sim_menu.add_command(label="Avvia", command=self._start_simulation)
        sim_menu.add_command(label="Pausa", command=self._stop_simulation)
        sim_menu.add_command(label="Step Singolo", command=self._step_simulation)
        sim_menu.add_command(label="Reset", command=self._reset_simulation)
        sim_menu.add_separator()
        sim_menu.add_command(label="Esegui Batch (no GUI)", command=self._run_batch)

        # Menu Aiuto
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Aiuto", menu=help_menu)
        help_menu.add_command(label="Informazioni", command=self._show_about)

    def _build_layout(self):
        """Costruisce il layout principale dell'applicazione."""
        # Frame principale con PanedWindow
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Pannello sinistro: Controlli
        left_frame = tk.Frame(main_paned, bg="#181825", width=280)
        left_frame.pack_propagate(False)
        main_paned.add(left_frame, weight=0)

        self.control_panel = ControlPanel(
            left_frame,
            on_start=self._start_simulation,
            on_stop=self._stop_simulation,
            on_step=self._step_simulation,
            on_reset=self._reset_simulation,
            on_config_change=self._on_config_change,
        )
        self.control_panel.pack(fill=tk.BOTH, expand=True)

        # Pannello centrale e destro
        right_paned = ttk.PanedWindow(main_paned, orient=tk.VERTICAL)
        main_paned.add(right_paned, weight=1)

        # Parte superiore: Visualizzazione rete
        canvas_frame = tk.Frame(right_paned, bg="#1e1e2e")
        right_paned.add(canvas_frame, weight=1)

        # Header del canvas
        header = tk.Frame(canvas_frame, bg="#1e1e2e")
        header.pack(fill=tk.X, padx=10, pady=(10, 5))
        tk.Label(
            header, text="🔀 Topologia della Rete",
            bg="#1e1e2e", fg="#cdd6f4", font=("Segoe UI", 12, "bold")
        ).pack(side=tk.LEFT)

        self.network_canvas = NetworkCanvas(
            canvas_frame,
            num_inputs=self._config.num_inputs,
            num_stages=self._config.num_stages,
        )
        self.network_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Parte inferiore: Statistiche
        stats_frame = tk.Frame(right_paned, bg="#181825")
        right_paned.add(stats_frame, weight=1)

                # Parte inferiore: Statistiche
        stats_frame = tk.Frame(right_paned, bg="#181825")
        right_paned.add(stats_frame, weight=1)

        self.stats_panel = StatsPanel(stats_frame)
        self.stats_panel.pack(fill=tk.BOTH, expand=True)

    def _initialize_network(self):
        """Inizializza la rete con la configurazione corrente."""
        try:
            self._config = self.control_panel.get_config()
            if self._config is None:
                self._config = SimulationConfig()

            self._network = BanyanNetwork(self._config)
            self._network.set_callbacks(
                on_cycle_complete=self._on_cycle_complete_callback,
                on_simulation_complete=self._on_simulation_complete_callback,
            )
            self.stats_panel.set_metrics_collector(self._network.metrics_collector)

        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile inizializzare la rete:\n{str(e)}")

    def _start_simulation(self):
        """Avvia la simulazione."""
        if self._is_running:
            return

        # Aggiorna configurazione
        config = self.control_panel.get_config()
        if config is None:
            return

        # Se la rete non esiste o la config è cambiata, ricrea
        if self._network is None or self._needs_reconfiguration(config):
            self._config = config
            self._network = BanyanNetwork(self._config)
            self._network.set_callbacks(
                on_cycle_complete=self._on_cycle_complete_callback,
                on_simulation_complete=self._on_simulation_complete_callback,
            )
            self.stats_panel.set_metrics_collector(self._network.metrics_collector)
            self.network_canvas.reconfigure(config.num_inputs, config.num_stages)

        self._is_running = True
        self._is_paused = False
        self.control_panel.set_controls_enabled(False)

        # Avvia animazione
        self._schedule_animation_step()

    def _stop_simulation(self):
        """Mette in pausa la simulazione."""
        self._is_running = False
        self._is_paused = True
        if self._animation_job:
            self.root.after_cancel(self._animation_job)
            self._animation_job = None
        self.control_panel.set_controls_enabled(True)

    def _step_simulation(self):
        """Esegue un singolo step della simulazione."""
        if self._network is None:
            self._initialize_network()

        if self._network and not self._network.is_complete:
            config = self.control_panel.get_config()
            if config and self._needs_reconfiguration(config):
                self._config = config
                self._network.reconfigure(self._config)
                self.network_canvas.reconfigure(config.num_inputs, config.num_stages)
                self.stats_panel.set_metrics_collector(self._network.metrics_collector)

            cycle_metrics = self._network.step()
            self._update_gui_from_cycle(cycle_metrics)

    def _reset_simulation(self):
        """Reset completo della simulazione."""
        self._is_running = False
        self._is_paused = False

        if self._animation_job:
            self.root.after_cancel(self._animation_job)
            self._animation_job = None

        # Ricrea la rete
        config = self.control_panel.get_config()
        if config:
            self._config = config
            self._network = BanyanNetwork(self._config)
            self._network.set_callbacks(
                on_cycle_complete=self._on_cycle_complete_callback,
                on_simulation_complete=self._on_simulation_complete_callback,
            )
            self.network_canvas.reconfigure(config.num_inputs, config.num_stages)
            self.stats_panel.set_metrics_collector(self._network.metrics_collector)

        # Reset UI
        self.stats_panel.reset()
        self.network_canvas.clear_highlights()
        self.control_panel.set_controls_enabled(True)

    def _schedule_animation_step(self):
        """Schedula il prossimo step di animazione."""
        if not self._is_running or self._network is None or self._network.is_complete:
            return

        # Esegui uno step
        cycle_metrics = self._network.step()
        self._update_gui_from_cycle(cycle_metrics)

        # Controlla se la simulazione è completa
        if self._network.is_complete:
            self._on_simulation_finished()
            return

        # Schedula il prossimo step
        speed = self.control_panel.var_anim_speed.get()
        self._animation_job = self.root.after(speed, self._schedule_animation_step)

    def _update_gui_from_cycle(self, cycle_metrics):
        """Aggiorna la GUI dopo un ciclo di simulazione."""
        if self._network is None or cycle_metrics is None:
            return

        # Aggiorna canvas della rete
        network_state = self._network.get_network_state()
        self.network_canvas.update_state(network_state)

        # Aggiorna metriche real-time
        total_gen = self._network.metrics_collector.metrics_collector_total_generated \
            if hasattr(self._network.metrics_collector, 'metrics_collector_total_generated') \
            else len(self._network.metrics_collector.all_packets)
        total_del = len(self._network.metrics_collector.delivered_packets)
        total_drop = len(self._network.metrics_collector.dropped_packets)

        delivery_rate = (total_del / total_gen * 100) if total_gen > 0 else 0
        drop_rate = (total_drop / total_gen * 100) if total_gen > 0 else 0

        realtime_data = {
            "cycle": str(self._network.current_cycle),
            "throughput": f"{cycle_metrics.throughput:.4f}",
            "avg_latency": f"{cycle_metrics.average_latency:.2f}",
            "packets_generated": str(total_gen),
            "packets_delivered": str(total_del),
            "packets_dropped": str(total_drop),
            "packets_in_transit": str(cycle_metrics.packets_in_transit),
            "packets_buffered": str(cycle_metrics.packets_buffered),
            "conflicts": str(cycle_metrics.conflicts),
            "total_conflicts": str(sum(
                cm.conflicts for cm in self._network.metrics_collector.cycle_metrics
            )),
            "delivery_rate": f"{delivery_rate:.2f}%",
            "drop_rate": f"{drop_rate:.2f}%",
        }
        self.stats_panel.update_realtime(realtime_data)

        # Aggiorna progress bar
        self.control_panel.update_progress(
            self._network.current_cycle, self._config.num_cycles
        )

        # Aggiorna grafici ogni N cicli per performance
        if self._network.current_cycle % 50 == 0:
            self.stats_panel.refresh_charts()
            self.stats_panel.update_switch_table(self._network.get_switch_stats())

    def _on_simulation_finished(self):
        """Gestisce il completamento della simulazione."""
        self._is_running = False

        if self._animation_job:
            self.root.after_cancel(self._animation_job)
            self._animation_job = None

        # Aggiorna UI finale
        self.control_panel.mark_simulation_complete()
        self.control_panel.set_controls_enabled(True)

        # Calcola e mostra metriche finali
        if self._network:
            aggregate = self._network.get_aggregate_metrics()
            self.stats_panel.update_summary(aggregate)
            self.stats_panel.refresh_charts()
            self.stats_panel.update_switch_table(self._network.get_switch_stats())

            # Mostra tab riepilogo
            self.stats_panel.notebook.select(3)

    def _on_cycle_complete_callback(self, cycle: int):
        """Callback chiamata dalla rete al completamento di un ciclo (thread-safe)."""
        self._update_queue.put(("cycle_complete", cycle))

    def _on_simulation_complete_callback(self):
        """Callback chiamata dalla rete al completamento della simulazione."""
        self._update_queue.put(("simulation_complete", None))

    def _process_update_queue(self):
        """Processa gli aggiornamenti dalla coda (per thread safety)."""
        try:
            while True:
                msg_type, data = self._update_queue.get_nowait()
                if msg_type == "simulation_complete":
                    self._on_simulation_finished()
        except queue.Empty:
            pass
        finally:
            self.root.after(50, self._process_update_queue)

    def _needs_reconfiguration(self, new_config: SimulationConfig) -> bool:
        """Verifica se la rete necessita di riconfigurazione."""
        if self._network is None:
            return True
        return (
            new_config.num_inputs != self._config.num_inputs or
            new_config.conflict_resolution != self._config.conflict_resolution or
            new_config.buffer_size != self._config.buffer_size or
            new_config.traffic_pattern != self._config.traffic_pattern
        )

    def _run_batch(self):
        """Esegue la simulazione in batch senza animazione."""
        config = self.control_panel.get_config()
        if config is None:
            return

        result = messagebox.askyesno(
            "Simulazione Batch",
            f"Eseguire {config.num_cycles} cicli senza animazione?\n"
            "La GUI si bloccherà brevemente durante l'esecuzione."
        )
        if not result:
            return

        self._config = config
        self._network = BanyanNetwork(self._config)
        self.stats_panel.set_metrics_collector(self._network.metrics_collector)
        self.network_canvas.reconfigure(config.num_inputs, config.num_stages)

        # Disabilita controlli
        self.control_panel.set_controls_enabled(False)
        self.control_panel.var_status.set("⏳ Esecuzione batch...")
        self.root.update()

        # Esegui in un thread separato
        def run_batch_thread():
            aggregate = self._network.run_full_simulation()
            self._update_queue.put(("simulation_complete", None))

        thread = threading.Thread(target=run_batch_thread, daemon=True)
        thread.start()

        # Polling per completamento
        def check_batch_complete():
            if thread.is_alive():
                # Aggiorna progress
                if self._network:
                    self.control_panel.update_progress(
                        self._network.current_cycle, self._config.num_cycles
                    )
                self.root.after(100, check_batch_complete)
            else:
                self._on_simulation_finished()

        self.root.after(100, check_batch_complete)

    def _export_metrics(self):
        """Esporta le metriche in un file di testo."""
        if self._network is None:
            messagebox.showwarning("Attenzione", "Nessuna simulazione da esportare.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("File di testo", "*.txt"), ("CSV", "*.csv"), ("Tutti", "*.*")],
            title="Esporta Metriche",
        )
        if not filepath:
            return

        try:
            aggregate = self._network.get_aggregate_metrics()
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"Simulatore Rete Banyan - Report Metriche\n")
                f.write(f"{'=' * 60}\n\n")
                f.write(f"Configurazione:\n")
                f.write(f"  Dimensione rete: {self._config.num_inputs}x{self._config.num_outputs}\n")
                f.write(f"  Stadi: {self._config.num_stages}\n")
                f.write(f"  Pattern traffico: {self._config.traffic_pattern.value}\n")
                f.write(f"  Tasso generazione: {self._config.packet_generation_rate}\n")
                f.write(f"  Risoluzione conflitti: {self._config.conflict_resolution.value}\n")
                f.write(f"  Cicli: {self._config.num_cycles}\n\n")
                
                f.write(self.stats_panel._format_summary(aggregate))
                
                # Esporta anche serie temporali se CSV
                if filepath.endswith(".csv"):
                    f.write("\n\nCiclo,Throughput,Latenza,Conflitti,Consegne\n")
                    throughput = self._network.metrics_collector.get_throughput_series()
                    latency = self._network.metrics_collector.get_latency_series()
                    conflicts = self._network.metrics_collector.get_conflict_series()
                    deliveries = self._network.metrics_collector.get_delivery_series()
                    
                    for i in range(len(throughput)):
                        f.write(f"{i+1},{throughput[i]:.4f},{latency[i]:.2f},"
                                f"{conflicts[i]},{deliveries[i]}\n")

            messagebox.showinfo("Esportazione", f"Metriche esportate in:\n{filepath}")

        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante l'esportazione:\n{str(e)}")

    def _export_network(self):
        """Esporta la visualizzazione della rete come PostScript."""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".ps",
            filetypes=[("PostScript", "*.ps"), ("Tutti", "*.*")],
            title="Esporta Rete",
        )
        if filepath:
            try:
                self.network_canvas.export_as_postscript(filepath)
                messagebox.showinfo("Esportazione", f"Rete esportata in:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Errore", f"Errore durante l'esportazione:\n{str(e)}")

    def _on_config_change(self):
        """Gestisce il cambio di configurazione."""
        config = self.control_panel.get_config()
        if config and self._needs_reconfiguration(config):
            self._config = config
            if not self._is_running:
                self.network_canvas.reconfigure(config.num_inputs, config.num_stages)

        def _show_about(self):
        """Mostra la finestra informazioni."""
        messagebox.showinfo(
            "Informazioni",
            f"{self.APP_TITLE}\n"
            f"Versione: {self.APP_VERSION}\n\n"
            f"Simulatore di rete di interconnessione Banyan (Omega)\n"
            f"con supporto per:\n"
            f"  • Reti N×N configurabili (4-64 porte)\n"
            f"  • Pattern di traffico multipli\n"
            f"  • Strategie di risoluzione conflitti\n"
            f"  • Metriche e statistiche complete\n"
            f"  • Visualizzazione topologica in tempo reale\n"
            f"  • Esportazione dati e grafici\n\n"
            f"Sviluppato in Python con tkinter e matplotlib."
        )

    def _on_close(self):
        """Gestisce la chiusura dell'applicazione."""
        if self._is_running:
            result = messagebox.askyesno(
                "Conferma Uscita",
                "La simulazione è in corso. Vuoi uscire comunque?"
            )
            if not result:
                return

        self._is_running = False
        if self._animation_job:
            self.root.after_cancel(self._animation_job)
        self.root.destroy()

    def run(self):
        """Avvia il main loop dell'applicazione."""
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()
        