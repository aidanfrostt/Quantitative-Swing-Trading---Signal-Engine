# Simple commands — run from the repo root (`make help`).
.PHONY: help install setup dev test

help:
	@echo "Targets:"
	@echo "  make install   pip install -e \".[dev]\""
	@echo "  make setup     first-time: install + Docker + migrations (no API)"
	@echo "  make dev       Docker + migrations + Signal API (foreground)"
	@echo "  make test      ruff + pytest (see scripts/verify_local.sh for more)"

install:
	pip install -e ".[dev]"

setup: install
	./scripts/setup_local.sh

dev:
	./scripts/dev.sh

test:
	./scripts/verify_local.sh
