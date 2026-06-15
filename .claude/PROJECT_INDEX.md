# Workspace Codebase Index

## Overview
This document provides a concise index of the projects within the `workspace` directory, outlining their core purpose, architectural highlights, key files, and dependencies where discernible from the file structure.

---

## Projects

### 1-line-deploy
- **Core Purpose**: Simplifies deployment processes for various services (Homepage, NetBox Agent, Proxmox Agent, WikiJS Integration) with single-line commands. Focuses on automation and streamlined infrastructure management.
- **Architecture**: Script-based deployment leveraging shell scripts (`ct/`). Integrates with configuration management (`MCP_CONFIGURATION.md`).
- **Key Files**:
    - `Architecture-Integration.md`: High-level architectural overview.
    - `ct/homepage.sh`: Homepage deployment script.
    - `ct/netbox-agent.sh`: NetBox agent deployment script.
    - `ct/proxmox-agent.sh`: Proxmox agent deployment script.
    - `ct/wikijs-integration.sh`: WikiJS integration deployment script.
    - `MCP_CONFIGURATION.md`: Configuration details for MCP.
- **Dependencies**: MCP (Master Control Program) for configuration, various target services (Homepage, NetBox, Proxmox, WikiJS).

### 3ddash
- **Core Purpose**: Dashboard for 3D-related activities, likely integrating with smart home or visualization systems. Documentation suggests setup, dashboard elements, activity scenes, sensors, and styling.
- **Architecture**: Step-by-step implementation guide suggests a modular approach.
- **Key Files**:
    - `01_setup_and_installation.md` to `06_testing_and_validation.md`: Step-by-step guides.
    - `INDEX.md`, `QUICK_REFERENCE.md`: Documentation.
- **Dependencies**: Undefined, but likely Home Assistant or similar smart home platforms based on common use cases for dashboards and sensors.

### 3d-print
- **Core Purpose**: Stores G-code and STL files for various 3D printing projects, including specialized components for BirdnetGone, camera mounts, and home fixtures. Includes configuration profiles and tooling for managing them.
- **Architecture**: A collection of 3D models and print configurations. Scripts for profile synchronization.
- **Key Files**:
    - `.gitleaks.toml`: Security configuration for detecting sensitive information.
    - `.pre-commit-config.yaml`: Pre-commit hooks for code quality/standards.
    - `CLAUDE.md`: Claude AI related documentation for 3d-print.
    - `model-catalog-3mf-feature-prompt.md`: Likely documentation for 3MF features in a model catalog.
    - `sync-profiles.sh`: Script to synchronize printer profiles.
    - Numerous `.gcode`, `.stl`, `.3mf` files.
- **Dependencies**: PrusaSlicer (implied by `.gcode` and `.3mf` files), 3D printers, potentially Home Assistant for integrations (implied by `birdnet_shell`).

### api
- **Core Purpose**: Provides various API endpoints, including configuration loading, CSV export, email notifications, GitHub/MCP management, and integration with Serena and Wiki Agent. Features a v2 server and websocket capabilities.
- **Architecture**: Node.js based (package.json, server.js, server-v2.js), using Jest for testing. Integrates with MCP and Serena.
- **Key Files**:
    - `package.json`: Project dependencies and scripts.
    - `server.js`, `server-v2.js`: Main API server implementations.
    - `websocket-server.js`: WebSocket functionality.
    - `mcp-connector.js`: Connects to MCP.
    - `serena-orchestrator.js`: Orchestrates Serena interactions.
    - `wiki-agent-manager.js`: Manages Wiki Agent interactions.
    - `jest.config.js`: Jest test configuration.
- **Dependencies**: Node.js, Express.js (implied), MCP, Serena, WikiJS, Jest.

### biometric-gateway
- **Core Purpose**: A biometric gateway application, likely handling authentication or data processing related to biometric inputs.
- **Architecture**: Go-based application (`go.mod`, `main.go` likely in `cmd/`). Structured with internal packages, scripts, and tests. Dockerized deployment.
- **Key Files**:
    - `go.mod`, `go.sum`: Go module dependencies.
    - `Dockerfile`: Docker build instructions.
    - `cmd/`: Main application entry points.
    - `internal/`: Internal Go packages.
- **Dependencies**: Go, Docker.

