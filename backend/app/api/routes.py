from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any, List, Optional
import logging
import uuid

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
    protein_service: ProteinService = Depends(get_protein_service)
):
    """
    Get detailed information about a specific protein.
    """
    try:
        protein_data = await protein_service.get_protein_info(protein_id)
        return ProteinResponse(**protein_data)
    except Exception as e:
        logger.exception(f"Error fetching protein {protein_id}: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail=f"Protein not found: {str(e)}"
        )

@router.get("/protein/{protein_id}/structure")
async def get_protein_structure(
    protein_id: str,
    protein_service: ProteinService = Depends(get_protein_service)
):
    """
    Get structure information for a protein.
    """
    try:
        structure_data = await protein_service.get_protein_structure(protein_id)
        return structure_data
    except Exception as e:
        logger.exception(f"Error fetching structure for {protein_id}: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail=f"Structure not found: {str(e)}"
        )

@router.get("/protein/{protein_id}/interactions")
async def get_protein_interactions(
    protein_id: str,
    protein_service: ProteinService = Depends(get_protein_service)
):
    """
    Get protein-protein interactions for a specific protein.
    """
    try:
        interactions = await protein_service.get_protein_interactions(protein_id)
        return interactions
    except Exception as e:
        logger.exception(f"Error fetching interactions for {protein_id}: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail=f"Interactions not found: {str(e)}"
        )

@router.get("/protein/{protein_id}/diseases")
async def get_protein_diseases(
    protein_id: str,
    protein_service: ProteinService = Depends(get_protein_service)
):
    """
    Get diseases associated with a specific protein.
    """
    try:
        diseases = await protein_service.get_disease_associations(protein_id)
        return diseases
    except Exception as e:
        logger.exception(f"Error fetching diseases for {protein_id}: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail=f"Disease associations not found: {str(e)}"
        )

@router.get("/protein/{protein_id}/drugs")
async def get_protein_drugs(
    protein_id: str,
    protein_service: ProteinService = Depends(get_protein_service)
):
    """
    Get drugs that target a specific protein.
    """
    try:
        drugs = await protein_service.get_drug_interactions(protein_id)
        return drugs
    except Exception as e:
        logger.exception(f"Error fetching drugs for {protein_id}: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail=f"Drug interactions not found: {str(e)}"
        )

@router.get("/knowledge-graph/{entity_id}")
async def get_knowledge_graph(
    entity_id: str,
    entity_type: str = Query("Protein", description="Entity type (Protein, Disease, Drug, etc.)"),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """
    Get knowledge graph data centered around a specific entity.
    """
    try:
        graph_data = await kg_service.get_entity_graph(entity_id, entity_type)
        return graph_data
    except Exception as e:
        logger.exception(f"Error fetching knowledge graph for {entity_id}: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail=f"Knowledge graph not found: {str(e)}"
        )