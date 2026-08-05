// Subset of Neo4j's classic Movie graph.
// Loaded by the test fixture before the Neo4j -> Iceberg direction runs.
// Kept intentionally small but with enough Person/Movie/ACTED_IN/DIRECTED
// coverage to make a round-trip assertion meaningful.

// Start clean so re-runs are deterministic.
MATCH (n) DETACH DELETE n;

CREATE (TheMatrix:Movie {title:'The Matrix', released:1999, tagline:'Welcome to the Real World'})
CREATE (Keanu:Person {name:'Keanu Reeves', born:1964})
CREATE (Carrie:Person {name:'Carrie-Anne Moss', born:1967})
CREATE (Laurence:Person {name:'Laurence Fishburne', born:1961})
CREATE (Hugo:Person {name:'Hugo Weaving', born:1960})
CREATE (LillyW:Person {name:'Lilly Wachowski', born:1967})
CREATE (LanaW:Person {name:'Lana Wachowski', born:1965})
CREATE (JoelS:Person {name:'Joel Silver', born:1952})
CREATE (Keanu)-[:ACTED_IN {roles:['Neo']}]->(TheMatrix)
CREATE (Carrie)-[:ACTED_IN {roles:['Trinity']}]->(TheMatrix)
CREATE (Laurence)-[:ACTED_IN {roles:['Morpheus']}]->(TheMatrix)
CREATE (Hugo)-[:ACTED_IN {roles:['Agent Smith']}]->(TheMatrix)
CREATE (LillyW)-[:DIRECTED]->(TheMatrix)
CREATE (LanaW)-[:DIRECTED]->(TheMatrix)

CREATE (TheMatrixReloaded:Movie {title:'The Matrix Reloaded', released:2003, tagline:'Free your mind'})
CREATE (Keanu)-[:ACTED_IN {roles:['Neo']}]->(TheMatrixReloaded)
CREATE (Carrie)-[:ACTED_IN {roles:['Trinity']}]->(TheMatrixReloaded)
CREATE (Laurence)-[:ACTED_IN {roles:['Morpheus']}]->(TheMatrixReloaded)
CREATE (Hugo)-[:ACTED_IN {roles:['Agent Smith']}]->(TheMatrixReloaded)
CREATE (LillyW)-[:DIRECTED]->(TheMatrixReloaded)
CREATE (LanaW)-[:DIRECTED]->(TheMatrixReloaded)

CREATE (TheDevilsAdvocate:Movie {title:"The Devil's Advocate", released:1997, tagline:'Evil has its winning ways'})
CREATE (Al:Person {name:'Al Pacino', born:1940})
CREATE (Taylor:Person {name:'Taylor Hackford', born:1944})
CREATE (Charlize:Person {name:'Charlize Theron', born:1975})
CREATE (Keanu)-[:ACTED_IN {roles:['Kevin Lomax']}]->(TheDevilsAdvocate)
CREATE (Charlize)-[:ACTED_IN {roles:['Mary Ann Lomax']}]->(TheDevilsAdvocate)
CREATE (Al)-[:ACTED_IN {roles:['John Milton']}]->(TheDevilsAdvocate)
CREATE (Taylor)-[:DIRECTED]->(TheDevilsAdvocate)

CREATE (AFewGoodMen:Movie {title:'A Few Good Men', released:1992, tagline:"Deep down, you want the truth."})
CREATE (TomC:Person {name:'Tom Cruise', born:1962})
CREATE (JackN:Person {name:'Jack Nicholson', born:1937})
CREATE (DemiM:Person {name:'Demi Moore', born:1962})
CREATE (RobR:Person {name:'Rob Reiner', born:1947})
CREATE (TomC)-[:ACTED_IN {roles:['Lt. Daniel Kaffee']}]->(AFewGoodMen)
CREATE (JackN)-[:ACTED_IN {roles:['Col. Nathan R. Jessup']}]->(AFewGoodMen)
CREATE (DemiM)-[:ACTED_IN {roles:['Lt. Cdr. JoAnne Galloway']}]->(AFewGoodMen)
CREATE (RobR)-[:DIRECTED]->(AFewGoodMen)

CREATE (TopGun:Movie {title:'Top Gun', released:1986, tagline:'I feel the need, the need for speed.'})
CREATE (KellyM:Person {name:'Kelly McGillis', born:1957})
CREATE (TonyS:Person {name:'Tony Scott', born:1944})
CREATE (TomC)-[:ACTED_IN {roles:['Maverick']}]->(TopGun)
CREATE (KellyM)-[:ACTED_IN {roles:['Charlie']}]->(TopGun)
CREATE (TonyS)-[:DIRECTED]->(TopGun);
