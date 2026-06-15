# Project Index: workspace

## 1. Core Purpose
This workspace functions as a comprehensive homelab management and automation platform. Its core purpose is to streamline the deployment, configuration, monitoring, and maintenance of various services and infrastructure components within a homelab environment. It integrates tools for GitOps, container orchestration, home automation, 3D printing management, and potentially AI/ML-driven automation and monitoring. The project aims to provide a robust, automated, and observable homelab.

## 2. Architecture
The architecture is modular and distributed, built around a microservices-oriented approach.

*   **Centralized APIs & Orchestration**: A central API layer (`api` directory) likely serves as the control plane, interacting with various specialized agents and services. The `homelab-gitops` and `mcp-servers` directories suggest a Master Control Program (MCP) framework for managing and coordinating these services.
*   **Specialized Agents/Services**: Numerous sub-projects (`birdnet-go`, `birdnet-gone`, `biometric-gateway`, `proxmox-agent`, `serena`, `stormcrow`, `tender`, `tender-photos`, `portal-chat`) operate as distinct services or agents, each handling specific functionalities (e.g., bird detection, biometric authentication, Proxmox integration, chat interfaces).
*   **Frontend & Dashboards**: Multiple web-based dashboards (`dashboard`, `fitbit-dashboard`, `pi-status-dashboard`, `3ddash`) provide user interfaces for monitoring, configuration, and data visualization.
*   **Infrastructure as Code (IaC)**: The `homelab-iac` directory, utilizing tools like Ansible and Terraform, manages the underlying infrastructure in a declarative manner.
*   **Deployment Pipelines**: `1-line-deploy`, `homelab-gitops`, `scripts`, `github-actions-runner`, and `cron` indicate robust CI/CD and GitOps-driven deployment mechanisms for automating software delivery.
*   **Home Automation Integration**: `home-assistant-config` and `hass-ab-ble-gateway-suite` are dedicated to managing and extending a Home Assistant smart home setup.
*   **Operations & Logging**: The `operations` directory contains configurations for monitoring tools (e.g., Fluent Bit for log collection, Loki for log aggregation) and system-level scripts.
*   **Shared Libraries/Wrappers**: The `modules` and `wrappers` directories provide reusable code and shell scripts for interacting with different services and systems.

## 3. Key Files
*   `./deploy-ssh-keys-working.sh`: Script for deploying SSH keys.
*   `./verify-dns-migration.sh`: Script to verify DNS migration.
*   `./portal-chat/README.md`: Documentation for the portal-chat project.
*   `./portal-chat/tests/test_chat_endpoint.py`: Tests for the chat endpoint.
*   `./portal-chat/tests/test_agent_tier1.py`: Tests for Tier 1 agents in portal-chat.
*   `./portal-chat/tests/test_ha.py`: High-availability tests for portal-chat.
*   `./portal-chat/tests/test_agent_tier2.py`: Tests for Tier 2 agents in portal-chat.
*   `./portal-chat/tests/test_health.py`: Health check tests for portal-chat.
*   `./portal-chat/tests/test_sensitive_devices.py`: Tests for sensitive device interactions in portal-chat.
*   `./portal-chat/tests/test_prompt.py`: Prompt-related tests for portal-chat.
*   `./portal-chat/tests/test_config.py`: Configuration tests for portal-chat.
*   `./portal-chat/tests/test_stormcrow.py`: Stormcrow integration tests for portal-chat.
*   `./portal-chat/tests/test_guardrails.py`: Guardrail tests for portal-chat.
*   `./portal-chat/tests/test_stormcrow_format.py`: Stormcrow format tests for portal-chat.

(Note: `portal-chat/.venv/lib/python3.11/site-packages/pip/...` are internal pip library files and are not considered key project files.)

## 4. Dependencies
The codebase utilizes a diverse set of technologies:

*   **Backend Languages**:
    *   **Python**: Used extensively for various agents, scripts, and Home Assistant integrations (`fitbit-dashboard`, `portal-chat`, `model-catalog`, `proxmox-agent`, `serena`, `stormcrow`, `home-assistant-config`, `create-consolidated-config.py`). Managed with `pip` (via `requirements.txt`) and `Poetry` (via `pyproject.toml`).
    *   **Go**: Used for several specialized services and gateways (`biometric-gateway`, `birdnet-go`, `birdnet-gone`, `tender`, `tender-photos`). Managed with Go Modules (`go.mod`, `go.sum`).
    *   **JavaScript/TypeScript**: Used for APIs and frontend applications (`api`, `dashboard`, `gw4-config-tool`, `homelab-gitops`). Managed with `npm`/`yarn` (via `package.json`, `package-lock.json`).
*   **Frontend Frameworks**: React/Vite (in `dashboard`), HTML/CSS/JavaScript (various UIs). Tailwind CSS is used for styling.
*   **Containerization**: Docker and Docker Compose (`Dockerfile`, `docker-compose.yml`) are used for packaging and orchestrating services.
*   **Infrastructure as Code**: Ansible and Terraform (`homelab-iac`) for infrastructure provisioning and configuration.
*   **Home Automation**: Home Assistant ecosystem (YAML configurations, custom components).
*   **Scripting**: Extensive use of Bash scripts (`.sh` files) for automation, deployment, and operational tasks.
*   **Configuration Management**: Various `.yaml`, `.json`, `.conf`, and `.toml` files for application and system configuration.
*   **Pre-commit Hooks**: `.pre-commit-config.yaml` for code quality and linting.
