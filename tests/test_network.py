"""
Test suite per il simulatore di rete Banyan.
"""
import unittest
import sys
from pathlib import Path

# Aggiungi il path del progetto
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import SimulationConfig, TrafficPattern, ConflictResolution
from core.network import BanyanNetwork
from core.packet import Packet, PacketStatus
from core.switch_element import SwitchElement
from core.routing import BanyanRouter, TrafficGenerator
from core.metrics import MetricsCollector


class TestSimulationConfig(unittest.TestCase):
    """Test per la configurazione della simulazione."""

    def test_default_config(self):
        config = SimulationConfig()
        self.assertEqual(config.num_inputs, 8)
        self.assertEqual(config.num_stages, 3)
        self.assertEqual(config.switches_per_stage, 4)

    def test_custom_config(self):
        config = SimulationConfig(num_inputs=16, num_cycles=500)
        self.assertEqual(config.num_inputs, 16)
        self.assertEqual(config.num_stages, 4)
        self.assertEqual(config.num_cycles, 500)

    def test_invalid_num_inputs(self):
        with self.assertRaises(ValueError):
            SimulationConfig(num_inputs=7)

    def test_invalid_rate(self):
        with self.assertRaises(ValueError):
            SimulationConfig(packet_generation_rate=1.5)

    def test_power_of_two_sizes(self):
        for n in [4, 8, 16, 32, 64]:
            config = SimulationConfig(num_inputs=n)
            self.assertEqual(config.num_outputs, n)


class TestPacket(unittest.TestCase):
    """Test per la classe Packet."""

    def test_packet_creation(self):
        pkt = Packet(packet_id=0, source=3, destination=5, creation_cycle=1)
        self.assertEqual(pkt.source, 3)
        self.assertEqual(pkt.destination, 5)
        self.assertEqual(pkt.status, PacketStatus.CREATED)

    def test_routing_bit(self):
        # Destinazione 5 = 101 in binario (3 bit)
        pkt = Packet(packet_id=0, source=0, destination=5, creation_cycle=0)
        # Stage 0 -> MSB (bit 2) = 1
        self.assertEqual(pkt.get_routing_bit(0, 3), 1)
        # Stage 1 -> bit 1 = 0
        self.assertEqual(pkt.get_routing_bit(1, 3), 0)
        # Stage 2 -> LSB (bit 0) = 1
        self.assertEqual(pkt.get_routing_bit(2, 3), 1)

    def test_packet_delivery(self):
        pkt = Packet(packet_id=0, source=0, destination=7, creation_cycle=5)
        pkt.mark_delivered(10)
        self.assertEqual(pkt.status, PacketStatus.DELIVERED)
        self.assertEqual(pkt.latency, 5)

    def test_packet_drop(self):
        pkt = Packet(packet_id=0, source=0, destination=3, creation_cycle=0)
        pkt.mark_dropped()
        self.assertEqual(pkt.status, PacketStatus.DROPPED)

    def test_path_recording(self):
        pkt = Packet(packet_id=0, source=0, destination=7, creation_cycle=0)
        pkt.record_position(0, 0)
        pkt.record_position(1, 2)
        pkt.record_position(2, 3)
        self.assertEqual(len(pkt.path), 3)
        self.assertEqual(pkt.hops, 3)
        self.assertEqual(pkt.current_stage, 2)


