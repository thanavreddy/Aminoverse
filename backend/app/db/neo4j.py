import logging
import asyncio
from typing import Any, Dict, List, Optional, Union, Tuple
from neo4j import AsyncGraphDatabase, AsyncDriver, Record, GraphDatabase
import neo4j

from app.core.config import settings

logger = logging.getLogger(__name__)

class Neo4jConnection:
    def __init__(self):
        self.uri = settings.NEO4J_URI
        self.user = settings.NEO4J_USER
        self.password = settings.NEO4J_PASSWORD
        self.driver = None

    async def get_driver(self):
        """Get or create a Neo4j driver instance"""
        if self.driver is None:
            # Using async driver to match async usage
            self.driver = AsyncGraphDatabase.driver(
                self.uri, 
                auth=(self.user, self.password)
            )
        return self.driver

    async def close(self):
        """Close the driver connection"""
        if self.driver is not None:
            await self.driver.close()
            self.driver = None

    async def test_connection(self) -> bool:
        """Test the Neo4j connection by running a simple query
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            driver = await self.get_driver()
            async with driver.session() as session:
                result = await session.run("RETURN 1 AS num")
                record = await result.single()
                return record and record['num'] == 1
        except Exception as e:
            logger.error(f"Neo4j connection error: {e}")
            return False

    async def query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return results
        
        Args:
            query: The Cypher query to execute
            params: Optional parameters for the query
            
        Returns:
            List of records as dictionaries
        """
        driver = await self.get_driver()
        
        result_list = []
        async with driver.session() as session:
            result = await session.run(query, params or {})
            records = await result.records()
            for record in records:
                result_list.append(dict(record))
        
        return result_list

class Neo4jDatabase:
    """Neo4j database interface for graph operations."""
    
    def __init__(self):
        """Initialize Neo4j connection."""
        try:
            # Create Neo4j driver instance
            self.driver = AsyncGraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            logger.info(f"Connected to Neo4j database at {settings.NEO4J_URI}")
        except Exception as e:
            logger.exception(f"Failed to connect to Neo4j: {str(e)}")
            self.driver = None
    
    async def close(self):
        """Close the Neo4j connection."""
        if self.driver:
            await self.driver.close()
            logger.info("Neo4j connection closed")
    
    async def verify_connectivity(self) -> bool:
        """Verify Neo4j connectivity."""
        if not self.driver:
            return False
        
        try:
            await self.driver.verify_connectivity()
            return True
        except Exception as e:
            logger.error(f"Neo4j connectivity verification failed: {str(e)}")
            return False
    
    async def execute_query(
        self,
        query: str,
        parameters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return results."""
        if not self.driver:
            logger.error("Neo4j driver not initialized")
            return []
        
        parameters = parameters or {}
        
        try:
            async with self.driver.session() as session:
                result = await session.run(query, parameters)
                records = await result.values()
                
                # Process records into dictionaries
                processed_results = []
                for record in records:
                    # Convert Neo4j types to Python native types
                    processed_record = {}
                    for i, field in enumerate(record):
                        if hasattr(field, 'items'):
                            processed_record[result.keys()[i]] = dict(field)
                        elif hasattr(field, '__iter__') and not isinstance(field, str):
                            processed_record[result.keys()[i]] = list(field)
                        else:
                            processed_record[result.keys()[i]] = field
                    
                    processed_results.append(processed_record)
                
                return processed_results
                
        except Exception as e:
            logger.exception(f"Error executing Neo4j query: {str(e)}")
            return []
    
    async def get_protein(self, protein_id: str) -> Optional[Dict[str, Any]]:
        """Get a protein from the database by ID."""
        query = """
        MATCH (p:Protein {id: $protein_id})
        RETURN p
        """
        results = await self.execute_query(query, {"protein_id": protein_id})
        
        if results and len(results) > 0 and 'p' in results[0]:
            return results[0]['p']
        
        return None
    
    async def get_protein_interactions(self, protein_id: str) -> List[Dict[str, Any]]:
        """Get protein interactions from the database."""
        query = """
        MATCH (p:Protein {id: $protein_id})-[r:INTERACTS_WITH]->(target:Protein)
        RETURN target.id AS protein_id, target.name AS protein_name, 
               target.description AS description, r.score AS score
        """
        return await self.execute_query(query, {"protein_id": protein_id})
    
    async def get_protein_diseases(self, protein_id: str) -> List[Dict[str, Any]]:
        """Get diseases associated with a protein."""
        query = """
        MATCH (p:Protein {id: $protein_id})-[r:ASSOCIATED_WITH]->(d:Disease)
        RETURN d.id AS disease_id, d.name AS name, 
               d.description AS description, r.evidence AS evidence
        """
        return await self.execute_query(query, {"protein_id": protein_id})
    
    async def get_protein_drugs(self, protein_id: str) -> List[Dict[str, Any]]:
        """Get drugs that target a protein."""
        query = """
        MATCH (d:Drug)-[r:TARGETS]->(p:Protein {id: $protein_id})
        RETURN d.id AS drug_id, d.name AS name, 
               d.description AS description, r.mechanism AS mechanism
        """
        return await self.execute_query(query, {"protein_id": protein_id})
    
    async def get_protein_variants(self, protein_id: str) -> List[Dict[str, Any]]:
        """Get variants of a protein."""
        query = """
        MATCH (v:Variant)-[r:VARIANT_OF]->(p:Protein {id: $protein_id})
        RETURN v.id AS variant_id, v.name AS name, v.type AS type,
               v.location AS location, v.original_residue AS original_residue,
               v.variant_residue AS variant_residue, v.effect AS effect,
               v.clinical_significance AS clinical_significance
        """
        return await self.execute_query(query, {"protein_id": protein_id})
    
    async def create_protein(self, protein_data: Dict[str, Any]) -> bool:
        """Create a new protein in the database."""
        if not protein_data.get('id'):
            logger.error("Protein ID is required")
            return False
        
        query = """
        CREATE (p:Protein {
            id: $id,
            name: $name,
            full_name: $full_name,
            function: $function,
            description: $description,
            sequence: $sequence
        })
        RETURN p
        """
        
        # Set default values for optional fields
        params = {
            'id': protein_data['id'],
            'name': protein_data.get('name', ''),
            'full_name': protein_data.get('full_name', ''),
            'function': protein_data.get('function', ''),
            'description': protein_data.get('description', ''),
            'sequence': protein_data.get('sequence', '')
        }
        
        results = await self.execute_query(query, params)
        return len(results) > 0
    
    async def import_graph_data(self, cypher_file_path: str) -> bool:
        """
        Import graph data from a Cypher script file.
        
        This is typically used to initialize the database with sample data.
        """
        try:
            with open(cypher_file_path, 'r') as file:
                cypher_script = file.read()
            
            # Split the script into individual statements
            statements = cypher_script.split(';')
            
            success_count = 0
            for statement in statements:
                # Skip empty statements
                if not statement.strip():
                    continue
                
                try:
                    # Execute each statement
                    await self.execute_query(statement)
                    success_count += 1
                except Exception as e:
                    logger.error(f"Error executing statement: {str(e)}")
            
            logger.info(f"Successfully executed {success_count} statements")
            return success_count > 0
            
        except Exception as e:
            logger.exception(f"Error importing graph data: {str(e)}")
            return False