# EcoFlow Cloud Integration Development Makefile
# Provides shortcuts for common development tasks

.PHONY: help run restart stop logs status docs clean

# Default target
help:
	@echo "EcoFlow Cloud Integration Development Commands:"
	@echo ""
	@echo "Development:"
	@echo "  run           - Start Home Assistant (via container launch)"
	@echo "  restart       - Restart Home Assistant (kills and auto-restarts)"
	@echo "  stop          - Stop Home Assistant (disable auto-restart)"
	@echo "  logs          - Show Home Assistant logs (tail -f)"
	@echo "  status        - Check if Home Assistant is running"
	@echo "  docs          - Generate device documentation"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean         - Clean up generated files"

# Development
run:
	@echo "Starting Home Assistant via container launch..."
	@sudo -E container launch

restart:
	@echo "Restarting Home Assistant..."
	@sudo pkill -f 'hass -c /config' || true
	@echo "Waiting for auto-restart (HASS_AUTO_RESTART=true)..."
	@sleep 3
	@echo "Home Assistant should be restarting now."
	@echo "Check status with: make status"

stop:
	@echo "Stopping Home Assistant (disabling auto-restart)..."
	@export HASS_AUTO_RESTART=false && sudo pkill -f 'hass -c /config' || true
	@echo "Home Assistant stopped."

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