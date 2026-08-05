#!/usr/bin/env bash
# Sourced by other scripts (not run directly). Loads .env and builds the Iceberg
# catalog --conf flags used by every Spark invocation, so the job runner and the
# inspection tools always talk to the same catalog. After sourcing, use the
# CONF_FLAGS bash array:  spark-submit "${CONF_FLAGS[@]}" ...
_HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "${_HERE}/../.env" ]]; then
  set -a; source "${_HERE}/../.env"; set +a
fi

ICEBERG_CATALOG="${ICEBERG_CATALOG:-iceberg}"
ICEBERG_REST_URI="${ICEBERG_REST_URI:-http://iceberg-rest:8181}"
ICEBERG_WAREHOUSE="${ICEBERG_WAREHOUSE:-s3://warehouse/}"
ICEBERG_S3_ENDPOINT="${ICEBERG_S3_ENDPOINT:-http://minio:9000}"

CONF_FLAGS=(
  --conf "spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions"
  --conf "spark.sql.catalog.${ICEBERG_CATALOG}=org.apache.iceberg.spark.SparkCatalog"
  --conf "spark.sql.catalog.${ICEBERG_CATALOG}.type=rest"
  --conf "spark.sql.catalog.${ICEBERG_CATALOG}.uri=${ICEBERG_REST_URI}"
  --conf "spark.sql.catalog.${ICEBERG_CATALOG}.warehouse=${ICEBERG_WAREHOUSE}"
  --conf "spark.sql.catalog.${ICEBERG_CATALOG}.io-impl=org.apache.iceberg.aws.s3.S3FileIO"
  --conf "spark.sql.catalog.${ICEBERG_CATALOG}.s3.endpoint=${ICEBERG_S3_ENDPOINT}"
  --conf "spark.sql.catalog.${ICEBERG_CATALOG}.s3.path-style-access=true"
  --conf "spark.sql.defaultCatalog=${ICEBERG_CATALOG}"
)
