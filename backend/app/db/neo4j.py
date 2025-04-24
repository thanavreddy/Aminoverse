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
    
    async def create_protein_interaction(self, source_id: str, target_id: str, score: float, evidence: str = None) -> bool:
        """Create an interaction relationship between two proteins with evidence."""
        query = """
        MATCH (source:Protein {id: $source_id})
        MATCH (target:Protein {id: $target_id})
        MERGE (source)-[r:INTERACTS_WITH {score: $score}]->(target)
        SET r.evidence = $evidence,
            r.source = $source,
            r.last_updated = datetime()
        RETURN r
        """
        results = await self.execute_query(query, {
            "source_id": source_id,
            "target_id": target_id,
            "score": score,
            "evidence": evidence or "",
            "source": "STRING-db"
        })
        return len(results) > 0
    
    async def create_protein_disease_association(self, protein_id: str, disease_id: str, evidence: str) -> bool:
        """Create an association between a protein and a disease."""
        # First ensure the disease exists
        disease_query = """
        MERGE (d:Disease {id: $disease_id})
        RETURN d
        """
        await self.execute_query(disease_query, {"disease_id": disease_id})
        
        # Then create the relationship
        query = """
        MATCH (p:Protein {id: $protein_id})
        MATCH (d:Disease {id: $disease_id})
        MERGE (p)-[r:ASSOCIATED_WITH]->(d)
        ON CREATE SET r.evidence = $evidence, r.source = $source, r.last_updated = datetime()
        ON MATCH SET r.evidence = $evidence, r.last_updated = datetime()
        RETURN r
        """
        results = await self.execute_query(query, {
            "protein_id": protein_id,
            "disease_id": disease_id,
            "evidence": evidence,
            "source": "DisGeNET"
        })
        return len(results) > 0
    
    async def create_drug_protein_targeting(self, drug_id: str, protein_id: str, mechanism: str) -> bool:
        """Create a targeting relationship between a drug and a protein."""
        # First ensure the drug exists
        drug_query = """
        MERGE (d:Drug {id: $drug_id})
        RETURN d
        """
        await self.execute_query(drug_query, {"drug_id": drug_id})
        
        # Then create the relationship
        query = """
        MATCH (d:Drug {id: $drug_id})
        MATCH (p:Protein {id: $protein_id})
        MERGE (d)-[r:TARGETS]->(p)
        ON CREATE SET r.mechanism = $mechanism, r.source = $source, r.last_updated = datetime()
        ON MATCH SET r.mechanism = $mechanism, r.last_updated = datetime()
        RETURN r
        """
        results = await self.execute_query(query, {
            "drug_id": drug_id,
            "protein_id": protein_id,
            "mechanism": mechanism,
            "source": "DrugBank/ChEMBL"
        })
        return len(results) > 0
        
    async def create_protein_variant(self, variant_data: Dict[str, Any], protein_id: str) -> bool:
        """Create a variant of a protein."""
        if not variant_data.get('id'):
            logger.error("Variant ID is required")
            return False
        
        # Create the variant node
        create_query = """
        CREATE (v:Variant {
            id: $id,
            name: $name,
            type: $type,
            location: $location,
            original_residue: $original_residue,
            variant_residue: $variant_residue,
            effect: $effect,
            clinical_significance: $clinical_significance
        })
        RETURN v
        """
        
        # Set default values for optional fields
        params = {
            'id': variant_data['id'],
            'name': variant_data.get('name', ''),
            'type': variant_data.get('type', ''),
            'location': variant_data.get('location', 0),
            'original_residue': variant_data.get('original_residue', ''),
            'variant_residue': variant_data.get('variant_residue', ''),
            'effect': variant_data.get('effect', ''),
            'clinical_significance': variant_data.get('clinical_significance', '')
        }
        
        results = await self.execute_query(create_query, params)
        if len(results) == 0:
            return False
        
        # Create the relationship to the protein
        relation_query = """
        MATCH (v:Variant {id: $variant_id})
        MATCH (p:Protein {id: $protein_id})
        MERGE (v)-[r:VARIANT_OF]->(p)
        RETURN r
        """
        
        results = await self.execute_query(relation_query, {
            "variant_id": variant_data['id'],
            "protein_id": protein_id
        })
        
        return len(results) > 0

    async def create_disease(self, disease_data: Dict[str, Any]) -> bool:
        """Create a new disease node in the database."""
        if not disease_data.get('id'):
            logger.error("Disease ID is required")
            return False
        
        query = """
        MERGE (d:Disease {id: $id})
        ON CREATE SET 
            d.name = $name,
            d.description = $description,
            d.source = $source
        RETURN d
        """
        
        params = {
            'id': disease_data['id'],
            'name': disease_data.get('name', ''),
            'description': disease_data.get('description', ''),
            'source': disease_data.get('source', 'external-api')
        }
        
        results = await self.execute_query(query, params)
        return len(results) > 0
    
    async def create_drug(self, drug_data: Dict[str, Any]) -> bool:
        """Create a new drug node in the database."""
        if not drug_data.get('drug_id'):
            logger.error("Drug ID is required")
            return False
        
        query = """
        MERGE (d:Drug {id: $id})
        ON CREATE SET 
            d.name = $name,
            d.description = $description,
            d.mechanism = $mechanism,
            d.source = $source
        RETURN d
        """
        
        params = {
            'id': drug_data['drug_id'],
            'name': drug_data.get('name', ''),
            'description': drug_data.get('description', ''),
            'mechanism': drug_data.get('mechanism', ''),
            'source': drug_data.get('source', 'external-api')
        }
        
        results = await self.execute_query(query, params)
        return len(results) > 0
        
    async def run_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Run a custom Cypher query and return the results."""
        return await self.execute_query(query, parameters)