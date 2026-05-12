"""
Configurazione globale del simulatore di rete Banyan.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class RoutingAlgorithm(Enum):
    """Algoritmi di routing supportati."""
    BIT_CONTROLLED = "bit_controlled"
    DESTINATION_TAG = "destination_tag"


class ConflictResolution(Enum):
    """Strategie di risoluzione dei conflitti."""
    DROP = "drop"
    BUFFER = "buffer"
    DEFLECTION = "deflection"


class TrafficPattern(Enum):
    """Pattern di traffico per la generazione dei pacchetti."""
    UNIFORM = "uniform"
    HOTSPOT = "hotspot"
    PERMUTATION = "permutation"
    COMPLEMENT = "complement"
    BIT_REVERSAL = "bit_reversal"
    CUSTOM = "custom"


@dataclass
class SimulationConfig:
    """Configurazione completa della simulazione."""
    # Parametri di rete
    num_inputs: int = 8
    num_stages: Optional[int] = None  # Auto-calcolato se None
    switch_size: int = 2  # 2x2 switch elements

    # Parametri di simulazione
    num_cycles: int = 1000
    packet_generation_rate: float = 0.5  # Probabilità di generare un pacchetto per ciclo
    
    # Algoritmi
    routing_algorithm: RoutingAlgorithm = RoutingAlgorithm.BIT_CONTROLLED
    conflict_resolution: ConflictResolution = ConflictResolution.DROP
    
    # Traffico
    traffic_pattern: TrafficPattern = TrafficPattern.UNIFORM
    hotspot_destination: int = 0
    hotspot_fraction: float = 0.3
    
    # Buffer (se conflict_resolution == BUFFER)
    buffer_size: int = 4
    
    # Visualizzazione
    animation_speed_ms: int = 100
    show_packet_paths: bool = True

    def __post_init__(self):
        """Validazione e calcolo parametri derivati."""
        if self.num_inputs < 2 or (self.num_inputs & (self.num_inputs - 1)) != 0:
            raise ValueError(
                f"num_inputs deve essere una potenza di 2, ricevuto: {self.num_inputs}"
            )
        if self.num_stages is None:
            self.num_stages = self._calculate_stages()
        if not 0.0 <= self.packet_generation_rate <= 1.0:
            raise ValueError(
                f"packet_generation_rate deve essere in [0, 1], ricevuto: {self.packet_generation_rate}"
            )

    def _calculate_stages(self) -> int:
        """Calcola il numero di stadi per una rete Banyan N×N con switch 2×2."""
        import math
        return int(math.log2(self.num_inputs))

    @property
    def num_outputs(self) -> int:
        return self.num_inputs

    @property
    def switches_per_stage(self) -> int:
        return self.num_inputs // self.switch_size