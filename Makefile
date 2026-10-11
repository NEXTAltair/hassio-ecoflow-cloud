# Development-only shortcuts; keep separate from upstream contributions.
.PHONY: help check lint typecheck smoke versions status logs docs

help:
	@echo "make check | lint | typecheck | smoke | versions | status | logs | docs"
	@echo "Run inside the development container; see .devcontainer/README.md."

check lint typecheck smoke versions status logs docs:
	@bash .devcontainer/dev.sh $@
