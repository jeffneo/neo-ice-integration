#!/usr/bin/env bash
# Run one PySpark job inside the spark-iceberg container.
#
#   ./scripts/run_spark_job.sh neo4j_to_iceberg.py
#   ./scripts/run_spark_job.sh iceberg_to_neo4j.py
#
# Neo4j credentials are read from the host environment (or .env) and forwarded
# into the container, so they are never baked into any file.
set -euo pipefail

JOB="${1:?usage: run_spark_job.sh <job_file.py>}"
HERE="$(cd "$(dirname "$0")" && pwd)"

# Loads .env and populates the CONF_FLAGS array with the Iceberg catalog config.
source "${HERE}/_iceberg_conf.sh"

NEO4J_SPARK_CONNECTOR="${NEO4J_SPARK_CONNECTOR:-org.neo4j:neo4j-connector-apache-spark_2.12:5.3.1_for_spark_3}"

exec docker compose exec -T \
  -e NEO4J_URI -e NEO4J_USERNAME -e NEO4J_PASSWORD -e NEO4J_DATABASE \
  -e ICEBERG_CATALOG -e ICEBERG_NAMESPACE \
  spark-iceberg \
  spark-submit \
    --packages "${NEO4J_SPARK_CONNECTOR}" \
    "${CONF_FLAGS[@]}" \
    "/home/iceberg/jobs/${JOB}"
