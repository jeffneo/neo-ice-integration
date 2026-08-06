"""Wipe every node/relationship from the configured Neo4j database.

Used by `make clean` (and runnable on its own) to reset the dedicated test
instance. Connects using the host-reachable URI, mirroring the test harness:
NEO4J_URI_HOST if set, else NEO4J_URI.
"""
import os
import pathlib

from dotenv import load_dotenv
from neo4j import GraphDatabase

ROOT = pathlib.Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

URI = os.environ.get("NEO4J_URI_HOST") or os.environ.get("NEO4J_URI") or "bolt://localhost:7687"
USER = os.environ.get("NEO4J_USERNAME", "neo4j")
PASSWORD = os.environ.get("NEO4J_PASSWORD", "password12345")
DATABASE = os.environ.get("NEO4J_DATABASE", "neo4j")


def main():
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    driver.verify_connectivity()
    with driver.session(database=DATABASE) as session:
        before = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
        session.run("MATCH (n) DETACH DELETE n")
        after = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
    driver.close()
    print(f"wiped Neo4j graph at {URI} (db={DATABASE}): {before} -> {after} nodes")


if __name__ == "__main__":
    main()
