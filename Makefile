# EcoFlow Cloud Integration Development Makefile
# Provides shortcuts for common development tasks
# Note: Home Assistant starts automatically via .devcontainer/post-start.sh

.PHONY: help logs status docs clean

# Default target
help:
	@echo "EcoFlow Cloud Integration Development Commands:"
	@echo ""
	@echo "Development:"
	@echo "  logs          - Show Home Assistant logs (tail -f)"
	@echo "  status        - Check if Home Assistant is running"
	@echo "  docs          - Generate device documentation"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean         - Clean up generated files"
	@echo ""
	@echo "Note: Home Assistant starts automatically when container starts"
	@echo "      Use Home Assistant GUI to restart if needed"

# Development
logs:
	@echo "Showing Home Assistant logs (Ctrl+C to exit)..."
	@tail -f /config/home-assistant.log

status:
	@echo "Checking Home Assistant status..."
	@ps aux | grep 'hass -c /config' | grep -v grep && echo "✅ Home Assistant is running" || echo "❌ Home Assistant is not running"

docs:
	@echo "Generating device documentation..."
	@cd docs && PYTHONPATH=$(PWD):$$PYTHONPATH python gen.py

# Maintenance
clean:
	@echo "Cleaning up generated files in custom_components..."
	@find ./custom_components -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find ./custom_components -name "*.pyc" -delete 2>/dev/null || true
	@find ./custom_components -name "*.pyo" -delete 2>/dev/null || true
	@echo "Cleanup complete."