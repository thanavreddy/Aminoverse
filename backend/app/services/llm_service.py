import logging
import json
import httpx
import re
from typing import Dict, List, Optional, Any, Union, Tuple

from app.core.config import settings
from app.cache.redis_client import RedisClient

logger = logging.getLogger(__name__)

class LLMService:
    """Service for natural language processing using LLMs."""
    
    def __init__(self, redis_client: RedisClient):
        """Initialize the LLM service."""
        self.redis_client = redis_client
        self.gemini_api_key = settings.GEMINI_API_KEY
        self.gemini_api_url = settings.GEMINI_API_URL
        
        # For backward compatibility
        self.api_key = settings.OPENAI_API_KEY if hasattr(settings, 'OPENAI_API_KEY') else None
    
    async def analyze_query(self, query: str) -> Tuple[str, List[str]]:
        """
        Analyze a user query to determine intent and entities.
        
        Returns:
            Tuple containing (intent, list of entities)
        """
        # Check cache first
        cache_key = f"query_analysis:{hash(query)}"
        cached_result = await self.redis_client.get_value(cache_key)
        if cached_result:
            return cached_result["intent"], cached_result["entities"]
        
        # Use Gemini to analyze the query
        if self.gemini_api_key:
            result = await self._call_gemini_api({
                "contents": [{
                    "parts": [{
                        "text": f"""Analyze this user query about proteins and return JSON with 'intent' and 'entities'.
                        Query: {query}
                        Possible intents: protein_info, structure_info, interactions, disease_info, drug_info, variant_info, general
                        Format: {{"intent": "intent_type", "entities": ["entity1", "entity2"]}}
                        """
                    }]
                }]
            })
            
            try:
                # Extract JSON from response
                json_match = re.search(r'```json\s*(.*?)\s*```', result, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_str = result
                
                # Clean up the JSON if needed
                json_str = json_str.strip()
                if not (json_str.startswith('{') and json_str.endswith('}')):
                    raise ValueError("Invalid JSON format")
                
                parsed_result = json.loads(json_str)
                intent = parsed_result.get("intent", "general")
                entities = parsed_result.get("entities", [])
                
                # Hard-coded mapping for protein symbols (as a fallback)
                protein_mapping = {
                    "P53": "P04637", "TP53": "P04637", "BRCA1": "P38398",
                    "PTEN": "P60484", "MDM2": "Q00987", "EGFR": "P00533", "KRAS": "P01116"
                }
                
                # Map known protein names to UniProt IDs
                mapped_entities = []
                for entity in entities:
                    if entity in protein_mapping:
                        mapped_entities.append(protein_mapping[entity])
                    else:
                        mapped_entities.append(entity)
                
                # Cache the result for future queries
                await self.redis_client.set_value(
                    cache_key,
                    {"intent": intent, "entities": mapped_entities},
                    expire=3600  # Cache for 1 hour
                )
                
                return intent, mapped_entities
            except Exception as e:
                logger.error(f"Error parsing Gemini response: {str(e)}")
                # Fall back to regex-based approach
        
        # Fall back to regex patterns if API call fails
        # Define patterns for common query types
        protein_info_pattern = r"(?:tell me about|what is|info on|information about)\s+(\w+)"
        structure_pattern = r"(?:structure of|show me the structure|display structure|protein structure)\s+(\w+)"
        interactions_pattern = r"(?:interactions of|interacts with|binding partners|proteins that interact with)\s+(\w+)"
        disease_pattern = r"(?:diseases|disorders|conditions|pathologies|what diseases are associated with)\s+(\w+)"
        drug_pattern = r"(?:drugs|medications|compounds|treatments|therapeutics|what drugs target)\s+(\w+)"
        variant_pattern = r"(?:variants|mutations|alterations|polymorphisms|snps)\s+(\w+)"
        
        # Check for matches
        protein_match = re.search(protein_info_pattern, query.lower())
        structure_match = re.search(structure_pattern, query.lower())
        interactions_match = re.search(interactions_pattern, query.lower())
        disease_match = re.search(disease_pattern, query.lower())
        drug_match = re.search(drug_pattern, query.lower())
        variant_match = re.search(variant_pattern, query.lower())
        
        # Determine intent and entities
        intent = "general"
        entities = []
        
        if protein_match:
            intent = "protein_info"
            entities = [protein_match.group(1).upper()]
        elif structure_match:
            intent = "structure_info"
            entities = [structure_match.group(1).upper()]
        elif interactions_match:
            intent = "interactions"
            entities = [interactions_match.group(1).upper()]
        elif disease_match:
            intent = "disease_info"
            entities = [disease_match.group(1).upper()]
        elif drug_match:
            intent = "drug_info"
            entities = [drug_match.group(1).upper()]
        elif variant_match:
            intent = "variant_info"
            entities = [variant_match.group(1).upper()]
        
        # Hard-coded mapping for protein symbols
        protein_mapping = {
            "P53": "P04637",
            "TP53": "P04637",
            "BRCA1": "P38398",
            "PTEN": "P60484",
            "MDM2": "Q00987",
            "EGFR": "P00533",
            "KRAS": "P01116"
        }
        
        # Map known protein names to UniProt IDs
        mapped_entities = []
        for entity in entities:
            if entity in protein_mapping:
                mapped_entities.append(protein_mapping[entity])
            else:
                mapped_entities.append(entity)
        
        # Cache the result for future queries
        await self.redis_client.set_value(
            cache_key,
            {"intent": intent, "entities": mapped_entities},
            expire=3600  # Cache for 1 hour
        )
        
        return intent, mapped_entities
    
    async def generate_response(self, query: str, data: Dict[str, Any], intent: str, session_id: str = None) -> str:
        """
        Generate a response based on the query, data, and intent using Gemini.
        Includes conversation history for better context handling.
        """
        if not self.gemini_api_key:
            # Fall back to template-based responses if no API key
            if intent == "protein_info":
                return await self.generate_protein_response(query, data)
            elif intent == "structure_info":
                return await self.generate_structure_response(query, data)
            elif intent == "interactions":
                return await self.generate_interactions_response(query, data)
            elif intent == "disease_info":
                return await self.generate_disease_response(query, data)
            elif intent == "drug_info":
                return await self.generate_drug_response(query, data)
            elif intent == "variant_info":
                return await self.generate_variant_response(query, data)
            else:
                return await self.generate_general_response(query)
        
        # Get conversation history if session_id is provided
        context = ""
        if session_id:
            try:
                history = await self.redis_client.get_chat_history(session_id)
                
                # Debug logging for chat history
                logger.info(f"Retrieved {len(history)} chat messages for session {session_id}")
                
                if history and len(history) > 0:
                    # Format the history for context
                    context = "Previous conversation:\n"
                    for msg in history:
                        role = "User" if msg.get("role") == "user" else "Assistant"
                        content = msg.get("content", "")
                        if content:
                            context += f"{role}: {content}\n"
            except Exception as e:
                logger.error(f"Error fetching conversation history: {str(e)}")
                # Continue with empty context if there's an error
        
        # Clean data for API input - handle different data types properly
        if isinstance(data, dict) or isinstance(data, list):
            clean_data = json.dumps(data)
        else:
            clean_data = str(data)
        
        # Generate a prompt based on the intent
        if intent == "protein_info":
            prompt = f"""Generate a detailed but concise response about this protein based on the user query: '{query}'
                    Here's the protein data: {clean_data}
                    
                    {context}
                    
                    Include details like the protein's function, structure, cellular location, and significance.
                    Make the response educational and scientifically accurate."""
        elif intent == "structure_info":
            prompt = f"""Generate a response about this protein's structure based on the user query: '{query}'
                    Here's the structure data: {clean_data}
                    
                    {context}
                    
                    Include details about the structure type (experimental vs. predicted), resolution, and key features.
                    Explain the significance of the structure in understanding the protein's function."""
        elif intent == "interactions":
            prompt = f"""Generate a response about this protein's interactions with other proteins based on the user query: '{query}'
                    Here's the interaction data: {clean_data}
                    
                    {context}
                    
                    Explain the significance of these interactions, their confidence scores, and the biological pathways they might be involved in.
                    Include how these interactions relate to the protein's function."""
        elif intent == "disease_info":
            prompt = f"""Generate a response about the diseases associated with this protein based on the user query: '{query}'
                    Here's the disease data: {clean_data}
                    
                    {context}
                    
                    Explain the mechanisms by which this protein contributes to these diseases,
                    include information about mutations, expression changes, or other relevant factors."""
        elif intent == "drug_info":
            prompt = f"""Generate a response about drugs that target this protein based on the user query: '{query}'
                    Here's the drug data: {clean_data}
                    
                    {context}
                    
                    Include information about the mechanisms of action, efficacy, development stage,
                    and any known side effects of these drugs."""
        elif intent == "variant_info":
            prompt = f"""Generate a response about variants of this protein based on the user query: '{query}'
                    Here's the variant data: {clean_data}
                    
                    {context}
                    
                    Explain the impact of these variants on protein function, their prevalence,
                    and their association with diseases or phenotypes."""
        else:
            # For general queries, rely more heavily on the conversation history
            prompt = f"""The user is asking about protein information with this query: '{query}'
                    
                    {context}
                    
                    Provide a helpful response based on general protein biology knowledge,
                    suggesting specific proteins they might be interested in if appropriate."""
        
        # Call the Gemini API with explicit instructions about conversation context
        response = await self._call_gemini_api({
            "contents": [{
                "parts": [{
                    "text": f"""You are AminoVerse, a protein research assistant for scientists.
                    Your role is to provide accurate, scientifically grounded information about proteins.
                    Maintain a professional but approachable tone. Format your response in a clear, 
                    readable way with important terms in bold if appropriate.
                    
                    If there is previous conversation context, use it to understand what the user is referring to.
                    For example, if they previously asked about TP53 and now ask "How does it relate to cancer?",
                    understand that "it" refers to TP53. Answer follow-up questions completely without requiring
                    the user to repeat information.
                    
                    When referring to previous conversation, don't explicitly mention it - just incorporate
                    the context naturally in your response as if continuing the conversation.
                    
                    {prompt}
                    """
                }]
            }]
        })
        
        # Store the assistant's response in chat history if session_id provided
        if session_id:
            try:
                await self.redis_client.store_chat_message(
                    session_id,
                    {
                        "role": "assistant",
                        "content": response
                    }
                )
                logger.info(f"Stored assistant response in chat history for session {session_id}")
            except Exception as e:
                logger.error(f"Error storing chat message: {str(e)}")
        
        return response

    async def _call_gemini_api(self, payload: Dict[str, Any]) -> str:
        """
        Call the Gemini API to generate a response.
        """
        try:
            url = f"{self.gemini_api_url}?key={self.gemini_api_key}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Extract the generated text from the response
                if "candidates" in result and result["candidates"]:
                    candidate = result["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        parts = candidate["content"]["parts"]
                        if parts and "text" in parts[0]:
                            return parts[0]["text"]
                
                # Handle case where response format is different
                logger.warning(f"Unexpected Gemini API response format: {result}")
                return "I'm sorry, I couldn't process that request properly."
                
        except Exception as e:
            logger.error(f"Error calling Gemini API: {str(e)}")
            return "I apologize, but I'm having trouble generating a response right now."
    
    async def test_connection(self) -> bool:
        """Test connection to the LLM API
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            # Attempt a simple API call to test connectivity
            test_result = await self._call_gemini_api({
                "contents": [{
                    "parts": [{
                        "text": "Hello, this is a test message. Please respond with 'OK' to confirm the API is working."
                    }]
                }]
            })
            
            # Check if we received any response
            return test_result is not None and len(test_result) > 0
        except Exception as e:
            logger.error(f"LLM API connection test failed: {str(e)}")
            return False
    
    # Keep the original template-based methods for fallback
    
    async def generate_protein_response(
        self, 
        query: str, 
        protein_data: Dict[str, Any]
    ) -> str:
        """
        Generate a natural language response about a protein.
        """
        protein_name = protein_data.get("name", "Unknown")
        full_name = protein_data.get("full_name", "")
        function = protein_data.get("function", "")
        description = protein_data.get("description", "")
        
        # Simple template-based response
        if function and description:
            return f"{protein_name} ({full_name}) is a protein that {function} {description}"
        elif description:
            return f"{protein_name} ({full_name}) is {description}"
        else:
            return f"I found information about {protein_name}, but detailed description is not available."
    
    async def generate_structure_response(
        self, 
        query: str, 
        structure_data: Dict[str, Any]
    ) -> str:
        """
        Generate a natural language response about protein structure.
        """
        pdb_id = structure_data.get("pdb_id")
        alphafold_id = structure_data.get("alphafold_id")
        method = structure_data.get("method", "Unknown method")
        resolution = structure_data.get("resolution")
        
        if pdb_id:
            response = f"The protein has an experimentally determined structure in the Protein Data Bank (PDB ID: {pdb_id})."
            if resolution:
                response += f" It was determined using {method} at {resolution} Å resolution."
            return response
        elif alphafold_id:
            return f"The protein structure has been computationally predicted by AlphaFold (ID: {alphafold_id})."
        else:
            return "No structural information is currently available for this protein."
    
    async def generate_interactions_response(
        self, 
        query: str, 
        interactions_data: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a natural language response about protein interactions.
        """
        if not interactions_data:
            return "No known protein interactions were found."
        
        # Count interactions
        num_interactions = len(interactions_data)
        
        # Sort by confidence score
        sorted_interactions = sorted(interactions_data, key=lambda x: x.get("score", 0), reverse=True)
        
        # Get top interactions
        top_interactions = sorted_interactions[:3]
        
        # Format response
        response = f"I found {num_interactions} protein interaction{'s' if num_interactions != 1 else ''}."
        
        if top_interactions:
            response += " The most significant interactions are with "
            interaction_texts = []
            
            for interaction in top_interactions:
                protein_name = interaction.get("protein_name", "Unknown protein")
                score = interaction.get("score", 0)
                interaction_texts.append(f"{protein_name} (confidence: {score:.2f})")
            
            response += ", ".join(interaction_texts) + "."
        
        return response
    
    async def generate_disease_response(
        self, 
        query: str, 
        disease_data: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a natural language response about disease associations.
        """
        if not disease_data:
            return "No disease associations were found for this protein."
        
        # Count diseases
        num_diseases = len(disease_data)
        
        # Format response
        response = f"This protein is associated with {num_diseases} disease{'s' if num_diseases != 1 else ''}."
        
        if num_diseases <= 3:
            # List all diseases for a small number
            disease_texts = []
            for disease in disease_data:
                disease_name = disease.get("name", "Unknown disease")
                disease_desc = disease.get("description", "")
                
                if disease_desc:
                    disease_texts.append(f"{disease_name} ({disease_desc})")
                else:
                    disease_texts.append(disease_name)
            
            response += " These include " + ", ".join(disease_texts) + "."
        else:
            # List just a few for many diseases
            disease_names = [disease.get("name", "Unknown disease") for disease in disease_data[:3]]
            response += f" These include {', '.join(disease_names)}, and others."
        
        return response
    
    async def generate_drug_response(
        self, 
        query: str, 
        drug_data: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a natural language response about drug interactions.
        """
        if not drug_data:
            return "No known drugs target this protein."
        
        # Count drugs
        num_drugs = len(drug_data)
        
        # Format response
        response = f"There {'are' if num_drugs > 1 else 'is'} {num_drugs} known drug{'s' if num_drugs != 1 else ''} that target{'s' if num_drugs == 1 else ''} this protein."
        
        if drug_data:
            drug_texts = []
            for drug in drug_data:
                drug_name = drug.get("name", "Unknown drug")
                mechanism = drug.get("mechanism", "")
                
                if mechanism:
                    drug_texts.append(f"{drug_name} ({mechanism})")
                else:
                    drug_texts.append(drug_name)
            
            response += " " + ", ".join(drug_texts) + "."
        
        return response
    
    async def generate_variant_response(
        self, 
        query: str, 
        variant_data: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a natural language response about protein variants.
        """
        if not variant_data:
            return "No variant information is available for this protein."
        
        # Count variants
        num_variants = len(variant_data)
        
        # Count pathogenic variants
        pathogenic_count = sum(1 for v in variant_data if v.get("clinical_significance") == "pathogenic")
        
        # Format response
        response = f"This protein has {num_variants} documented variant{'s' if num_variants != 1 else ''}."
        
        if pathogenic_count:
            response += f" {pathogenic_count} of these {'are' if pathogenic_count > 1 else 'is'} classified as pathogenic."
        
        if num_variants <= 3:
            # List all variants for a small number
            variant_texts = []
            for variant in variant_data:
                name = variant.get("name", "Unknown variant")
                effect = variant.get("effect", "")
                
                if effect:
                    variant_texts.append(f"{name} ({effect})")
                else:
                    variant_texts.append(name)
            
            response += " These include " + ", ".join(variant_texts) + "."
        
        return response
    
    async def generate_general_response(self, query: str) -> str:
        """
        Generate a response for general queries.
        """
        # Default response for queries without recognized entities
        return "I can provide information about proteins, their structures, interactions, disease associations, and more. Try asking about a specific protein like TP53 or BRCA1."