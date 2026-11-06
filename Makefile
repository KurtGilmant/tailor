# Tailor — commandes du projet. `make help` liste les cibles.

.DEFAULT_GOAL := help
.PHONY: help install dev dev-api dev-web test lint typecheck api-client build eval

BACKEND := backend
WEB := web

help: ## Liste les commandes disponibles
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Installe les dépendances backend et front
	cd $(BACKEND) && uv sync
	cd $(WEB) && npm install

dev: ## Lance le backend et Vite (proxy vers l'API) en parallèle
	@$(MAKE) -j2 dev-api dev-web

dev-api: ## Lance uniquement le backend en mode rechargement
	cd $(BACKEND) && TAILOR_DEV=1 uv run tailor --reload

dev-web: ## Lance uniquement le serveur Vite
	cd $(WEB) && npm run dev

test: ## Lance tous les tests (backend + front)
	cd $(BACKEND) && uv run pytest
	cd $(WEB) && npm run test

lint: ## Lint backend et front
	cd $(BACKEND) && uv run ruff check . && uv run ruff format --check .
	cd $(WEB) && npm run lint

typecheck: ## Vérification de types backend et front
	cd $(BACKEND) && uv run pyright
	cd $(WEB) && npm run typecheck

api-client: ## Régénère le client TypeScript depuis l'OpenAPI du backend
	cd $(BACKEND) && uv run python -m tailor.openapi > ../$(WEB)/openapi.json
	cd $(WEB) && npm run gen:api

build: api-client ## Build le front et le copie dans le backend (servi par FastAPI)
	cd $(WEB) && npm run build
	rm -rf $(BACKEND)/src/tailor/static && cp -R $(WEB)/dist $(BACKEND)/src/tailor/static

eval: ## Lance l'évaluation qualité (groupe 8 du plan)
	@echo "Pas encore implémenté (jalon M3)." && exit 1
