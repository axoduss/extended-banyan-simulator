"""
Modulo per la gestione dei pacchetti nella rete Banyan.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import time


class PacketStatus(Enum):
    """Stato corrente del pacchetto."""
    CREATED = "created"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    DROPPED = "dropped"
    BUFFERED = "buffered"
    DEFLECTED = "deflected"


@dataclass
class Packet:
    """Rappresenta un pacchetto nella rete Banyan."""
    packet_id: int
    source: int
    destination: int
    creation_cycle: int
    status: PacketStatus = PacketStatus.CREATED
    current_stage: int = -1
    current_position: int = -1
    delivery_cycle: Optional[int] = None
    hops: int = 0
    path: List[tuple] = field(default_factory=list)
    conflicts_encountered: int = 0
    deflections: int = 0
    buffer_waits: int = 0

    @property
    def latency(self) -> Optional[int]:
        """Calcola la latenza del pacchetto in cicli."""
        if self.delivery_cycle is not None:
            return self.delivery_cycle - self.creation_cycle
        return None

    @property
    def destination_bits(self) -> List[int]:
        """Restituisce i bit della destinazione (MSB first)."""
        bits = []
        dest = self.destination
        # Calcola il numero di bit necessari
        num_bits = max(1, self.destination.bit_length())
        for i in range(num_bits - 1, -1, -1):
            bits.append((dest >> i) & 1)
        return bits

    def get_routing_bit(self, stage: int, num_stages: int) -> int:
        """Restituisce il bit di routing per lo stadio specificato."""
        # Per rete Banyan: usa il bit corrispondente allo stadio
        # Stage 0 usa MSB, stage n-1 usa LSB
        bit_position = num_stages - 1 - stage
        return (self.destination >> bit_position) & 1

    def record_position(self, stage: int, position: int):
        """Registra la posizione corrente nel percorso."""
        self.path.append((stage, position))
        self.current_stage = stage
        self.current_position = position
        self.hops += 1

    def mark_delivered(self, cycle: int):
        """Segna il pacchetto come consegnato."""
        self.status = PacketStatus.DELIVERED
        self.delivery_cycle = cycle

    def mark_dropped(self):
        """Segna il pacchetto come scartato."""
        self.status = PacketStatus.DROPPED

    def mark_deflected(self):
        """Segna il pacchetto come deflesso."""
        self.status = PacketStatus.DEFLECTED
        self.deflections += 1

    def __repr__(self) -> str:
        return (
            f"Packet(id={self.packet_id}, src={self.source}, "
            f"dst={self.destination}, status={self.status.value})"
        )