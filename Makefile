.PHONY: help dev test lint migrate worker build

help:
	@echo "dev        - Start all services with docker-compose"
	@echo "test       - Run test suite"
	@echo "lint       - Run ruff linter + mypy"
	@echo "migrate    - Run Alembic migrations"
	@echo "worker     - Start Celery worker locally"
	@echo "build      - Build production Docker image"

dev:
	docker compose up --build

test:
	pytest tests/ -v --cov=app --cov-report=term-missing

lint:
	ruff check app tests
	mypy app

migrate:
	alembic upgrade head

new-migration:
	alembic revision --autogenerate -m "$(name)"

worker:
	celery -A app.workers.celery_app worker --loglevel=info

build:
	docker build -t taskflow-api:latest .
