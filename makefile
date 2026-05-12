.PHONY: run test clean install lint

# Avvia l'applicazione GUI
run:
	python main.py

# Esegui simulazione batch
batch:
	python main.py --batch --size 16 --cycles 5000 --rate 0.6 --output results.json

# Parameter sweep
sweep:
	python main.py --sweep --sweep-sizes 4,8,16,32 --cycles 2000 --output sweep_results.csv

# Esegui i test
test:
	python -m pytest tests/ -v --tb=short

# Test con coverage
test-cov:
	python -m pytest tests/ -v --cov=core --cov=config --cov-report=html

# Installa dipendenze
install:
	pip install -r requirements.txt
	pip install pytest pytest-cov

# Pulizia
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov .coverage .pytest_cache
	rm -f results.json sweep_results.csv

# Lint
lint:
	python -m flake8 core/ config/ gui/ main.py --max-line-length=100