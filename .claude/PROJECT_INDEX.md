# Project Index: workspace

## 1. Core Purpose
This workspace serves as a comprehensive self-managed homelab and DevOps environment, integrating various custom-built applications, services, and automation scripts. It focuses on infrastructure as code, continuous deployment, monitoring, and AI-driven automation for tasks ranging from smart home management to data processing and device control.

## 2. Architecture
The project exhibits a distributed, microservice-oriented architecture, leveraging a mix of programming languages (Go, Python, JavaScript/TypeScript) and containerization technologies (Docker, Podman, LXC).
-   **API Services**: Core API functionalities are provided by Node.js applications (`api/server.js`) and Go-based services (e.g., `birdnet-go`, `tender`).
-   **Frontend Applications**: Multiple web-based dashboards and user interfaces (`dashboard`, `3ddash`, `fitbit-dashboard`) offer monitoring and interaction capabilities.
-   **Automation & Orchestration**: A central "Management Control Plane" (`.mcp`, `mcp-servers`) provides automation and integration points. Extensive shell scripts (`scripts`, `wrappers`) and GitOps practices (`homelab-gitops`) manage deployments, configurations, and system health.
-   **Infrastructure as Code (IaC)**: Terraform and Ansible configurations (`homelab-iac`) define and manage the underlying infrastructure.
-   **AI/Agent Integration**: Specialized agents (e.g., `serena`, `.claude`) are integrated to enhance automation, content processing, and intelligent operations.
-   **Home Automation**: Deep integration with Home Assistant (`home-assistant-config`) for smart device management and custom automations.

## 3. Key Files

-   `./VERSION`: Stores the overall project version.
-   `./.pre-commit-config.yaml`: Configuration for pre-commit hooks, ensuring code quality and standards.
-   `./install.sh`: Primary script for initial setup and installation.
-   `./update-production.sh`: Script for updating the production environment.
-   `./manual-deploy.sh`, `./quick-fix-deploy.sh`: Scripts for specific deployment scenarios.
-   `./cleanup-mcp-structure.sh`: Script for managing the MCP directory structure.
-   `./.mcp/`: Contains core scripts and configurations for the Management Control Plane.
-   `./.prompts/`: Houses prompts and configurations for AI agents.
-   `./.serena/`: Directory for the Serena AI agent's files.
-   `./api/server.js`: Main entry point for the Node.js API server.
-   `./homelab-gitops/README.md`: Overview and documentation for the GitOps implementation.
-   `./home-assistant-config/configuration.yaml`: Central configuration file for Home Assistant.
-   `./mcp-servers/README.md`: Documentation for the various MCP server components.
-   `./portal-chat/README.md`: Documentation for the Portal Chat application.
-   `./serena/README.md`: Documentation for the Serena AI agent.
-   `./wrappers/`: Collection of shell scripts that act as wrappers for different services.
-   `./deploy-ssh-keys-working.sh`: Script related to SSH key deployment.
-   `./verify-dns-migration.sh`: Script to verify DNS migration.
-   `./portal-chat/src/`: Source code for the Portal Chat application.
-   `./portal-chat/tests/`: Unit and integration tests for the Portal Chat.

## 4. Dependencies
-   **Languages & Runtimes**: Go, Python, Node.js (JavaScript/TypeScript), Bash.
-   **Frameworks & Libraries**: React/Vite (for frontends), Express.js (Node.js APIs), FastAPI/Flask/Django (Python APIs), Gorilla Mux (Go web toolkit), various Python libraries (e.g., for data processing, Home Assistant integrations).
-   **Containerization**: Docker, Podman, LXC.
-   **Orchestration & Virtualization**: Proxmox, potentially Kubernetes (inferred from IaC).
-   **Home Automation**: Home Assistant.
-   **Databases**: Likely PostgreSQL, SQLite, possibly others.
-   **Monitoring & Logging**: Grafana, Loki, Uptime Kuma, Fluent Bit.
-   **Version Control**: Git.
-   **CI/CD**: GitHub Actions.
-   **Configuration Management**: Ansible, Terraform, Infisical.
-   **Documentation**: Wiki.js.
-   **Cloud/External Services**: GitHub for GitOps and actions, potentially other cloud services for specific integrations.
