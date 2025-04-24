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
        Uses STRING database or internal knowledge graph.
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
        
        # Query STRING database
        try:
            logger.info(f"Querying STRING DB for interactions with {protein_id}")
            
            # Use gene symbol from UniProt if available
            uniprot_data = await self._fetch_uniprot_data(protein_id)
            gene_symbol = uniprot_data.get("name", protein_id) if uniprot_data else protein_id
            
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
                    return await self._query_biogrid_interactions(protein_id)
                    
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
                
                # Cache the result
                if formatted_interactions:
                    await self.redis_client.set(cache_key, json.dumps(formatted_interactions), expire=86400)
                    
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
            
            # Try BioGRID as a fallback
            try:
                return await self._query_biogrid_interactions(protein_id)
            except Exception as biogrid_error:
                logger.error(f"Error querying BioGRID for {protein_id}: {str(biogrid_error)}")
        
        # Return empty list if no interactions found
        return []

    async def _query_biogrid_interactions(self, protein_id: str) -> List[Dict[str, Any]]:
        """
        Query BioGRID database for protein-protein interactions as fallback
        """
        logger.info(f"Querying BioGRID for interactions with {protein_id}")
        
        try:
            # First get the gene symbol from protein data
            protein_data = await self.get_protein_info(protein_id)
            gene_symbol = protein_data.get("name", "")
            
            if not gene_symbol:
                return []
                
            # BioGRID API endpoint
            api_url = "https://webservice.thebiogrid.org/interactions"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    api_url,
                    params={
                        "geneList": gene_symbol,
                        "searchNames": "true",
                        "includeInteractors": "true",
                        "format": "json",
                        "taxId": 9606,  # Human
                        "accessKey": settings.BIOGRID_API_KEY
                    },
                    timeout=15.0
                )
                
                if response.status_code != 200:
                    return []
                    
                data = response.json()
                
                # Format the interaction data
                formatted_interactions = []
                seen_partners = set()
                
                for interaction_id, interaction in data.items():
                    # Determine which is the interaction partner
                    is_a_interactor = interaction.get("OFFICIAL_SYMBOL_A") == gene_symbol
                    partner_symbol = interaction.get("OFFICIAL_SYMBOL_B" if is_a_interactor else "OFFICIAL_SYMBOL_A")
                    partner_id = interaction.get("ENTREZ_GENE_B" if is_a_interactor else "ENTREZ_GENE_A")
                    
                    # Skip self-interactions and duplicates
                    if partner_symbol == gene_symbol or partner_symbol in seen_partners:
                        continue
                        
                    seen_partners.add(partner_symbol)
                    
                    # Default confidence score based on experimental evidence
                    score = 0.7  # Medium-high confidence
                    
                    formatted_interactions.append({
                        "protein_id": partner_id,
                        "protein_name": partner_symbol,
                        "score": score,
                        "evidence": interaction.get("EXPERIMENTAL_SYSTEM", ""),
                        "source": "BioGRID"
                    })
                
                return formatted_interactions
        except Exception as e:
            logger.error(f"Error querying BioGRID: {str(e)}")
            return []

    async def get_disease_associations(self, protein_id: str) -> List[Dict[str, Any]]:
        """
        Get diseases associated with a protein.
        Uses DisGeNET or internal knowledge graph.
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
        
        # Query DisGeNET API
        try:
            # DisGeNET uses gene symbols, so we might need to convert UniProt ID to gene symbol
            # For simplicity, we'll assume the gene symbol is in the protein data
            protein_data = await self.get_protein_info(protein_id)
            gene_symbol = protein_data.get("name", "")
            
            if not gene_symbol:
                logger.warning(f"Could not find gene symbol for {protein_id}")
                return []
                
            logger.info(f"Querying DisGeNET for disease associations with gene {gene_symbol}")
            
            # DisGeNET API endpoint for gene-disease associations
            api_url = "https://www.disgenet.org/api/gda/gene"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    api_url,
                    params={"gene_symbol": gene_symbol},
                    headers={"Authorization": f"Bearer {settings.DISGENET_API_KEY}"},
                    timeout=15.0
                )
                
                if response.status_code != 200:
                    logger.warning(f"DisGeNET API returned status code {response.status_code}")
                    return []
                    
                data = response.json()
                
                # Format the disease associations for our API
                formatted_diseases = []
                for association in data.get("results", []):
                    disease_data = {
                        "disease_id": association.get("diseaseId"),
                        "name": association.get("diseaseName"),
                        "score": association.get("score"),
                        "evidence": association.get("nofPmids", 0),
                        "source": "DisGeNET"
                    }
                    formatted_diseases.append(disease_data)
                    
                    # Optionally store in knowledge graph for future use
                    try:
                        await self.db.create_protein_disease_association(
                            protein_id,
                            disease_data["disease_id"],
                            f"DisGeNET score: {disease_data['score']}, PMIDs: {disease_data['evidence']}"
                        )
                    except Exception as e:
                        logger.error(f"Error storing disease association in KG: {str(e)}")
                
                # Cache the result
                if formatted_diseases:
                    await self.redis_client.set(cache_key, json.dumps(formatted_diseases), expire=86400)
                    
                return formatted_diseases
        
        except Exception as e:
            logger.error(f"Error querying DisGeNET for {protein_id}: {str(e)}")
            
            # Try CTD as fallback
            try:
                return await self._query_ctd_diseases(protein_id)
            except Exception as ctd_error:
                logger.error(f"Error querying CTD for {protein_id}: {str(ctd_error)}")
        
        # Return empty list if no disease data found
        logger.info(f"No disease data found for {protein_id}")
        return []

    async def _query_ctd_diseases(self, protein_id: str) -> List[Dict[str, Any]]:
        """
        Query the CTD (Comparative Toxicogenomics Database) for disease associations as fallback
        """
        logger.info(f"Querying CTD for disease associations with {protein_id}")
        
        try:
            protein_data = await self.get_protein_info(protein_id)
            gene_symbol = protein_data.get("name", "")
            
            if not gene_symbol:
                return []
                
            # CTD API endpoint for gene-disease associations
            api_url = "http://ctdbase.org/tools/batchQuery.go"
            
            async with httpx.AsyncClient() as client:
                # CTD doesn't have a formal API, so we simulate a form submission
                form_data = {
                    "inputType": "gene",
                    "inputTerms": gene_symbol,
                    "report": "diseases",
                    "format": "json"
                }
                
                response = await client.post(api_url, data=form_data)
                
                if response.status_code != 200:
                    return []
                    
                data = response.json()
                
                # Format for our API
                formatted_diseases = []
                for association in data.get("results", []):
                    disease_data = {
                        "disease_id": association.get("DiseaseID"),
                        "name": association.get("DiseaseName"),
                        "evidence": association.get("DirectEvidence", ""),
                        "source": "CTD"
                    }
                    formatted_diseases.append(disease_data)
                
                return formatted_diseases
        except Exception as e:
            logger.error(f"Error querying CTD: {str(e)}")
            return []
    
    async def get_drug_interactions(self, protein_id: str) -> List[Dict[str, Any]]:
        """
        Get drugs that interact with a protein.
        Uses DrugBank and ChEMBL data or internal knowledge graph.
        """
        # Check cache first
        cache_key = f"drugs:{protein_id}"
        cached_data = await self.redis_client.get(cache_key)
        if cached_data:
            logger.info(f"Retrieved drug interaction data for {protein_id} from cache")
            return json.loads(cached_data)
        
        # Check knowledge graph
        kg_drugs = await self.db.get_protein_drugs(protein_id)
        if kg_drugs:
            logger.info(f"Retrieved drug data for {protein_id} from knowledge graph")
            # Cache the result
            await self.redis_client.set(cache_key, json.dumps(kg_drugs), expire=86400)
            return kg_drugs
        
        # Query DrugBank API
        try:
            # First get the gene symbol from protein data
            protein_data = await self.get_protein_info(protein_id)
            gene_symbol = protein_data.get("name", "")
            
            if not gene_symbol:
                return []
                
            logger.info(f"Querying DrugBank for drug targets of {gene_symbol}")
            
            # DrugBank API requires authentication
            api_url = "https://go.drugbank.com/api/v1/targets"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    api_url,
                    params={"q": gene_symbol, "format": "json"},
                    headers={"Authorization": f"Bearer {settings.DRUGBANK_API_KEY}"},
                    timeout=15.0
                )
                
                if response.status_code != 200:
                    logger.warning(f"DrugBank API returned status code {response.status_code}")
                    # Try ChEMBL as fallback
                    return await self._query_chembl_drugs(gene_symbol)
                    
                data = response.json()
                
                # Format the drug data for our API
                formatted_drugs = []
                for target in data.get("targets", []):
                    for drug in target.get("drugs", []):
                        drug_data = {
                            "drug_id": drug.get("drugbank_id"),
                            "name": drug.get("name"),
                            "description": drug.get("description", ""),
                            "mechanism": drug.get("mechanism_of_action", ""),
                            "source": "DrugBank"
                        }
                        formatted_drugs.append(drug_data)
                        
                        # Store in knowledge graph
                        try:
                            await self.db.create_drug_protein_targeting(
                                drug_data["drug_id"],
                                protein_id,
                                drug_data["mechanism"]
                            )
                        except Exception as e:
                            logger.error(f"Error storing drug in KG: {str(e)}")
                
                # Cache the result
                if formatted_drugs:
                    await self.redis_client.set(cache_key, json.dumps(formatted_drugs), expire=86400)
                    
                return formatted_drugs
                    
        except Exception as e:
            logger.error(f"Error querying DrugBank for {protein_id}: {str(e)}")
            
            # Try ChEMBL as fallback
            try:
                protein_data = await self.get_protein_info(protein_id)
                gene_symbol = protein_data.get("name", "")
                return await self._query_chembl_drugs(gene_symbol)
            except Exception as chembl_error:
                logger.error(f"Error querying ChEMBL for {protein_id}: {str(chembl_error)}")
        
        # Return empty list if no drug data found
        logger.info(f"No drug interaction data found for {protein_id}")
        return []

    async def _query_chembl_drugs(self, gene_symbol: str) -> List[Dict[str, Any]]:
        """
        Query ChEMBL database for drug-protein interactions as fallback
        """
        logger.info(f"Querying ChEMBL for drug targets of gene {gene_symbol}")
        
        try:
            # ChEMBL API endpoint
            api_url = f"https://www.ebi.ac.uk/chembl/api/data/target.json"
            
            async with httpx.AsyncClient() as client:
                # First find the ChEMBL target ID for the gene
                response = await client.get(
                    api_url,
                    params={"target_components__target_component_synonyms__component_synonym__icontains": gene_symbol},
                    timeout=15.0
                )
                
                if response.status_code != 200:
                    return []
                    
                data = response.json()
                
                if not data.get("targets"):
                    return []
                    
                # Get the first target's ChEMBL ID
                chembl_id = data["targets"][0]["target_chembl_id"]
                
                # Now search for compounds targeting this target
                compounds_url = f"https://www.ebi.ac.uk/chembl/api/data/activity.json"
                compound_response = await client.get(
                    compounds_url,
                    params={"target_chembl_id": chembl_id, "limit": 20},
                    timeout=15.0
                )
                
                if compound_response.status_code != 200:
                    return []
                    
                compounds_data = compound_response.json()
                
                # Format the drug data
                formatted_drugs = []
                seen_drugs = set()
                
                for activity in compounds_data.get("activities", []):
                    drug_id = activity.get("molecule_chembl_id")
                    
                    # Skip duplicates
                    if drug_id in seen_drugs:
                        continue
                        
                    seen_drugs.add(drug_id)
                    
                    drug_data = {
                        "drug_id": drug_id,
                        "name": activity.get("molecule_pref_name", drug_id),
                        "description": f"Activity: {activity.get('standard_value', 'Unknown')} {activity.get('standard_units', '')}",
                        "mechanism": activity.get("target_type", ""),
                        "source": "ChEMBL"
                    }
                    
                    formatted_drugs.append(drug_data)
                
                return formatted_drugs
        except Exception as e:
            logger.error(f"Error querying ChEMBL: {str(e)}")
            return []

    async def get_protein_variants(self, uniprot_id: str) -> List[Dict[str, Any]]:
        """
        Get protein variants information from cache, knowledge graph, or external APIs
        
        Args:
            uniprot_id: UniProt ID of the protein
            
        Returns:
            List of variant objects with variant information
        """
        cache_key = f"protein_variants:{uniprot_id}"
        cached_data = await self.redis_client.get(cache_key)
        
        if cached_data:
            logger.info(f"Retrieved protein variants for {uniprot_id} from cache")
            return json.loads(cached_data)
        
        # Try to get variants from knowledge graph
        variants = await self._get_variants_from_kg(uniprot_id)
        if variants:
            await self.redis_client.set(cache_key, json.dumps(variants), expire=86400)  # Cache for 24 hours
            return variants
            
        # If not in KG, query external APIs like ClinVar
        variants = await self._query_variant_apis(uniprot_id)
        
        if variants:
            await self.redis_client.set(cache_key, json.dumps(variants), expire=86400)
            
            # Optionally store in KG for future use
            await self._store_variants_in_kg(uniprot_id, variants)
        
        return variants

    async def _get_variants_from_kg(self, uniprot_id: str) -> List[Dict[str, Any]]:
        """
        Get protein variants from knowledge graph
        """
        query = """
        MATCH (p:Protein {uniprot_id: $uniprot_id})-[r:HAS_VARIANT]->(v:Variant)
        RETURN v.variant_id as id, v.position as position, v.original as original,
               v.variant as variant, v.effect as effect, v.clinical_significance as clinical_significance,
               v.source as source
        """
        
        try:
            result = await self.db.run_query(query, {"uniprot_id": uniprot_id})
            
            if not result:
                return []
                
            variants = []
            for record in result:
                variant_data = {
                    "id": record.get("id"),
                    "position": record.get("position"),
                    "original": record.get("original"),
                    "variant": record.get("variant"),
                    "effect": record.get("effect"),
                    "clinical_significance": record.get("clinical_significance"),
                    "source": record.get("source")
                }
                variants.append(variant_data)
                
            logger.info(f"Retrieved {len(variants)} variants from knowledge graph for {uniprot_id}")
            return variants
            
        except Exception as e:
            logger.error(f"Error retrieving variants from KG: {str(e)}")
            return []

    async def _query_variant_apis(self, uniprot_id: str) -> List[Dict[str, Any]]:
        """
        Query external APIs like ClinVar and Ensembl for protein variants
        """
        logger.info(f"Querying variant data for {uniprot_id}")
        
        try:
            # First get the gene symbol from protein data to use with ClinVar
            protein_data = await self.get_protein_info(uniprot_id)
            gene_symbol = protein_data.get("name", "")
            
            if not gene_symbol:
                logger.warning(f"Could not find gene symbol for {uniprot_id}")
                return []
                
            # Try Ensembl first for genomic variants
            variants = await self._query_ensembl_variants(gene_symbol)
            
            # If Ensembl didn't return results, try ClinVar
            if not variants:
                variants = await self._query_clinvar_variants(gene_symbol)
                
            return variants
        except Exception as e:
            logger.error(f"Error querying variant APIs: {str(e)}")
            return []
        
    async def _query_ensembl_variants(self, gene_symbol: str) -> List[Dict[str, Any]]:
        """
        Query Ensembl for variants associated with a gene
        """
        logger.info(f"Querying Ensembl for variants of gene {gene_symbol}")
        
        try:
            # Ensembl REST API endpoint
            api_url = "https://rest.ensembl.org/variation/human"
            
            async with httpx.AsyncClient() as client:
                headers = {"Content-Type": "application/json", "Accept": "application/json"}
                
                # First get the Ensembl gene ID
                lookup_url = f"https://rest.ensembl.org/lookup/symbol/homo_sapiens/{gene_symbol}"
                response = await client.get(lookup_url, headers=headers, timeout=15.0)
                
                if response.status_code != 200:
                    logger.warning(f"Ensembl gene lookup failed with status {response.status_code}")
                    return []
                    
                gene_data = response.json()
                gene_id = gene_data.get("id")
                
                if not gene_id:
                    return []
                    
                # Now get variants for this gene
                variants_url = f"https://rest.ensembl.org/overlap/id/{gene_id}"
                response = await client.get(
                    variants_url, 
                    headers=headers,
                    params={"feature": "variation"},
                    timeout=15.0
                )
                
                if response.status_code != 200:
                    logger.warning(f"Ensembl variants query failed with status {response.status_code}")
                    return []
                    
                variants_data = response.json()
                
                # Format the variant data for our API
                formatted_variants = []
                for variant in variants_data[:50]:  # Limit to 50 variants
                    variant_id = variant.get("id")
                    
                    # Get additional details about this variant
                    detail_url = f"https://rest.ensembl.org/variation/human/{variant_id}"
                    detail_response = await client.get(detail_url, headers=headers)
                    
                    if detail_response.status_code != 200:
                        continue
                        
                    detail_data = detail_response.json()
                    
                    variant_data = {
                        "id": variant_id,
                        "position": variant.get("start"),
                        "original": detail_data.get("ancestral_allele", ""),
                        "variant": ", ".join(detail_data.get("alleles", [])),
                        "clinical_significance": detail_data.get("clinical_significance", ""),
                        "effect": detail_data.get("most_severe_consequence", ""),
                        "source": "Ensembl"
                    }
                    
                    formatted_variants.append(variant_data)
                
                return formatted_variants
        except Exception as e:
            logger.error(f"Error querying Ensembl: {str(e)}")
            return []
            
    async def _query_clinvar_variants(self, gene_symbol: str) -> List[Dict[str, Any]]:
        """
        Query ClinVar for variants associated with a gene
        """
        logger.info(f"Querying ClinVar for variants of gene {gene_symbol}")
        
        try:
            # ClinVar API endpoint through NCBI's E-utilities
            api_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            
            async with httpx.AsyncClient() as client:
                # First search for the gene in ClinVar
                search_response = await client.get(
                    api_url,
                    params={
                        "db": "clinvar",
                        "term": f"{gene_symbol}[gene]",
                        "retmode": "json",
                        "retmax": 100
                    },
                    timeout=15.0
                )
                
                if search_response.status_code != 200:
                    return []
                    
                search_data = search_response.json()
                variant_ids = search_data.get("esearchresult", {}).get("idlist", [])
                
                if not variant_ids:
                    return []
                    
                # Now fetch details for these variants
                summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
                summary_response = await client.get(
                    summary_url,
                    params={
                        "db": "clinvar",
                        "id": ",".join(variant_ids[:50]),  # Limit to 50 variants
                        "retmode": "json"
                    },
                    timeout=15.0
                )
                
                if summary_response.status_code != 200:
                    return []
                    
                summary_data = summary_response.json()
                result = summary_data.get("result", {})
                
                # Format the variant data
                formatted_variants = []
                
                for variant_id in variant_ids[:50]:
                    variant = result.get(variant_id, {})
                    
                    if not variant:
                        continue
                    
                    # Extract HGVS notation to get position and change
                    hgvs = variant.get("title", "")
                    position = None
                    original = ""
                    variant_aa = ""
                    
                    # Parse HGVS notation (e.g., NP_001289726.1:p.Val600Glu)
                    import re
                    match = re.search(r'p\.([A-Za-z]+)(\d+)([A-Za-z]+)', hgvs)
                    if match:
                        original = match.group(1)
                        position = match.group(2)
                        variant_aa = match.group(3)
                    
                    variant_data = {
                        "id": f"ClinVar:{variant_id}",
                        "position": position,
                        "original": original,
                        "variant": variant_aa,
                        "clinical_significance": variant.get("clinical_significance", {}).get("description", ""),
                        "effect": variant.get("variation_type", ""),
                        "source": "ClinVar"
                    }
                    
                    formatted_variants.append(variant_data)
                
                return formatted_variants
        except Exception as e:
            logger.error(f"Error querying ClinVar: {str(e)}")
            return []

    async def _store_variants_in_kg(self, uniprot_id: str, variants: List[Dict[str, Any]]) -> None:
        """
        Store variants in knowledge graph for future use
        """
        try:
            for variant in variants:
                query = """
                MATCH (p:Protein {uniprot_id: $uniprot_id})
                MERGE (v:Variant {variant_id: $variant_id})
                ON CREATE SET 
                    v.position = $position,
                    v.original = $original,
                    v.variant = $variant,
                    v.effect = $effect,
                    v.clinical_significance = $clinical_significance,
                    v.source = $source
                MERGE (p)-[r:HAS_VARIANT]->(v)
                """
                
                params = {
                    "uniprot_id": uniprot_id,
                    "variant_id": variant.get("id"),
                    "position": variant.get("position"),
                    "original": variant.get("original"),
                    "variant": variant.get("variant"),
                    "effect": variant.get("effect"),
                    "clinical_significance": variant.get("clinical_significance"),
                    "source": variant.get("source")
                }
                
                await self.db.run_query(query, params)
                
            logger.info(f"Stored {len(variants)} variants in knowledge graph for {uniprot_id}")
            
        except Exception as e:
            logger.error(f"Error storing variants in KG: {str(e)}")

    async def _fetch_uniprot_data(self, protein_id: str) -> Dict[str, Any]:
        """
        Fetch protein data from UniProt API
        
        Args:
            protein_id: UniProt ID of the protein
            
        Returns:
            Protein data from UniProt or empty dict if not found
        """
        logger.info(f"Fetching data from UniProt API for {protein_id}")
        
        try:
            # UniProt's REST API endpoints
            uniprot_api_url = "https://rest.uniprot.org/uniprotkb"
            
            async with httpx.AsyncClient() as client:
                # Query the API
                response = await client.get(
                    f"{uniprot_api_url}/{protein_id}",
                    params={"format": "json"},
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    logger.warning(f"UniProt API returned status code {response.status_code}")
                    return {}
                    
                data = response.json()
                
                # Extract relevant information
                protein_data = {
                    "id": protein_id,
                    "name": data.get("gene", [{}])[0].get("name", {}).get("value", protein_id),
                    "full_name": data.get("protein", {}).get("recommendedName", {}).get("fullName", {}).get("value", ""),
                    "function": "",
                    "description": "",
                    "sequence": data.get("sequence", {}).get("value", "")
                }
                
                # Extract function and description from comments
                for comment in data.get("comments", []):
                    if comment.get("commentType") == "FUNCTION":
                        protein_data["function"] = comment.get("texts", [{}])[0].get("value", "")
                    
                # Set description from protein existence
                protein_data["description"] = data.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value", "")
                
                # Get taxonomy information
                organism = data.get("organism", {}).get("scientificName", "")
                if organism:
                    protein_data["organism"] = organism
                    
                # Get sequence length
                protein_data["length"] = data.get("sequence", {}).get("length", 0)
                
                return protein_data
                
        except Exception as e:
            logger.error(f"Error fetching UniProt data: {str(e)}")
            return {}