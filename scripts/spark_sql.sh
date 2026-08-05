#!/usr/bin/env bash
# Open an interactive spark-sql shell wired to the Iceberg catalog.
# Try:  SHOW TABLES IN iceberg.movies;   SELECT * FROM iceberg.movies.movie;
# Exit with:  quit;   (or Ctrl-D)
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
source "${HERE}/_iceberg_conf.sh"

exec docker compose exec -it spark-iceberg \
  spark-sql "${CONF_FLAGS[@]}"