### birdnet-go
- **Core Purpose**: A Go-based application for bird sound detection, likely an evolution or alternative to `birdnet-gone`. Features a frontend, data processing, and various deployment options.
- **Architecture**: Go backend (`main.go`, `internal/`) with a frontend (potentially React/Vue based on `package.json`, `tailwind.config.js`). Docker and Podman support.
- **Key Files**:
    - `main.go`: Main Go application.
    - `frontend/`: Frontend application code.
    - `go.mod`, `go.sum`: Go module dependencies.
    - `package.json`: Frontend dependencies.
    - `Dockerfile`: Docker build instructions.
    - `tailwind.config.js`: Tailwind CSS configuration.
    - `ARCHITECTURE.md`: Architecture documentation.
- **Dependencies**: Go, Tailwind CSS, potentially Node.js/npm for frontend build, Docker/Podman.

### birdnet-gone
- **Core Purpose**: A Go-based application for bird sound detection and monitoring, with a focus on deployment and firmware. Features a frontend, data processing, and integration with Vicohome.
- **Architecture**: Go backend (`main.go`, `internal/`) with a frontend (likely static assets served by Go). Includes firmware components and a Vicohome bridge. Dockerized.
- **Key Files**:
    - `main.go`: Main Go application.
    - `frontend/`: Frontend assets.
    - `firmware/`: Firmware source code.
    - `vicohome-bridge/`: Integration with Vicohome.
    - `go.mod`, `go.sum`: Go module dependencies.
    - `Dockerfile`, `docker-compose.yml`: Docker configuration.
    - `ARCHITECTURE.md`: Architecture documentation.
    - `TESTING.md`: Testing documentation.
- **Dependencies**: Go, Docker, Vicohome API/protocol, ESP32S3 (implied by firmware).

### communications
- **Core Purpose**: Manages communication functionalities, likely a messaging or notification system.
- **Architecture**: Source code in `src/`, with scripts and documentation.
- **Key Files**:
    - `src/`: Source code.
    - `docs/`: Documentation.
    - `scripts/`: Utility scripts.
- **Dependencies**: Undefined, but could be a Go, Python, or Node.js project.

### dashboard
- **Core Purpose**: A web-based dashboard application, possibly for monitoring or displaying information from other services.
- **Architecture**: Frontend application (Vite, TypeScript, React implied by `vite.config.ts`, `tsconfig.json`, `package.json`). Uses Tailwind CSS. Python proxy server.
- **Key Files**:
    - `package.json`: Frontend dependencies.
    - `src/`: Frontend source code.
    - `vite.config.ts`, `tsconfig.json`: Vite and TypeScript configuration.
    - `tailwind.config.js`: Tailwind CSS configuration.
    - `proxy-server.py`: Python proxy.
- **Dependencies**: Node.js/npm, Vite, TypeScript, React (likely), Tailwind CSS, Python.

### docs
- **Core Purpose**: Comprehensive documentation for various aspects of the homelab and associated projects, including deployment plans, security, network configuration, and operational procedures.
- **Architecture**: A collection of Markdown documents.
- **Key Files**:
    - `3-TIER-DEPLOYMENT.md`, `DEPLOYMENT-PLANS-SUMMARY.md`: Deployment strategies.
    - `SECURITY-SCANNING-DEPLOYMENT-PLAN.md`: Security documentation.
    - `homelab-networking-reference.md`: Network configuration.
    - `PROXMOX_MAINTENANCE_PROCEDURES.md`: Proxmox operational guides.
- **Dependencies**: Markdown reader.

### finances
- **Core Purpose**: Manages financial data and related processes.
- **Architecture**: Data in `data/`, scripts for processing, and documentation. Infrastructure-related files in `infra/`.
- **Key Files**:
    - `data/`: Financial data.
    - `scripts/`: Data processing scripts.
    - `docs/`: Documentation.
    - `infra/`: Infrastructure definitions.
- **Dependencies**: Undefined, likely Python or another scripting language for data processing.

### fitbit-dashboard
- **Core Purpose**: A Python-based dashboard for visualizing Fitbit and Apple Health data.
- **Architecture**: Python Flask application (`app.py`) with data loaders for Fitbit and Apple Health. Uses `requirements.txt` for dependencies. Includes scripts and tests.
- **Key Files**:
    - `app.py`: Main Flask application.
    - `fitbit_loader.py`, `apple_health_loader.py`: Data loading scripts.
    - `requirements.txt`: Python dependencies.
    - `charts.py`: Charting logic.
    - `insights.py`: Data insights.
- **Dependencies**: Python, Flask, Fitbit API, Apple Health data.

### github-actions-runner
- **Core Purpose**: Manages GitHub Actions self-hosted runners, including deployment, backups, logging, and Nginx configuration.
- **Architecture**: Docker Compose based deployment, with Fluent Bit for logging and Nginx for proxying.
- **Key Files**:
    - `docker-compose.yml.backup`: Docker Compose configuration.
    - `fluent-bit/`: Fluent Bit configuration.
    - `nginx/`: Nginx configuration.
    - `deploy/`: Deployment scripts.
