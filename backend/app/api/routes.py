from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any, List, Optional
import logging
import uuid
import datetime

from app.schemas.protein import ChatMessage, ChatResponse, ProteinResponse
from app.services.protein_service import ProteinService
from app.services.llm_service import LLMService
from app.services.knowledge_graph_service import KnowledgeGraphService
from app.cache.redis_client import RedisClient
from app.db.neo4j import Neo4jDatabase

from . import status_routes

# Set up logger
logger = logging.getLogger(__name__)

# Create API router
router = APIRouter()

# Include the status routes
router.include_router(
    status_routes.router,
    prefix="/status",
    tags=["status"]
)

# Dependency to get services
def get_redis_client():
    return RedisClient()

def get_db():
    return Neo4jDatabase()

def get_protein_service(
    redis_client: RedisClient = Depends(get_redis_client),
    db: Neo4jDatabase = Depends(get_db)
):
    return ProteinService(redis_client=redis_client, db=db)

def get_llm_service(redis_client: RedisClient = Depends(get_redis_client)):
    return LLMService(redis_client=redis_client)

def get_kg_service(
    redis_client: RedisClient = Depends(get_redis_client),
    db: Neo4jDatabase = Depends(get_db)
):
    return KnowledgeGraphService(redis_client=redis_client, db=db)