class TestSwitchElement(unittest.TestCase):
    """Test per lo switch element."""

    def test_single_packet_upper_to_upper(self):
        sw = SwitchElement(stage=0, position=0)
        # Pacchetto con destinazione 0 (bit 0 al stage 0 di 1 stadio -> va a upper)
        pkt = Packet(packet_id=0, source=0, destination=0, creation_cycle=0)
        pkt.status = PacketStatus.IN_TRANSIT
        sw.inject_packet(0, pkt)
        upper, lower = sw.process(num_stages=1)
        self.assertIsNotNone(upper)
        self.assertIsNone(lower)

    def test_single_packet_upper_to_lower(self):
        sw = SwitchElement(stage=0, position=0)
        # Destinazione 1 -> bit = 1 -> va a lower
        pkt = Packet(packet_id=0, source=0, destination=1, creation_cycle=0)
        pkt.status = PacketStatus.IN_TRANSIT
        sw.inject_packet(0, pkt)
        upper, lower = sw.process(num_stages=1)
        self.assertIsNone(upper)
        self.assertIsNotNone(lower)

    def test_no_conflict(self):
        sw = SwitchElement(stage=0, position=0)
        # Due pacchetti che vogliono uscite diverse
        pkt1 = Packet(packet_id=0, source=0, destination=0, creation_cycle=0)
        pkt2 = Packet(packet_id=1, source=1, destination=1, creation_cycle=0)
        pkt1.status = PacketStatus.IN_TRANSIT
        pkt2.status = PacketStatus.IN_TRANSIT
        sw.inject_packet(0, pkt1)
        sw.inject_packet(1, pkt2)
        upper, lower = sw.process(num_stages=1)
        self.assertIsNotNone(upper)
        self.assertIsNotNone(lower)
        self.assertEqual(sw.total_conflicts, 0)

    def test_conflict_drop(self):
        sw = SwitchElement(stage=0, position=0, conflict_resolution=ConflictResolution.DROP)
        # Due pacchetti che vogliono la stessa uscita (upper, bit=0)
        pkt1 = Packet(packet_id=0, source=0, destination=0, creation_cycle=0)
        pkt2 = Packet(packet_id=1, source=1, destination=0, creation_cycle=0)
        pkt1.status = PacketStatus.IN_TRANSIT
        pkt2.status = PacketStatus.IN_TRANSIT
        sw.inject_packet(0, pkt1)
        sw.inject_packet(1, pkt2)
        upper, lower = sw.process(num_stages=1)
        self.assertEqual(sw.total_conflicts, 1)
        self.assertEqual(sw.total_packets_dropped, 1)

    def test_conflict_buffer(self):
        sw = SwitchElement(
            stage=0, position=0,
            conflict_resolution=ConflictResolution.BUFFER,
            buffer_size=4
        )
        pkt1 = Packet(packet_id=0, source=0, destination=0, creation_cycle=0)
        pkt2 = Packet(packet_id=1, source=1, destination=0, creation_cycle=0)
        pkt1.status = PacketStatus.IN_TRANSIT
        pkt2.status = PacketStatus.IN_TRANSIT
        sw.inject_packet(0, pkt1)
        sw.inject_packet(1, pkt2)
        upper, lower = sw.process(num_stages=1)
        self.assertEqual(sw.total_conflicts, 1)
        self.assertEqual(sw.total_packets_buffered, 1)


class TestBanyanRouter(unittest.TestCase):
    """Test per il router Banyan."""

    def test_perfect_shuffle_4(self):
        # Per N=4: 0->0, 1->2, 2->1, 3->3
        router = BanyanRouter(4, 2)
        self.assertEqual(router._perfect_shuffle(0, 4), 0)
        self.assertEqual(router._perfect_shuffle(1, 4), 2)
        self.assertEqual(router._perfect_shuffle(2, 4), 1)
        self.assertEqual(router._perfect_shuffle(3, 4), 3)

    def test_perfect_shuffle_8(self):
        # Per N=8: rotazione ciclica sinistra di 1 bit su 3 bit
        router = BanyanRouter(8, 3)
        # 0(000)->0(000), 1(001)->2(010), 2(010)->4(100), 3(011)->6(110)
        # 4(100)->1(001), 5(101)->3(011), 6(110)->5(101), 7(111)->7(111)
        expected = [0, 2, 4, 6, 1, 3, 5, 7]
        for i in range(8):
            self.assertEqual(router._perfect_shuffle(i, 8), expected[i])

    def test_input_mapping(self):
        router = BanyanRouter(8, 3)
        # Input 0 -> switch 0, port 0
        self.assertEqual(router.get_input_switch_and_port(0), (0, 0))
        # Input 1 -> switch 0, port 1
        self.assertEqual(router.get_input_switch_and_port(1), (0, 1))
        # Input 4 -> switch 2, port 0
        self.assertEqual(router.get_input_switch_and_port(4), (2, 0))

    def test_output_mapping(self):
        router = BanyanRouter(8, 3)
        self.assertEqual(router.get_output_index(0, 0), 0)
        self.assertEqual(router.get_output_index(0, 1), 1)
        self.assertEqual(router.get_output_index(3, 1), 7)


