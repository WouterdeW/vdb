SHELL = /bin/bash

all: up init-db init-schema

build:
	docker build -t vandebron-wouter:latest .

up: ## Starts docker-compose setup
	docker-compose up -d

down: ## Stops docker-compose setup
	docker-compose down

clean: ## Stop docker-compose setup and delete all volumes
	docker-compose down --volumes --remove-orphans

init-db: up ## Initialize database
	@while ! docker ps --no-trunc --filter "label=com.docker.compose.service=db" | grep -q 'healthy'; do echo "initializing PostgreSQL.."; sleep 15; done
	docker-compose exec -T db psql -f /tmp/sql/init-db.sql

init-schema: up init-db
	docker-compose exec -T db psql --dbname=vdb --username=vdb -f /tmp/sql/init-schema.sql

get-data:
	docker-compose exec -T db psql -d vdb -U vdb -f /tmp/sql/get-data.sql

get-aggregated-data:
	docker-compose exec -T db psql -d vdb -U vdb -f /tmp/sql/get-aggregated-data.sql