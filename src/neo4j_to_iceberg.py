"""Direction 1:  Neo4j  ->  Apache Iceberg.

Reads the Movie graph out of Neo4j with the Neo4j Spark Connector and writes it
into four Iceberg tables (nodes + relationships modelled relationally):

    movies.movie      (title, released, tagline)
    movies.person     (name, born)
    movies.acted_in   (person, movie, roles)
    movies.directed   (person, movie)

Run inside the spark-iceberg container via scripts/run_spark_job.sh.
"""
import sys

from pyspark.sql import SparkSession

import config


def read_neo4j_query(spark, query):
    reader = spark.read.format(config.NEO4J_FORMAT)
    for key, value in config.neo4j_options().items():
        reader = reader.option(key, value)
    return reader.option("query", query).load()


def main():
    spark = SparkSession.builder.appName("neo4j_to_iceberg").getOrCreate()
    spark.sql(
        f"CREATE NAMESPACE IF NOT EXISTS "
        f"{config.ICEBERG_CATALOG}.{config.ICEBERG_NAMESPACE}"
    )

    tables = {
        "movie": "MATCH (m:Movie) "
                 "RETURN m.title AS title, m.released AS released, "
                 "m.tagline AS tagline",
        "person": "MATCH (p:Person) "
                  "RETURN p.name AS name, p.born AS born",
        "acted_in": "MATCH (p:Person)-[r:ACTED_IN]->(m:Movie) "
                    "RETURN p.name AS person, m.title AS movie, "
                    "r.roles AS roles",
        "directed": "MATCH (p:Person)-[:DIRECTED]->(m:Movie) "
                    "RETURN p.name AS person, m.title AS movie",
    }

    for table, query in tables.items():
        df = read_neo4j_query(spark, query)
        target = config.fq(table)
        # createOrReplace makes the job idempotent across re-runs.
        df.writeTo(target).using("iceberg").createOrReplace()
        count = spark.table(target).count()
        print(f"[neo4j->iceberg] wrote {count:>4} rows to {target}", flush=True)

    spark.stop()


if __name__ == "__main__":
    sys.exit(main())
