# Neo4j ↔ Apache Iceberg — Bidirectional Integration Test

A round-trip integration test that moves Neo4j's classic **Movie graph** into
**Apache Iceberg** and back, then asserts the data survived intact:

```
Neo4j ──(neo4j_to_iceberg.py)──▶ Iceberg tables ──(iceberg_to_neo4j.py)──▶ Neo4j (:*RT labels)
                                                                             │
                                          pytest compares :*RT vs originals ─┘
```

## Why the Neo4j Spark Connector?

Apache **Spark** is the one engine that speaks *both* endpoints natively:
Iceberg ships a first-class Spark runtime, and the
[Neo4j Spark Connector](https://neo4j.com/docs/spark/current/) gives Spark
first-class Neo4j read/write. So each direction of the test is a single Spark
job — no custom format-translation glue.

This is the right choice for a **batch / analytical** round-trip like this one.
If the goal were *continuous CDC/streaming* sync instead, the better tool would
be the **Neo4j Connector for Kafka** with an Iceberg sink.

## Components

| Piece | Role |
|-------|------|
| `iceberg-rest` | Iceberg REST catalog (table metadata) |
| `minio` + `mc` | S3-compatible object store + bucket bootstrap |
| `spark-iceberg` | Spark 3.5 with Iceberg jars; runs both jobs |
| `neo4j` | Neo4j (latest LTS), started by default; swappable for an external instance |

Everything runs in Docker **except** the pytest harness, which runs on the host
and talks to Neo4j over Bolt for seeding and verification.

## Data model in Iceberg

The graph is flattened into four Iceberg tables in the `movies` namespace:

- `movie(title, released, tagline)`
- `person(name, born)`
- `acted_in(person, movie, roles)`  — `roles` is an Iceberg `array<string>`
- `directed(person, movie)`

## Prerequisites

- Docker + Docker Compose
- [uv](https://docs.astral.sh/uv/) on the host (Python 3.9+)

## Setup

No manual virtualenv needed — `uv` creates and manages `.venv` for you.

```bash
cp .env.example .env          # works out of the box for the default Docker setup
uv sync                       # creates .venv and installs host deps
```

`uv run <cmd>` (used by `make test`) auto-syncs and runs inside that `.venv`,
so you never have to activate it manually. Prefer plain pip? `pip install
neo4j==5.26.0 pytest==8.3.2 python-dotenv==1.0.1` in a venv of your own works
too — the dependencies live in `pyproject.toml`.

## Run (default: everything in Docker)

By default Neo4j runs in Docker alongside Iceberg — the stock `.env` needs no
edits. `make up` waits until Neo4j is healthy, so `make test` can run right away:

```bash
make up            # iceberg-rest + minio + spark-iceberg + neo4j (waits for health)
make test
```

The Neo4j Browser is at **http://localhost:7474** (Bolt on `7687`); log in with
the `NEO4J_USERNAME` / `NEO4J_PASSWORD` from `.env` (defaults `neo4j` /
`password12345`).

### Using an external Neo4j instead (Aura or any non-Docker instance)

Neo4j settings are read entirely from the environment. To target an external
instance, set these in `.env` and start Iceberg only (don't run the container):

| Variable | Meaning |
|----------|---------|
| `NEO4J_URI` | Bolt URI **as seen from the Spark container** |
| `NEO4J_URI_HOST` | Bolt URI **as seen from the host** (pytest driver) |
| `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE` | credentials + target database |

For a Dockerized Neo4j the two URIs differ (`bolt://neo4j:7687` from the Spark
container vs `bolt://localhost:7687` from the host). For an external instance
they're the **same reachable URI**, e.g.:

```bash
# .env
NEO4J_URI=neo4j+s://<your-db-id>.databases.neo4j.io
NEO4J_URI_HOST=neo4j+s://<your-db-id>.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<your-password>
```
```bash
make up-external   # Iceberg only; uses your external Neo4j
make test
```

> ⚠️ The test **wipes the target database** at the start of every run (it assumes
> a throwaway instance). Don't point it at a Neo4j that holds data you care about.

Run the Spark jobs by hand if you want to inspect the intermediate state:

```bash
./scripts/run_spark_job.sh neo4j_to_iceberg.py
./scripts/run_spark_job.sh iceberg_to_neo4j.py
```

## What the test asserts

`tests/test_roundtrip.py`:

1. **Wipes the target database and asserts it is empty**, then seeds it from
   `data/seed_movies.cypher` and snapshots node/relationship counts. (The
   configured Neo4j is assumed to be a throwaway instance dedicated to this test.)
2. Runs **Neo4j → Iceberg** and confirms each Iceberg table was written.
3. Runs **Iceberg → Neo4j**, rebuilding under `:MovieRT` / `:PersonRT` /
   `[:ACTED_IN_RT]` / `[:DIRECTED_RT]` labels.
4. Asserts the round-trip graph **equals** the original (counts + a
   relationship-property spot check on `roles`).

The test does **not** clean up afterward: the originals *and* the `:*RT`
round-trip result are left in Neo4j so you can inspect both. The graph is wiped
only at the **start** of the next run (step 1) or by `make clean`.

## Inspecting Iceberg

There is no "Iceberg login" — Iceberg is a **table format**, not a server. Its
two moving parts here are the **REST catalog** (`iceberg-rest`, tracks which
tables exist) and the **object store** (`minio`, holds the actual data +
metadata files). You inspect it two ways:

**1. Query the tables (see the rows):**

```bash
make inspect      # namespaces, tables, row counts, and sample rows
make sql          # interactive spark-sql shell for ad-hoc queries
```

In the `make sql` shell, try:

```sql
SHOW TABLES IN iceberg.movies;
SELECT * FROM iceberg.movies.movie ORDER BY released;
SELECT person, movie, roles FROM iceberg.movies.acted_in;
-- Iceberg keeps snapshot history; each write shows up here:
SELECT * FROM iceberg.movies.movie.snapshots;
quit;
```

**2. See the physical files (watch them appear):**

Open the MinIO console at **http://localhost:9001** (`make minio` prints the
login — default `admin` / `password`). Browse the **`warehouse`** bucket:
you'll see `movies.db/<table>/data/` (Parquet data files) and `metadata/`
(Iceberg manifest + snapshot JSON). Re-run a Spark job and refresh — new files
appear. This is the most direct way to *watch* Iceberg do its thing.

> Want to see it build from nothing? `make clean && make up`, open the MinIO
> console (empty `warehouse`), then `make test` and refresh — the tables and
> files materialize.

## Teardown

`make test` deliberately **leaves everything in place** — containers keep
running and the Neo4j graph (originals + `:*RT`) is untouched — so you can
inspect both sides afterward. Tear down explicitly when you're done:

```bash
make wipe     # wipe the Neo4j graph only (containers stay up)
make down     # stop & remove containers; Iceberg data survives in the volume
make clean    # wipe Neo4j graph AND remove containers + volumes (full reset)
```

`make clean` wipes the Neo4j graph first (while a local Neo4j container, if
used, is still reachable), then removes the Docker containers and Iceberg volume.

## Layout

```
docker-compose.yml          # Iceberg stack (+ optional Neo4j)
.env.example                # configurable Neo4j creds + Iceberg wiring
Makefile                    # up / test / inspect / down helpers
data/seed_movies.cypher     # Movie-graph subset
scripts/_iceberg_conf.sh    # shared Iceberg catalog --conf flags
scripts/run_spark_job.sh    # spark-submit wrapper (wires both connectors)
scripts/inspect_iceberg.sh  # canned catalog report (make inspect)
scripts/spark_sql.sh        # interactive spark-sql shell (make sql)
scripts/wipe_neo4j.py       # wipe the Neo4j graph (make wipe / make clean)
src/config.py               # env-driven config shared by both jobs
src/neo4j_to_iceberg.py     # direction 1
src/iceberg_to_neo4j.py     # direction 2
tests/test_roundtrip.py     # the bidirectional assertion
```