- **Dependencies**: Docker, Docker Compose, GitHub Actions, Fluent Bit, Nginx.

### gw4-config-tool
- **Core Purpose**: A configuration tool, likely web-based (HTML, CSS, JS), for managing settings related to "gw4" (Gateway 4).
- **Architecture**: Frontend application using HTML, CSS, JavaScript, and Gulp for task automation.
- **Key Files**:
    - `index.html`: Main HTML file.
    - `js/`, `css/`: JavaScript and CSS files.
    - `gulpfile.js`: Gulp build configuration.
    - `package.json`: Node.js dependencies.
- **Dependencies**: Node.js/npm, Gulp.js.

### hass-ab-ble-gateway-suite
- **Core Purpose**: A suite of tools and configurations for Home Assistant related to Bluetooth Low Energy (BLE) gateways, including various dashboard layouts and custom components.
- **Architecture**: Home Assistant custom components and configurations (YAML files for dashboards). Python for scripts and tests.
- **Key Files**:
    - `custom_components/`: Home Assistant custom components.
    - `*_dashboard.yaml`: Various dashboard configurations.
    - `README.md`, `setup_instructions.md`: Documentation.
    - `requirements.txt`: Python dependencies.
- **Dependencies**: Home Assistant, Python.

### heydj
- **Core Purpose**: A project related to "heydj", possibly an audio or media management system.
- **Architecture**: Documentation, scripts, and tests. Metadata in `metadata/`.
- **Key Files**:
    - `docs/`: Documentation.
    - `scripts/`: Utility scripts.
    - `metadata/`: Metadata files.
- **Dependencies**: Undefined.

### home-assistant-config
- **Core Purpose**: Comprehensive configuration for Home Assistant, including automations, scripts, sensors, and integrations with various devices and services (BLE, Broadlink, MQTT, ESPHome, Zigbee2MQTT, Z-Wave JS).
- **Architecture**: YAML-based Home Assistant configuration, with Python scripts for entity management and migration tools. Includes dashboards and custom components.
- **Key Files**:
    - `configuration.yaml`: Main Home Assistant configuration.
    - `automations.yaml`, `scripts.yaml`, `sensors.yaml`, `lights.yaml`: Various component configurations.
    - `custom_components/`: Custom Home Assistant components.
    - `python_scripts/`: Python scripts for Home Assistant.
    - `dashboards/`: Dashboard configurations.
    - `zigbee2mqtt/`, `esphome/`: Integration configurations.
- **Dependencies**: Home Assistant, Python, various smart home devices and integrations (BLE, Broadlink, MQTT, ESPHome, Zigbee2MQTT, Z-Wave JS).

### homelab-gitops
- **Core Purpose**: Manages the homelab infrastructure using GitOps principles, including CI/CD pipelines, automated documentation, Infisical integration, and various MCP servers.
- **Architecture**: Extensive GitOps setup with Docker Compose, Node.js APIs, Python scripts, and documentation. Integrates with Infisical for secret management and WikiJS for documentation.
- **Key Files**:
    - `README.md`, `PROJECT_OVERVIEW.md`, `ROADMAP-2025.md`: Project documentation.
    - `CI_CD_PIPELINE_IMPLEMENTATION.md`: CI/CD pipeline details.
    - `docker-compose.production.yml`: Production Docker Compose.
    - `api/`, `frontend/`: API and frontend components.
    - `mcp-servers/`, `mcp-enhanced-servers/`: MCP server implementations.
    - `upload-docs-to-wiki.js`, `wikijs-ai-content-processor.js`: WikiJS integration.
    - `INFISICAL_INTEGRATION.md`: Infisical integration documentation.
- **Dependencies**: Git, Docker, Docker Compose, Node.js, Python, Infisical, WikiJS, MCP.

### homelab-iac
- **Core Purpose**: Infrastructure as Code for the homelab, using Ansible and Terraform to manage infrastructure provisioning and configuration.
- **Architecture**: Ansible playbooks in `ansible/` and Terraform configurations in `terraform/`.
- **Key Files**:
    - `ansible/`: Ansible playbooks and roles.
    - `terraform/`: Terraform configurations.
    - `README.md`: Project overview.
- **Dependencies**: Ansible, Terraform.

### mcp-enhanced-servers
- **Core Purpose**: Contains enhanced MCP (Master Control Program) server components, including a directory polling system and Serena documentation tools.
- **Architecture**: Python-based server components.
- **Key Files**:
    - `directory-polling-system.py`: Directory polling script.
    - `serena-documentation-tools.py`: Serena documentation tools.
