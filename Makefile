.PHONY: install train evaluate api frontend docker test lint clean help

## Install all Python dependencies
install:
	pip install -r requirements.txt

## Download the RAVDESS dataset
data:
	bash scripts/download_data.sh

## Train the model (add GRID=1 for grid search)
train:
	cd src && python train.py --data-path ../data/raw $(if $(GRID),--grid-search,)

## Evaluate the trained model
evaluate:
	cd src && python evaluate.py --data-path ../data/raw

## Start the FastAPI backend (dev mode)
api:
	PYTHONPATH=src uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

## Start the React frontend (dev mode)
frontend:
	cd frontend && npm install && npm run dev

## Open MLflow UI
mlflow:
	mlflow ui --host 0.0.0.0 --port 5000

## Build and start all services with Docker Compose
docker:
	docker-compose up --build

## Stop Docker services
docker-stop:
	docker-compose down

## Run all tests
test:
	pytest tests/ -v

## Lint Python code
lint:
	ruff check src/ api/ tests/

## Check model accuracy gate
gate:
	python scripts/accuracy_gate.py --threshold 0.65

## Check prediction drift
drift:
	python monitoring/drift_detector.py

## Save current prediction distribution as baseline
baseline:
	python monitoring/drift_detector.py --save-baseline

## Clean generated files
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
	rm -rf .pytest_cache htmlcov .coverage

help:
	@grep -E '^##' Makefile | sed 's/## //'