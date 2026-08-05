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
| `neo4j` *(optional)* | Local Neo4j, only with `--profile local-neo4j` |

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
cp .env.example .env          # then edit Neo4j creds if needed
uv sync                       # creates .venv and installs host deps
```

`uv run <cmd>` (used by `make test`) auto-syncs and runs inside that `.venv`,
so you never have to activate it manually. Prefer plain pip? `pip install
neo4j==5.23.0 pytest==8.3.2 python-dotenv==1.0.1` in a venv of your own works
too — the dependencies live in `pyproject.toml`.

### Configure Neo4j (via environment variables)

Neo4j credentials are read entirely from the environment — nothing is
hard-coded. Set these in `.env`:

| Variable | Meaning |
|----------|---------|
| `NEO4J_URI` | Bolt URI **as seen from the Spark container** (e.g. `bolt://neo4j:7687`, `bolt://host.docker.internal:7687`, or `neo4j+s://…` for Aura) |
| `NEO4J_URI_HOST` | Bolt URI **as seen from the host** (defaults to `bolt://localhost:7687`) |
| `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE` | credentials + target database |

> The two URIs differ because the Spark job runs inside Docker while the pytest
> harness runs on your host. With Aura (or any externally reachable URI) you can
> set both to the same value.

## Run

**Option A — bring your own Neo4j** (external / Aura), Iceberg in Docker:

```bash
make up            # starts iceberg-rest, minio, spark-iceberg
make test
```

**Option B — everything local**, including a throwaway Neo4j:

```bash
make up-local      # also starts a neo4j container
make test
```

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
5. Cleans up the `:*RT` graph afterward.

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

`make test` deliberately **leaves the stack running** so you can inspect the
tables afterward. Tear down explicitly when you're done:

```bash
make down     # stop & remove containers; Iceberg data survives in the volume
make clean    # stop & remove containers AND volumes (wipes all Iceberg data)
```

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
src/config.py               # env-driven config shared by both jobs
src/neo4j_to_iceberg.py     # direction 1
src/iceberg_to_neo4j.py     # direction 2
tests/test_roundtrip.py     # the bidirectional assertion
```
