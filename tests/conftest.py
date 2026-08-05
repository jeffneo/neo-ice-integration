"""Pytest fixtures for the Neo4j <-> Iceberg integration test.

Runs on the host. Talks to Neo4j directly over Bolt (via the `neo4j` driver)
for seeding and verification, and shells out to the Spark jobs that run inside
the docker stack.
"""
import os
import pathlib
import subprocess

import pytest
from dotenv import load_dotenv
from neo4j import GraphDatabase

ROOT = pathlib.Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

# The Spark jobs reach Neo4j over the docker network; the host-side driver may
# need a different URI. They only differ for a *dockerized local* Neo4j (where
# the container sees `bolt://neo4j:7687` but the host sees `bolt://localhost:7687`).
# For Aura / any externally reachable instance the same URI works from both, so
# default NEO4J_URI_HOST to NEO4J_URI and only override it for the local case.
HOST_NEO4J_URI = (
    os.environ.get("NEO4J_URI_HOST")
    or os.environ.get("NEO4J_URI")
    or "bolt://localhost:7687"
)
NEO4J_USERNAME = os.environ.get("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password12345")
NEO4J_DATABASE = os.environ.get("NEO4J_DATABASE", "neo4j")


@pytest.fixture(scope="session")
def driver():
    drv = GraphDatabase.driver(HOST_NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    drv.verify_connectivity()
    yield drv
    drv.close()


def run_cypher(driver, cypher, **params):
    with driver.session(database=NEO4J_DATABASE) as session:
        return list(session.run(cypher, **params))


@pytest.fixture(scope="session")
def seeded_graph(driver):
    """Guarantee an empty database, then load the movie-graph subset.

    This Aura instance exists only to run this test, so the fixture actively
    wipes it and asserts it is empty before seeding — a deterministic starting
    point every run, independent of whatever was left behind previously.
    """
    with driver.session(database=NEO4J_DATABASE) as session:
        session.run("MATCH (n) DETACH DELETE n")
        remaining = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
        assert remaining == 0, f"database not empty after wipe: {remaining} node(s)"

        seed = (ROOT / "data" / "seed_movies.cypher").read_text()
        # The seed file is a set of `;`-terminated statements.
        for stmt in [s.strip() for s in seed.split(";")
                     if s.strip() and not s.strip().startswith("//")]:
            session.run(stmt)
    return driver


def run_spark_job(job_file: str):
    """Invoke scripts/run_spark_job.sh <job_file> and return the completed process."""
    script = ROOT / "scripts" / "run_spark_job.sh"
    result = subprocess.run(
        ["bash", str(script), job_file],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=600,
    )
    # Surface Spark output on failure to make debugging painless.
    print(result.stdout)
    print(result.stderr)
    return result