- **Dependencies**: Python, MCP, Serena.

### mcp-servers
- **Core Purpose**: Collection of various MCP (Master Control Program) servers, each handling specific functionalities like Claude auto-commit, code linting, directory polling, Gmail management, network operations, Proxmox integration, memory search, TrueNAS, and Vikunja.
- **Architecture**: Each subdirectory represents a distinct MCP server, likely implemented in Node.js (implied by `package.json` at root, and subdirs like `claude-auto-commit-mcp-server`).
- **Key Files**:
    - `claude-auto-commit-mcp-server/`: Claude auto-commit functionality.
    - `code-linter-mcp-server/`: Code linting server.
    - `directory-polling-server/`: Directory polling server.
    - `gmail-manage-mcp-server/`: Gmail management server.
    - `network-mcp-server/`: Network operations server.
    - `proxmox-mcp-server/`: Proxmox integration server.
    - `memory-search-mcp-server/`: Memory search server.
    - `truenas-mcp-server/`: TrueNAS integration server.
    - `vikunja-mcp-server/`: Vikunja integration server.
    - `package.json`: Dependencies for the servers.
- **Dependencies**: MCP framework, Node.js (likely), various APIs for integrated services (Claude, Gmail, Proxmox, TrueNAS, Vikunja).

### model-catalog
- **Core Purpose**: A catalog and management system for AI models and agents, including a frontend, CLI, and deployment tools.
- **Architecture**: Python-based backend (`pyproject.toml`, `app/`, `cli/`) with a frontend (`frontend/`) and deployment scripts.
- **Key Files**:
    - `app/`: Application code.
    - `cli/`: Command-line interface.
    - `frontend/`: Frontend code.
    - `pyproject.toml`: Python project configuration.
    - `deploy/`: Deployment scripts.
    - `AGENTS.md`, `INITIAL_TASKS.md`: Documentation on agents and initial setup.
- **Dependencies**: Python, potentially a frontend framework (React/Vue/Angular), Docker (implied by `deploy`).

### modules
- **Core Purpose**: Contains reusable code modules, currently including `GitHubActionsTools`.
- **Architecture**: A directory for shared code, facilitating reusability across projects.
- **Key Files**:
    - `GitHubActionsTools/`: Module for GitHub Actions related utilities.
- **Dependencies**: Dependent projects will import these modules.

### operations
- **Core Purpose**: Houses operational scripts, configurations, and documentation related to system monitoring, logging (Fluent Bit), network analysis (AdGuard, Omada, KEA DHCP), and general system management.
- **Architecture**: Collection of shell scripts, Lua scripts for Fluent Bit parsing, and YAML configurations for various services.
- **Key Files**:
    - `fluent-bit-*.yaml`: Fluent Bit configurations for various services.
    - `adguard-querylog-result.lua`, `kea-dhcp-parser.lua`, `omada-wifi-parser.lua`: Lua scripts for log parsing.
    - `scripts/`: Operational scripts.
    - `README.md`: Project overview.
    - `loki.yml`: Loki configuration.
- **Dependencies**: Fluent Bit, AdGuard Home, KEA DHCP, Omada Controller, Loki, Grafana, various network devices.

### pi-status-dashboard
- **Core Purpose**: A dashboard for monitoring the status of Raspberry Pi devices, including Grafana configurations and setup scripts.
- **Architecture**: Grafana for visualization, with scripts for Raspberry Pi setup.
- **Key Files**:
    - `grafana/`: Grafana configurations.
    - `pi-setup/`: Raspberry Pi setup scripts.
    - `scripts/`: Utility scripts.
- **Dependencies**: Raspberry Pi, Grafana, Prometheus (likely for data collection).

### portal-chat
- **Core Purpose**: A chat application, potentially for a portal interface.
- **Architecture**: Python-based (`pyproject.toml`, `src/`) with tests.
- **Key Files**:
    - `src/`: Source code.
    - `pyproject.toml`: Python project configuration.
- **Dependencies**: Python.

### proxmox-agent
- **Core Purpose**: An agent for interacting with Proxmox, likely for monitoring, automation, or data collection. Includes a dashboard component.
- **Architecture**: Python-based (`requirements.txt`, `src/`) with deployment scripts, documentation, and a dashboard.
- **Key Files**:
    - `src/`: Source code.
    - `requirements.txt`: Python dependencies.
    - `dashboard/`: Dashboard components.
    - `deploy/`: Deployment scripts.
    - `README.md`, `QUICKSTART.md`: Documentation.
