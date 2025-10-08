# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Structure & Branch Strategy

**CRITICAL: Always verify which branch you are working on before making changes.**

### Remote Repositories
- **upstream**: https://github.com/tolwi/hassio-ecoflow-cloud.git (original project)
- **origin**: https://github.com/NEXTAltair/hassio-ecoflow-cloud.git (your fork)

### Branch Purposes

#### `main` branch - **KEEP CLEAN**
**Purpose**: Upstream sync + minimal DeltaPro3 support changes only
- Merge latest changes from `upstream/main`
- Contains ONLY essential code changes for DeltaPro3 support
- **NO development artifacts, documentation, scripts, or AI assistant configurations**
- Ready to create pull requests to upstream at any time
- Changed files should be limited to:
  - `custom_components/ecoflow_cloud/` (core integration code only)
  - Essential configuration files if absolutely necessary

#### `dev` branch - **DEVELOPMENT WORKSPACE** (Current branch)
**Purpose**: Active development, experimentation, and all supporting materials
- Contains AI assistant configurations (`.claude/`, `.cursor/`)
- Development documentation (`docs_4ai/`)
- Research scripts (`scripts/`)
- Development tools (`.devcontainer/`, `Makefile`, `CLAUDE.md`)
- Work-in-progress features and experiments
- **~79 files** differ from main branch - this is intentional

**File categories in dev branch:**
- `.claude/`, `.cursor/` - AI assistant configurations
- `docs_4ai/` - Development documentation and specifications
- `scripts/` - Testing, debugging, and research scripts
- `.devcontainer/`, `.vscode/` - Development environment setup
- `CLAUDE.md`, `Makefile` - Development tooling

### Working with Branches

**Before making ANY changes:**
1. Run `git branch` to verify current branch
2. Ask yourself: "Does this change need to go to upstream?"
   - YES → Ensure you're on `main`, keep changes minimal
   - NO → Switch to `dev` branch

**When syncing with upstream:**
```bash
git checkout main
git fetch upstream
git merge upstream/main
# Only commit DeltaPro3-related changes
```

**When working on features/experiments:**
```bash
git checkout dev
# All development work, scripts, docs go here
```

### Pre-Task Checklist for Claude Code

**MANDATORY: Execute this checklist at the start of EVERY session:**

1. **Verify current branch**
   ```bash
   git branch
   ```
   - Expected: `* dev` for development work
   - If on `main`: STOP and confirm with user before proceeding

2. **Understand the task scope**
   - Is this a core integration change that should go to upstream? → Use `main`
   - Is this development/research/tooling? → Use `dev`
   - When in doubt, ASK THE USER

3. **Review uncommitted changes**
   ```bash
   git status
   ```
   - Identify which branch these changes belong to
   - Never mix dev-only files with main branch commits

### Files that should NEVER be on `main` branch
- `.claude/` (entire directory)
- `.cursor/` (entire directory)
- `docs_4ai/` (entire directory)
- `scripts/` (dev-specific scripts)
- `.devcontainer/post-start.sh` (dev customization)
- `.vscode/tasks.json`
- `CLAUDE.md` (this file)
- `Makefile`
- `.python-version`
- `.gitattributes` (dev-only merge strategy)
- Any test/debug/research scripts

**Note**: `.devcontainer/devcontainer.json` exists in both branches:
- `main`: Uses upstream version (minimal config)
- `dev`: Extended with AI tools and custom setup

## Branch Separation Implementation

The repository uses the following mechanisms to keep branches separate:

### 1. .gitignore (on main branch)
The `main` branch `.gitignore` excludes all dev-only files, preventing accidental commits:
```gitignore
# Development-only files
.claude/
.cursor/
docs_4ai/
scripts/delta_pro3_*/
.devcontainer/post-start.sh
CLAUDE.md
Makefile
.python-version
```

### 2. .gitattributes (on dev branch)
The `dev` branch `.gitattributes` prevents dev customizations from overwriting main during merges:
```gitattributes
.devcontainer/devcontainer.json merge=ours
.devcontainer/post-start.sh merge=ours
.gitignore merge=ours
```

### 3. Recommended Workflow

