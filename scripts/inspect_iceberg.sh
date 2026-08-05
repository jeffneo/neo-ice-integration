#!/usr/bin/env bash
# Print a quick report of what's in the Iceberg catalog: namespaces, tables,
# row counts, and a few sample rows. Run any time after the jobs have written.
#
#   ./scripts/inspect_iceberg.sh                 # canned report
#   ./scripts/inspect_iceberg.sh "SELECT * FROM iceberg.movies.movie"   # custom SQL
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
source "${HERE}/_iceberg_conf.sh"

NS="${ICEBERG_CATALOG}.${ICEBERG_NAMESPACE:-movies}"

SQL="${1:-$(cat <<EOF
SHOW NAMESPACES IN ${ICEBERG_CATALOG};
SHOW TABLES IN ${NS};
SELECT 'movie' AS table, count(*) AS rows FROM ${NS}.movie
  UNION ALL SELECT 'person', count(*) FROM ${NS}.person
  UNION ALL SELECT 'acted_in', count(*) FROM ${NS}.acted_in
  UNION ALL SELECT 'directed', count(*) FROM ${NS}.directed;
SELECT * FROM ${NS}.movie ORDER BY released;
SELECT person, movie, roles FROM ${NS}.acted_in ORDER BY movie LIMIT 10;
EOF
)}"

exec docker compose exec -T spark-iceberg \
  spark-sql "${CONF_FLAGS[@]}" -e "${SQL}"
