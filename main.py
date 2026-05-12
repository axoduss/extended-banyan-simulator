#!/usr/bin/env python3
"""
Simulatore di Rete Banyan - Entry Point

Un simulatore completo e configurabile di reti di interconnessione Banyan (Omega)
con interfaccia grafica, metriche in tempo reale e analisi statistica.

Utilizzo:
    python main.py              # Avvia con GUI
    python main.py --batch      # Esegue simulazione batch (senza GUI)
    python main.py --help       # Mostra aiuto

Autore: Simulatore Rete Banyan
Versione: 1.0.0
"""
import sys
import argparse
import json
from pathlib import Path


def run_gui():
    """Avvia l'applicazione con interfaccia grafica."""
    from gui.app import BanyanSimulatorApp
    app = BanyanSimulatorApp()
    app.run()


def run_batch(args):
    """Esegue una simulazione batch dalla riga di comando."""
    from config.settings import SimulationConfig, TrafficPattern, ConflictResolution
    from core.network import BanyanNetwork

    # Costruisci configurazione
    try:
        config = SimulationConfig(
            num_inputs=args.size,
            num_cycles=args.cycles,
            packet_generation_rate=args.rate,
            traffic_pattern=TrafficPattern(args.traffic),
            conflict_resolution=ConflictResolution(args.conflict),
            buffer_size=args.buffer_size,
            hotspot_destination=args.hotspot_dest,
            hotspot_fraction=args.hotspot_frac,
        )
    except ValueError as e:
        print(f"❌ Errore di configurazione: {e}", file=sys.stderr)
        sys.exit(1)

    print("=" * 60)
    print("  SIMULATORE RETE BANYAN - Modalità Batch")
    print("=" * 60)
    print(f"\n  Configurazione:")
    print(f"    Dimensione rete:       {config.num_inputs}×{config.num_outputs}")
    print(f"    Stadi:                 {config.num_stages}")
    print(f"    Switch per stadio:     {config.switches_per_stage}")
    print(f"    Cicli:                 {config.num_cycles}")
    print(f"    Tasso generazione:     {config.packet_generation_rate}")
    print(f"    Pattern traffico:      {config.traffic_pattern.value}")
    print(f"    Risoluzione conflitti: {config.conflict_resolution.value}")
    if config.conflict_resolution == ConflictResolution.BUFFER:
        print(f"    Dimensione buffer:     {config.buffer_size}")
    print()

    # Esegui simulazione
    print("  ⏳ Simulazione in corso...")
    network = BanyanNetwork(config)

    # Progress bar testuale
    progress_interval = max(1, config.num_cycles // 20)
    for cycle in range(config.num_cycles):
        network.step()
        if (cycle + 1) % progress_interval == 0:
            pct = (cycle + 1) / config.num_cycles * 100
            bar_len = 30
            filled = int(bar_len * (cycle + 1) / config.num_cycles)
            bar = "█" * filled + "░" * (bar_len - filled)
            print(f"\r    [{bar}] {pct:.0f}%", end="", flush=True)

    print(f"\r    [{'█' * 30}] 100%")
    print("\n  ✅ Simulazione completata!\n")

    # Calcola e mostra risultati
    metrics = network.get_aggregate_metrics()

    print("─" * 60)
    print("  RISULTATI")
    print("─" * 60)
    print(f"\n  📊 Throughput:")
    print(f"    Medio:    {metrics.avg_throughput:.4f}")
    print(f"    Massimo:  {metrics.max_throughput:.4f}")
    print(f"    Minimo:   {metrics.min_throughput:.4f}")
    print(f"\n  ⏱️  Latenza:")
    print(f"    Media:    {metrics.avg_latency:.2f} cicli")
    print(f"    Mediana:  {metrics.median_latency:.2f} cicli")
    print(f"    Minima:   {metrics.min_latency}")
    print(f"    Massima:  {metrics.max_latency}")
    print(f"    Std Dev:  {metrics.latency_std_dev:.2f}")
    print(f"    P95:      {metrics.latency_percentile_95:.2f}")
    print(f"    P99:      {metrics.latency_percentile_99:.2f}")
    print(f"\n  📦 Pacchetti:")
    print(f"    Generati:   {metrics.total_packets_generated}")
    print(f"    Consegnati: {metrics.total_packets_delivered}")
    print(f"    Scartati:   {metrics.total_packets_dropped}")
    print(f"    Deflessi:   {metrics.total_packets_deflected}")
    print(f"\n  📈 Tassi:")
    print(f"    Consegna:   {metrics.delivery_rate * 100:.2f}%")
    print(f"    Scarto:     {metrics.drop_rate * 100:.2f}%")
    print(f"    Conflitti:  {metrics.conflict_rate:.3f}/ciclo")
    print(f"\n  🔲 Utilizzo Switch:")
    print(f"    Medio:    {metrics.avg_switch_utilization * 100:.2f}%")
    print(f"    Massimo:  {metrics.max_switch_utilization * 100:.2f}%")
    print(f"    Minimo:   {metrics.min_switch_utilization * 100:.2f}%")
    print(f"\n  ⚖️  Fairness (Jain): {metrics.jain_fairness_index:.4f}")
    print("\n" + "=" * 60)

    # Esporta risultati se richiesto
    if args.output:
        output_path = Path(args.output)
        results = {
            "config": {
                "num_inputs": config.num_inputs,
                "num_stages": config.num_stages,
                "num_cycles": config.num_cycles,
                "packet_generation_rate": config.packet_generation_rate,
                "traffic_pattern": config.traffic_pattern.value,
                "conflict_resolution": config.conflict_resolution.value,
                "buffer_size": config.buffer_size,
            },
            "metrics": {
                "throughput": {
                    "average": metrics.avg_throughput,
                    "max": metrics.max_throughput,
                    "min": metrics.min_throughput,
                },
                "latency": {
                    "average": metrics.avg_latency,
                    "median": metrics.median_latency,
                    "min": metrics.min_latency,
                    "max": metrics.max_latency,
                    "std_dev": metrics.latency_std_dev,
                    "p95": metrics.latency_percentile_95,
                    "p99": metrics.latency_percentile_99,
                },
                "packets": {
                    "generated": metrics.total_packets_generated,
                    "delivered": metrics.total_packets_delivered,
                    "dropped": metrics.total_packets_dropped,
                    "deflected": metrics.total_packets_deflected,
                },
                "rates": {
                    "delivery": metrics.delivery_rate,
                    "drop": metrics.drop_rate,
                    "conflict_per_cycle": metrics.conflict_rate,
                },
                "switch_utilization": {
                    "average": metrics.avg_switch_utilization,
                    "max": metrics.max_switch_utilization,
                    "min": metrics.min_switch_utilization,
                },
                "jain_fairness_index": metrics.jain_fairness_index,
            },
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\n  💾 Risultati esportati in: {output_path}")


def run_sweep(args):
    """Esegue un parameter sweep su più configurazioni."""
    from config.settings import SimulationConfig, TrafficPattern, ConflictResolution
    from core.network import BanyanNetwork
    import csv

    rates = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    sizes = [int(s) for s in args.sweep_sizes.split(",")]
    patterns = [TrafficPattern(p) for p in args.sweep_patterns.split(",")]

    output_path = Path(args.output) if args.output else Path("sweep_results.csv")

    print("=" * 60)
    print("  PARAMETER SWEEP")
    print("=" * 60)
    print(f"  Dimensioni: {sizes}")
    print(f"  Pattern: {[p.value for p in patterns]}")
    print(f"  Tassi: {rates}")
    print(f"  Cicli per run: {args.cycles}")
    print(f"  Output: {output_path}")
    print()

    total_runs = len(sizes) * len(patterns) * len(rates)
    current_run = 0

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "size", "pattern", "rate", "conflict_strategy",
            "avg_throughput", "avg_latency", "delivery_rate",
            "drop_rate", "conflict_rate", "jain_fairness"
        ])

        for size in sizes:
            for pattern in patterns:
                for rate in rates:
                    current_run += 1
                    pct = current_run / total_runs * 100
                    print(f"\r  [{current_run}/{total_runs}] {pct:.0f}% - "
                          f"N={size}, {pattern.value}, rate={rate:.1f}",
                          end="", flush=True)

                    try:
                        config = SimulationConfig(
                            num_inputs=size,
                            num_cycles=args.cycles,
                            packet_generation_rate=rate,
                            traffic_pattern=pattern,
                            conflict_resolution=ConflictResolution(args.conflict),
                            buffer_size=args.buffer_size,
                        )
                        network = BanyanNetwork(config)
                        metrics = network.run_full_simulation()

                        writer.writerow([
                            size, pattern.value, rate, args.conflict,
                            f"{metrics.avg_throughput:.6f}",
                            f"{metrics.avg_latency:.4f}",
                            f"{metrics.delivery_rate:.6f}",
                            f"{metrics.drop_rate:.6f}",
                            f"{metrics.conflict_rate:.6f}",
                            f"{metrics.jain_fairness_index:.6f}",
                        ])
                    except Exception as e:
                        print(f"\n  ⚠️ Errore per config ({size}, {pattern.value}, {rate}): {e}")

    print(f"\n\n  ✅ Sweep completato! Risultati in: {output_path}")


