import logging
import json
from typing import Dict, List, Optional, Any, Union

from app.db.neo4j import Neo4jDatabase
from app.cache.redis_client import RedisClient

logger = logging.getLogger(__name__)

class KnowledgeGraphService:
    """Service for managing and querying the knowledge graph."""
    
    def __init__(self, db: Neo4jDatabase, redis_client: RedisClient):
        """Initialize the knowledge graph service."""
        self.db = db
        self.redis_client = redis_client
    
    async def get_protein_graph(self, protein_id: str, depth: int = 1) -> Dict[str, Any]:
        """
        Get a graph representation of a protein and its relationships.
        
        Args:
            protein_id: The UniProt ID of the protein
            depth: The depth of relationships to retrieve (default: 1)
        
        Returns:
            Dict with nodes and edges representing the protein network
        """
        # Check cache first
        cache_key = f"protein_graph:{protein_id}:depth:{depth}"
        cached_graph = await self.redis_client.get_value(cache_key)
        if cached_graph:
            logger.info(f"Retrieved protein graph for {protein_id} from cache")
            return cached_graph
        
        # Query Neo4j for the protein and its relationships
        cypher_query = """
        MATCH (p:Protein {id: $protein_id})
        CALL apoc.path.subgraphAll(p, {maxLevel: $depth})
        YIELD nodes, relationships
        RETURN nodes, relationships
        """
        
        try:
            result = await self.db.execute_query(cypher_query, {"protein_id": protein_id, "depth": depth})
            if not result:
                return {"nodes": [], "edges": []}
            
            # Process nodes
            nodes = []
            for node in result.get("nodes", []):
                node_type = list(node.labels)[0]  # Get the first label as node type
                node_data = {
                    "id": node.id,
                    "type": node_type,
                    **node._properties  # Include all node properties
                }
                nodes.append(node_data)
            
            # Process relationships
            edges = []
            for rel in result.get("relationships", []):
                edge_data = {
                    "id": rel.id,
                    "source": rel.start_node.id,
                    "target": rel.end_node.id,
                    "type": rel.type,
                    **rel._properties  # Include all edge properties
                }
                edges.append(edge_data)
            
            graph_data = {
                "nodes": nodes,
                "edges": edges
            }
            
            # Cache the result
            await self.redis_client.set_value(cache_key, graph_data, expire=3600)  # Cache for 1 hour
            
            return graph_data
        
        except Exception as e:
            logger.error(f"Error retrieving protein graph for {protein_id}: {str(e)}")
            return {"nodes": [], "edges": []}
    
    async def get_pathway(self, pathway_id: str) -> Dict[str, Any]:
        """
        Get a complete biological pathway.
        
        Args:
            pathway_id: The ID of the pathway (e.g., KEGG or Reactome ID)
        
        Returns:
            Dict with pathway information and all involved proteins
        """
        # Check cache first
        cache_key = f"pathway:{pathway_id}"
        cached_pathway = await self.redis_client.get_value(cache_key)
        if cached_pathway:
            return cached_pathway
        
        # Query Neo4j for the pathway
        cypher_query = """
        MATCH (pathway:Pathway {id: $pathway_id})
        OPTIONAL MATCH (pathway)-[r:INVOLVES]->(p:Protein)
        RETURN pathway, collect(p) as proteins
        """
        
        try:
            result = await self.db.execute_query(cypher_query, {"pathway_id": pathway_id})
            if not result or not result.get("pathway"):
                return {"error": f"Pathway {pathway_id} not found"}
            
            pathway_node = result.get("pathway")
            proteins = result.get("proteins", [])
            
            pathway_data = {
                "id": pathway_node.get("id"),
                "name": pathway_node.get("name"),
                "description": pathway_node.get("description"),
                "source": pathway_node.get("source"),  # KEGG, Reactome, etc.
                "proteins": [
                    {
                        "id": p.get("id"),
                        "name": p.get("name"),
                        "function": p.get("function")
                    }
                    for p in proteins
                ]
            }
            
            # Cache the result
            await self.redis_client.set_value(cache_key, pathway_data, expire=3600)  # Cache for 1 hour
            
            return pathway_data
        
        except Exception as e:
            logger.error(f"Error retrieving pathway {pathway_id}: {str(e)}")
            return {"error": f"Error retrieving pathway: {str(e)}"}
    
    async def find_shortest_path(self, source_id: str, target_id: str) -> Dict[str, Any]:
        """
        Find the shortest path between two proteins in the knowledge graph.
        
        Args:
            source_id: UniProt ID of the source protein
            target_id: UniProt ID of the target protein
        
        Returns:
            Dict with path information
        """
        # Check cache first
        cache_key = f"path:{source_id}:{target_id}"
        cached_path = await self.redis_client.get_value(cache_key)
        if cached_path:
            return cached_path
        
        # Query Neo4j for the shortest path
        cypher_query = """
        MATCH (source:Protein {id: $source_id}),
              (target:Protein {id: $target_id}),
              path = shortestPath((source)-[*]-(target))
        RETURN path
        """
        
        try:
            result = await self.db.execute_query(cypher_query, {
                "source_id": source_id, 
                "target_id": target_id
            })
            
            if not result or not result.get("path"):
                return {
                    "found": False,
                    "message": f"No path found between proteins {source_id} and {target_id}"
                }
            
            path = result.get("path")
            
            # Extract nodes and relationships from the path
            nodes = []
            for node in path.nodes:
                node_type = list(node.labels)[0]
                node_data = {
                    "id": node.id,
                    "type": node_type,
                    **node._properties
                }
                nodes.append(node_data)
            
            relationships = []
            for rel in path.relationships:
                rel_data = {
                    "id": rel.id,
                    "source": rel.start_node.id,
                    "target": rel.end_node.id,
                    "type": rel.type,
                    **rel._properties
                }
                relationships.append(rel_data)
            
            path_data = {
                "found": True,
                "length": len(relationships),
                "nodes": nodes,
                "relationships": relationships
            }
            
            # Cache the result
            await self.redis_client.set_value(cache_key, path_data, expire=3600)  # Cache for 1 hour
            
            return path_data
        
        except Exception as e:
            logger.error(f"Error finding path between {source_id} and {target_id}: {str(e)}")
            return {"error": f"Error finding path: {str(e)}"}
    
    async def get_common_targets(self, drug_ids: List[str]) -> Dict[str, Any]:
        """
        Get common protein targets between multiple drugs.
        
        Args:
            drug_ids: List of drug IDs (e.g., DrugBank IDs)
        
        Returns:
            Dict with common targets and their information
        """
        if not drug_ids:
            return {"targets": []}
        
        # Check cache first
        drug_ids_key = ":".join(sorted(drug_ids))
        cache_key = f"common_targets:{drug_ids_key}"
        cached_targets = await self.redis_client.get_value(cache_key)
        if cached_targets:
            return cached_targets
        
        # Query Neo4j for common targets
        drug_params = {f"drug_{i}": drug_id for i, drug_id in enumerate(drug_ids)}
        drug_match_clauses = [f"(d{i}:Drug {{id: $drug_{i}}})" for i in range(len(drug_ids))]
        drug_match_string = ", ".join(drug_match_clauses)
        
        # Build a Cypher query that finds proteins targeted by ALL drugs in the list
        target_match_clauses = [f"(d{i})-[:TARGETS]->(p:Protein)" for i in range(len(drug_ids))]
        target_match_string = " AND ".join(target_match_clauses)
        
        cypher_query = f"""
        MATCH {drug_match_string}, {target_match_string}
        RETURN p as protein, collect(distinct [d.id, d.name]) as drugs
        """
        
        try:
            result = await self.db.execute_query(cypher_query, drug_params)
            if not result:
                return {"targets": []}
            
            targets = []
            for record in result:
                protein = record.get("protein")
                drugs = record.get("drugs", [])
                
                target_data = {
                    "protein_id": protein.get("id"),
                    "protein_name": protein.get("name"),
                    "function": protein.get("function"),
                    "drugs": [{"id": d[0], "name": d[1]} for d in drugs]
                }
                targets.append(target_data)
            
            result_data = {"targets": targets}
            
            # Cache the result
            await self.redis_client.set_value(cache_key, result_data, expire=3600)  # Cache for 1 hour
            
            return result_data
        
        except Exception as e:
            logger.error(f"Error finding common targets for drugs {drug_ids}: {str(e)}")
            return {"error": f"Error finding common targets: {str(e)}"}
    
    async def search_knowledge_graph(self, query: str) -> Dict[str, Any]:
        """
        Search the knowledge graph for entities matching a text query.
        
        Args:
            query: Text to search for in the knowledge graph
        
        Returns:
            Dict with search results grouped by entity type
        """
        # Check cache first
        cache_key = f"search:{hash(query)}"
        cached_results = await self.redis_client.get_value(cache_key)
        if cached_results:
            return cached_results
        
        # Prepare Neo4j full-text search query
        # This assumes we have full-text search indexes set up in Neo4j
        cypher_query = """
        // Search proteins
        CALL db.index.fulltext.queryNodes("proteinIndex", $query) YIELD node as protein, score
        WITH collect({entity: protein, score: score, type: 'protein'}) as proteins
        
        // Search diseases
        CALL db.index.fulltext.queryNodes("diseaseIndex", $query) YIELD node as disease, score
        WITH proteins, collect({entity: disease, score: score, type: 'disease'}) as diseases
        
        // Search drugs
        CALL db.index.fulltext.queryNodes("drugIndex", $query) YIELD node as drug, score
        WITH proteins, diseases, collect({entity: drug, score: score, type: 'drug'}) as drugs
        
        // Search pathways
        CALL db.index.fulltext.queryNodes("pathwayIndex", $query) YIELD node as pathway, score
        WITH proteins, diseases, drugs, collect({entity: pathway, score: score, type: 'pathway'}) as pathways
        
        // Combine all results
        UNWIND proteins + diseases + drugs + pathways as result
        RETURN result.type as type, result.entity as entity, result.score as score
        ORDER BY score DESC
        LIMIT 20
        """
        
        try:
            result = await self.db.execute_query(cypher_query, {"query": query})
            if not result:
                return {
                    "proteins": [],
                    "diseases": [],
                    "drugs": [],
                    "pathways": []
                }
            
            # Organize results by type
            organized_results = {
                "proteins": [],
                "diseases": [],
                "drugs": [],
                "pathways": []
            }
            
            for record in result:
                entity_type = record.get("type")
                entity = record.get("entity")
                score = record.get("score", 0.0)
                
                entity_data = {
                    **entity._properties,  # Include all properties
                    "score": score
                }
                
                if entity_type in organized_results:
                    organized_results[entity_type].append(entity_data)
            
            # Cache the result
            await self.redis_client.set_value(cache_key, organized_results, expire=3600)  # Cache for 1 hour
            
            return organized_results
        
        except Exception as e:
            logger.error(f"Error searching knowledge graph for '{query}': {str(e)}")
            return {"error": f"Error searching knowledge graph: {str(e)}"}
    
    # Additional graph management methods
    
    async def add_protein_interaction(
        self, 
        source_id: str, 
        target_id: str, 
        interaction_type: str, 
        score: float,
        evidence: str = None
    ) -> bool:
        """
        Add a protein-protein interaction to the knowledge graph.
        
        Args:
            source_id: UniProt ID of the source protein
            target_id: UniProt ID of the target protein
            interaction_type: Type of interaction (e.g., 'binds', 'phosphorylates')
            score: Confidence score for the interaction (0-1)
            evidence: Source or evidence for the interaction
            
        Returns:
            Boolean indicating success
        """
        cypher_query = """
        MATCH (source:Protein {id: $source_id})
        MATCH (target:Protein {id: $target_id})
        MERGE (source)-[r:INTERACTS_WITH {type: $interaction_type}]->(target)
        ON CREATE SET r.score = $score, r.evidence = $evidence, r.created_at = datetime()
        ON MATCH SET r.score = $score, r.evidence = $evidence, r.updated_at = datetime()
        RETURN source, r, target
        """
        
        try:
            await self.db.execute_query(cypher_query, {
                "source_id": source_id,
                "target_id": target_id,
                "interaction_type": interaction_type,
                "score": score,
                "evidence": evidence
            })
            
            # Invalidate related caches
            await self._invalidate_protein_caches(source_id)
            await self._invalidate_protein_caches(target_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding interaction between {source_id} and {target_id}: {str(e)}")
            return False
    
    async def add_drug_target(
        self, 
        drug_id: str, 
        protein_id: str, 
        mechanism: str = None, 
        affinity: float = None,
        source: str = None
    ) -> bool:
        """
        Add a drug-protein targeting relationship to the knowledge graph.
        
        Args:
            drug_id: DrugBank ID of the drug
            protein_id: UniProt ID of the target protein
            mechanism: Mechanism of action
            affinity: Binding affinity (e.g., IC50 in nM)
            source: Source of the drug-target interaction
            
        Returns:
            Boolean indicating success
        """
        cypher_query = """
        MERGE (d:Drug {id: $drug_id})
        ON CREATE SET d.name = $drug_id
        
        WITH d
        MATCH (p:Protein {id: $protein_id})
        MERGE (d)-[r:TARGETS]->(p)
        ON CREATE SET r.mechanism = $mechanism, r.affinity = $affinity, 
                      r.source = $source, r.created_at = datetime()
        ON MATCH SET r.mechanism = $mechanism, r.affinity = $affinity, 
                     r.source = $source, r.updated_at = datetime()
        RETURN d, r, p
        """
        
        try:
            await self.db.execute_query(cypher_query, {
                "drug_id": drug_id,
                "protein_id": protein_id,
                "mechanism": mechanism,
                "affinity": affinity,
                "source": source
            })
            
            # Invalidate related caches
            await self._invalidate_protein_caches(protein_id)
            await self._invalidate_drug_caches(drug_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding drug target relationship: {str(e)}")
            return False
    
    async def get_entity_graph(self, entity_id: str, entity_type: str = "Protein") -> Dict[str, Any]:
        """
        Get graph representation centered around any entity type.
        
        Args:
            entity_id: The ID of the entity
            entity_type: The type of entity (Protein, Disease, Drug, etc.)
        
        Returns:
            Dict with nodes and edges representing the entity subgraph
        """
        # Check cache first
        cache_key = f"entity_graph:{entity_type}:{entity_id}"
        cached_graph = await self.redis_client.get_value(cache_key)
        if cached_graph:
            logger.info(f"Retrieved entity graph for {entity_type}:{entity_id} from cache")
            return cached_graph
        
        try:
            # Try first with the simpler query that doesn't rely on APOC
            simple_query = """
            MATCH (e:{entity_type} {{id: $entity_id}})
            OPTIONAL MATCH (e)-[r1]-(n1)
            OPTIONAL MATCH (n1)-[r2]-(n2)
            WHERE n2 <> e AND NOT (n2)--(e)
            RETURN e, collect(distinct r1) as direct_rels, collect(distinct n1) as level1_nodes,
                   collect(distinct r2) as indirect_rels, collect(distinct n2) as level2_nodes
            """.format(entity_type=entity_type)
            
            logger.info(f"Executing simple query for {entity_type}:{entity_id}")
            result = await self.db.execute_query(simple_query, {"entity_id": entity_id})
            
            if not result:
                logger.warning(f"No results from simple query for {entity_type}:{entity_id}")
                # If no results, try fallback to demo data
                return self._generate_demo_knowledge_graph(entity_id, entity_type)
            
            # Extract central entity
            central_entity = result.get("e")
            if not central_entity:
                logger.warning(f"Central entity not found for {entity_type}:{entity_id}")
                return self._generate_demo_knowledge_graph(entity_id, entity_type)
            
            # Process nodes and relationships from results
            all_nodes = []
            all_edges = []
            node_map = {}  # For deduplication and quick lookups
            
            # Helper function for safe property extraction
            def safe_get_property(obj, prop, default=None):
                if hasattr(obj, "_properties") and prop in obj._properties:
                    return obj._properties[prop]
                return default
            
            # Helper function for node processing
            def process_node(node, is_central=False):
                if not node:
                    return None
                    
                try:
                    node_id = safe_get_property(node, "id")
                    if not node_id:
                        node_id = str(hash(str(node)))
                        
                    # Skip if we've already processed this node
                    if node_id in node_map:
                        return node_id
                        
                    # Get labels
                    node_type = None
                    if hasattr(node, "labels"):
                        labels = list(node.labels)
                        if labels:
                            node_type = labels[0]
                            
                    if not node_type:
                        node_type = entity_type if is_central else "Unknown"
                    
                    # Get properties safely
                    props = {}
                    if hasattr(node, "_properties"):
                        props = dict(node._properties)
                    
                    # Create node data with defaults for missing fields
                    node_data = {
                        "id": node_id,
                        "type": node_type,
                        "label": safe_get_property(node, "name", safe_get_property(node, "id", "Unknown")),
                    }
                    
                    # Add all properties
                    node_data.update(props)
                    
                    # Mark as central if needed
                    if is_central:
                        node_data["centrality"] = 1
                    
                    # Add to nodes list and mapping
                    all_nodes.append(node_data)
                    node_map[node_id] = len(all_nodes) - 1
                    
                    return node_id
                except Exception as e:
                    logger.error(f"Error processing node: {str(e)}")
                    return None
            
            # Helper function for relationship processing
            def process_relationship(rel):
                if not rel:
                    return
                    
                try:
                    # Get source and target nodes
                    source_node = rel.start_node if hasattr(rel, "start_node") else None
                    target_node = rel.end_node if hasattr(rel, "end_node") else None
                    
                    if not source_node or not target_node:
                        return
                    
                    source_id = safe_get_property(source_node, "id")
                    target_id = safe_get_property(target_node, "id")
                    
                    if not source_id or not target_id:
                        return
                    
                    # Get relationship type and properties
                    rel_type = rel.type if hasattr(rel, "type") else "RELATED_TO"
                    
                    props = {}
                    if hasattr(rel, "_properties"):
                        props = dict(rel._properties)
                    
                    # Create edge data
                    edge_id = f"edge_{len(all_edges)}"
                    edge_data = {
                        "id": edge_id,
                        "source": source_id,
                        "target": target_id,
                        "type": rel_type
                    }
                    
                    # Add all properties
                    edge_data.update(props)
                    
                    all_edges.append(edge_data)
                except Exception as e:
                    logger.error(f"Error processing relationship: {str(e)}")
            
            # Process central entity
            central_id = process_node(central_entity, True)
            
            # Process level 1 nodes
            level1_nodes = result.get("level1_nodes", [])
            for node in level1_nodes:
                process_node(node)
            
            # Process level 2 nodes
            level2_nodes = result.get("level2_nodes", [])
            for node in level2_nodes:
                process_node(node)
            
            # Process direct relationships
            direct_rels = result.get("direct_rels", [])
            for rel in direct_rels:
                process_relationship(rel)
            
            # Process indirect relationships
            indirect_rels = result.get("indirect_rels", [])
            for rel in indirect_rels:
                process_relationship(rel)
            
            # If we processed nodes but got no relationships, try to add some basic edges
            if len(all_nodes) > 1 and not all_edges and central_id:
                # Connect central node to all others
                for node in all_nodes:
                    if node["id"] != central_id:
                        all_edges.append({
                            "id": f"edge_{len(all_edges)}",
                            "source": central_id,
                            "target": node["id"],
                            "type": "RELATED_TO"
                        })
            
            # Prepare final graph data
            graph_data = {
                "nodes": all_nodes,
                "edges": all_edges
            }
            
            # Log the results
            logger.info(f"Generated knowledge graph with {len(all_nodes)} nodes and {len(all_edges)} edges")
            
            # If we have insufficient data, return demo data instead
            if len(all_nodes) <= 1 or len(all_edges) == 0:
                logger.warning(f"Insufficient graph data for {entity_type}:{entity_id}, using demo data")
                return self._generate_demo_knowledge_graph(entity_id, entity_type)
            
            # Cache the result
            await self.redis_client.set_value(cache_key, graph_data, expire=3600)  # Cache for 1 hour
            
            return graph_data
            
        except Exception as e:
            logger.error(f"Error retrieving entity graph for {entity_type}:{entity_id}: {str(e)}")
            # Return demo data on error
            return self._generate_demo_knowledge_graph(entity_id, entity_type)

    def _generate_demo_knowledge_graph(self, entity_id: str, entity_type: str) -> Dict[str, Any]:
        """
        Generate a demonstration knowledge graph for visualization purposes.
        Used as a fallback when real data cannot be retrieved.
        
        Args:
            entity_id: The ID of the entity
            entity_type: The type of entity (Protein, Disease, Drug, etc.)
            
        Returns:
            Dict with nodes and edges for visualization
        """
        logger.info(f"Generating demo knowledge graph for {entity_type}:{entity_id}")
        
        # Create central entity node
        central_node = {
            "id": entity_id,
            "type": entity_type,
            "label": f"{entity_type} {entity_id}",
            "name": f"{entity_type} {entity_id}",
            "centrality": 1
        }
        
        nodes = [central_node]
        edges = []
        
        # Generate different demo graphs based on entity type
        if entity_type.lower() == "protein":
            # Add related proteins
            for i in range(1, 5):
                related_id = f"PROTEIN_{i}"
                nodes.append({
                    "id": related_id,
                    "type": "Protein",
                    "label": f"Related Protein {i}",
                    "name": f"Related Protein {i}"
                })
                edges.append({
                    "id": f"edge_{i}",
                    "source": entity_id,
                    "target": related_id,
                    "type": "INTERACTS_WITH"
                })
            
            # Add associated diseases
            for i in range(1, 3):
                disease_id = f"DISEASE_{i}"
                nodes.append({
                    "id": disease_id,
                    "type": "Disease",
                    "label": f"Associated Disease {i}",
                    "name": f"Associated Disease {i}"
                })
                edges.append({
                    "id": f"edge_d{i}",
                    "source": entity_id,
                    "target": disease_id,
                    "type": "ASSOCIATED_WITH"
                })
            
            # Add drugs targeting the protein
            for i in range(1, 3):
                drug_id = f"DRUG_{i}"
                nodes.append({
                    "id": drug_id,
                    "type": "Drug",
                    "label": f"Targeting Drug {i}",
                    "name": f"Targeting Drug {i}"
                })
                edges.append({
                    "id": f"edge_t{i}",
                    "source": drug_id,
                    "target": entity_id,
                    "type": "TARGETS"
                })
                
            # Add a pathway
            pathway_id = "PATHWAY_1"
            nodes.append({
                "id": pathway_id,
                "type": "Pathway",
                "label": "Related Pathway",
                "name": "Related Pathway"
            })
            edges.append({
                "id": "edge_p1",
                "source": entity_id,
                "target": pathway_id,
                "type": "PART_OF"
            })
            
            # Connect some nodes with each other
            edges.append({
                "id": "edge_cross1",
                "source": "PROTEIN_1",
                "target": "DISEASE_1",
                "type": "ASSOCIATED_WITH"
            })
            edges.append({
                "id": "edge_cross2", 
                "source": "DRUG_1",
                "target": "DISEASE_1",
                "type": "TREATS"
            })
            
        elif entity_type.lower() == "disease":
            # Add associated proteins
            for i in range(1, 4):
                protein_id = f"PROTEIN_{i}"
                nodes.append({
                    "id": protein_id,
                    "type": "Protein",
                    "label": f"Related Protein {i}",
                    "name": f"Related Protein {i}"
                })
                edges.append({
                    "id": f"edge_{i}",
                    "source": protein_id,
                    "target": entity_id,
                    "type": "ASSOCIATED_WITH"
                })
            
            # Add treatments
            for i in range(1, 3):
                drug_id = f"DRUG_{i}"
                nodes.append({
                    "id": drug_id,
                    "type": "Drug",
                    "label": f"Treatment {i}",
                    "name": f"Treatment {i}"
                })
                edges.append({
                    "id": f"edge_t{i}",
                    "source": drug_id,
                    "target": entity_id,
                    "type": "TREATS"
                })
                
            # Connect proteins with drugs
            edges.append({
                "id": "edge_cross1",
                "source": "DRUG_1",
                "target": "PROTEIN_1",
                "type": "TARGETS"
            })
            
        elif entity_type.lower() == "drug":
            # Add target proteins
            for i in range(1, 4):
                protein_id = f"PROTEIN_{i}"
                nodes.append({
                    "id": protein_id,
                    "type": "Protein",
                    "label": f"Target Protein {i}",
                    "name": f"Target Protein {i}"
                })
                edges.append({
                    "id": f"edge_{i}",
                    "source": entity_id,
                    "target": protein_id,
                    "type": "TARGETS"
                })
            
            # Add treated diseases
            for i in range(1, 3):
                disease_id = f"DISEASE_{i}"
                nodes.append({
                    "id": disease_id,
                    "type": "Disease",
                    "label": f"Treated Condition {i}",
                    "name": f"Treated Condition {i}"
                })
                edges.append({
                    "id": f"edge_d{i}",
                    "source": entity_id,
                    "target": disease_id,
                    "type": "TREATS"
                })
                
            # Connect diseases with proteins
            edges.append({
                "id": "edge_cross1",
                "source": "DISEASE_1",
                "target": "PROTEIN_1",
                "type": "ASSOCIATED_WITH"
            })
        
        else:
            # Generic demo graph for other entity types
            entity_types = ["Protein", "Disease", "Drug", "Pathway"]
            for i in range(1, 6):
                # Select a random entity type different from the central one
                related_type = entity_types[i % len(entity_types)]
                if related_type.lower() == entity_type.lower():
                    related_type = entity_types[(i+1) % len(entity_types)]
                    
                related_id = f"{related_type.upper()}_{i}"
                nodes.append({
                    "id": related_id,
                    "type": related_type,
                    "label": f"Related {related_type} {i}",
                    "name": f"Related {related_type} {i}"
                })
                edges.append({
                    "id": f"edge_{i}",
                    "source": entity_id,
                    "target": related_id,
                    "type": "RELATED_TO"
                })
        
        # Add a few more connections between nodes to make the graph more interesting
        if len(nodes) > 3:
            edges.append({
                "id": f"edge_extra_1",
                "source": nodes[1]["id"],
                "target": nodes[2]["id"],
                "type": "RELATED_TO"
            })
            
        if len(nodes) > 4:
            edges.append({
                "id": f"edge_extra_2",
                "source": nodes[2]["id"],
                "target": nodes[3]["id"],
                "type": "RELATED_TO"
            })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "is_demo": True  # Flag to indicate this is demo data
        }
    
    async def get_protein_knowledge_graph(self, protein_id: str) -> Dict[str, Any]:
        """
        Get knowledge graph centered around a protein entity.
        This is a convenience wrapper for get_entity_graph with protein-specific settings.
        
        Args:
            protein_id: The ID of the protein
            
        Returns:
            Dict with nodes and edges representing the protein's knowledge graph
        """
        return await self.get_entity_graph(protein_id, "Protein")
    
    # Helper methods for cache invalidation
    
    async def _invalidate_protein_caches(self, protein_id: str):
        """Invalidate caches related to a protein."""
        # Get all keys related to this protein
        protein_keys = await self.redis_client.get_keys_by_pattern(f"*{protein_id}*")
        
        # Delete all matched keys
        if protein_keys:
            await self.redis_client.delete_keys(protein_keys)
    
    async def _invalidate_drug_caches(self, drug_id: str):
        """Invalidate caches related to a drug."""
        # Get all keys related to this drug
        drug_keys = await self.redis_client.get_keys_by_pattern(f"*{drug_id}*")
        
        # Delete all matched keys
        if drug_keys:
            await self.redis_client.delete_keys(drug_keys)