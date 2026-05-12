"""
Modulo per gli elementi di commutazione (switch) della rete Banyan.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Deque
from collections import deque

from .packet import Packet, PacketStatus
from config.settings import ConflictResolution


@dataclass
class SwitchPort:
    """Porta di uno switch element."""
    packet: Optional[Packet] = None
    buffer: Deque[Packet] = field(default_factory=deque)
    buffer_capacity: int = 4

    @property
    def is_occupied(self) -> bool:
        return self.packet is not None

    @property
    def buffer_occupancy(self) -> int:
        return len(self.buffer)

    @property
    def buffer_full(self) -> bool:
        return len(self.buffer) >= self.buffer_capacity

    def enqueue(self, packet: Packet) -> bool:
        """Inserisce un pacchetto nel buffer. Restituisce False se pieno."""
        if self.buffer_full:
            return False
        self.buffer.append(packet)
        return True

    def dequeue(self) -> Optional[Packet]:
        """Estrae un pacchetto dal buffer."""
        if self.buffer:
            return self.buffer.popleft()
        return None


@dataclass
class SwitchElement:
    """
    Elemento di commutazione 2×2 della rete Banyan.
    Ha 2 ingressi e 2 uscite (upper=0, lower=1).
    """
    stage: int
    position: int
    conflict_resolution: ConflictResolution = ConflictResolution.DROP
    buffer_size: int = 4

    # Porte di ingresso
    input_upper: SwitchPort = field(default_factory=SwitchPort)
    input_lower: SwitchPort = field(default_factory=SwitchPort)

    # Statistiche
    total_packets_processed: int = 0
    total_conflicts: int = 0
    total_packets_dropped: int = 0
    total_packets_buffered: int = 0
    total_packets_deflected: int = 0
    utilization_cycles: int = 0
    total_cycles: int = 0

    def __post_init__(self):
        self.input_upper = SwitchPort(buffer_capacity=self.buffer_size)
        self.input_lower = SwitchPort(buffer_capacity=self.buffer_size)

    def process(self, num_stages: int) -> tuple:
        """
        Processa i pacchetti sulle porte di ingresso e li instrada.
        
        Returns:
            Tuple (output_upper, output_lower) con i pacchetti instradati.
        """
        self.total_cycles += 1
        
        upper_packet = self.input_upper.packet
        lower_packet = self.input_lower.packet

        # Controlla anche i buffer
        if upper_packet is None:
            upper_packet = self.input_upper.dequeue()
        if lower_packet is None:
            lower_packet = self.input_lower.dequeue()

        output_upper: Optional[Packet] = None
        output_lower: Optional[Packet] = None

        if upper_packet is None and lower_packet is None:
            return (None, None)

        self.utilization_cycles += 1

        # Determina la destinazione di ciascun pacchetto
        upper_wants = None
        lower_wants = None

        if upper_packet is not None:
            upper_wants = upper_packet.get_routing_bit(self.stage, num_stages)
            self.total_packets_processed += 1

        if lower_packet is not None:
            lower_wants = lower_packet.get_routing_bit(self.stage, num_stages)
            self.total_packets_processed += 1

        # Caso: nessun conflitto
        if upper_packet is not None and lower_packet is None:
            if upper_wants == 0:
                output_upper = upper_packet
            else:
                output_lower = upper_packet
        elif upper_packet is None and lower_packet is not None:
            if lower_wants == 0:
                output_upper = lower_packet
            else:
                output_lower = lower_packet
        elif upper_packet is not None and lower_packet is not None:
            # Entrambi presenti - verifica conflitto
            if upper_wants != lower_wants:
                # Nessun conflitto: instrada normalmente
                if upper_wants == 0:
                    output_upper = upper_packet
                    output_lower = lower_packet
                else:
                    output_upper = lower_packet
                    output_lower = upper_packet
            else:
                # CONFLITTO: entrambi vogliono la stessa uscita
                self.total_conflicts += 1
                upper_packet.conflicts_encountered += 1
                lower_packet.conflicts_encountered += 1

                winner = upper_packet  # Priorità all'upper
                loser = lower_packet

                if upper_wants == 0:
                    output_upper = winner
                else:
                    output_lower = winner

                # Gestisci il perdente
                self._resolve_conflict(loser, upper_wants)

        # Pulisci le porte di ingresso
        self.input_upper.packet = None
        self.input_lower.packet = None

        return (output_upper, output_lower)

    def _resolve_conflict(self, loser: Packet, contested_output: int):
        """Risolve il conflitto per il pacchetto perdente."""
        if self.conflict_resolution == ConflictResolution.DROP:
            loser.mark_dropped()
            self.total_packets_dropped += 1

        elif self.conflict_resolution == ConflictResolution.BUFFER:
            # Prova a bufferizzare
            port = self.input_upper if contested_output == 0 else self.input_lower
            if port.enqueue(loser):
                loser.status = PacketStatus.BUFFERED
                loser.buffer_waits += 1
                self.total_packets_buffered += 1
            else:
                loser.mark_dropped()
                self.total_packets_dropped += 1

        elif self.conflict_resolution == ConflictResolution.DEFLECTION:
            loser.mark_deflected()
            self.total_packets_deflected += 1

    def inject_packet(self, port: int, packet: Packet):
        """Inietta un pacchetto nella porta specificata (0=upper, 1=lower)."""
        if port == 0:
            self.input_upper.packet = packet
        else:
            self.input_lower.packet = packet

    @property
    def utilization(self) -> float:
        """Percentuale di utilizzo dello switch."""
        if self.total_cycles == 0:
            return 0.0
        return self.utilization_cycles / self.total_cycles

    @property
    def conflict_rate(self) -> float:
        """Tasso di conflitti."""
        if self.total_packets_processed == 0:
            return 0.0
        return self.total_conflicts / (self.total_packets_processed / 2)

    def reset_stats(self):
        """Reset delle statistiche."""
        self.total_packets_processed = 0
        self.total_conflicts = 0
        self.total_packets_dropped = 0
        self.total_packets_buffered = 0
        self.total_packets_deflected = 0
        self.utilization_cycles = 0
        self.total_cycles = 0