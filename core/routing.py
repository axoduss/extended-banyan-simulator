"""
Modulo per gli algoritmi di routing nella rete Banyan.
"""
import math
import random
from typing import List, Tuple, Optional

from config.settings import TrafficPattern


class TrafficGenerator:
    """Generatore di traffico per la rete Banyan."""

    def __init__(self, num_inputs: int, num_outputs: int, pattern: TrafficPattern,
                 hotspot_destination: int = 0, hotspot_fraction: float = 0.3):
        self.num_inputs = num_inputs
        self.num_outputs = num_outputs
        self.pattern = pattern
        self.hotspot_destination = hotspot_destination
        self.hotspot_fraction = hotspot_fraction
        self._permutation_map: Optional[List[int]] = None
        self._generate_permutation_map()

    def _generate_permutation_map(self):
        """Genera la mappa di permutazione se necessario."""
        if self.pattern == TrafficPattern.PERMUTATION:
            self._permutation_map = list(range(self.num_outputs))
            random.shuffle(self._permutation_map)

    def generate_destination(self, source: int) -> int:
        """Genera una destinazione in base al pattern di traffico configurato."""
        if self.pattern == TrafficPattern.UNIFORM:
            return random.randint(0, self.num_outputs - 1)

        elif self.pattern == TrafficPattern.HOTSPOT:
            if random.random() < self.hotspot_fraction:
                return self.hotspot_destination
            else:
                return random.randint(0, self.num_outputs - 1)

        elif self.pattern == TrafficPattern.PERMUTATION:
            return self._permutation_map[source]

        elif self.pattern == TrafficPattern.COMPLEMENT:
            return (self.num_outputs - 1) - source

        elif self.pattern == TrafficPattern.BIT_REVERSAL:
            num_bits = int(math.log2(self.num_outputs))
            reversed_bits = 0
            for i in range(num_bits):
                if source & (1 << i):
                    reversed_bits |= (1 << (num_bits - 1 - i))
            return reversed_bits

        else:
            return random.randint(0, self.num_outputs - 1)

    def should_generate_packet(self, rate: float) -> bool:
        """Determina se generare un pacchetto in base al tasso configurato."""
        return random.random() < rate


class BanyanRouter:
    """
    Router per la rete Banyan.
    Gestisce la topologia di interconnessione tra gli stadi.
    """

    def __init__(self, num_inputs: int, num_stages: int):
        self.num_inputs = num_inputs
        self.num_stages = num_stages
        self.num_switches_per_stage = num_inputs // 2
        self._connection_map = self._build_connection_map()

    def _build_connection_map(self) -> List[List[List[Tuple[int, int]]]]:
        """
        Costruisce la mappa di connessione tra gli stadi.
        
        Per una rete Banyan (Omega network), la connessione tra stage s e stage s+1
        segue il pattern di shuffle perfetto (perfect shuffle).
        
        Returns:
            connection_map[stage][switch][output_port] = (next_switch, next_port)
        """
        connection_map = []

        for stage in range(self.num_stages - 1):
            stage_connections = []
            for switch_idx in range(self.num_switches_per_stage):
                switch_connections = []
                for output_port in range(2):  # 0=upper, 1=lower
                    # Calcola l'indice globale dell'uscita
                    global_output = switch_idx * 2 + output_port
                    
                    # Applica perfect shuffle per determinare l'ingresso del prossimo stadio
                    next_global_input = self._perfect_shuffle(
                        global_output, self.num_inputs
                    )
                    
                    # Determina switch e porta di destinazione
                    next_switch = next_global_input // 2
                    next_port = next_global_input % 2
                    
                    switch_connections.append((next_switch, next_port))
                stage_connections.append(switch_connections)
            connection_map.append(stage_connections)

        return connection_map

    @staticmethod
    def _perfect_shuffle(index: int, n: int) -> int:
        """
        Calcola il perfect shuffle di un indice.
        Equivale a una rotazione ciclica a sinistra dei bit.
        """
        num_bits = int(math.log2(n))
        # Rotazione ciclica a sinistra di 1 bit
        shifted = ((index << 1) | (index >> (num_bits - 1))) & (n - 1)
        return shifted

    def get_next_destination(self, stage: int, switch_idx: int, 
                             output_port: int) -> Tuple[int, int]:
        """
        Dato uno stadio, switch e porta di uscita, restituisce
        lo switch e la porta di ingresso del prossimo stadio.
        
        Returns:
            (next_switch_index, next_input_port)
        """
        if stage >= self.num_stages - 1:
            raise ValueError(f"Stage {stage} è l'ultimo stadio, non c'è un prossimo.")
        return self._connection_map[stage][switch_idx][output_port]

    def get_output_index(self, last_stage_switch: int, output_port: int) -> int:
        """Calcola l'indice di uscita finale dalla rete."""
        return last_stage_switch * 2 + output_port

    def get_input_switch_and_port(self, input_index: int) -> Tuple[int, int]:
        """Dato un indice di ingresso, restituisce switch e porta del primo stadio."""
        switch_idx = input_index // 2
        port = input_index % 2
        return switch_idx, port