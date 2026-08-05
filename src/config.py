"""Shared configuration, read entirely from environment variables.

Both PySpark jobs import this so Neo4j credentials and Iceberg wiring live in
exactly one place. Everything has a sensible default that matches
docker-compose.yml, but every value can be overridden via the environment.
"""
import os


def _env(name: str, default: str) -> str:
    val = os.environ.get(name)
    return val if val not in (None, "") else default


# --- Neo4j (configurable via environment variables) ------------------------
NEO4J_URI = _env("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USERNAME = _env("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = _env("NEO4J_PASSWORD", "password12345")
NEO4J_DATABASE = _env("NEO4J_DATABASE", "neo4j")

# --- Iceberg catalog -------------------------------------------------------
ICEBERG_CATALOG = _env("ICEBERG_CATALOG", "iceberg")
ICEBERG_NAMESPACE = _env("ICEBERG_NAMESPACE", "movies")


def fq(table: str) -> str:
    """Fully-qualified Iceberg table name: catalog.namespace.table."""
    return f"{ICEBERG_CATALOG}.{ICEBERG_NAMESPACE}.{table}"


# Neo4j Spark Connector data source class name.
NEO4J_FORMAT = "org.neo4j.spark.DataSource"


def neo4j_options() -> dict:
    """Common Neo4j Spark Connector options (url + basic auth + database)."""
    return {
        "url": NEO4J_URI,
        "authentication.type": "basic",
        "authentication.basic.username": NEO4J_USERNAME,
        "authentication.basic.password": NEO4J_PASSWORD,
        "database": NEO4J_DATABASE,
    }