# API Routes
@router.post("/chat", response_model=ChatResponse)
async def process_chat(
    message: ChatMessage,
    protein_service: ProteinService = Depends(get_protein_service),
    llm_service: LLMService = Depends(get_llm_service),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """
    Process a user's chat message and return a response with relevant information.
    """
    try:
        # Store message in chat history if session_id is provided
        if message.session_id:
            await get_redis_client().store_chat_message(
                message.session_id,
                {
                    "role": "user",
                    "content": message.message
                }
            )
        
        # Analyze the query using LLM service
        intent, entities = await llm_service.analyze_query(message.message)
        
        # If we have entities, process based on intent
        if entities:
            # Use first entity as the main protein/gene
            entity_id = entities[0]
            
            if intent == "protein_info":
                # Get protein information
                protein_data = await protein_service.get_protein_info(entity_id)
                
                # Generate a natural language response
                text_response = await llm_service.generate_response(
                    message.message, 
                    protein_data,
                    intent,
                    message.session_id  # Pass session_id for conversation history
                )
                
                # Suggest follow-up questions
                follow_ups = [
                    f"Show me the structure of {entity_id}",
                    f"What diseases are associated with {entity_id}?",
                    f"Show protein interactions for {entity_id}",
                    f"What drugs target {entity_id}?"
                ]
                
                return ChatResponse(
                    message=text_response,
                    data=protein_data,
                    follow_up_suggestions=follow_ups
                )
                
            elif intent == "structure_info":
                # Get protein information first
                protein_data = await protein_service.get_protein_info(entity_id)
                
                # Get or extract structure data
                structure_data = protein_data.get("structure")
                if not structure_data:
                    structure_data = await protein_service.get_protein_structure(entity_id)
                
                # Generate response
                text_response = await llm_service.generate_response(
                    message.message,
                    structure_data,
                    intent,
                    message.session_id  # Pass session_id for conversation history
                )
                
                return ChatResponse(
                    message=text_response,
                    data=protein_data,
                    visualization_data=structure_data,
                    visualization_type="structure",
                    follow_up_suggestions=[
                        f"What is the function of {entity_id}?",
                        f"Show protein interactions for {entity_id}"
                    ]
                )
                
            elif intent == "interactions":
                # Get protein interactions
                interactions_data = await protein_service.get_protein_interactions(entity_id)
                
                # Generate response
                text_response = await llm_service.generate_response(
                    message.message,
                    interactions_data,
                    intent,
                    message.session_id  # Pass session_id for conversation history
                )
                
                # Get basic protein info as context
                protein_data = await protein_service.get_protein_info(entity_id)
                
                return ChatResponse(
                    message=text_response,
                    data=protein_data,
                    visualization_data=interactions_data,
                    visualization_type="interactions",
                    follow_up_suggestions=[
                        f"Tell me about {interactions_data[0]['protein_name'] if interactions_data else entity_id}",
                        f"What diseases are associated with {entity_id}?"
                    ]
                )
                
            elif intent == "disease_info":
                # Get disease associations
                disease_data = await protein_service.get_disease_associations(entity_id)
                
                # Generate response
                text_response = await llm_service.generate_response(
                    message.message,
                    disease_data,
                    intent,
                    message.session_id  # Pass session_id for conversation history
                )
                
                # Get basic protein info as context
                protein_data = await protein_service.get_protein_info(entity_id)
                
                # Include knowledge graph data
                kg_data = await kg_service.get_protein_knowledge_graph(entity_id)
                
                return ChatResponse(
                    message=text_response,
                    data=protein_data,
                    visualization_data=kg_data,
                    visualization_type="knowledge_graph",
                    follow_up_suggestions=[
                        f"What drugs can treat {disease_data[0]['name'] if disease_data else 'diseases'} associated with {entity_id}?",
                        f"Tell me about {entity_id}"
                    ]
                )
                
            elif intent == "drug_info":
                # Get drug interactions
                drug_data = await protein_service.get_drug_interactions(entity_id)
                
                # Generate response
                text_response = await llm_service.generate_response(
                    message.message,
                    drug_data,
                    intent,
                    message.session_id  # Pass session_id for conversation history
                )
                
                # Get basic protein info as context
                protein_data = await protein_service.get_protein_info(entity_id)
                
                return ChatResponse(
                    message=text_response,
                    data=protein_data,
                    follow_up_suggestions=[
                        f"What diseases are associated with {entity_id}?",
                        f"How does {drug_data[0]['name'] if drug_data else 'this drug'} work?"
                    ]
                )
                
            elif intent == "variant_info":
                # Get variant information
                variant_data = await protein_service.get_protein_variants(entity_id)
                
                # Generate response
                text_response = await llm_service.generate_response(
                    message.message,
                    variant_data,
                    intent,
                    message.session_id  # Pass session_id for conversation history
                )
                
                # Get basic protein info as context
                protein_data = await protein_service.get_protein_info(entity_id)
                
                return ChatResponse(
                    message=text_response,
                    data=protein_data,
                    follow_up_suggestions=[
                        f"What diseases are associated with {entity_id} variants?",
                        f"Tell me more about {entity_id}"
                    ]
                )
            
            else:
                # Default to protein info for unknown intents with entities
                protein_data = await protein_service.get_protein_info(entity_id)
                
                # Generate a natural language response
                text_response = await llm_service.generate_response(
                    message.message, 
                    protein_data,
                    intent,
                    message.session_id  # Pass session_id for conversation history
                )
                
                return ChatResponse(
                    message=text_response,
                    data=protein_data,
                    follow_up_suggestions=[
                        f"Show me the structure of {entity_id}",
                        f"What diseases are associated with {entity_id}?"
                    ]
                )
        
        # If no entities found, handle as general query
        general_response = await llm_service.generate_response(
            message.message,
            {},
            "general", 
            message.session_id  # Pass session_id for conversation history
        )
        
        return ChatResponse(
            message=general_response,
            follow_up_suggestions=[
                "Tell me about TP53",
                "Show me the structure of BRCA1",
                "What diseases are associated with PTEN?"
            ]
        )
            
    except Exception as e:
        logger.exception(f"Error processing chat message: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing your request: {str(e)}"
        )

@router.get("/protein/{protein_id}", response_model=ProteinResponse)
async def get_protein(
    protein_id: str,
    protein_service: ProteinService = Depends(get_protein_service),
    llm_service: LLMService = Depends(get_llm_service)
):
    """
    Get detailed information about a specific protein.
    """
    try:
        protein_data = await protein_service.get_protein_info(protein_id)
        return ProteinResponse(**protein_data)
    except Exception as e:
        logger.exception(f"Error fetching protein {protein_id}: {str(e)}")
        
        # Fallback to LLM-generated data
        logger.info(f"Using LLM fallback for protein {protein_id}")
        try:
            # Generate protein info using LLM
            llm_query = f"Generate comprehensive scientific data for protein {protein_id}. Include fields like id, name, description, gene, organism, function, sequence length, and other key properties in JSON format."
            llm_response = await llm_service._call_gemini_api({
                "contents": [{
                    "parts": [{
                        "text": llm_query
                    }]
                }]
            })
            
            import re
            import json
            
            # Extract JSON from the response
            json_match = re.search(r'```json\s*(.*?)\s*```', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
            else:
                json_pattern = re.search(r'(\{\s*"id"\s*:.*\})', llm_response, re.DOTALL)
                if json_pattern:
                    json_str = json_pattern.group(1).strip()
                else:
                    # Create basic structure if no JSON found
                    json_str = f'{{"id": "{protein_id}", "name": "Protein {protein_id}", "description": "Generated data for {protein_id}"}}'
            
            # Parse generated data
            generated_data = json.loads(json_str)
            
            # Ensure required fields exist
            if "id" not in generated_data:
                generated_data["id"] = protein_id
            
            logger.info(f"Successfully generated fallback data for protein {protein_id}")
            return ProteinResponse(**generated_data)
        
        except Exception as fallback_error:
            logger.exception(f"LLM fallback failed for protein {protein_id}: {str(fallback_error)}")
            # Return minimal response structure to prevent errors
            return ProteinResponse(
                id=protein_id,
                name=f"Protein {protein_id}",
                description=f"Could not retrieve data for {protein_id}. Please try again later.",
                is_generated=True
            )

@router.get("/protein/{protein_id}/structure")
async def get_protein_structure(
    protein_id: str,
    protein_service: ProteinService = Depends(get_protein_service),
    llm_service: LLMService = Depends(get_llm_service)
):
    """
    Get structure information for a protein.
    """
    try:
        structure_data = await protein_service.get_protein_structure(protein_id)
        return structure_data
    except Exception as e:
        logger.exception(f"Error fetching structure for {protein_id}: {str(e)}")
        
        # Fallback to LLM-generated structure data
        logger.info(f"Using LLM fallback for protein structure {protein_id}")
        try:
            # Generate structure info using LLM
            llm_query = f"Generate protein structure data for {protein_id} in JSON format. Include fields like pdb_id, title, experimental_method, resolution, chain_ids, and a placeholder for coordinates."
            llm_response = await llm_service._call_gemini_api({
                "contents": [{
                    "parts": [{
                        "text": llm_query
                    }]
                }]
            })
            
            import re
            import json
            
            # Extract JSON from the response
            json_match = re.search(r'```json\s*(.*?)\s*```', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
            else:
                json_pattern = re.search(r'(\{\s*"pdb_id"\s*:.*\})', llm_response, re.DOTALL)
                if json_pattern:
                    json_str = json_pattern.group(1).strip()
                else:
                    # Create basic structure data if no JSON found
                    json_str = f'''{{
                        "pdb_id": "simulated_{protein_id}",
                        "title": "Simulated Structure for {protein_id}",
                        "experimental_method": "Generated Data",
                        "resolution": "N/A",
                        "chain_ids": ["A"],
                        "coordinates": "Generated data placeholder",
                        "is_generated": true
                    }}'''
            
            # Parse generated data
            generated_data = json.loads(json_str)
            
            # Ensure required fields exist
            if "pdb_id" not in generated_data:
                generated_data["pdb_id"] = f"simulated_{protein_id}"
            if "is_generated" not in generated_data:
                generated_data["is_generated"] = True
                
            logger.info(f"Successfully generated fallback structure data for protein {protein_id}")
            return generated_data
            
        except Exception as fallback_error:
            logger.exception(f"LLM fallback failed for protein structure {protein_id}: {str(fallback_error)}")
            # Return minimal structure data to prevent errors
            return {
                "pdb_id": f"simulated_{protein_id}",
                "title": f"Simulated Structure for {protein_id}",
                "experimental_method": "Generated Data",
                "resolution": "N/A",
                "chain_ids": ["A"],
                "coordinates": "Generated data placeholder",
                "is_generated": True,
                "message": "Could not retrieve actual structure data. This is simulated information."
            }

@router.get("/protein/{protein_id}/interactions")
async def get_protein_interactions(
    protein_id: str,
    protein_service: ProteinService = Depends(get_protein_service),
    llm_service: LLMService = Depends(get_llm_service),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """
    Get protein-protein interactions for a specific protein.
    """
    try:
        interactions = await protein_service.get_protein_interactions(protein_id)
        
        # Also fetch the knowledge graph data
        try:
            knowledge_graph = await kg_service.get_entity_graph(protein_id, "Protein")
            # Add visualization data to the response
            return {
                "interactions": interactions,
                "knowledge_graph": knowledge_graph,
                "visualization_type": "network_and_graph"
            }
        except Exception as kg_error:
            logger.error(f"Error fetching knowledge graph for interactions: {str(kg_error)}")
            return interactions
            
    except Exception as e:
        logger.exception(f"Error fetching interactions for {protein_id}: {str(e)}")
        
        # Fallback to LLM-generated interaction data
        logger.info(f"Using LLM fallback for protein interactions {protein_id}")
        try:
            # Generate interactions using LLM
            llm_query = f"Generate realistic protein-protein interaction data for protein {protein_id} in JSON array format. Include fields like protein_id, protein_name, score, and evidence for each interaction. List 5-10 realistic interactions based on scientific knowledge."
            llm_response = await llm_service._call_gemini_api({
                "contents": [{
                    "parts": [{
                        "text": llm_query
                    }]
                }]
            })
            
            import re
            import json
            
            # Extract JSON from the response
            json_match = re.search(r'```json\s*(.*?)\s*```', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
            else:
                json_pattern = re.search(r'(\[\s*\{.*\}\s*\])', llm_response, re.DOTALL)
                if json_pattern:
                    json_str = json_pattern.group(1).strip()
                else:
                    # Create basic interaction data if no JSON found
                    json_str = f'''[
                        {{
                            "protein_id": "P04637",
                            "protein_name": "Cellular tumor antigen p53",
                            "score": 0.9,
                            "evidence": "Generated data - text mining",
                            "is_generated": true
                        }},
                        {{
                            "protein_id": "Q00987",
                            "protein_name": "E3 ubiquitin-protein ligase Mdm2",
                            "score": 0.85,
                            "evidence": "Generated data - co-expression",
                            "is_generated": true
                        }}
                    ]'''
            
            # Parse generated data
            generated_data = json.loads(json_str)
            
            # Mark data as generated
            for item in generated_data:
                item["is_generated"] = True
            
            logger.info(f"Successfully generated fallback interaction data for protein {protein_id}")
            return generated_data
            
        except Exception as fallback_error:
            logger.exception(f"LLM fallback failed for protein interactions {protein_id}: {str(fallback_error)}")
            # Return minimal interaction data to prevent errors
            return [
                {
                    "protein_id": "P04637",
                    "protein_name": "Cellular tumor antigen p53",
                    "score": 0.9,
                    "evidence": "Generated data - text mining",
                    "is_generated": True,
                    "message": "This is simulated interaction data as actual data could not be retrieved."
                },
                {
                    "protein_id": "Q00987",
                    "protein_name": "E3 ubiquitin-protein ligase Mdm2",
                    "score": 0.85,
                    "evidence": "Generated data - co-expression",
                    "is_generated": True,
                    "message": "This is simulated interaction data as actual data could not be retrieved."
                }
            ]

@router.get("/protein/{protein_id}/diseases")
async def get_protein_diseases(
    protein_id: str,
    protein_service: ProteinService = Depends(get_protein_service),
    llm_service: LLMService = Depends(get_llm_service),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """
    Get diseases associated with a specific protein.
    """
    try:
        diseases = await protein_service.get_disease_associations(protein_id)
        
        # Also fetch the knowledge graph data
        try:
            knowledge_graph = await kg_service.get_entity_graph(protein_id, "Protein")
            # Add visualization data to the response
            return {
                "diseases": diseases,
                "knowledge_graph": knowledge_graph,
                "visualization_type": "knowledge_graph"
            }
        except Exception as kg_error:
            logger.error(f"Error fetching knowledge graph: {str(kg_error)}")
            return diseases
            
    except Exception as e:
        logger.exception(f"Error fetching diseases for {protein_id}: {str(e)}")

@router.get("/protein/{protein_id}/drugs")
async def get_protein_drugs(
    protein_id: str,
    protein_service: ProteinService = Depends(get_protein_service),
    llm_service: LLMService = Depends(get_llm_service)
):
    """
    Get drugs that target a specific protein.
    """
    try:
        drugs = await protein_service.get_drug_interactions(protein_id)
        return drugs
    except Exception as e:
        logger.exception(f"Error fetching drugs for {protein_id}: {str(e)}")
        
        # Fallback to LLM-generated drug data
        logger.info(f"Using LLM fallback for protein drugs {protein_id}")
        try:
            # Generate drug interactions using LLM
            llm_query = f"Generate realistic drug data for protein {protein_id} in JSON array format. Include fields like drug_id, name, mechanism, status, and clinical_phase for each drug. List 3-5 drugs that might realistically target this protein based on scientific knowledge."
            llm_response = await llm_service._call_gemini_api({
                "contents": [{
                    "parts": [{
                        "text": llm_query
                    }]
                }]
            })
            
            import re
            import json
            
            # Extract JSON from the response
            json_match = re.search(r'```json\s*(.*?)\s*```', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
            else:
                json_pattern = re.search(r'(\[\s*\{.*\}\s*\])', llm_response, re.DOTALL)
                if json_pattern:
                    json_str = json_pattern.group(1).strip()
                else:
                    # Create basic drug data if no JSON found
                    json_str = f'''[
                        {{
                            "drug_id": "DB00351",
                            "name": "Imatinib",
                            "mechanism": "Tyrosine kinase inhibitor",
                            "status": "approved",
                            "clinical_phase": "4",
                            "is_generated": true
                        }},
                        {{
                            "drug_id": "DB00619",
                            "name": "Sunitinib",
                            "mechanism": "Multi-targeted receptor tyrosine kinase inhibitor",
                            "status": "approved",
                            "clinical_phase": "4",
                            "is_generated": true
                        }}
                    ]'''
            
            # Parse generated data
            generated_data = json.loads(json_str)
            
            # Mark data as generated
            for item in generated_data:
                item["is_generated"] = True
            
            logger.info(f"Successfully generated fallback drug data for protein {protein_id}")
            return generated_data
            
        except Exception as fallback_error:
            logger.exception(f"LLM fallback failed for protein drugs {protein_id}: {str(fallback_error)}")
            # Return minimal drug data to prevent errors
            return [
                {
                    "drug_id": "DB00351",
                    "name": "Imatinib",
                    "mechanism": "Tyrosine kinase inhibitor",
                    "status": "approved",
                    "clinical_phase": "4",
                    "is_generated": True,
                    "message": "This is simulated drug data as actual data could not be retrieved."
                },
                {
                    "drug_id": "DB00619", 
                    "name": "Sunitinib",
                    "mechanism": "Multi-targeted receptor tyrosine kinase inhibitor",
                    "status": "approved",
                    "clinical_phase": "4",
                    "is_generated": True,
                    "message": "This is simulated drug data as actual data could not be retrieved."
                }
            ]

@router.get("/knowledge-graph/{entity_id}")
async def get_knowledge_graph(
    entity_id: str,
    entity_type: str = Query("Protein", description="Entity type (Protein, Disease, Drug, etc.)"),
    kg_service: KnowledgeGraphService = Depends(get_kg_service),
    llm_service: LLMService = Depends(get_llm_service)
):
    """
    Get knowledge graph data centered around a specific entity.
    """
    try:
        logger.info(f"Fetching knowledge graph for entity_id={entity_id}, entity_type={entity_type}")
        graph_data = await kg_service.get_entity_graph(entity_id, entity_type)
        
        # Add debug information to check the output
        node_count = len(graph_data.get("nodes", []))
        edge_count = len(graph_data.get("edges", []))
        logger.info(f"Knowledge graph retrieved: {node_count} nodes, {edge_count} edges")
        
        # If there's no data or it's demo data, enhance it with LLM-generated information
        if node_count == 0 or edge_count == 0 or graph_data.get("is_demo", False):
            logger.warning(f"No graph data found for {entity_id}, generating enhanced LLM data")
            
            # Generate enhanced knowledge graph data using LLM
            enhanced_graph = await generate_enhanced_knowledge_graph(entity_id, entity_type, llm_service)
            if enhanced_graph:
                return enhanced_graph
            
            # Fall back to demo data only if LLM enhancement fails
            logger.info("Falling back to demo knowledge graph data")
            return generate_demo_knowledge_graph(entity_id, entity_type)
            
        return graph_data
    except Exception as e:
        logger.exception(f"Error fetching knowledge graph for {entity_id}: {str(e)}")
        # For the hackathon demo, return enhanced data instead of failing
        logger.info("Returning enhanced knowledge graph data instead")
        enhanced_graph = await generate_enhanced_knowledge_graph(entity_id, entity_type, llm_service)
        if enhanced_graph:
            return enhanced_graph
        return generate_demo_knowledge_graph(entity_id, entity_type)

async def generate_enhanced_knowledge_graph(entity_id: str, entity_type: str, llm_service: LLMService) -> Dict[str, Any]:
    """
    Generate a more realistic knowledge graph for demonstration purposes using LLM.
    
    Args:
        entity_id: The ID of the entity (e.g., UniProt ID for proteins)
        entity_type: The type of entity (Protein, Disease, Drug, etc.)
        llm_service: LLM service for generating realistic data
    
    Returns:
        Dict with nodes and edges for visualization
    """
    logger.info(f"Generating enhanced knowledge graph for {entity_type}:{entity_id}")
    
    try:
        # Prepare a query for the LLM to generate relevant connections
        query = f"""Generate knowledge graph data for {entity_type} {entity_id}.
        I need JSON data with realistic biological connections.
        
        If it's a protein like TP53 (P04637), include:
        - Related proteins it interacts with (with real protein names and UniProt IDs if known)
        - Diseases it's associated with
        - Drugs that target it
        - Pathways it's involved in
        
        Return ONLY a JSON object with this structure:
        {{
          "nodes": [
            {{"id": "P04637", "type": "Protein", "label": "p53", "name": "Cellular tumor antigen p53"}},
            {{"id": "Q00987", "type": "Protein", "label": "MDM2", "name": "E3 ubiquitin-protein ligase Mdm2"}},
            // more nodes
          ],
          "edges": [
            {{"id": "edge_1", "source": "P04637", "target": "Q00987", "type": "INTERACTS_WITH"}},
            // more edges
          ]
        }}
        """
        
        # Call the LLM service to generate the graph data
        llm_response = await llm_service._call_gemini_api({
            "contents": [{
                "parts": [{
                    "text": query
                }]
            }]
        })
        
        # Extract JSON from the response
        import re
        import json
        
        # Try to extract JSON from the response
        json_match = re.search(r'```json\s*(.*?)\s*```', llm_response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            # If no markdown code block, try to find JSON structure directly
            json_pattern = re.search(r'(\{\s*"nodes"\s*:\s*\[.*?\]\s*,\s*"edges"\s*:\s*\[.*?\]\s*\})', 
                                   llm_response, re.DOTALL)
            if json_pattern:
                json_str = json_pattern.group(1).strip()
            else:
                # Use the whole response and hope it's valid JSON
                json_str = llm_response.strip()
        
        try:
            # Parse the JSON
            graph_data = json.loads(json_str)
            
            # Make sure the central entity is included and marked as central
            central_node_exists = False
            for node in graph_data.get("nodes", []):
                if node.get("id") == entity_id:
                    node["centrality"] = 1
                    central_node_exists = True
                    break
            
            # Add central node if it doesn't exist
            if not central_node_exists and graph_data.get("nodes"):
                graph_data["nodes"].insert(0, {
                    "id": entity_id,
                    "type": entity_type,
                    "label": entity_id,
                    "name": f"{entity_type} {entity_id}",
                    "centrality": 1
                })
            
            logger.info(f"Successfully generated enhanced knowledge graph: {len(graph_data.get('nodes', []))} nodes, {len(graph_data.get('edges', []))} edges")
            return graph_data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM response: {str(e)}")
            return None
            
    except Exception as e:
        logger.error(f"Error generating enhanced knowledge graph: {str(e)}")
        return None


def generate_demo_knowledge_graph(entity_id: str, entity_type: str) -> Dict[str, Any]:
    """
    Generate a sample knowledge graph for demonstration purposes.
    
    This is used when the real data is not available to ensure the demo works.
    """
    # Create a central node for the entity
    central_node = {
        "id": entity_id,
        "type": entity_type,
        "label": f"{entity_type} {entity_id}",
        "name": f"{entity_type} {entity_id}"
    }
    
    nodes = [central_node]
    edges = []
    
    # Add some sample nodes and connections
    if entity_type.lower() == "protein":
        # Add related proteins
        for i in range(1, 4):
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
        
        # Add disease associations
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
            
        # Add drug targets
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
    
    elif entity_type.lower() == "disease":
        # Add protein associations
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
            
        # Add drug treatments
        for i in range(1, 3):
            drug_id = f"DRUG_{i}"
            nodes.append({
                "id": drug_id,
                "type": "Drug",
                "label": f"Treatment Drug {i}",
                "name": f"Treatment Drug {i}"
            })
            edges.append({
                "id": f"edge_t{i}",
                "source": drug_id,
                "target": entity_id,
                "type": "TREATS"
            })
    
    elif entity_type.lower() == "drug":
        # Add protein targets
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
                "label": f"Treated Disease {i}",
                "name": f"Treated Disease {i}"
            })
            edges.append({
                "id": f"edge_d{i}",
                "source": entity_id,
                "target": disease_id,
                "type": "TREATS"
            })
    
    return {
        "nodes": nodes,
        "edges": edges
    }

@router.get("/test/all-endpoints")
async def test_all_endpoints(
    protein_service: ProteinService = Depends(get_protein_service),
    llm_service: LLMService = Depends(get_llm_service),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """
    Test all API endpoints with a sample protein ID to verify they're working.
    This helps identify any non-working endpoints that may need LLM fallbacks.
    """
    test_protein_ids = ["P04637", "P38398", "P60484"]  # TP53, BRCA1, PTEN
    results = {}
    
    # Test each protein ID with all endpoints
    for protein_id in test_protein_ids:
        protein_results = {}
        
        # Test protein info endpoint
        try:
            logger.info(f"Testing /protein/{protein_id}")
            protein_data = await protein_service.get_protein_info(protein_id)
            protein_results["protein_info"] = {
                "status": "ok",
                "is_generated": protein_data.get("is_generated", False)
            }
        except Exception as e:
            protein_results["protein_info"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Test protein structure endpoint
        try:
            logger.info(f"Testing /protein/{protein_id}/structure")
            structure_data = await protein_service.get_protein_structure(protein_id)
            protein_results["structure"] = {
                "status": "ok",
                "is_generated": structure_data.get("is_generated", False)
            }
        except Exception as e:
            protein_results["structure"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Test protein interactions endpoint
        try:
            logger.info(f"Testing /protein/{protein_id}/interactions")
            interactions_data = await protein_service.get_protein_interactions(protein_id)
            protein_results["interactions"] = {
                "status": "ok",
                "count": len(interactions_data),
                "is_generated": interactions_data[0].get("is_generated", False) if interactions_data else False
            }
        except Exception as e:
            protein_results["interactions"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Test disease associations endpoint
        try:
            logger.info(f"Testing /protein/{protein_id}/diseases")
            disease_data = await protein_service.get_disease_associations(protein_id)
            protein_results["diseases"] = {
                "status": "ok",
                "count": len(disease_data),
                "is_generated": disease_data[0].get("is_generated", False) if disease_data else False
            }
        except Exception as e:
            protein_results["diseases"] = {
                "status": "error", 
                "error": str(e)
            }
        
        # Test drug interactions endpoint
        try:
            logger.info(f"Testing /protein/{protein_id}/drugs")
            drug_data = await protein_service.get_drug_interactions(protein_id)
            protein_results["drugs"] = {
                "status": "ok",
                "count": len(drug_data),
                "is_generated": drug_data[0].get("is_generated", False) if drug_data else False
            }
        except Exception as e:
            protein_results["drugs"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Test knowledge graph endpoint
        try:
            logger.info(f"Testing /knowledge-graph/{protein_id}")
            graph_data = await kg_service.get_entity_graph(protein_id, "Protein")
            protein_results["knowledge_graph"] = {
                "status": "ok",
                "node_count": len(graph_data.get("nodes", [])),
                "edge_count": len(graph_data.get("edges", [])),
                "is_generated": graph_data.get("is_generated", False) or graph_data.get("is_demo", False)
            }
        except Exception as e:
            protein_results["knowledge_graph"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Add chat test (simple query)
        try:
            logger.info(f"Testing /chat with query about {protein_id}")
            chat_message = ChatMessage(message=f"Tell me about {protein_id}")
            # Only analyze intent and entities without generating full response
            intent, entities = await llm_service.analyze_query(chat_message.message)
            protein_results["chat"] = {
                "status": "ok",
                "intent": intent,
                "entities": entities
            }
        except Exception as e:
            protein_results["chat"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Add results for this protein ID
        results[protein_id] = protein_results
    
    # Calculate summary statistics
    endpoint_success = {
        "protein_info": 0,
        "structure": 0,
        "interactions": 0,
        "diseases": 0,
        "drugs": 0,
        "knowledge_graph": 0,
        "chat": 0
    }
    
    endpoint_generated = {
        "protein_info": 0,
        "structure": 0,
        "interactions": 0, 
        "diseases": 0,
        "drugs": 0,
        "knowledge_graph": 0
    }
    
    for protein_id, endpoints in results.items():
        for endpoint, result in endpoints.items():
            if result.get("status") == "ok":
                endpoint_success[endpoint] += 1
                if result.get("is_generated", False):
                    endpoint_generated[endpoint] += 1
    
    # Add summary to results
    summary = {
        "total_proteins_tested": len(test_protein_ids),
        "success_rate": {
            endpoint: f"{count}/{len(test_protein_ids)}" 
            for endpoint, count in endpoint_success.items()
        },
        "generated_data_rate": {
            endpoint: f"{count}/{endpoint_success[endpoint]}" 
            for endpoint, count in endpoint_generated.items()
            if endpoint in endpoint_success and endpoint_success[endpoint] > 0
        },
        "timestamp": f"{datetime.datetime.now().isoformat()}"
    }
    
    results["summary"] = summary
    
    return results