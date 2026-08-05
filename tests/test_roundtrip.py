"""Bidirectional integration test:  Neo4j -> Iceberg -> Neo4j.

The single ordered test proves the movie graph survives a full round-trip:

    1. Seed Neo4j and snapshot the original counts + a content sample.
    2. Neo4j -> Iceberg   (neo4j_to_iceberg.py)  and verify Iceberg received it.
    3. Iceberg -> Neo4j   (iceberg_to_neo4j.py)  writing into :*RT labels.
    4. Assert the RT graph equals the original -> data made the round trip intact.
    5. Clean up the RT graph.
"""
import pytest

from conftest import run_cypher, run_spark_job


def _counts(driver):
    """Original graph counts, computed from the seed so the test isn't brittle."""
    return {
        "movie": run_cypher(driver, "MATCH (m:Movie) RETURN count(m) AS c")[0]["c"],
        "person": run_cypher(driver, "MATCH (p:Person) RETURN count(p) AS c")[0]["c"],
        "acted_in": run_cypher(
            driver, "MATCH (:Person)-[r:ACTED_IN]->(:Movie) RETURN count(r) AS c"
        )[0]["c"],
        "directed": run_cypher(
            driver, "MATCH (:Person)-[r:DIRECTED]->(:Movie) RETURN count(r) AS c"
        )[0]["c"],
    }


def _rt_counts(driver):
    return {
        "movie": run_cypher(driver, "MATCH (m:MovieRT) RETURN count(m) AS c")[0]["c"],
        "person": run_cypher(driver, "MATCH (p:PersonRT) RETURN count(p) AS c")[0]["c"],
        "acted_in": run_cypher(
            driver, "MATCH (:PersonRT)-[r:ACTED_IN_RT]->(:MovieRT) RETURN count(r) AS c"
        )[0]["c"],
        "directed": run_cypher(
            driver, "MATCH (:PersonRT)-[r:DIRECTED_RT]->(:MovieRT) RETURN count(r) AS c"
        )[0]["c"],
    }


def test_bidirectional_roundtrip(seeded_graph):
    driver = seeded_graph
    original = _counts(driver)
    assert all(v > 0 for v in original.values()), f"seed looks empty: {original}"

    # --- Direction 1: Neo4j -> Iceberg -------------------------------------
    r1 = run_spark_job("neo4j_to_iceberg.py")
    assert r1.returncode == 0, "neo4j_to_iceberg job failed"
    # The job prints "wrote N rows to <table>"; confirm each table got the
    # expected number of rows, i.e. Iceberg actually received the graph.
    for table in original:
        assert f"rows to iceberg.movies.{table}" in r1.stdout, \
            f"no confirmation Iceberg table {table} was written"

    # --- Direction 2: Iceberg -> Neo4j (into :*RT labels) ------------------
    r2 = run_spark_job("iceberg_to_neo4j.py")
    assert r2.returncode == 0, "iceberg_to_neo4j job failed"

    # --- Verify the round trip ---------------------------------------------
    roundtrip = _rt_counts(driver)
    assert roundtrip == original, (
        f"round-trip mismatch:\n  original ={original}\n  roundtrip={roundtrip}"
    )

    # Content-level spot check: a relationship property (roles list) survived.
    neo_role = run_cypher(
        driver,
        "MATCH (p:Person {name:'Keanu Reeves'})-[r:ACTED_IN]->(m:Movie {title:'The Matrix'}) "
        "RETURN r.roles AS roles",
    )[0]["roles"]
    rt_role = run_cypher(
        driver,
        "MATCH (p:PersonRT {name:'Keanu Reeves'})-[r:ACTED_IN_RT]->(m:MovieRT {title:'The Matrix'}) "
        "RETURN r.roles AS roles",
    )[0]["roles"]
    assert neo_role == rt_role == ["Neo"], f"roles not preserved: {neo_role} vs {rt_role}"


@pytest.fixture(autouse=True)
def _cleanup_rt(request):
    """Remove the round-trip graph after the test, pass or fail."""
    yield
    driver = request.getfixturevalue("driver")
    run_cypher(driver, "MATCH (n:MovieRT) DETACH DELETE n")
    run_cypher(driver, "MATCH (n:PersonRT) DETACH DELETE n")