- **Dependencies**: Python, Proxmox API.

### seed2smoke
- **Core Purpose**: A project named "seed2smoke", likely related to agricultural or horticultural processes, with backend and frontend components.
- **Architecture**: Python-based (`pyproject.toml`, `backend/`) with a frontend (`frontend/`), documentation, and scripts.
- **Key Files**:
    - `backend/`: Backend code.
    - `frontend/`: Frontend code.
    - `pyproject.toml`: Python project configuration.
    - `docs/`: Documentation.
- **Dependencies**: Python, potentially a frontend framework.

### serena
- **Core Purpose**: A core project, possibly an AI assistant or orchestration engine, with Docker integration, Nix flake support, and a focus on LLMs.
- **Architecture**: Python-based (`pyproject.toml`, `src/`) with Docker integration, Nix environment configuration (`flake.nix`, `flake.lock`). Includes scripts for repository synchronization.
- **Key Files**:
    - `src/`: Source code.
    - `pyproject.toml`: Python project configuration.
    - `compose.yaml`, `Dockerfile`: Docker configurations.
    - `flake.nix`, `flake.lock`: Nix flake configuration.
    - `repo_dir_sync.py`, `sync.py`: Repository synchronization scripts.
    - `README.md`, `DOCKER.md`, `llms-install.md`: Documentation.
- **Dependencies**: Python, Docker, Nix, LLMs (Large Language Models).

### stormcrow
- **Core Purpose**: A project named "stormcrow", likely a tool or service for automation or data processing.
- **Architecture**: Python-based (`pyproject.toml`, `src/`) with deployment tools, profiles, and documentation.
- **Key Files**:
    - `src/`: Source code.
    - `pyproject.toml`: Python project configuration.
    - `deploy/`: Deployment scripts.
    - `profiles/`: Configuration profiles.
- **Dependencies**: Python.

### tender
- **Core Purpose**: A Go-based application, potentially a service or tool related to "tender" (e.g., bidding, contracts, or data processing).
- **Architecture**: Go application (`go.mod`, `cmd/`, `internal/`) with a web component and deployment scripts.
- **Key Files**:
    - `cmd/`: Main application entry points.
    - `internal/`: Internal Go packages.
    - `web/`: Web interface components.
    - `go.mod`, `go.sum`: Go module dependencies.
    - `deploy/`: Deployment scripts.
- **Dependencies**: Go.

### tender-photos
- **Core Purpose**: A Go-based application specifically for handling photos related to the "tender" project.
- **Architecture**: Go application (`go.mod`, `cmd/`, `internal/`) with a web component, similar to `tender`.
- **Key Files**:
    - `cmd/`: Main application entry points.
    - `internal/`: Internal Go packages.
    - `web/`: Web interface components.
    - `go.mod`, `go.sum`: Go module dependencies.
- **Dependencies**: Go.

### unified-adaptive-lighting
- **Core Purpose**: Provides unified adaptive lighting functionalities, likely a custom component for Home Assistant.
- **Architecture**: Home Assistant custom component.
- **Key Files**:
    - `custom_components/`: Custom Home Assistant components.
- **Dependencies**: Home Assistant.

### wikijs-monitoring
- **Core Purpose**: Monitoring solution specifically for Wiki.js instances.
- **Architecture**: Likely scripts or configurations for monitoring.
- **Key Files**: (No specific files listed, but implies monitoring configurations).
- **Dependencies**: Wiki.js, monitoring tools (e.g., Prometheus, Grafana, Uptime Kuma).

### wrappers
- **Core Purpose**: Collection of shell scripts that act as wrappers for various MCP (Master Control Program) servers and other utilities, providing a standardized interface for interaction.
- **Architecture**: Bash shell scripts, each calling a specific MCP server or utility.
- **Key Files**:
    - `claude-auto-commit.sh`: Wrapper for Claude auto-commit MCP.
    - `code-linter.sh`: Wrapper for code linter MCP.
    - `directory-polling.sh`: Wrapper for directory polling MCP.
    - `github.sh`: GitHub related utility wrapper.
    - `gmail-manage.sh`: Wrapper for Gmail management MCP.
    - `home-assistant.sh`: Home Assistant related utility wrapper.
    - `network-fs.sh`: Network file system utility wrapper.
    - `proxmox.sh`: Wrapper for Proxmox MCP.
    - `serena-enhanced.sh`: Wrapper for enhanced Serena functionalities.
    - `truenas.sh`: Wrapper for TrueNAS MCP.
    - `vikunja.sh`: Wrapper for Vikunja MCP.
- **Dependencies**: Bash shell, various MCP servers and underlying utilities.