def main():
    """Entry point principale."""
    parser = argparse.ArgumentParser(
        description="Simulatore di Rete Banyan - Rete di interconnessione multistadio",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  python main.py                                    # GUI
  python main.py --batch --size 16 --cycles 5000   # Batch 16x16
  python main.py --batch --traffic hotspot --rate 0.8
  python main.py --sweep --sweep-sizes 8,16,32 --cycles 2000
        """
    )

    # Modalità
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--batch", action="store_true", help="Esegui in modalità batch (no GUI)")
    mode_group.add_argument("--sweep", action="store_true", help="Esegui parameter sweep")

    # Parametri di rete
    parser.add_argument("--size", type=int, default=8,
                        help="Dimensione della rete N (potenza di 2, default: 8)")
    parser.add_argument("--cycles", type=int, default=1000,
                        help="Numero di cicli di simulazione (default: 1000)")
    parser.add_argument("--rate", type=float, default=0.5,
                        help="Tasso di generazione pacchetti [0-1] (default: 0.5)")
    parser.add_argument("--traffic", type=str, default="uniform",
                        choices=["uniform", "hotspot", "permutation", "complement", "bit_reversal"],
                        help="Pattern di traffico (default: uniform)")
    parser.add_argument("--conflict", type=str, default="drop",
                        choices=["drop", "buffer", "deflection"],
                        help="Strategia risoluzione conflitti (default: drop)")
    parser.add_argument("--buffer-size", type=int, default=4,
                        help="Dimensione buffer per switch (default: 4)")
    parser.add_argument("--hotspot-dest", type=int, default=0,
                        help="Destinazione hotspot (default: 0)")
    parser.add_argument("--hotspot-frac", type=float, default=0.3,
                        help="Frazione traffico hotspot [0-1] (default: 0.3)")

    # Output
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="File di output per i risultati (JSON per batch, CSV per sweep)")

    # Sweep parameters
    parser.add_argument("--sweep-sizes", type=str, default="4,8,16",
                        help="Dimensioni per sweep, separate da virgola (default: 4,8,16)")
    parser.add_argument("--sweep-patterns", type=str, default="uniform,hotspot,complement",
                        help="Pattern per sweep, separati da virgola")

    args = parser.parse_args()

    if args.batch:
        run_batch(args)
    elif args.sweep:
        run_sweep(args)
    else:
        run_gui()


if __name__ == "__main__":
    main()