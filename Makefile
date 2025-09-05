# EcoFlow Cloud Integration Development Makefile
# Provides shortcuts for common development tasks

.PHONY: help setup docs run clean dev

# Default target
help:
	@echo "EcoFlow Cloud Integration Development Commands:"
	@echo ""
	@echo "Setup & Environment:"
	@echo "  setup         - Setup Home Assistant configuration"
	@echo ""
	@echo "Development:"
	@echo "  docs          - Generate device documentation"
	@echo "  run           - Run Home Assistant Core"
	@echo "  dev           - Setup development environment (setup + docs)"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean         - Clean up generated files"
	@echo "  update-readme - Reminder to update README with generated docs"

# Setup & Environment
setup:
	@echo "Setting up Home Assistant configuration..."
	# Create config directory if it doesn't exist
	mkdir -p ./core/config/
	# Generate basic configuration using Home Assistant script
	cd core && hass --script ensure_config -c config
	# Create symlink to custom components
	ln -sf $(PWD)/custom_components ./core/config/custom_components
	@echo "Home Assistant configuration setup complete!"

# Development
docs:
	@echo "Generating device documentation..."
	cd docs && PYTHONPATH=$(PWD):$$PYTHONPATH python gen.py

run:
	@echo "Starting Home Assistant Core..."
	cd core && hass -c ./config

# Development shortcuts
dev: setup docs
	@echo "Development environment ready!"
	@echo "You can now run 'make run' to start Home Assistant"

# Maintenance
clean:
	@echo "Cleaning up generated files in custom_components..."
	find ./custom_components -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find ./custom_components -name "*.pyc" -delete 2>/dev/null || true
	find ./custom_components -name "*.pyo" -delete 2>/dev/null || true

update-readme:
	@echo "Manual step required:"
	@echo "1. Run 'make docs' to generate documentation"
	@echo "2. Replace the 'Current state' section in README.md with content from docs/summary.md"