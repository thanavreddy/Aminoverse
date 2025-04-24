import logging
import httpx
import json
from typing import Dict, List, Optional, Any, Union

from app.core.config import settings
from app.cache.redis_client import RedisClient
from app.db.neo4j import Neo4jDatabase

logger = logging.getLogger(__name__)

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
        Get protein structure information.
        
        Args:
            protein_id: UniProt ID of the protein
            
        Returns:
            Dict with structure information including PDB ID or AlphaFold ID
        """
        # Check cache first
        cached_structure = await self.redis_client.get_cached_structure_data(protein_id)
        if cached_structure:
            logger.info(f"Retrieved structure data for {protein_id} from cache")
            return cached_structure
        
        # Initialize structure data
        structure_data = {
            "protein_id": protein_id,
            "status": "unavailable"
        }
        
        try:
            # First check if we have the protein in our database
            query = """
            MATCH (p:Protein {id: $protein_id})
            OPTIONAL MATCH (p)-[r:HAS_STRUCTURE]->(s:Structure)
            RETURN p, s
            """
            
            result = await self.db.execute_query(query, {"protein_id": protein_id})
            
            if result and result.get("s"):
                structure = result.get("s")
                
                # Extract structure info from Neo4j
                if "pdb_id" in structure:
                    structure_data.update({
                        "pdb_id": structure.get("pdb_id"),
                        "method": structure.get("method", "Unknown"),
                        "resolution": structure.get("resolution"),
                        "release_date": structure.get("release_date"),
                        "status": "available",
                        "type": "experimental",
                        # Add direct link for visualization
                        "view_url": f"https://www.rcsb.org/3d-view/{structure.get('pdb_id')}?color=entity"
                    })
                elif "alphafold_id" in structure:
                    structure_data.update({
                        "alphafold_id": structure.get("alphafold_id"),
                        "confidence": structure.get("confidence"),
                        "status": "available", 
                        "type": "predicted",
                        # Add direct links for visualization
                        "view_url": f"https://alphafold.ebi.ac.uk/entry/{structure.get('alphafold_id')}",
                        "thumbnail_url": f"https://alphafold.ebi.ac.uk/files/AF-{structure.get('alphafold_id')}-F1-predicted_aligned_error_v4.png"
                    })
                
                # Cache and return
                await self.redis_client.cache_structure_data(protein_id, structure_data)
                return structure_data
            
            # If not in database, query external APIs
            # First try PDB API
            pdb_data = await self._query_pdb(protein_id)
            
            if pdb_data and "pdb_id" in pdb_data:
                structure_data.update({
                    **pdb_data,
                    "status": "available",
                    "type": "experimental",
                    # Add direct link for visualization
                    "view_url": f"https://www.rcsb.org/3d-view/{pdb_data.get('pdb_id')}?color=entity"
                })
                
                # Cache and return
                await self.redis_client.cache_structure_data(protein_id, structure_data)
                return structure_data
            
            # If no PDB structure, try AlphaFold
            alphafold_data = await self._query_alphafold(protein_id)
            
            if alphafold_data and "alphafold_id" in alphafold_data:
                structure_data.update({
                    **alphafold_data,
                    "status": "available",
                    "type": "predicted",
                    # Add direct links for visualization
                    "view_url": f"https://alphafold.ebi.ac.uk/entry/{alphafold_data.get('alphafold_id')}",
                    "thumbnail_url": f"https://alphafold.ebi.ac.uk/files/AF-{alphafold_data.get('alphafold_id')}-F1-predicted_aligned_error_v4.png"
                })
                
                # Cache and return
                await self.redis_client.cache_structure_data(protein_id, structure_data)
                return structure_data
            
            # If we get here, no structure was found
            logger.info(f"No structure found for protein {protein_id}")
            
            # Cache negative result (but for a shorter time)
            await self.redis_client.cache_structure_data(protein_id, structure_data, expire=3600*24)  # 1 day
            return structure_data
            
        except Exception as e:
            logger.error(f"Error retrieving protein structure for {protein_id}: {str(e)}")
            return structure_data
    
    async def get_protein_interactions(self, protein_id: str) -> List[Dict[str, Any]]:
        """
        Get protein-protein interactions from STRING-DB API.
        """
        # Try to get from graph DB first
        interactions = await self.db.get_protein_interactions(protein_id)
        if interactions:
            logger.info(f"Retrieved interactions for {protein_id} from database, {len(interactions)} found")
            return interactions
        
        # If not in DB, fetch from STRING-db API
        try:
            logger.info(f"Fetching protein interactions for {protein_id} from STRING-DB API")
            async with httpx.AsyncClient(timeout=15.0) as client:
                # First try to map the UniProt ID to STRING ID
                string_mapping_url = f"{self.string_db_api_url}/json/get_string_ids?identifiers={protein_id}&species=9606"
                logger.info(f"Mapping UniProt ID to STRING ID: {string_mapping_url}")
                
                mapping_response = await client.get(string_mapping_url)
                
                string_id = None
                if mapping_response.status_code == 200:
                    mappings = mapping_response.json()
                    if mappings and len(mappings) > 0:
                        # Get the first mapping result
                        string_id = mappings[0].get("stringId")
                        logger.info(f"Mapped {protein_id} to STRING ID: {string_id}")
                
                if not string_id:
                    # If no mapping found but protein_id looks like a gene symbol, try direct query
                    if len(protein_id) < 10 and protein_id.isalnum():
                        string_id = f"9606.{protein_id}"
                        logger.info(f"Using gene symbol directly: {string_id}")
                    else:
                        logger.warning(f"Could not map {protein_id} to STRING ID")
                        return []
                
                # Now get the interactions using the STRING ID
                interactions_url = f"{self.string_db_api_url}/json/interaction_partners?identifiers={string_id}&limit=30&required_score=0.7"
                logger.info(f"Getting interactions: {interactions_url}")
                
                int_response = await client.get(interactions_url)
                if int_response.status_code == 200:
                    raw_interactions = int_response.json()
                    
                    # Extract the main protein node for normalization
                    main_node = None
                    for item in raw_interactions:
                        if item.get("stringId_A") == string_id or item.get("preferredName_A", "").upper() == protein_id.upper():
                            main_node = {
                                "string_id": string_id,
                                "name": item.get("preferredName_A", protein_id)
                            }
                            break
                    
                    if not main_node:
                        logger.warning(f"Could not identify main protein node for {protein_id}")
                        return []
                    
                    # Transform the data into our format
                    formatted_interactions = []
                    seen_proteins = set()
                    
                    for item in raw_interactions:
                        # Only include interactions with the main protein
                        if item.get("stringId_A") == string_id:
                            partner_id = item.get("stringId_B")
                            partner_name = item.get("preferredName_B")
                            
                            # Skip if we've already seen this protein
                            if partner_id in seen_proteins:
                                continue
                            seen_proteins.add(partner_id)
                            
                            # Create a normalized ID that includes original protein
                            interaction_data = {
                                "protein_id": f"{partner_id}",
                                "protein_name": partner_name,
                                "description": f"Interaction with {main_node['name']}",
                                "score": item.get("score", 0) / 1000.0  # STRING scores are 0-1000, normalize to 0-1
                            }
                            formatted_interactions.append(interaction_data)
                    
                    logger.info(f"Found {len(formatted_interactions)} interactions for {protein_id}")
                    return formatted_interactions
        
        except Exception as e:
            logger.error(f"Error fetching protein interactions for {protein_id}: {str(e)}")
            return []
        
        return []
    
    async def get_disease_associations(self, protein_id: str) -> List[Dict[str, Any]]:
        """
        Get diseases associated with a protein.
        """
        # Try to get from graph DB first
        diseases = await self.db.get_protein_diseases(protein_id)
        if diseases:
            return diseases
        
        # If not in DB, we would call an external API
        # For demonstration, we'll return mock data
        if protein_id == "P04637":  # TP53
            return [
                {
                    "disease_id": "MONDO:0007254",
                    "name": "Li-Fraumeni syndrome",
                    "description": "A rare, autosomal dominant cancer predisposition syndrome characterized by early-onset of multiple primary cancers.",
                    "evidence": "numerous studies"
                },
                {
                    "disease_id": "DOID:1793",
                    "name": "Pancreatic cancer",
                    "description": "An aggressive malignancy arising from pancreatic cells with poor prognosis.",
                    "evidence": "strong"
                }
            ]
        elif protein_id == "P38398":  # BRCA1
            return [
                {
                    "disease_id": "DOID:1612",
                    "name": "Breast cancer",
                    "description": "A common malignancy that arises from breast epithelial tissue.",
                    "evidence": "strong"
                }
            ]
        
        return []
    
    async def get_drug_interactions(self, protein_id: str) -> List[Dict[str, Any]]:
        """
        Get drugs that target a protein.
        """
        # Try to get from graph DB first
        drugs = await self.db.get_protein_drugs(protein_id)
        if drugs:
            return drugs
        
        # If not in DB, we would call an external API
        # For demonstration, we'll return mock data
        if protein_id == "P38398":  # BRCA1
            return [
                {
                    "drug_id": "DB00398",
                    "name": "Olaparib",
                    "description": "PARP inhibitor used for the treatment of BRCA-mutated advanced ovarian cancer",
                    "mechanism": "PARP inhibitor"
                },
                {
                    "drug_id": "DB11748",
                    "name": "Rucaparib",
                    "description": "PARP inhibitor used for the treatment of ovarian cancer",
                    "mechanism": "PARP inhibitor"
                }
            ]
        
        return []
    
    async def get_protein_variants(self, protein_id: str) -> List[Dict[str, Any]]:
        """
        Get variants of a protein.
        """
        # Try to get from graph DB first
        variants = await self.db.get_protein_variants(protein_id)
        if variants:
            return variants
        
        # If not in DB, we would call an external API
        # For demonstration, we'll return mock data
        if protein_id == "P04637":  # TP53
            return [
                {
                    "variant_id": "P04637_R175H",
                    "name": "TP53 R175H",
                    "type": "missense",
                    "location": 175,
                    "original_residue": "R",
                    "variant_residue": "H",
                    "effect": "Loss of function",
                    "clinical_significance": "pathogenic"
                }
            ]
        elif protein_id == "P38398":  # BRCA1
            return [
                {
                    "variant_id": "P38398_R1443X",
                    "name": "BRCA1 R1443X",
                    "type": "nonsense",
                    "location": 1443,
                    "original_residue": "R",
                    "variant_residue": "X",
                    "effect": "Loss of function",
                    "clinical_significance": "pathogenic"
                }
            ]
        
        return []
    
    # Private helper methods
    
    async def _fetch_uniprot_data(self, protein_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch protein data from UniProt API.
        """
        try:
            logger.info(f"Fetching protein data for {protein_id} from UniProt API")
            async with httpx.AsyncClient(timeout=15.0) as client:
                # First check if the ID is a valid UniProt ID
                direct_url = f"{self.uniprot_api_url}/{protein_id}"
                logger.info(f"Trying direct UniProt lookup: {direct_url}")
                
                response = await client.get(direct_url)
                
                # If direct lookup fails, try searching by the ID
                if response.status_code != 200:
                    logger.info(f"Direct lookup failed, trying search for {protein_id}")
                    search_url = f"{self.uniprot_api_url}/search?query={protein_id}&format=json"
                    search_response = await client.get(search_url)
                    
                    if search_response.status_code != 200:
                        logger.warning(f"UniProt search failed for {protein_id}")
                        return None
                    
                    search_data = search_response.json()
                    results = search_data.get("results", [])
                    
                    if not results or len(results) == 0:
                        logger.warning(f"No UniProt results for {protein_id}")
                        return None
                    
                    # Use the first (best match) result ID
                    uniprot_id = results[0].get("primaryAccession")
                    if not uniprot_id:
                        logger.warning(f"No primary accession in UniProt result for {protein_id}")
                        return None
                    
                    # Fetch details for the matched ID
                    logger.info(f"Found UniProt ID {uniprot_id}, fetching details")
                    detail_url = f"{self.uniprot_api_url}/{uniprot_id}"
                    response = await client.get(detail_url)
                    
                    if response.status_code != 200:
                        logger.warning(f"Failed to get details for UniProt ID {uniprot_id}")
                        return None
                
                # Process the UniProt data
                uniprot_data = response.json()
                
                # Extract key information from the UniProt response
                protein_data = {
                    "id": uniprot_data.get("primaryAccession", protein_id),
                    "name": uniprot_data.get("gene", [{"geneName": {"value": protein_id}}])[0].get("geneName", {}).get("value", protein_id),
                    "full_name": uniprot_data.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value", ""),
                    "function": "",
                    "description": "",
                    "sequence": uniprot_data.get("sequence", {}).get("value", "")
                }
                
                # Extract function and description from comments
                for comment in uniprot_data.get("comments", []):
                    if comment.get("commentType") == "FUNCTION":
                        protein_data["function"] = comment.get("texts", [{}])[0].get("value", "")
                    elif comment.get("commentType") == "CATALYTIC ACTIVITY":
                        if not protein_data["function"]:
                            protein_data["function"] = comment.get("reaction", {}).get("name", "")
                
                # If we still don't have a description, use other fields
                if not protein_data["description"]:
                    for comment in uniprot_data.get("comments", []):
                        if comment.get("commentType") == "FUNCTION" or comment.get("commentType") == "DOMAIN":
                            protein_data["description"] = comment.get("texts", [{}])[0].get("value", "")
                            break
                
                logger.info(f"Successfully retrieved UniProt data for {protein_id}")
                return protein_data
                
        except Exception as e:
            logger.error(f"Error fetching UniProt data for {protein_id}: {str(e)}")
            return None