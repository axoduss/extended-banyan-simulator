"""
Modulo per la raccolta e l'analisi delle metriche di simulazione.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import statistics
import math

from .packet import Packet, PacketStatus


@dataclass
class CycleMetrics:
    """Metriche per un singolo ciclo di simulazione."""
    cycle: int
    packets_generated: int = 0
    packets_delivered: int = 0
    packets_dropped: int = 0
    packets_in_transit: int = 0
    packets_buffered: int = 0
    conflicts: int = 0
    throughput: float = 0.0
    average_latency: float = 0.0


@dataclass
class AggregateMetrics:
    """Metriche aggregate della simulazione."""
    total_packets_generated: int = 0
    total_packets_delivered: int = 0
    total_packets_dropped: int = 0
    total_packets_deflected: int = 0
    total_conflicts: int = 0
    total_cycles: int = 0

    # Latenza
    min_latency: Optional[int] = None
    max_latency: Optional[int] = None
    avg_latency: float = 0.0
    median_latency: float = 0.0
    latency_std_dev: float = 0.0
    latency_percentile_95: float = 0.0
    latency_percentile_99: float = 0.0

    # Throughput
    avg_throughput: float = 0.0
    max_throughput: float = 0.0
    min_throughput: float = 0.0

    # Tassi
    delivery_rate: float = 0.0
    drop_rate: float = 0.0
    conflict_rate: float = 0.0

    # Per-switch
    avg_switch_utilization: float = 0.0
    max_switch_utilization: float = 0.0
    min_switch_utilization: float = 0.0

    # Fairness
    jain_fairness_index: float = 0.0


class MetricsCollector:
    """Raccoglie e calcola le metriche della simulazione."""

    def __init__(self, num_inputs: int, num_outputs: int):
        self.num_inputs = num_inputs
        self.num_outputs = num_outputs
        self.cycle_metrics: List[CycleMetrics] = []
        self.delivered_packets: List[Packet] = []
        self.dropped_packets: List[Packet] = []
        self.all_packets: List[Packet] = []
        self._per_output_delivered: Dict[int, int] = {i: 0 for i in range(num_outputs)}
        self._per_input_generated: Dict[int, int] = {i: 0 for i in range(num_inputs)}
        self._throughput_history: List[float] = []
        self._latency_history: List[int] = []

    def record_packet_generated(self, packet: Packet):
        """Registra la generazione di un pacchetto."""
        self.all_packets.append(packet)
        self._per_input_generated[packet.source] = (
            self._per_input_generated.get(packet.source, 0) + 1
        )

    def record_packet_delivered(self, packet: Packet):
        """Registra la consegna di un pacchetto."""
        self.delivered_packets.append(packet)
        self._per_output_delivered[packet.destination] = (
            self._per_output_delivered.get(packet.destination, 0) + 1
        )
        if packet.latency is not None:
            self._latency_history.append(packet.latency)

    def record_packet_dropped(self, packet: Packet):
        """Registra lo scarto di un pacchetto."""
        self.dropped_packets.append(packet)

    def record_cycle(self, cycle: int, packets_generated: int, packets_delivered: int,
                     packets_dropped: int, packets_in_transit: int,
                     packets_buffered: int, conflicts: int):
        """Registra le metriche di un ciclo."""
        throughput = packets_delivered / self.num_outputs if self.num_outputs > 0 else 0.0
        self._throughput_history.append(throughput)

        avg_latency = 0.0
        if self._latency_history:
            # Media mobile sugli ultimi 100 pacchetti consegnati
            recent = self._latency_history[-100:]
            avg_latency = statistics.mean(recent)

        cycle_metric = CycleMetrics(
            cycle=cycle,
            packets_generated=packets_generated,
            packets_delivered=packets_delivered,
            packets_dropped=packets_dropped,
            packets_in_transit=packets_in_transit,
            packets_buffered=packets_buffered,
            conflicts=conflicts,
            throughput=throughput,
            average_latency=avg_latency,
        )
        self.cycle_metrics.append(cycle_metric)

    def compute_aggregate_metrics(self, switch_elements=None) -> AggregateMetrics:
        """Calcola le metriche aggregate finali."""
        metrics = AggregateMetrics()

        metrics.total_packets_generated = len(self.all_packets)
        metrics.total_packets_delivered = len(self.delivered_packets)
        metrics.total_packets_dropped = len(self.dropped_packets)
        metrics.total_packets_deflected = sum(
            1 for p in self.all_packets if p.deflections > 0
        )
        metrics.total_cycles = len(self.cycle_metrics)
        metrics.total_conflicts = sum(cm.conflicts for cm in self.cycle_metrics)

        # Latenza
        if self._latency_history:
            sorted_latencies = sorted(self._latency_history)
            metrics.min_latency = sorted_latencies[0]
            metrics.max_latency = sorted_latencies[-1]
            metrics.avg_latency = statistics.mean(sorted_latencies)
            metrics.median_latency = statistics.median(sorted_latencies)
            if len(sorted_latencies) > 1:
                metrics.latency_std_dev = statistics.stdev(sorted_latencies)
            metrics.latency_percentile_95 = self._percentile(sorted_latencies, 95)
            metrics.latency_percentile_99 = self._percentile(sorted_latencies, 99)

        # Throughput
        if self._throughput_history:
            metrics.avg_throughput = statistics.mean(self._throughput_history)
            metrics.max_throughput = max(self._throughput_history)
            metrics.min_throughput = min(self._throughput_history)

        # Tassi
        if metrics.total_packets_generated > 0:
            metrics.delivery_rate = (
                metrics.total_packets_delivered / metrics.total_packets_generated
            )
            metrics.drop_rate = (
                metrics.total_packets_dropped / metrics.total_packets_generated
            )

        if metrics.total_cycles > 0:
            metrics.conflict_rate = metrics.total_conflicts / metrics.total_cycles

        # Switch utilization
        if switch_elements:
            utilizations = [sw.utilization for row in switch_elements for sw in row]
            if utilizations:
                metrics.avg_switch_utilization = statistics.mean(utilizations)
                metrics.max_switch_utilization = max(utilizations)
                metrics.min_switch_utilization = min(utilizations)

        # Jain's Fairness Index
        metrics.jain_fairness_index = self._compute_jain_fairness()

        return metrics

    def _compute_jain_fairness(self) -> float:
        """Calcola l'indice di fairness di Jain sulla distribuzione delle consegne."""
        deliveries = list(self._per_output_delivered.values())
        n = len(deliveries)
        if n == 0 or sum(deliveries) == 0:
            return 1.0
        sum_x = sum(deliveries)
        sum_x2 = sum(x * x for x in deliveries)
        if sum_x2 == 0:
            return 1.0
        return (sum_x ** 2) / (n * sum_x2)

    @staticmethod
    def _percentile(sorted_data: List[int], percentile: float) -> float:
        """Calcola il percentile di una lista ordinata."""
        if not sorted_data:
            return 0.0
        k = (len(sorted_data) - 1) * (percentile / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return float(sorted_data[int(k)])
        d0 = sorted_data[int(f)] * (c - k)
        d1 = sorted_data[int(c)] * (k - f)
        return d0 + d1

    def get_throughput_series(self) -> List[float]:
        """Restituisce la serie temporale del throughput."""
        return self._throughput_history

    def get_latency_series(self) -> List[float]:
        """Restituisce la serie temporale della latenza media."""
        return [cm.average_latency for cm in self.cycle_metrics]

    def get_conflict_series(self) -> List[int]:
        """Restituisce la serie temporale dei conflitti."""
        return [cm.conflicts for cm in self.cycle_metrics]

    def get_delivery_series(self) -> List[int]:
        """Restituisce la serie temporale delle consegne."""
        return [cm.packets_delivered for cm in self.cycle_metrics]

    