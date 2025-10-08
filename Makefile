# EcoFlow Cloud Integration Development Makefile
# Provides shortcuts for common development tasks

.PHONY: help  run clean

# Default target
help:
	@echo "EcoFlow Cloud Integration Development Commands:"
	@echo ""
	@echo "Development:"
	@echo "  run           - Run Home Assistant Core"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean         - Clean up generated files"

# Development
docs:
	@echo "Generating device documentation..."
	cd docs && PYTHONPATH=$(PWD):$$PYTHONPATH python gen.py

run:
	@echo "Starting Home Assistant Core..."
	cd core && hass -c ./config

# Maintenance
clean:
	@echo "Cleaning up generated files in custom_components..."
	find ./custom_components -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find ./custom_components -name "*.pyc" -delete 2>/dev/null || true
	find ./custom_components -name "*.pyo" -delete 2>/dev/null || tru