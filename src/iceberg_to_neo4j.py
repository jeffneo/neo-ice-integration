"""Direction 2:  Apache Iceberg  ->  Neo4j.

Reads the four Iceberg tables back and rebuilds the graph in Neo4j using the
Neo4j Spark Connector. To keep the round-trip verifiable, the rebuilt graph is
written under *distinct* labels/relationship types suffixed "RT" (round-trip):

    :MovieRT, :PersonRT, [:ACTED_IN_RT], [:DIRECTED_RT]

The test then compares the RT graph against the originals to prove the data
survived Neo4j -> Iceberg -> Neo4j intact.
"""
import sys

from pyspark.sql import SparkSession

import config


def _writer(df):
    w = df.write.format(config.NEO4J_FORMAT)
    for key, value in config.neo4j_options().items():
        w = w.option(key, value)
    return w


def write_nodes(df, label, key):
    (
        _writer(df)
        .mode("Overwrite")               # MERGE on the node key -> idempotent
        .option("labels", f":{label}")
        .option("node.keys", key)
        .save()
    )


def write_relationship(df, rel_type, src_label, src_key, tgt_label, tgt_key):
    (
        _writer(df)
        .mode("Overwrite")
        .option("relationship", rel_type)
        .option("relationship.save.strategy", "keys")
        # Source and target nodes already exist (written above) -> just Match them.
        .option("relationship.source.save.mode", "Match")
        .option("relationship.source.labels", f":{src_label}")
        .option("relationship.source.node.keys", src_key)
        .option("relationship.target.save.mode", "Match")
        .option("relationship.target.labels", f":{tgt_label}")
        .option("relationship.target.node.keys", tgt_key)
        .save()
    )


def main():
    spark = SparkSession.builder.appName("iceberg_to_neo4j").getOrCreate()

    movie = spark.table(config.fq("movie"))
    person = spark.table(config.fq("person"))
    acted_in = spark.table(config.fq("acted_in"))
    directed = spark.table(config.fq("directed"))

    # 1) Nodes first, so relationships can Match against them.
    write_nodes(person, "PersonRT", "name")
    write_nodes(movie, "MovieRT", "title")
    print(f"[iceberg->neo4j] wrote {person.count()} PersonRT, "
          f"{movie.count()} MovieRT nodes", flush=True)

    # 2) Relationships. "person:name" maps DF column `person` -> node prop `name`.
    #    The unused `roles` column is stored as a relationship property.
    write_relationship(acted_in, "ACTED_IN_RT",
                       "PersonRT", "person:name", "MovieRT", "movie:title")
    write_relationship(directed, "DIRECTED_RT",
                       "PersonRT", "person:name", "MovieRT", "movie:title")
    print(f"[iceberg->neo4j] wrote {acted_in.count()} ACTED_IN_RT, "
          f"{directed.count()} DIRECTED_RT relationships", flush=True)

    spark.stop()


if __name__ == "__main__":
    sys.exit(main())
