.PHONY: help install dev prod

APP_MODULE ?= src.main:app
HOST ?= 127.0.0.1
PORT ?= 8000

help:
	@echo "make install  - install dependencies via uv"
	@echo "make dev      - run uvicorn with reload"
	@echo "make prod     - run uvicorn (no reload)"

install:
	uv sync

dev:
	uv run uvicorn $(APP_MODULE) --reload --host $(HOST) --port $(PORT)

prod:
	uv run uvicorn $(APP_MODULE) --host 0.0.0.0 --port $(PORT)
