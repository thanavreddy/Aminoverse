import logging
import httpx
import json
import asyncio
from typing import Dict, List, Optional, Any, Union

from app.core.config import settings
from app.cache.redis_client import RedisClient
from app.db.neo4j import Neo4jDatabase

logger = logging.getLogger(__name__)

# Global dictionary to track API calls in progress
# Using a class to make it shareable between instances
class APICallTracker:
    def __init__(self):
        self.in_progress = {}
        self.locks = {}

# Singleton instance
api_tracker = APICallTracker()

class ProteinService:
    """Service for retrieving and processing protein information."""
    
    def __init__(self, redis_client: RedisClient, db: Neo4jDatabase):
        """Initialize the protein service with cache and database clients."""
        self.redis_client = redis_client
        self.db = db
        self.uniprot_api_url = settings.UNIPROT_API_URL
        self.pdb_api_url = settings.PDB_API_URL
        self.string_db_api_url = settings.STRING_DB_API_URL
    
    async def get_protein_info(self, protein_id: str) -> Dict[str, Any]:
        """
        Get comprehensive information about a protein.
        
        This method first checks the cache, then the graph database,
        and finally external APIs if necessary.
        """
        # Check cache first
        cached_data = await self.redis_client.get_cached_protein_data(protein_id)
        if cached_data:
            logger.info(f"Retrieved protein data for {protein_id} from cache")
            return cached_data
        
        # Check graph database
        db_data = await self.db.get_protein(protein_id)
        if db_data:
            # Format data
            protein_data = {
                'id': db_data.get('id'),
                'name': db_data.get('name'),
                'full_name': db_data.get('full_name'),
                'function': db_data.get('function'),
                'description': db_data.get('description'),
                'sequence': db_data.get('sequence')
            }
            
            # Get additional data
            interactions = await self.get_protein_interactions(protein_id)
            diseases = await self.get_disease_associations(protein_id)
            structure = await self.get_protein_structure(protein_id)
            drugs = await self.get_drug_interactions(protein_id)
            variants = await self.get_protein_variants(protein_id)
            
            # Add to response
            if interactions:
                protein_data['interactions'] = interactions
            if diseases:
                protein_data['diseases'] = diseases
            if structure:
                protein_data['structure'] = structure
            if drugs:
                protein_data['drugs'] = drugs
            if variants:
                protein_data['variants'] = variants
            
            # Cache the result
            await self.redis_client.cache_protein_data(protein_id, protein_data)
            
            logger.info(f"Retrieved protein data for {protein_id} from graph database")
            return protein_data
        
        # If not found in DB or cache, fetch from external APIs
        try:
            # Try UniProt first
            uniprot_data = await self._fetch_uniprot_data(protein_id)
            if uniprot_data:
                logger.info(f"Retrieved protein data for {protein_id} from UniProt")
                
                # Cache the result
                await self.redis_client.cache_protein_data(protein_id, uniprot_data)
                
                # Optionally store in graph database for future queries
                await self.db.create_protein({
                    'id': uniprot_data.get('id'),
                    'name': uniprot_data.get('name'),
                    'full_name': uniprot_data.get('full_name'),
                    'function': uniprot_data.get('function'),
                    'description': uniprot_data.get('description'),
                    'sequence': uniprot_data.get('sequence')
                })
                
                return uniprot_data
        except Exception as e:
            logger.error(f"Error fetching UniProt data for {protein_id}: {str(e)}")
        
        # If all else fails, return a minimal record with just the ID
        logger.warning(f"No data found for protein {protein_id}")
        return {
            "id": protein_id,
            "name": protein_id,
            "description": f"No information available for protein {protein_id}."
        }
    
    async def get_protein_structure(self, protein_id: str) -> Dict[str, Any]:
        """
        Get 3D structure information for a protein.
        
        Attempts to retrieve from:
        1. PDB (experimental structures)
        2. AlphaFold DB (predicted structures)
        """
        # Check cache first
        cache_key = f"structure:{protein_id}"
        cached_data = await self.redis_client.get(cache_key)
        if cached_data:
            logger.info(f"Retrieved structure data for {protein_id} from cache")
            return json.loads(cached_data)
        
        # Try to get experimental structure from PDB
        try:
            pdb_data = await self._query_pdb(protein_id)
            if pdb_data and pdb_data.get('pdb_id'):
                # Cache the result
                await self.redis_client.set(cache_key, json.dumps(pdb_data), expire=86400)
                return pdb_data
        except Exception as e:
            logger.warning(f"Error querying PDB for {protein_id}: {str(e)}")
        
        # If no PDB structure, try AlphaFold
        try:
            alphafold_data = await self._query_alphafold(protein_id)
            if alphafold_data and alphafold_data.get('alphafold_id'):
                # Cache the result
                await self.redis_client.set(cache_key, json.dumps(alphafold_data), expire=86400)
                return alphafold_data
        except Exception as e:
            logger.warning(f"Error querying AlphaFold for {protein_id}: {str(e)}")
        
        # If we get here, no structure was found
        result = {"status": "unavailable", "message": f"No structure data found for {protein_id}"}
        await self.redis_client.set(cache_key, json.dumps(result), expire=3600)  # Cache for shorter time
        return result
        
    async def _query_pdb(self, uniprot_id: str) -> Dict[str, Any]:
        """
        Query PDB API to get protein structure data for a UniProt ID
        """
        logger.info(f"Querying PDB for protein: {uniprot_id}")
        
        try:
            # Step 1: Search for structures containing the UniProt ID
            search_url = f"{self.pdb_api_url}/search/polymer_entity"
            
            # Constructing proper search query that matches PDB API requirements
            search_payload = {
                "query": {
                    "type": "terminal",
                    "service": "text",
                    "parameters": {
                        "attribute": "rcsb_polymer_entity_container_identifiers.reference_sequence_identifiers.database_accession",
                        "operator": "exact_match",
                        "value": uniprot_id
                    }
                },
                "return_type": "polymer_entity",
                "request_options": {
                    "pager": {
                        "start": 0,
                        "rows": 100
                    },
                    "scoring_strategy": "combined",
                    "sort": [
                        {
                            "sort_by": "rcsb_entry_info.resolution_combined",
                            "direction": "asc"
                        }
                    ]
                }
            }
            
            async with httpx.AsyncClient() as client:
                # Step 1: Search for PDB IDs
                response = await client.post(search_url, json=search_payload)
                
                if response.status_code != 200:
                    logger.error(f"PDB search failed with status {response.status_code}: {response.text}")
                    return {}
                
                search_data = response.json()
                result_ids = search_data.get("result_set", [])
                
                if not result_ids:
                    logger.warning(f"No PDB structures found for {uniprot_id}")
                    return {}
                
                # Get the best structure (first result sorted by resolution)
                best_match = result_ids[0]
                entity_id = best_match.get("identifier", "").split('_')[0]
                
                if not entity_id:
                    logger.error("Failed to extract entity ID from search results")
                    return {}
                
                # Step 2: Get structure details
                structure_url = f"{self.pdb_api_url}/graphql"
                graphql_query = {
                    "query": """
                    query StructureQuery($id: String!) {
                        entry(entry_id: $id) {
                            rcsb_id
                            struct {
                                title
                                pdbx_descriptor
                            }
                            rcsb_entry_info {
                                resolution_combined
                                experimental_method
                                structure_determination_methodology  
                            }
                            polymer_entities {
                                rcsb_id
                                entity_poly {
                                    pdbx_seq_one_letter_code
                                }
                                rcsb_polymer_entity {
                                    pdbx_description
                                }
                            }
                        }
                    }
                    """,
                    "variables": {
                        "id": entity_id
                    }
                }
                
                struct_response = await client.post(structure_url, json=graphql_query)
                
                if struct_response.status_code != 200:
                    logger.error(f"PDB structure query failed with status {struct_response.status_code}")
                    return {}
                
                struct_data = struct_response.json()
                entry_data = struct_data.get("data", {}).get("entry", {})
                
                if not entry_data:
                    logger.error("Failed to retrieve structure details")
                    return {}
                
                # Step 3: Prepare structure data in the format expected by the frontend
                structure_data = {
                    "pdb_id": entity_id,
                    "title": entry_data.get("struct", {}).get("title", ""),
                    "description": entry_data.get("struct", {}).get("pdbx_descriptor", ""),
                    "resolution": entry_data.get("rcsb_entry_info", {}).get("resolution_combined"),
                    "method": entry_data.get("rcsb_entry_info", {}).get("experimental_method", ""),
                    "polymer_entities": [
                        {
                            "entity_id": entity.get("rcsb_id", ""),
                            "description": entity.get("rcsb_polymer_entity", {}).get("pdbx_description", ""),
                            "sequence": entity.get("entity_poly", {}).get("pdbx_seq_one_letter_code", "")
                        }
                        for entity in entry_data.get("polymer_entities", [])
                    ],
                    "viewer_url": f"https://www.rcsb.org/3d-view/{entity_id}",
                    "download_url": f"https://files.rcsb.org/download/{entity_id}.pdb"
                }
                
                return structure_data
        
        except Exception as e:
            logger.error(f"Error querying PDB API: {str(e)}")
            return {}
    
    async def _query_alphafold(self, protein_id: str) -> Dict[str, Any]:
        """
        Query the AlphaFold DB API to get predicted structure information.
        """
        logger.info(f"Querying AlphaFold DB for {protein_id} structure")
        
        try:
            # AlphaFold DB doesn't have a formal API, but we can check if a structure exists
            # by trying to access the metadata JSON
            uniprot_id = protein_id.split('-')[0] if '-' in protein_id else protein_id
            metadata_url = f"https://alphafold.ebi.ac.uk/api/prediction/{uniprot_id}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(metadata_url, timeout=10.0)
                
                if response.status_code == 200:
                    # Structure exists
                    metadata = response.json()
                    
                    # Return the structure data
                    structure_data = {
                        "alphafold_id": uniprot_id,
                        "status": "available",
                        "source": "alphafold",
                        "confidence": metadata.get("confidenceAvgLocalScore", None),
                        "length": metadata.get("uniprotLength", None)
                    }
                    
                    return structure_data
                else:
                    logger.info(f"No AlphaFold structure found for {protein_id}")
                    return {}
                    
        except Exception as e:
            logger.error(f"Error querying AlphaFold DB for {protein_id}: {str(e)}")
            raise
    
    async def get_protein_interactions(self, protein_id: str) -> List[Dict[str, Any]]:
        """
        Get protein-protein interactions for a given protein.
        Uses STRING database, internal knowledge graph, or LLM fallback.
        """
        # Check cache first
        cache_key = f"interactions:{protein_id}"
        cached_data = await self.redis_client.get(cache_key)
        if cached_data:
            logger.info(f"Retrieved interaction data for {protein_id} from cache")
            return json.loads(cached_data)
        
        # Check knowledge graph
        kg_interactions = await self.db.get_protein_interactions(protein_id)
        if kg_interactions:
            logger.info(f"Retrieved interaction data for {protein_id} from knowledge graph")
            # Cache the result
            await self.redis_client.set(cache_key, json.dumps(kg_interactions), expire=86400)
            return kg_interactions
        
        # Check if we're already making this API call using the singleton tracker
        if f"string_{protein_id}" in api_tracker.in_progress:
            logger.info(f"API call to STRING DB for {protein_id} already in progress, waiting for result...")
            # Wait for the existing call to finish
            if f"string_{protein_id}" not in api_tracker.locks:
                api_tracker.locks[f"string_{protein_id}"] = asyncio.Lock()
            
            async with api_tracker.locks[f"string_{protein_id}"]:
                # Check cache again after waiting
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    logger.info(f"Retrieved interaction data for {protein_id} from cache after waiting")
                    return json.loads(cached_data)
                else:
                    logger.warning(f"Still no cached interaction data for {protein_id} after waiting, making new API call")
        
        # Mark this API call as in progress
        api_tracker.in_progress[f"string_{protein_id}"] = True
        if f"string_{protein_id}" not in api_tracker.locks:
            api_tracker.locks[f"string_{protein_id}"] = asyncio.Lock()
        
        # Acquire lock while making the API call  
        async with api_tracker.locks[f"string_{protein_id}"]:
            try:
                # Query STRING database
                logger.info(f"Querying STRING DB for interactions with {protein_id}")
                
                # Use gene symbol from UniProt if available
                uniprot_data = await self._fetch_uniprot_data(protein_id)
                gene_symbol = uniprot_data.get("gene_name", protein_id) if uniprot_data else protein_id
                
                # STRING API endpoint
                api_url = "https://string-db.org/api/json/network"
                
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        api_url,
                        params={
                            "identifiers": gene_symbol,
                            "species": 9606,  # Human
                            "limit": 50,
                            "network_type": "physical",
                            "required_score": 700,  # High confidence (0-1000)
                            "add_nodes": 15,  # Add up to 15 indirect interactors
                        },
                        timeout=15.0
                    )
                    
                    if response.status_code != 200:
                        logger.warning(f"STRING-db API returned status code {response.status_code}")
                        # Try BioGRID as first fallback
                        try:
                            biogrid_result = await self._query_biogrid_interactions(protein_id)
                            if biogrid_result and len(biogrid_result) > 0:
                                return biogrid_result
                        except Exception as biogrid_error:
                            logger.error(f"Error from BioGRID fallback: {str(biogrid_error)}")
                        
                        # If BioGRID fails or returns no data, use LLM fallback
                        logger.info(f"No interaction data from APIs, using LLM fallback for {protein_id}")
                        return await self._generate_interactions_with_llm(protein_id, gene_symbol)
                        
                    data = response.json()
                    
                    # Format the response for our API
                    formatted_interactions = []
                    for interaction in data:
                        # Skip if it's not our target protein
                        if interaction.get("preferredName_A") != gene_symbol and interaction.get("preferredName_B") != gene_symbol:
                            continue
                        
                        # Determine which is the interaction partner
                        is_a_query = interaction.get("preferredName_A") == gene_symbol
                        partner_id = interaction.get("stringId_B" if is_a_query else "stringId_A", "")
                        partner_name = interaction.get("preferredName_B" if is_a_query else "preferredName_A", "")
                        
                        # Skip self-interactions
                        if partner_id == protein_id or partner_name == gene_symbol:
                            continue
                        
                        score = float(interaction.get("score", 0)) / 1000.0  # Normalize to 0-1
                        
                        formatted_interactions.append({
                            "protein_id": partner_id,
                            "protein_name": partner_name,
                            "score": score,
                            "evidence": interaction.get("evidence", ""),
                            "source": "STRING-db"
                        })
                    
                    # If the API didn't return any interactions, use LLM fallback
                    if not formatted_interactions:
                        logger.info(f"STRING-db API returned no interactions for {protein_id}, using LLM fallback")
                        return await self._generate_interactions_with_llm(protein_id, gene_symbol)
                    
                    # Cache the result
                    if formatted_interactions:
                        success = await self.redis_client.set(cache_key, json.dumps(formatted_interactions), expire=86400)
                        if success:
                            logger.info(f"Successfully cached interaction data for {protein_id}")
                        else:
                            logger.warning(f"Failed to cache interaction data for {protein_id}")
                        
                        # Optionally save to knowledge graph
                        for interaction in formatted_interactions:
                            try:
                                await self.db.create_protein_interaction(
                                    protein_id, 
                                    interaction["protein_id"],
                                    interaction["score"]
                                )
                            except Exception as e:
                                logger.error(f"Error storing interaction in KG: {str(e)}")
                    
                    return formatted_interactions
            
            except Exception as e:
                logger.error(f"Error querying STRING DB for {protein_id}: {str(e)}")
                
                # If all API calls fail, use LLM fallback
                logger.info(f"Using LLM to generate interaction data for {protein_id}")
                return await self._generate_interactions_with_llm(protein_id, gene_symbol if 'gene_symbol' in locals() else protein_id)
            
            finally:
                # Remove the in-progress marker
                if f"string_{protein_id}" in api_tracker.in_progress:
                    del api_tracker.in_progress[f"string_{protein_id}"]

    async def _generate_interactions_with_llm(self, protein_id: str, gene_symbol: str = None) -> List[Dict[str, Any]]:
        """
        Generate realistic protein interaction data using LLM when API fails.
        This is more accurate than static mock data.
        """
        logger.info(f"Generating interaction data with LLM for {protein_id}")
        
        try:
            # Get an LLM service instance
            from app.services.llm_service import LLMService
            llm_service = LLMService(self.redis_client)
            
            # First get protein description to improve the quality of generated interactions
            protein_info = ""
            try:
                uniprot_data = await self._fetch_uniprot_data(protein_id)
                if uniprot_data:
                    protein_info = f"Protein: {uniprot_data.get('name', '')}"
                    if uniprot_data.get('gene_name'):
                        protein_info += f", Gene: {uniprot_data.get('gene_name')}"
                    if uniprot_data.get('function'):
                        protein_info += f", Function: {uniprot_data.get('function')}"
            except Exception as e:
                logger.error(f"Error getting protein info for LLM: {str(e)}")
            
            # Generate the prompt for the LLM
            if not gene_symbol or gene_symbol == protein_id:
                gene_symbol = protein_id
                # Try to extract something that looks like a gene name
                if protein_id.startswith('P') and len(protein_id) <= 6:
                    gene_symbol = f"protein {protein_id}"
            
            prompt = f"""
            Generate scientifically accurate protein-protein interaction data for {gene_symbol} ({protein_id}).
            {protein_info}
            
            Return a JSON array of 5-8 proteins that interact with {gene_symbol} with high confidence based on scientific literature.
            Each interaction should include:
            1. protein_id (UniProt ID if known, otherwise use a placeholder)
            2. protein_name (full protein name)
            3. score (interaction confidence from 0.0 to 1.0)
            4. evidence (brief description of evidence types)
            
            Example:
            [
              {{
                "protein_id": "P53350",
                "protein_name": "PLK1 (Polo-like kinase 1)",
                "score": 0.92,
                "evidence": "experimental, text mining",
                "source": "LLM-generated based on scientific literature"
              }}
            ]
            
            Return ONLY the JSON array, no other text.
            """
            
            # Call the LLM to generate interaction data
            llm_response = await llm_service._call_gemini_api({
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }]
            })
            
            # Extract the JSON from the response
            import re
            import json
            
            # Look for JSON pattern in the response
            json_match = re.search(r'```json\s*(.*?)\s*```', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
            else:
                json_pattern = re.search(r'(\[\s*\{.*\}\s*\])', llm_response, re.DOTALL)
                if json_pattern:
                    json_str = json_pattern.group(1).strip()
                else:
                    # Failed to extract JSON, return empty list
                    logger.error(f"Failed to extract JSON from LLM response for {protein_id}")
                    return []
            
            # Parse the JSON
            interactions = json.loads(json_str)
            
            # Validate and clean up the interactions
            valid_interactions = []
            for interaction in interactions:
                # Ensure required fields exist
                if not interaction.get("protein_id") or not interaction.get("protein_name"):
                    continue
                    
                # Add source field
                interaction["source"] = "LLM-generated based on scientific literature"
                
                # Default score if missing
                if "score" not in interaction:
                    interaction["score"] = 0.7
                    
                # Default evidence if missing
                if "evidence" not in interaction:
                    interaction["evidence"] = "scientific literature"
                    
                valid_interactions.append(interaction)
            
            # Cache the result
            cache_key = f"interactions:{protein_id}"
            await self.redis_client.set(cache_key, json.dumps(valid_interactions), expire=86400)
            
            logger.info(f"Successfully generated {len(valid_interactions)} interactions for {protein_id} using LLM")
            return valid_interactions
            
        except Exception as e:
            logger.error(f"Error generating interactions with LLM for {protein_id}: {str(e)}")
            return []

    async def _fetch_uniprot_data(self, protein_id: str) -> Dict[str, Any]:
        """
        Fetch protein data from the UniProt API.
        """
        # First check if this data is already in cache (not using Redis for this check)
        cache_key = f"uniprot_data:{protein_id}"
        cached_data = await self.redis_client.get_value(cache_key)
        if cached_data is not None:
            logger.info(f"Retrieved UniProt data for {protein_id} from cache")
            return cached_data
        
        # Check if we're already making this API call using the singleton tracker
        if protein_id in api_tracker.in_progress:
            logger.info(f"API call to UniProt for {protein_id} already in progress, waiting for result...")
            # Wait for the existing call to finish
            if protein_id not in api_tracker.locks:
                api_tracker.locks[protein_id] = asyncio.Lock()
            
            async with api_tracker.locks[protein_id]:
                # Check cache again after waiting
                cached_data = await self.redis_client.get_value(cache_key)
                if cached_data is not None:
                    logger.info(f"Retrieved UniProt data for {protein_id} from cache after waiting")
                    return cached_data
                else:
                    logger.warning(f"Still no cached data for {protein_id} after waiting, making new API call")
        
        # Mark this API call as in progress
        api_tracker.in_progress[protein_id] = True
        if protein_id not in api_tracker.locks:
            api_tracker.locks[protein_id] = asyncio.Lock()
        
        # Acquire lock while making the API call
        async with api_tracker.locks[protein_id]:
            try:
                logger.info(f"Fetching data from UniProt API for {protein_id}")
                
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(
                        f"{self.uniprot_api_url}/uniprotkb/{protein_id}",
                        headers={"Accept": "application/json"}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Format the data to our standard
                        result = {
                            "id": data.get("primaryAccession", protein_id),
                            "name": data.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value") or 
                                data.get("proteinDescription", {}).get("submissionNames", [{}])[0].get("fullName", {}).get("value", "Unknown"),
                            "gene_name": data.get("genes", [{}])[0].get("geneName", {}).get("value") if data.get("genes") else None,
                            "organism": data.get("organism", {}).get("scientificName"),
                            "sequence": data.get("sequence", {}).get("value"),
                            "length": data.get("sequence", {}).get("length"),
                            "function": data.get("comments", [{}])[0].get("text") if data.get("comments") else None,
                            "uniprot_id": data.get("primaryAccession")
                        }
                        
                        # Cache detailed protein data - try multiple times if needed
                        success = False
                        for attempt in range(3):
                            try:
                                success = await self.redis_client.set_value(
                                    cache_key, 
                                    result,
                                    expire=604800  # 1 week
                                )
                                if success:
                                    logger.info(f"Successfully cached UniProt data for {protein_id}")
                                    break
                            except Exception as e:
                                logger.error(f"Error caching UniProt data (attempt {attempt+1}): {str(e)}")
                                await asyncio.sleep(0.5)
                        
                        if not success:
                            logger.warning(f"Failed to cache UniProt data for {protein_id} after multiple attempts")
                        
                        return result
                    else:
                        logger.warning(f"Failed to get data from UniProt for {protein_id}: {response.status_code}")
                        return None
                        
            except httpx.HTTPError as e:
                logger.error(f"HTTP error when fetching UniProt data for {protein_id}: {str(e)}")
                return None
            except Exception as e:
                logger.error(f"Error fetching UniProt data for {protein_id}: {str(e)}")
                return None
            finally:
                # Remove the in-progress marker
                if protein_id in api_tracker.in_progress:
                    del api_tracker.in_progress[protein_id]

    async def get_disease_associations(self, protein_id: str) -> List[Dict[str, Any]]:
        """
        Get diseases associated with a protein.
        Uses knowledge graph or external APIs.
        """
        # Check cache first
        cache_key = f"diseases:{protein_id}"
        cached_data = await self.redis_client.get(cache_key)
        if cached_data:
            logger.info(f"Retrieved disease data for {protein_id} from cache")
            return json.loads(cached_data)
        
        # Check knowledge graph
        kg_diseases = await self.db.get_protein_diseases(protein_id)
        if kg_diseases:
            logger.info(f"Retrieved disease data for {protein_id} from knowledge graph")
            # Cache the result
            await self.redis_client.set(cache_key, json.dumps(kg_diseases), expire=86400)
            return kg_diseases
        
        # Check if we're already making this API call
        api_key = f"disease_{protein_id}"
        if api_key in api_tracker.in_progress:
            logger.info(f"API call for diseases of {protein_id} already in progress, waiting...")
            if api_key not in api_tracker.locks:
                api_tracker.locks[api_key] = asyncio.Lock()
            
            async with api_tracker.locks[api_key]:
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    return json.loads(cached_data)
        
        # Mark API call as in progress
        api_tracker.in_progress[api_key] = True
        if api_key not in api_tracker.locks:
            api_tracker.locks[api_key] = asyncio.Lock()
        
        # Acquire lock for API call
        async with api_tracker.locks[api_key]:
            try:
                # Try to get disease associations from DisGeNET
                logger.info(f"Querying DisGeNET for disease associations with {protein_id}")
                
                # Use gene symbol from UniProt if available
                uniprot_data = await self._fetch_uniprot_data(protein_id)
                gene_symbol = uniprot_data.get("gene_name", "") if uniprot_data else ""
                
                if not gene_symbol:
                    # No gene symbol found, try to extract from protein name
                    if uniprot_data and uniprot_data.get("name"):
                        # Extract potential gene symbol (usually first word before space)
                        gene_symbol = uniprot_data.get("name").split()[0]
                
                diseases = []
                
                if gene_symbol:
                    try:
                        # DisGeNET API doesn't have a proper async endpoint, so use mock data for now
                        # In a real implementation, you'd call their API
                        
                        # Example mock data based on protein
                        if protein_id == "P04637" or gene_symbol.upper() == "TP53":
                            # TP53 is associated with many cancers
                            diseases = [
                                {"disease_id": "C0007097", "disease_name": "Colon Cancer", "score": 0.9},
                                {"disease_id": "C0699791", "disease_name": "Breast Cancer", "score": 0.9},
                                {"disease_id": "C0007115", "disease_name": "Lung Cancer", "score": 0.85},
                                {"disease_id": "C0023269", "disease_name": "Li-Fraumeni Syndrome", "score": 0.95},
                                {"disease_id": "C0085136", "disease_name": "Adrenocortical Carcinoma", "score": 0.8}
                            ]
                        elif protein_id == "P38398" or gene_symbol.upper() == "BRCA1":
                            # BRCA1 associations
                            diseases = [
                                {"disease_id": "C0699791", "disease_name": "Breast Cancer", "score": 0.95},
                                {"disease_id": "C0032449", "disease_name": "Ovarian Cancer", "score": 0.9},
                                {"disease_id": "C0027829", "disease_name": "Fanconi Anemia", "score": 0.7}
                            ]
                        elif protein_id == "P42336" or gene_symbol.upper() in ["PIK3CA", "PI3K"]:
                            # PIK3CA associations
                            diseases = [
                                {"disease_id": "C0699791", "disease_name": "Breast Cancer", "score": 0.8},
                                {"disease_id": "C0038941", "disease_name": "CLOVES Syndrome", "score": 0.85},
                                {"disease_id": "C0007113", "disease_name": "Colorectal Cancer", "score": 0.75}
                            ]
                        elif protein_id == "P00533" or gene_symbol.upper() == "EGFR":
                            # EGFR associations
                            diseases = [
                                {"disease_id": "C0007115", "disease_name": "Lung Cancer", "score": 0.9},
                                {"disease_id": "C0027765", "disease_name": "Glioblastoma", "score": 0.85},
                                {"disease_id": "C0007113", "disease_name": "Colorectal Cancer", "score": 0.7}
                            ]
                        
                        # If we have some diseases, store in KG and cache
                        if diseases:
                            # Cache the results
                            await self.redis_client.set(cache_key, json.dumps(diseases), expire=86400)
                            
                            # Store in KG
                            for disease in diseases:
                                try:
                                    await self.db.create_protein_disease_association(
                                        protein_id=protein_id,
                                        disease_id=disease["disease_id"],
                                        disease_name=disease["disease_name"],
                                        score=disease["score"]
                                    )
                                except Exception as e:
                                    logger.error(f"Error storing disease in KG: {str(e)}")
                            
                            return diseases
                    except Exception as e:
                        logger.error(f"Error querying disease associations: {str(e)}")
                
                # If we get here, either no gene symbol or no results
                logger.info(f"No disease associations found for {protein_id}")
                return []
                
            except Exception as e:
                logger.error(f"Error getting disease associations for {protein_id}: {str(e)}")
                return []
                
            finally:
                # Remove in-progress marker
                if api_key in api_tracker.in_progress:
                    del api_tracker.in_progress[api_key]

    async def get_drug_interactions(self, protein_id: str) -> List[Dict[str, Any]]:
        """
        Get drugs that interact with a protein.
        Uses knowledge graph or external APIs.
        """
        # Check cache first
        cache_key = f"drugs:{protein_id}"
        cached_data = await self.redis_client.get(cache_key)
        if cached_data:
            logger.info(f"Retrieved drug data for {protein_id} from cache")
            return json.loads(cached_data)
        
        # Check knowledge graph
        kg_drugs = await self.db.get_protein_drugs(protein_id)
        if kg_drugs:
            logger.info(f"Retrieved drug data for {protein_id} from knowledge graph")
            # Cache the result
            await self.redis_client.set(cache_key, json.dumps(kg_drugs), expire=86400)
            return kg_drugs
        
        # Check if we're already making this API call
        api_key = f"drug_{protein_id}"
        if api_key in api_tracker.in_progress:
            logger.info(f"API call for drugs targeting {protein_id} already in progress, waiting...")
            if api_key not in api_tracker.locks:
                api_tracker.locks[api_key] = asyncio.Lock()
            
            async with api_tracker.locks[api_key]:
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    return json.loads(cached_data)
        
        # Mark API call as in progress
        api_tracker.in_progress[api_key] = True
        if api_key not in api_tracker.locks:
            api_tracker.locks[api_key] = asyncio.Lock()
        
        # Acquire lock for API call
        async with api_tracker.locks[api_key]:
            try:
                # Try to get drug interactions from DrugBank or similar source
                logger.info(f"Querying for drugs targeting {protein_id}")
                
                # Use gene symbol from UniProt if available
                uniprot_data = await self._fetch_uniprot_data(protein_id)
                gene_symbol = uniprot_data.get("gene_name", "") if uniprot_data else ""
                
                if not gene_symbol and uniprot_data and uniprot_data.get("name"):
                    # Extract potential gene symbol from protein name
                    gene_symbol = uniprot_data.get("name").split()[0]
                
                drugs = []
                
                # For the hackathon demo, we'll provide mock data for common proteins
                if protein_id == "P04637" or gene_symbol.upper() == "TP53":
                    # TP53 targeted therapies 
                    drugs = [
                        {"drug_id": "DB15096", "drug_name": "APR-246", "drug_type": "Small Molecule", "status": "Investigational", "mechanism": "p53 reactivation"},
                        {"drug_id": "DB12819", "drug_name": "COTI-2", "drug_type": "Small Molecule", "status": "Investigational", "mechanism": "p53 mutant stabilizer"},
                        {"drug_id": "DB15022", "drug_name": "PC-14586", "drug_type": "Small Molecule", "status": "Clinical Trial", "mechanism": "Y220C mutant stabilizer"}
                    ]
                elif protein_id == "P00533" or gene_symbol.upper() == "EGFR":
                    # EGFR inhibitors
                    drugs = [
                        {"drug_id": "DB00619", "drug_name": "Erlotinib", "drug_type": "Small Molecule", "status": "Approved", "mechanism": "EGFR inhibitor"},
                        {"drug_id": "DB01259", "drug_name": "Gefitinib", "drug_type": "Small Molecule", "status": "Approved", "mechanism": "EGFR inhibitor"},
                        {"drug_id": "DB06589", "drug_name": "Osimertinib", "drug_type": "Small Molecule", "status": "Approved", "mechanism": "EGFR T790M inhibitor"},
                        {"drug_id": "DB00072", "drug_name": "Cetuximab", "drug_type": "Monoclonal Antibody", "status": "Approved", "mechanism": "EGFR antagonist"}
                    ]
                elif protein_id == "P38398" or gene_symbol.upper() == "BRCA1":
                    # BRCA1/2 pathway synthetic lethal drugs
                    drugs = [
                        {"drug_id": "DB09280", "drug_name": "Olaparib", "drug_type": "Small Molecule", "status": "Approved", "mechanism": "PARP inhibitor"},
                        {"drug_id": "DB11878", "drug_name": "Rucaparib", "drug_type": "Small Molecule", "status": "Approved", "mechanism": "PARP inhibitor"},
                        {"drug_id": "DB12010", "drug_name": "Niraparib", "drug_type": "Small Molecule", "status": "Approved", "mechanism": "PARP inhibitor"}
                    ]
                elif protein_id == "P42336" or gene_symbol.upper() in ["PIK3CA", "PI3K"]:
                    # PI3K pathway inhibitors
                    drugs = [
                        {"drug_id": "DB12010", "drug_name": "Alpelisib", "drug_type": "Small Molecule", "status": "Approved", "mechanism": "PI3K alpha inhibitor"},
                        {"drug_id": "DB11963", "drug_name": "Idelalisib", "drug_type": "Small Molecule", "status": "Approved", "mechanism": "PI3K delta inhibitor"},
                        {"drug_id": "DB11808", "drug_name": "Copanlisib", "drug_type": "Small Molecule", "status": "Approved", "mechanism": "PI3K inhibitor"}
                    ]
                
                if drugs:
                    # Cache the results
                    await self.redis_client.set(cache_key, json.dumps(drugs), expire=86400)
                    
                    # Store in KG
                    for drug in drugs:
                        try:
                            await self.db.create_protein_drug_interaction(
                                protein_id=protein_id,
                                drug_id=drug["drug_id"],
                                drug_name=drug["drug_name"],
                                mechanism=drug.get("mechanism", "")
                            )
                        except Exception as e:
                            logger.error(f"Error storing drug in KG: {str(e)}")
                    
                    logger.info(f"Found {len(drugs)} drugs targeting {protein_id}")
                    return drugs
                
                logger.info(f"No drug interactions found for {protein_id}")
                return []
                
            except Exception as e:
                logger.error(f"Error getting drug interactions for {protein_id}: {str(e)}")
                return []
                
            finally:
                # Remove in-progress marker
                if api_key in api_tracker.in_progress:
                    del api_tracker.in_progress[api_key]

    async def get_protein_variants(self, protein_id: str) -> List[Dict[str, Any]]:
        """
        Get protein variants/mutations information.
        Uses knowledge graph or external APIs or LLM fallback if unavailable.
        """
        # Check cache first
        cache_key = f"variants:{protein_id}"
        cached_data = await self.redis_client.get(cache_key)
        if cached_data:
            logger.info(f"Retrieved variant data for {protein_id} from cache")
            return json.loads(cached_data)
        
        # Try to use knowledge graph if available
        try:
            kg_variants = await self.db.get_protein_variants(protein_id)
            if kg_variants:
                logger.info(f"Retrieved variant data for {protein_id} from knowledge graph")
                # Cache the result
                await self.redis_client.set(cache_key, json.dumps(kg_variants), expire=86400)
                return kg_variants
        except Exception as e:
            # If the method doesn't exist or there's an error, just log it and continue
            logger.warning(f"Could not query knowledge graph for variants: {str(e)}")
        
        # Use the API tracker to prevent duplicate calls
        api_key = f"variants_{protein_id}"
        if api_key in api_tracker.in_progress:
            logger.info(f"API call for variants of {protein_id} already in progress, waiting...")
            if api_key not in api_tracker.locks:
                api_tracker.locks[api_key] = asyncio.Lock()
            
            async with api_tracker.locks[api_key]:
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    return json.loads(cached_data)
        
        # Mark API call as in progress
        api_tracker.in_progress[api_key] = True
        if api_key not in api_tracker.locks:
            api_tracker.locks[api_key] = asyncio.Lock()
        
        # Acquire lock for API call
        async with api_tracker.locks[api_key]:
            try:
                # For the hackathon demo, use mock data for common proteins
                variants = []
                
                # Use gene symbol from UniProt if available
                uniprot_data = await self._fetch_uniprot_data(protein_id)
                gene_symbol = uniprot_data.get("gene_name", "") if uniprot_data else ""
                
                if not gene_symbol and uniprot_data and uniprot_data.get("name"):
                    # Extract potential gene symbol from protein name
                    gene_symbol = uniprot_data.get("name").split()[0]
                
                # For the hackathon demo, we'll provide mock data for common proteins
                if protein_id == "P04637" or gene_symbol.upper() == "TP53":
                    # TP53 common mutations
                    variants = [
                        {"variant_id": "VAR_000001", "variant_name": "R273H", "impact": "Oncogenic", "frequency": 0.08, "effect": "DNA binding defect"},
                        {"variant_id": "VAR_000002", "variant_name": "R175H", "impact": "Oncogenic", "frequency": 0.07, "effect": "Structural destabilization"},
                        {"variant_id": "VAR_000003", "variant_name": "R248Q", "impact": "Oncogenic", "frequency": 0.07, "effect": "DNA contact change"},
                        {"variant_id": "VAR_000004", "variant_name": "G245S", "impact": "Oncogenic", "frequency": 0.06, "effect": "DNA binding defect"},
                        {"variant_id": "VAR_000005", "variant_name": "R249S", "impact": "Oncogenic", "frequency": 0.05, "effect": "DNA binding defect"}
                    ]
                elif protein_id == "P00533" or gene_symbol.upper() == "EGFR":
                    # EGFR common mutations
                    variants = [
                        {"variant_id": "VAR_000101", "variant_name": "L858R", "impact": "Activating", "frequency": 0.45, "effect": "Enhanced kinase activity"},
                        {"variant_id": "VAR_000102", "variant_name": "T790M", "impact": "Resistance", "frequency": 0.50, "effect": "TKI inhibitor resistance"},
                        {"variant_id": "VAR_000103", "variant_name": "exon 19 deletion", "impact": "Activating", "frequency": 0.44, "effect": "Enhanced kinase activity"},
                        {"variant_id": "VAR_000104", "variant_name": "G719X", "impact": "Activating", "frequency": 0.03, "effect": "Enhanced kinase activity"}
                    ]
                elif protein_id == "P38398" or gene_symbol.upper() == "BRCA1":
                    # BRCA1 common mutations
                    variants = [
                        {"variant_id": "VAR_000201", "variant_name": "185delAG", "impact": "Deleterious", "frequency": 0.12, "effect": "Protein truncation"},
                        {"variant_id": "VAR_000202", "variant_name": "C61G", "impact": "Deleterious", "frequency": 0.08, "effect": "RING domain disruption"},
                        {"variant_id": "VAR_000203", "variant_name": "5382insC", "impact": "Deleterious", "frequency": 0.11, "effect": "Protein truncation"}
                    ]
                elif protein_id == "P42336" or gene_symbol.upper() in ["PIK3CA", "PI3K"]:
                    # PIK3CA common mutations
                    variants = [
                        {"variant_id": "VAR_000301", "variant_name": "H1047R", "impact": "Activating", "frequency": 0.32, "effect": "Enhanced kinase activity"},
                        {"variant_id": "VAR_000302", "variant_name": "E545K", "impact": "Activating", "frequency": 0.28, "effect": "Release of inhibition"},
                        {"variant_id": "VAR_000303", "variant_name": "E542K", "impact": "Activating", "frequency": 0.12, "effect": "Release of inhibition"}
                    ]
                
                # If we have variants, cache them
                if variants:
                    # Try to store the data in Redis cache
                    await self.redis_client.set(cache_key, json.dumps(variants), expire=86400)
                    
                    # Try to store in KG
                    try:
                        for variant in variants:
                            try:
                                # Check if the method exists first
                                if hasattr(self.db, 'create_protein_variant') and callable(getattr(self.db, 'create_protein_variant')):
                                    await self.db.create_protein_variant(
                                        protein_id=protein_id,
                                        variant_id=variant["variant_id"],
                                        variant_name=variant["variant_name"],
                                        impact=variant.get("impact", "")
                                    )
                            except Exception as e:
                                # Just log the error and continue
                                logger.error(f"Error storing variant in KG: {str(e)}")
                    except Exception as e:
                        logger.warning(f"Error storing variants in KG: {str(e)}")
                    
                    logger.info(f"Found {len(variants)} variants for {protein_id}")
                    return variants
                
                # If no variants found through APIs or mock data, fall back to LLM response
                logger.info(f"No variants found for {protein_id}, falling back to LLM")
                
                # Try to get LLM description of variants
                try:
                    # Get an LLM service instance (using the LLM with Redis from your app)
                    from app.services.llm_service import LLMService
                    llm_service = LLMService(self.redis_client)
                    
                    # Generate a prompt based on available protein info
                    prompt = f"Describe common genetic mutations in the {gene_symbol or protein_id} protein and their effects."
                    
                    # Call the LLM
                    llm_response = await llm_service.query_llm(prompt)
                    
                    # Create a simple variant object with the LLM response
                    if llm_response:
                        variants = [
                            {
                                "variant_id": "LLM_GEN",
                                "variant_name": "LLM generated response",
                                "description": llm_response,
                                "source": "Generated by LLM"
                            }
                        ]
                        
                        # Cache the LLM response too
                        await self.redis_client.set(cache_key, json.dumps(variants), expire=86400)
                        return variants
                except Exception as llm_error:
                    logger.error(f"Error getting LLM description for variants: {str(llm_error)}")
                
                # If we reach here, we have no data
                logger.info(f"No variant data available for {protein_id}")
                return []
                
            except Exception as e:
                logger.error(f"Error getting variant data for {protein_id}: {str(e)}")
                return []
                
            finally:
                # Remove in-progress marker
                if api_key in api_tracker.in_progress:
                    del api_tracker.in_progress[api_key]