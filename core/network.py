"""
Modulo principale della rete Banyan.
Gestisce la simulazione completa della rete.
"""
import random
from typing import List, Optional, Tuple, Callable
from dataclasses import dataclass, field

from config.settings import SimulationConfig, ConflictResolution, TrafficPattern
from .packet import Packet, PacketStatus
from .switch_element import SwitchElement
from .routing import BanyanRouter, TrafficGenerator
from .metrics import MetricsCollector, AggregateMetrics, CycleMetrics


class BanyanNetwork:
    """
    Simulatore completo di una rete Banyan N×N.
    
    La rete è composta da log2(N) stadi, ciascuno con N/2 switch 2×2.
    La topologia di interconnessione segue il pattern Omega (perfect shuffle).
    """

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.num_inputs = config.num_inputs
        self.num_outputs = config.num_outputs
        self.num_stages = config.num_stages
        self.switches_per_stage = config.switches_per_stage

        # Componenti della rete
        self.switches: List[List[SwitchElement]] = self._build_switches()
        self.router = BanyanRouter(self.num_inputs, self.num_stages)
        self.traffic_generator = TrafficGenerator(
            num_inputs=self.num_inputs,
            num_outputs=self.num_outputs,
            pattern=config.traffic_pattern,
            hotspot_destination=config.hotspot_destination,
            hotspot_fraction=config.hotspot_fraction,
        )
        self.metrics_collector = MetricsCollector(self.num_inputs, self.num_outputs)

        # Stato della simulazione
        self.current_cycle: int = 0
        self.is_running: bool = False
        self.is_paused: bool = False
        self.is_complete: bool = False
        self._packet_counter: int = 0
        self._active_packets: List[Packet] = []

        # Callbacks per la GUI
        self._on_cycle_complete: Optional[Callable] = None
        self._on_simulation_complete: Optional[Callable] = None
        self._on_packet_event: Optional[Callable] = None

    def _build_switches(self) -> List[List[SwitchElement]]:
        """Costruisce la matrice di switch elements."""
        switches = []
        for stage in range(self.num_stages):
            stage_switches = []
            for pos in range(self.switches_per_stage):
                sw = SwitchElement(
                    stage=stage,
                    position=pos,
                    conflict_resolution=self.config.conflict_resolution,
                    buffer_size=self.config.buffer_size,
                )
                stage_switches.append(sw)
            switches.append(stage_switches)
        return switches

    def set_callbacks(self, on_cycle_complete: Optional[Callable] = None,
                      on_simulation_complete: Optional[Callable] = None,
                      on_packet_event: Optional[Callable] = None):
        """Imposta le callback per gli eventi della simulazione."""
        self._on_cycle_complete = on_cycle_complete
        self._on_simulation_complete = on_simulation_complete
        self._on_packet_event = on_packet_event

    def reset(self):
        """Reset completo della rete."""
        self.switches = self._build_switches()
        self.metrics_collector = MetricsCollector(self.num_inputs, self.num_outputs)
        self.current_cycle = 0
        self.is_running = False
        self.is_paused = False
        self.is_complete = False
        self._packet_counter = 0
        self._active_packets = []

    def reconfigure(self, config: SimulationConfig):
        """Riconfigura la rete con nuovi parametri."""
        self.config = config
        self.num_inputs = config.num_inputs
        self.num_outputs = config.num_outputs
        self.num_stages = config.num_stages
        self.switches_per_stage = config.switches_per_stage
        self.router = BanyanRouter(self.num_inputs, self.num_stages)
        self.traffic_generator = TrafficGenerator(
            num_inputs=self.num_inputs,
            num_outputs=self.num_outputs,
            pattern=config.traffic_pattern,
            hotspot_destination=config.hotspot_destination,
            hotspot_fraction=config.hotspot_fraction,
        )
        self.reset()

    def run_full_simulation(self) -> AggregateMetrics:
        """Esegue la simulazione completa senza GUI."""
        self.is_running = True
        for _ in range(self.config.num_cycles):
            if not self.is_running:
                break
            self.step()
        self.is_running = False
        self.is_complete = True
        return self.get_aggregate_metrics()

    def step(self) -> CycleMetrics:
        """Esegue un singolo ciclo di simulazione."""
        self.current_cycle += 1
        
        cycle_packets_generated = 0
        cycle_packets_delivered = 0
        cycle_packets_dropped = 0
        cycle_conflicts = 0
        cycle_packets_buffered = 0

        # Fase 1: Generazione pacchetti
        new_packets = self._generate_packets()
        cycle_packets_generated = len(new_packets)

        # Fase 2: Iniezione pacchetti nel primo stadio
        self._inject_packets(new_packets)

        # Fase 3: Processamento stadio per stadio
        for stage in range(self.num_stages):
            stage_outputs = self._process_stage(stage)
            
            if stage < self.num_stages - 1:
                # Propaga le uscite al prossimo stadio
                self._propagate_to_next_stage(stage, stage_outputs)
            else:
                # Ultimo stadio: consegna i pacchetti
                delivered, dropped = self._deliver_packets(stage_outputs)
                cycle_packets_delivered = delivered
                cycle_packets_dropped += dropped

        # Fase 4: Conta conflitti e pacchetti bufferizzati
        for stage_switches in self.switches:
            for sw in stage_switches:
                cycle_conflicts += sw.total_conflicts - getattr(sw, '_prev_conflicts', 0)
                sw._prev_conflicts = sw.total_conflicts

        # Conta pacchetti in transito e bufferizzati
        packets_in_transit = sum(
            1 for p in self._active_packets if p.status == PacketStatus.IN_TRANSIT
        )
        packets_buffered = self._count_buffered_packets()
        cycle_packets_buffered = packets_buffered

        # Fase 5: Pulizia pacchetti completati
        self._cleanup_packets()

        # Registra metriche del ciclo
        self.metrics_collector.record_cycle(
            cycle=self.current_cycle,
            packets_generated=cycle_packets_generated,
            packets_delivered=cycle_packets_delivered,
            packets_dropped=cycle_packets_dropped,
            packets_in_transit=packets_in_transit,
            packets_buffered=cycle_packets_buffered,
            conflicts=cycle_conflicts,
        )

        # Callback
        if self._on_cycle_complete:
            self._on_cycle_complete(self.current_cycle)

        # Verifica completamento
        if self.current_cycle >= self.config.num_cycles:
            self.is_complete = True
            self.is_running = False
            if self._on_simulation_complete:
                self._on_simulation_complete()

        return self.metrics_collector.cycle_metrics[-1] if self.metrics_collector.cycle_metrics else None

    def _generate_packets(self) -> List[Packet]:
        """Genera nuovi pacchetti per questo ciclo."""
        new_packets = []
        for input_idx in range(self.num_inputs):
            if self.traffic_generator.should_generate_packet(
                self.config.packet_generation_rate
            ):
                destination = self.traffic_generator.generate_destination(input_idx)
                packet = Packet(
                    packet_id=self._packet_counter,
                    source=input_idx,
                    destination=destination,
                    creation_cycle=self.current_cycle,
                )
                packet.status = PacketStatus.IN_TRANSIT
                self._packet_counter += 1
                new_packets.append(packet)
                self._active_packets.append(packet)
                self.metrics_collector.record_packet_generated(packet)

                if self._on_packet_event:
                    self._on_packet_event("generated", packet)

        return new_packets

    def _inject_packets(self, packets: List[Packet]):
        """Inietta i pacchetti nel primo stadio della rete."""
        for packet in packets:
            switch_idx, port = self.router.get_input_switch_and_port(packet.source)
            self.switches[0][switch_idx].inject_packet(port, packet)
            packet.record_position(0, switch_idx)

    def _process_stage(self, stage: int) -> List[Tuple[Optional[Packet], Optional[Packet]]]:
        """Processa tutti gli switch di uno stadio."""
        outputs = []
        for sw in self.switches[stage]:
            upper_out, lower_out = sw.process(self.num_stages)
            outputs.append((upper_out, lower_out))
        return outputs

    def _propagate_to_next_stage(self, stage: int,
                                  stage_outputs: List[Tuple[Optional[Packet], Optional[Packet]]]):
        """Propaga i pacchetti dallo stadio corrente al successivo."""
        for switch_idx, (upper_out, lower_out) in enumerate(stage_outputs):
            for output_port, packet in enumerate([upper_out, lower_out]):
                if packet is not None and packet.status == PacketStatus.IN_TRANSIT:
                    next_switch, next_port = self.router.get_next_destination(
                        stage, switch_idx, output_port
                    )
                    self.switches[stage + 1][next_switch].inject_packet(next_port, packet)
                    packet.record_position(stage + 1, next_switch)

    def _deliver_packets(self, stage_outputs: List[Tuple[Optional[Packet], Optional[Packet]]]) -> Tuple[int, int]:
        """Consegna i pacchetti all'uscita dell'ultimo stadio."""
        delivered = 0
        dropped = 0

        for switch_idx, (upper_out, lower_out) in enumerate(stage_outputs):
            for output_port, packet in enumerate([upper_out, lower_out]):
                if packet is not None and packet.status == PacketStatus.IN_TRANSIT:
                    output_index = self.router.get_output_index(switch_idx, output_port)
                    
                    if output_index == packet.destination:
                        packet.mark_delivered(self.current_cycle)
                        delivered += 1
                        self.metrics_collector.record_packet_delivered(packet)
                        if self._on_packet_event:
                            self._on_packet_event("delivered", packet)
                    else:
                        # Misrouting - non dovrebbe accadere in una rete Banyan corretta
                        # ma gestiamo il caso per robustezza
                        packet.mark_dropped()
                        dropped += 1
                        self.metrics_collector.record_packet_dropped(packet)

        return delivered, dropped

    def _count_buffered_packets(self) -> int:
        """Conta i pacchetti attualmente nei buffer."""
        count = 0
        for stage_switches in self.switches:
            for sw in stage_switches:
                count += sw.input_upper.buffer_occupancy
                count += sw.input_lower.buffer_occupancy
        return count

    def _cleanup_packets(self):
        """Rimuove i pacchetti completati dalla lista attiva."""
        self._active_packets = [
            p for p in self._active_packets
            if p.status == PacketStatus.IN_TRANSIT or p.status == PacketStatus.BUFFERED
        ]

    def get_aggregate_metrics(self) -> AggregateMetrics:
        """Restituisce le metriche aggregate correnti."""
        return self.metrics_collector.compute_aggregate_metrics(self.switches)

    def get_network_state(self) -> dict:
        """Restituisce lo stato corrente della rete per la visualizzazione."""
        state = {
            "cycle": self.current_cycle,
            "stages": [],
            "active_packets": [],
            "connections": [],
        }

        for stage_idx, stage_switches in enumerate(self.switches):
            stage_state = []
            for sw in stage_switches:
                sw_state = {
                    "stage": sw.stage,
                    "position": sw.position,
                    "upper_occupied": sw.input_upper.is_occupied,
                    "lower_occupied": sw.input_lower.is_occupied,
                    "upper_buffer": sw.input_upper.buffer_occupancy,
                    "lower_buffer": sw.input_lower.buffer_occupancy,
                    "utilization": sw.utilization,
                    "conflicts": sw.total_conflicts,
                }
                stage_state.append(sw_state)
            state["stages"].append(stage_state)

        for packet in self._active_packets:
            if packet.status in (PacketStatus.IN_TRANSIT, PacketStatus.BUFFERED):
                state["active_packets"].append({
                    "id": packet.packet_id,
                    "source": packet.source,
                    "destination": packet.destination,
                    "stage": packet.current_stage,
                    "position": packet.current_position,
                    "status": packet.status.value,
                })

        return state

    def get_switch_stats(self) -> List[List[dict]]:
        """Restituisce le statistiche dettagliate per ogni switch."""
        stats = []
        for stage_switches in self.switches:
            stage_stats = []
            for sw in stage_switches:
                stage_stats.append({
                    "stage": sw.stage,
                    "position": sw.position,
                    "packets_processed": sw.total_packets_processed,
                    "conflicts": sw.total_conflicts,
                    "packets_dropped": sw.total_packets_dropped,
                    "packets_buffered": sw.total_packets_buffered,
                    "utilization": sw.utilization,
                    "conflict_rate": sw.conflict_rate,
                })
            stats.append(stage_stats)
        return stats