.PHONY: help install up up-local down logs test inspect sql minio clean

help:
	@echo "Setup / run:"
	@echo "  make install     # sync host deps into .venv via uv"
	@echo "  make up          # start Iceberg stack (external Neo4j via NEO4J_URI)"
	@echo "  make up-local    # start Iceberg stack + a local Neo4j container"
	@echo "  make test        # run the bidirectional round-trip test (leaves stack UP)"
	@echo ""
	@echo "Inspect Iceberg (after a run; stack must be up):"
	@echo "  make inspect     # print namespaces, tables, row counts, sample rows"
	@echo "  make sql         # open an interactive spark-sql shell"
	@echo "  make minio       # print the MinIO console URL + login"
	@echo ""
	@echo "Teardown:"
	@echo "  make down        # stop & remove containers (Iceberg data survives)"
	@echo "  make clean       # stop & remove containers AND volumes (wipes Iceberg data)"

install:
	uv sync

up:
	docker compose up -d iceberg-rest minio mc spark-iceberg

up-local:
	docker compose --profile local-neo4j up -d

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

down:
	docker compose --profile local-neo4j down

clean:
	docker compose --profile local-neo4j down -v
