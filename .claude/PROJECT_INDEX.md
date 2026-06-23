# Project Index: workspace

## 1. Core Purpose

This repository contains a comprehensive suite of tools, applications, and configurations for managing a personal homelab environment. It automates the deployment, configuration, and monitoring of various services, including IoT, media, networking, and infrastructure management, following GitOps and Infrastructure-as-Code (IaC) principles.

## 2. Architecture

The project follows a distributed, service-oriented architecture composed of multiple independent but interconnected components.

-   **Automation & Orchestration**: A central "Master Control Program" (MCP) system, visible in directories like `.mcp/` and `mcp-servers/`, appears to orchestrate tasks across different services. Automation is heavily driven by shell scripts (`scripts/`, `wrappers/`), Python, and Go.
-   **GitOps**: The `homelab-gitops/` directory serves as the central repository for declarative infrastructure and application definitions, managing the state of the entire homelab.
-   **Applications**: The codebase includes several distinct applications, such as a Go-based `birdnet-go` and `birdnet-gone` for bird sound analysis, a Node.js `api` backend, a `dashboard` frontend, and a Python-based `fitbit-dashboard`.
-   **Infrastructure as Code (IaC)**: The `homelab-iac/` directory contains configurations for tools like Ansible and Terraform to manage the underlying infrastructure.
-   **Configuration Management**: Extensive configuration for services like Home Assistant (`home-assistant-config/`), Traefik, and various monitoring tools is version-controlled within this repository.

## 3. Key Files

-   `homelab-gitops/README.md`: Central documentation for the GitOps deployment and management process.
-   `api/server.js`: The main entry point for the primary Node.js backend API.
-   `dashboard/src/main.ts`: The main entry point for the frontend dashboard application.
-   `docker-compose.production.yml`: Key file defining the production services and their orchestration.
-   `./deploy-ssh-keys-working.sh`: Core script for managing SSH key deployment across the infrastructure.
-   `./verify-dns-migration.sh`: Utility script for verifying DNS changes, critical for service routing.
-   `./portal-chat/README.md`: Documentation for the `portal-chat` service.
-   `./portal-chat/tests/`: Directory containing the test suite for the `portal-chat` service, indicating its importance and complexity.
-   `wrappers/`: Contains wrapper scripts that likely simplify interaction with various MCP servers and other core components.
-   `home-assistant-config/configuration.yaml`: The primary configuration file for the Home Assistant instance.

## 4. Dependencies

-   **Languages**: Python, Go, JavaScript/TypeScript (Node.js), Shell (Bash)
-   **Frameworks/Libraries**: React (for `dashboard`), Express.js (likely for `api`), Flask/FastAPI (in Python services)
-   **Infrastructure & DevOps**: Docker, Ansible, Terraform, Proxmox, Traefik, Git
-   **Services**: Home Assistant, Wiki.js, NetBox, AdGuard Home, Zigbee2MQTT, Vaultwarden
-   **Databases**: SQLite, InfluxDB (inferred from monitoring setups)