class TestTrafficGenerator(unittest.TestCase):
    """Test per il generatore di traffico."""

    def test_uniform_traffic(self):
        gen = TrafficGenerator(8, 8, TrafficPattern.UNIFORM)
        destinations = set()
        for _ in range(1000):
            dest = gen.generate_destination(0)
            self.assertGreaterEqual(dest, 0)
            self.assertLess(dest, 8)
            destinations.add(dest)
        # Con 1000 tentativi, dovremmo coprire tutte le destinazioni
        self.assertEqual(len(destinations), 8)

    def test_complement_traffic(self):
        gen = TrafficGenerator(8, 8, TrafficPattern.COMPLEMENT)
        self.assertEqual(gen.generate_destination(0), 7)
        self.assertEqual(gen.generate_destination(1), 6)
        self.assertEqual(gen.generate_destination(7), 0)

    def test_bit_reversal_traffic(self):
        gen = TrafficGenerator(8, 8, TrafficPattern.BIT_REVERSAL)
        # 0(000) -> 0(000)
        self.assertEqual(gen.generate_destination(0), 0)
        # 1(001) -> 4(100)
        self.assertEqual(gen.generate_destination(1), 4)
        # 3(011) -> 6(110)
        self.assertEqual(gen.generate_destination(3), 6)

    def test_hotspot_traffic(self):
        gen = TrafficGenerator(8, 8, TrafficPattern.HOTSPOT,
                               hotspot_destination=3, hotspot_fraction=1.0)
        # Con fraction=1.0, tutto il traffico va all'hotspot
        for _ in range(100):
            self.assertEqual(gen.generate_destination(0), 3)


