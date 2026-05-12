# 🔀 Simulatore Rete Banyan

Un simulatore completo e altamente configurabile di reti di interconnessione Banyan (Omega Network)
con interfaccia grafica, metriche in tempo reale e analisi statistica avanzata.

## 🚀 Caratteristiche

- **Reti configurabili**: supporto per reti N×N con N = 4, 8, 16, 32, 64
- **Pattern di traffico multipli**: Uniform, Hotspot, Permutation, Complement, Bit-Reversal
- **Strategie di risoluzione conflitti**: Drop, Buffer, Deflection
- **Visualizzazione in tempo reale**: topologia della rete con animazione dei pacchetti
- **Metriche complete**: throughput, latenza, conflitti, utilizzo switch, fairness
- **Grafici interattivi**: serie temporali con smoothing
- **Esportazione dati**: JSON, CSV, PostScript
- **Modalità batch**: simulazione da riga di comando senza GUI
- **Parameter sweep**: analisi parametrica automatizzata
- **Test suite completa**: unit test e test di integrazione

## 📋 Requisiti

- Python 3.9+
- matplotlib >= 3.7.0
- numpy >= 1.24.0

## 🔧 Installazione

```bash
git clone <repository>
cd banyan_simulator
pip install -r requirements.txt