**Syncing upstream changes to main:**
```bash
git checkout main
git fetch upstream
git merge upstream/main
# Main is now clean with upstream changes
```

**Cherry-picking DeltaPro3 changes from dev to main:**
```bash
git checkout main
git cherry-pick <commit-hash>  # Pick only core code commits
# Only include custom_components/ecoflow_cloud/ changes
```

**Merging main updates into dev:**
```bash
git checkout dev
git merge main
# .gitattributes ensures dev configs aren't overwritten
```

**Creating PR to upstream:**
```bash
git checkout main
# Verify only DeltaPro3 core changes exist
git diff upstream/main
# Create PR from main branch
```

## Overview

EcoFlow Cloud Integration is a Home Assistant custom component that connects to EcoFlow power stations via their cloud APIs and MQTT brokers. It supports both private API (username/password) and public API (access/secret keys) authentication methods.

## Development Setup

For setting up the development environment, refer to `docs/Contribution.md` for dev container setup with VS Code.

### Common Development Tasks

Available VS Code tasks (run via `Ctrl+Shift+P` → "Tasks: Run Task"):
- **Reset homeassistant**: Sets up fresh Home Assistant config directory with necessary folders (config, .storage, deps) and basic configuration.yaml
- **Generate Docs**: Updates device documentation by running `docs/gen.py` which generates device summaries and creates individual device markdown files
- **Run Home Assistant Core**: Starts local Home Assistant instance for testing the integration

## Testing & Quality

**Important**: There are currently no automated tests. All testing must be done manually by running Home Assistant locally and testing the integration.

After making changes:
1. Test manually with Home Assistant using the "Run Home Assistant Core" task
2. Run the "Generate Docs" task to update device documentation 
3. Replace the "Current state" section in README.md with content from generated `summary.md`

## Architecture

### API Clients
- **Private API** (`api/private_api.py`): Uses username/password authentication with `api.ecoflow.com`
- **Public API** (`api/public_api.py`): Uses access/secret key authentication with `api-e.ecoflow.com`  
- **MQTT Client** (`api/ecoflow_mqtt.py`): Handles real-time device communication via MQTT

### Device Registry
The `devices/registry.py` maintains an ordered dictionary of all supported devices with their corresponding device classes:
- **Internal devices**: Use private API and direct MQTT communication
- **Public devices**: Use public API endpoints

### Device Structure
- Each device type has both `internal/` and `public/` implementations
- Device classes inherit from `BaseDevice` and handle entity creation
- Protocol buffers are used for binary message parsing (in `devices/internal/proto/`)

### Entity Types
Supports all standard Home Assistant entity types:
- Sensors (battery levels, power measurements, temperatures)
- Switches (AC/DC outputs, features toggles)
- Numbers (charge levels, power limits)
- Selects (timeout settings, charge currents)
- Buttons (device controls)

### Configuration
- Config flow handles device discovery and authentication
- Migration logic in `__init__.py` handles config version upgrades (currently v9)
- Device options include refresh periods, power steps, and diagnostic modes

## Key Files

- `__init__.py`: Main integration setup, config migration, device initialization
- `config_flow.py`: Configuration UI flow for adding devices
- `devices/registry.py`: Central device registry mapping device types to classes
- `api/ecoflow_mqtt.py`: MQTT client for real-time device communication
- `devices/internal/proto/`: Protocol buffer definitions for binary message parsing

## Development Notes

- Device support is added by implementing both internal and public versions
- Each device defines its available sensors, switches, numbers, and selects
- Protocol buffer files are generated from `.proto` definitions
- The integration supports device hierarchies (parent/child relationships)
- Diagnostic mode provides additional debugging sensors
- Entity availability is managed through MQTT connection status

## Dependencies

Key external dependencies:
- `paho-mqtt>=2.1.0`: MQTT client communication
- `protobuf>=5.29.1`: Binary message parsing
- `jsonpath-ng>=1.7.0`: JSON data extraction
- `homeassistant>=2024.5.5`: Home Assistant core

## Scripts Directory

Contains debugging and testing utilities:
- MQTT capture tools for protocol analysis
- Delta Pro 3 specific testing utilities
- Configuration templates for MQTT debugging