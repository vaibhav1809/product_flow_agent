.PHONY: help install dev prod pipeline-repository pipeline-query

APP_MODULE ?= src.main:app
HOST ?= 127.0.0.1
PORT ?= 8000
PIPELINE_MODULE ?= src.pipeline.run
APP_NAME ?= Zapmail
VIDEO_PATH ?= /Users/vaibhav/Documents/codes/new_products/product_flow_agent/data/clips/02_organizing_your_emails.mp4
QUERY ?= add a feature of attaching a file to the email before sending

-include .env
export

help:
	@echo "make install  - install dependencies via uv"
	@echo "make pipeline-repository - run pipeline: create_repository"
	@echo "make pipeline-query      - run pipeline: query"

install:
	uv sync

pipeline-repository:
	uv run python -m $(PIPELINE_MODULE) --pipeline-type repository --app-name "$(APP_NAME)" --video_path "$(VIDEO_PATH)"

pipeline-query:
	uv run python -m $(PIPELINE_MODULE) --pipeline-type query --query "$(QUERY)"
