.PHONY: help install up up-external down logs test inspect sql minio wipe clean

help:
	@echo "Setup / run:"
	@echo "  make install     # sync host deps into .venv via uv"
	@echo "  make up          # start the full stack incl. Neo4j (waits for health)"
	@echo "  make up-external # start Iceberg only (use your own external Neo4j)"
	@echo "  make test        # run the bidirectional round-trip test (leaves stack UP)"
	@echo ""
	@echo "Inspect Iceberg (after a run; stack must be up):"
	@echo "  make inspect     # print namespaces, tables, row counts, sample rows"
	@echo "  make sql         # open an interactive spark-sql shell"
	@echo "  make minio       # print the MinIO console URL + login"
	@echo ""
	@echo "Teardown:"
	@echo "  make wipe        # wipe the Neo4j graph only (leaves containers up)"
	@echo "  make down        # stop & remove containers (Iceberg data survives)"
	@echo "  make clean       # wipe Neo4j graph + remove containers AND volumes"

install:
	uv sync

# Default: start everything, including a Dockerized Neo4j. The first line starts
# all services (incl. the one-shot `mc` bucket creator); the second blocks until
# the long-running services are healthy so `make test` can run immediately.
# `mc` is excluded from --wait because it exits 0 on purpose (and --wait treats
# any container exit as a failure).
up:
	docker compose up -d
	docker compose up -d --wait iceberg-rest minio spark-iceberg neo4j

# Iceberg only — for when you point NEO4J_URI/NEO4J_URI_HOST at an external Neo4j.
up-external:
	docker compose up -d iceberg-rest minio mc spark-iceberg
	docker compose up -d --wait iceberg-rest minio spark-iceberg

# NOTE: `test` intentionally leaves the stack running so you can inspect the
# tables afterward. Tear down explicitly with `make down` / `make clean`.
test:
	uv run pytest

inspect:
	./scripts/inspect_iceberg.sh

sql:
	./scripts/spark_sql.sh

minio:
	@echo "MinIO console:  http://localhost:9001"
	@echo "  user:     $${AWS_ACCESS_KEY_ID:-admin}"
	@echo "  password: $${AWS_SECRET_ACCESS_KEY:-password}"
	@echo "Iceberg files live under the 'warehouse' bucket."

logs:
	docker compose logs -f spark-iceberg

wipe:
	uv run python scripts/wipe_neo4j.py

down:
	docker compose down

# Full reset: wipe the Neo4j graph FIRST (while the Neo4j container is still up),
# then remove containers and volumes (Iceberg data). The leading '-' makes the
# wipe best-effort so teardown still proceeds if Neo4j is unreachable (e.g.
# containers already down on a fresh checkout).
clean:
	-uv run python scripts/wipe_neo4j.py
	docker compose down -v
