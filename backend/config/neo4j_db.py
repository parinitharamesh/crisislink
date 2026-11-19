"""Neo4j graph database connection."""

import os
from neo4j import GraphDatabase

_driver = None


def get_neo4j_driver():
    global _driver
    if _driver is None:
        uri      = os.environ.get('NEO4J_URI',      'bolt://localhost:7687')
        user     = os.environ.get('NEO4J_USER',     'neo4j')
        password = os.environ.get('NEO4J_PASSWORD',  'crisislink_neo4j')
        _driver = GraphDatabase.driver(uri, auth=(user, password))
    return _driver


def run_cypher(query: str, params: dict = None):
    """Execute a Cypher query and return all records as dicts."""
    driver = get_neo4j_driver()
    with driver.session() as session:
        result = session.run(query, params or {})
        return [dict(record) for record in result]


def close_driver():
    global _driver
    if _driver:
        _driver.close()
        _driver = None