class TestBanyanNetwork(unittest.TestCase):
    """Test per la rete Banyan completa."""

    def test_network_creation(self):
        config = SimulationConfig(num_inputs=8, num_cycles=100)
        network = BanyanNetwork(config)
        self.assertEqual(len(network.switches), 3)  # 3 stadi
        self.assertEqual(len(network.switches[0]), 4)  # 4 switch per stadio

    def test_single_step(self):
        config = SimulationConfig(num_inputs=8, num_cycles=100, packet_generation_rate=1.0)
        network = BanyanNetwork(config)
        metrics = network.step()
        self.assertIsNotNone(metrics)
        self.assertEqual(network.current_cycle, 1)

    def test_full_simulation(self):
        config = SimulationConfig(num_inputs=8, num_cycles=100, packet_generation_rate=0.5)
        network = BanyanNetwork(config)
        aggregate = network.run_full_simulation()
        self.assertTrue(network.is_complete)
        self.assertGreater(aggregate.total_packets_generated, 0)
        self.assertGreater(aggregate.total_packets_delivered, 0)

    def test_low_load_high_delivery(self):
        """Con carico basso, quasi tutti i pacchetti dovrebbero essere consegnati."""
        config = SimulationConfig(
            num_inputs=8, num_cycles=500,
            packet_generation_rate=0.1,
            conflict_resolution=ConflictResolution.DROP,
        )
        network = BanyanNetwork(config)
        aggregate = network.run_full_simulation()
        # Con carico basso, il tasso di consegna dovrebbe essere alto
        self.assertGreater(aggregate.delivery_rate, 0.7)

    def test_buffer_reduces_drops(self):
        """La strategia buffer dovrebbe ridurre i pacchetti scartati."""
        config_drop = SimulationConfig(
            num_inputs=8, num_cycles=500,
            packet_generation_rate=0.8,
            conflict_resolution=ConflictResolution.DROP,
        )
        config_buffer = SimulationConfig(
            num_inputs=8, num_cycles=500,
            packet_generation_rate=0.8,
            conflict_resolution=ConflictResolution.BUFFER,
            buffer_size=8,
        )

        network_drop = BanyanNetwork(config_drop)
        metrics_drop = network_drop.run_full_simulation()

        network_buffer = BanyanNetwork(config_buffer)
        metrics_buffer = network_buffer.run_full_simulation()

        # Buffer dovrebbe avere meno drop (o uguale nel caso peggiore)
        self.assertLessEqual(metrics_buffer.drop_rate, metrics_drop.drop_rate + 0.1)

        def test_network_reset(self):
        """Test del reset della rete."""
        config = SimulationConfig(num_inputs=8, num_cycles=100, packet_generation_rate=0.5)
        network = BanyanNetwork(config)
        
        # Esegui qualche step
        for _ in range(50):
            network.step()
        
        self.assertEqual(network.current_cycle, 50)
        
        # Reset
        network.reset()
        self.assertEqual(network.current_cycle, 0)
        self.assertFalse(network.is_complete)
        self.assertEqual(len(network.metrics_collector.all_packets), 0)

    def test_network_reconfigure(self):
        """Test della riconfigurazione della rete."""
        config = SimulationConfig(num_inputs=8, num_cycles=100)
        network = BanyanNetwork(config)
        
        new_config = SimulationConfig(num_inputs=16, num_cycles=200)
        network.reconfigure(new_config)
        
        self.assertEqual(network.num_inputs, 16)
        self.assertEqual(network.num_stages, 4)
        self.assertEqual(network.switches_per_stage, 8)
        self.assertEqual(len(network.switches), 4)
        self.assertEqual(len(network.switches[0]), 8)

    def test_different_network_sizes(self):
        """Test con diverse dimensioni di rete."""
        for size in [4, 8, 16, 32]:
            config = SimulationConfig(num_inputs=size, num_cycles=100, packet_generation_rate=0.3)
            network = BanyanNetwork(config)
            aggregate = network.run_full_simulation()
            self.assertTrue(network.is_complete)
            self.assertGreater(aggregate.total_packets_generated, 0)

    def test_all_traffic_patterns(self):
        """Test con tutti i pattern di traffico."""
        patterns = [
            TrafficPattern.UNIFORM,
            TrafficPattern.HOTSPOT,
            TrafficPattern.PERMUTATION,
            TrafficPattern.COMPLEMENT,
            TrafficPattern.BIT_REVERSAL,
        ]
        for pattern in patterns:
            config = SimulationConfig(
                num_inputs=8, num_cycles=100,
                packet_generation_rate=0.5,
                traffic_pattern=pattern,
            )
            network = BanyanNetwork(config)
            aggregate = network.run_full_simulation()
            self.assertTrue(network.is_complete,
                            f"Simulazione non completata per pattern {pattern.value}")
            self.assertGreater(aggregate.total_packets_generated, 0,
                               f"Nessun pacchetto generato per pattern {pattern.value}")

    def test_all_conflict_strategies(self):
        """Test con tutte le strategie di risoluzione conflitti."""
        strategies = [
            ConflictResolution.DROP,
            ConflictResolution.BUFFER,
            ConflictResolution.DEFLECTION,
        ]
        for strategy in strategies:
            config = SimulationConfig(
                num_inputs=8, num_cycles=100,
                packet_generation_rate=0.7,
                conflict_resolution=strategy,
                buffer_size=4,
            )
            network = BanyanNetwork(config)
            aggregate = network.run_full_simulation()
            self.assertTrue(network.is_complete,
                            f"Simulazione non completata per strategia {strategy.value}")

    def test_zero_load(self):
        """Test con carico zero - nessun pacchetto generato."""
        config = SimulationConfig(
            num_inputs=8, num_cycles=100,
            packet_generation_rate=0.0,
        )
        network = BanyanNetwork(config)
        aggregate = network.run_full_simulation()
        self.assertEqual(aggregate.total_packets_generated, 0)
        self.assertEqual(aggregate.total_packets_delivered, 0)

    def test_full_load(self):
        """Test con carico massimo."""
        config = SimulationConfig(
            num_inputs=8, num_cycles=100,
            packet_generation_rate=1.0,
        )
        network = BanyanNetwork(config)
        aggregate = network.run_full_simulation()
        # Con rate=1.0, dovremmo generare circa 8 pacchetti per ciclo
        expected_min = 8 * 100 * 0.8  # Almeno 80% del massimo teorico
        self.assertGreater(aggregate.total_packets_generated, expected_min)

    def test_metrics_consistency(self):
        """Verifica la consistenza delle metriche."""
        config = SimulationConfig(
            num_inputs=8, num_cycles=200,
            packet_generation_rate=0.5,
            conflict_resolution=ConflictResolution.DROP,
        )
        network = BanyanNetwork(config)
        aggregate = network.run_full_simulation()
        
        # Generati = Consegnati + Scartati + In transito (approssimativo)
        accounted = aggregate.total_packets_delivered + aggregate.total_packets_dropped
        self.assertLessEqual(accounted, aggregate.total_packets_generated)
        
        # Tassi devono sommare a <= 1
        self.assertLessEqual(aggregate.delivery_rate + aggregate.drop_rate, 1.01)
        
        # Jain fairness deve essere in [0, 1]
        self.assertGreaterEqual(aggregate.jain_fairness_index, 0.0)
        self.assertLessEqual(aggregate.jain_fairness_index, 1.0)

    def test_latency_bounds(self):
        """Verifica che la latenza sia entro limiti ragionevoli."""
        config = SimulationConfig(
            num_inputs=8, num_cycles=500,
            packet_generation_rate=0.3,
        )
        network = BanyanNetwork(config)
        aggregate = network.run_full_simulation()
        
        if aggregate.min_latency is not None:
            # La latenza minima deve essere almeno il numero di stadi
            self.assertGreaterEqual(aggregate.min_latency, config.num_stages)
            # La latenza media deve essere >= minima
            self.assertGreaterEqual(aggregate.avg_latency, aggregate.min_latency)
            # La latenza massima deve essere >= media
            self.assertGreaterEqual(aggregate.max_latency, aggregate.avg_latency)


