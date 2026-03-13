.PHONY: dev run test smoke lint fmt

dev:
	uv sync --all-extras

run:
	uv run uvicorn visiomap.main:app --reload --host 0.0.0.0 --port 8000

lint:
	uv run ruff check src/

fmt:
	uv run ruff format src/

test: lint smoke

smoke:
	uv run python scripts/smoke_test.py
