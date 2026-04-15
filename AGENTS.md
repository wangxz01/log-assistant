# Repository Guidelines

## Project Overview
This repository contains the backend for **Log Assistant**, an intelligent log analysis and troubleshooting assistant.
The first milestone is a minimal but production-style backend scaffold using **Python**, **FastAPI**, **PostgreSQL**, **Redis**, **pytest**, and **Docker Compose**.

Current goal:
- Build a clean project skeleton
- Keep the first version simple and runnable
- Prioritize readability, correctness, and explainability over over-engineering

## Project Structure & Module Organization
Use the following layout:

- `app/`: main application package
  - `api/`: route handlers
  - `core/`: config, database, security, shared utilities
  - `models/`: ORM models
  - `schemas/`: request/response schemas
  - `services/`: business logic
- `tests/`: automated tests
- `assets/`: sample logs or static resources if needed
- root files:
  - `README.md`
  - `requirements.txt`
  - `Dockerfile`
  - `docker-compose.yml`
  - `.env.example`

Keep modules small and responsibility-focused. Prefer feature clarity over premature abstraction.

## Development Priorities
For the first scaffold, only implement:
- health check endpoint
- auth route placeholders
- log upload route placeholder
- log analysis route placeholder
- database and redis connection setup
- docker-based local startup
- basic test skeleton

Do NOT build the full business logic yet.
Do NOT introduce a frontend yet.
Do NOT over-design background tasks, RBAC, or AI orchestration in the first step.

## Build, Test, and Development Commands
Use one documented development path only.

Primary commands:
- install deps: `pip install -r requirements.txt`
- run app locally: `uvicorn app.main:app --reload`
- run tests: `pytest`
- start services: `docker compose up --build`

Document all commands in `README.md`.

## Coding Style & Naming Conventions
- Use Python 3.11+
- Follow PEP 8
- Use `snake_case` for modules, functions, and variables
- Use `PascalCase` for classes
- Keep files focused on one concern
- Prefer explicit names over short names
- Add type hints where practical
- Keep functions small and easy to explain in an interview

## Testing Guidelines
Add tests alongside the first production code.
Mirror the source structure under `tests/`.

Minimum initial coverage:
- app startup / health endpoint
- auth placeholder route
- log placeholder route

Every new feature should include at least one reproducible test when practical.

## Commit Guidelines
Use short, imperative commit messages.

Examples:
- `Scaffold FastAPI project structure`
- `Add docker compose setup`
- `Add auth route placeholders`
- `Add health endpoint tests`

Keep each commit focused on one logical change.

## Important Constraints
- Prefer simple implementations first
- Avoid unnecessary frameworks or patterns
- Code must be understandable by a student explaining it in an interview
- Generated code should be easy to run, inspect, and extend