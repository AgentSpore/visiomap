.PHONY: install dev lint check smoke test run

install:
	uv sync

dev:
	uv sync --extra dev

lint:
	uv run ruff check src/ --select E,W,F,I --ignore E501

check:
	uv run python -c "from visiomap.main import app; print(f'OK: {app.title} v{app.version}')"

smoke:
	uv run python scripts/smoke_test.py

test: lint check smoke

run:
	uv run uvicorn visiomap.main:app --reload --port 8000