class TestMetricsCollector(unittest.TestCase):
    """Test per il collector delle metriche."""

    def test_empty_metrics(self):
        collector = MetricsCollector(8, 8)
        aggregate = collector.compute_aggregate_metrics()
        self.assertEqual(aggregate.total_packets_generated, 0)
        self.assertEqual(aggregate.total_packets_delivered, 0)
        self.assertEqual(aggregate.jain_fairness_index, 1.0)

    def test_throughput_series(self):
        collector = MetricsCollector(8, 8)
        for i in range(10):
            collector.record_cycle(i, 4, 2, 1, 3, 0, 1)
        
        series = collector.get_throughput_series()
        self.assertEqual(len(series), 10)

    def test_percentile_calculation(self):
        data = list(range(1, 101))  # 1 to 100
        p50 = MetricsCollector._percentile(data, 50)
        self.assertAlmostEqual(p50, 50.5, places=1)
        
        p95 = MetricsCollector._percentile(data, 95)
        self.assertAlmostEqual(p95, 95.05, places=1)


class TestIntegration(unittest.TestCase):
    """Test di integrazione end-to-end."""

    def test_small_network_deterministic(self):
        """Test deterministico con rete 4x4."""
        import random
        random.seed(42)
        
        config = SimulationConfig(
            num_inputs=4, num_cycles=50,
            packet_generation_rate=0.5,
            traffic_pattern=TrafficPattern.UNIFORM,
            conflict_resolution=ConflictResolution.DROP,
        )
        network = BanyanNetwork(config)
        aggregate = network.run_full_simulation()
        
        # Verifica che la simulazione produca risultati consistenti
        self.assertEqual(network.current_cycle, 50)
        self.assertTrue(network.is_complete)

    def test_network_state_snapshot(self):
        """Test dello snapshot dello stato della rete."""
        config = SimulationConfig(num_inputs=8, num_cycles=10, packet_generation_rate=0.8)
        network = BanyanNetwork(config)
        network.step()
        
        state = network.get_network_state()
        self.assertIn("cycle", state)
        self.assertIn("stages", state)
        self.assertIn("active_packets", state)
        self.assertEqual(state["cycle"], 1)
        self.assertEqual(len(state["stages"]), 3)

    def test_switch_stats(self):
        """Test delle statistiche per switch."""
        config = SimulationConfig(num_inputs=8, num_cycles=100, packet_generation_rate=0.5)
        network = BanyanNetwork(config)
        network.run_full_simulation()
        
        stats = network.get_switch_stats()
        self.assertEqual(len(stats), 3)  # 3 stadi
        self.assertEqual(len(stats[0]), 4)  # 4 switch per stadio
        
        for stage_stats in stats:
            for sw_stat in stage_stats:
                self.assertIn("utilization", sw_stat)
                self.assertIn("conflicts", sw_stat)
                self.assertGreaterEqual(sw_stat["utilization"], 0.0)
                self.assertLessEqual(sw_stat["utilization"], 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)