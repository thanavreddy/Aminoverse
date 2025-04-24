from fastapi import APIRouter, HTTPException
from app.db.neo4j import Neo4jConnection
from app.cache.redis_client import RedisClient
from app.services.llm_service import LLMService
import requests
from app.core.config import settings
import httpx
import asyncio
import logging
from typing import Dict, Any

# Set up logger
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/")
async def check_all_services() -> Dict[str, Any]:
    """
    Check the status of all backend services.
    
    Returns:
        Dict: Status of each service (ok/error)
    """
    results = {
        "server": "ok",
        "neo4j": "checking",
        "redis": "checking",
        "llm": "checking",
        "api_integrations": "checking"
    }
    
    # Check Neo4j connection
    try:
        logger.info(f"Testing Neo4j connection to {settings.NEO4J_URI}")
        neo4j = Neo4jConnection()
        is_connected = await neo4j.test_connection()
        results["neo4j"] = "ok" if is_connected else "error" 
        if not is_connected:
            results["neo4j_error"] = "Connection established but test query failed"
    except Exception as e:
        logger.error(f"Neo4j connection error: {str(e)}")
        results["neo4j"] = "error"
        results["neo4j_error"] = str(e)
    
    # Check Redis connection
    try:
        logger.info(f"Testing Redis connection to {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        redis = RedisClient()
        test_key = "test_connection"
        await redis.set(test_key, "working")
        value = await redis.get(test_key)
        if value == "working":
            results["redis"] = "ok"
        else:
            results["redis"] = "error"
            results["redis_error"] = f"Data mismatch: expected 'working', got '{value}'"
    except Exception as e:
        logger.error(f"Redis connection error: {str(e)}")
        results["redis"] = "error"
        results["redis_error"] = str(e)
    
    # Check LLM API
    try:
        logger.info("Testing LLM API connection")
        redis = RedisClient()  # Create Redis client for LLM service
        llm = LLMService(redis_client=redis)  # Pass the redis client to LLM service
        response = await llm.test_connection()
        results["llm"] = "ok" if response else "error"
        if not response:
            results["llm_error"] = "API connection test returned False"
    except Exception as e:
        logger.error(f"LLM API error: {str(e)}")
        results["llm"] = "error"
        results["llm_error"] = str(e)
    
    # Check external APIs
    try:
        # Test UniProt API
        logger.info(f"Testing UniProt API: {settings.UNIPROT_API_URL}")
        uniprot_response = await asyncio.to_thread(
            lambda: requests.get(f"{settings.UNIPROT_API_URL}/search?query=id:P04637", timeout=5)
        )
        uniprot_status = uniprot_response.status_code == 200
        
        # Test PDB API
        logger.info(f"Testing PDB API: {settings.PDB_API_URL}")
        pdb_response = await asyncio.to_thread(
            lambda: requests.get(f"{settings.PDB_API_URL}/pdb/1TUP", timeout=5)
        )
        pdb_status = pdb_response.status_code == 200
        
        # Combine results
        results["api_integrations"] = "ok" if (uniprot_status and pdb_status) else "error"
        results["api_details"] = {
            "uniprot": "ok" if uniprot_status else "error",
            "pdb": "ok" if pdb_status else "error",
            "uniprot_code": uniprot_response.status_code,
            "pdb_code": pdb_response.status_code
        }
    except Exception as e:
        logger.error(f"API check error: {str(e)}")
        results["api_integrations"] = "error"
        results["api_error"] = str(e)
    
    logger.info(f"Service status check results: {results}")
    return results

@router.get("/neo4j")
async def check_neo4j() -> Dict[str, Any]:
    """Check Neo4j database connectivity"""
    try:
        neo4j = Neo4jConnection()
        is_connected = await neo4j.test_connection()
        
        if is_connected:
            return {"status": "ok", "message": "Connected to Neo4j successfully"}
        else:
            return {"status": "error", "message": "Failed to connect to Neo4j"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Neo4j connection error: {str(e)}")

@router.get("/redis")
async def check_redis() -> Dict[str, Any]:
    """Check Redis cache connectivity"""
    try:
        redis = RedisClient()
        test_key = "test_connection"
        await redis.set(test_key, "working")
        value = await redis.get(test_key)
        
        if value == "working":
            return {"status": "ok", "message": "Connected to Redis successfully"}
        else:
            return {"status": "error", "message": "Redis data mismatch"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis connection error: {str(e)}")

@router.get("/llm")
async def check_llm() -> Dict[str, Any]:
    """Check LLM API connectivity"""
    try:
        redis = RedisClient()  # Create Redis client for LLM service
        llm = LLMService(redis_client=redis)  # Pass the redis client
        response = await llm.test_connection()
        
        if response:
            return {"status": "ok", "message": "LLM API is working correctly"}
        else:
            return {"status": "error", "message": "LLM API test failed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM API error: {str(e)}")

@router.get("/apis")
async def check_apis() -> Dict[str, Any]:
    """Check external API integrations"""
    results = {}
    
    try:
        # Test UniProt API
        uniprot_response = await asyncio.to_thread(
            lambda: requests.get(f"{settings.UNIPROT_API_URL}/search?query=id:P04637")
        )
        results["uniprot"] = {
            "status": "ok" if uniprot_response.status_code == 200 else "error",
            "status_code": uniprot_response.status_code
        }
        
        # Test PDB API
        pdb_response = await asyncio.to_thread(
            lambda: requests.get(f"{settings.PDB_API_URL}/pdb/1TUP")
        )
        results["pdb"] = {
            "status": "ok" if pdb_response.status_code == 200 else "error",
            "status_code": pdb_response.status_code
        }
        
        # Test STRING-DB API
        string_response = await asyncio.to_thread(
            lambda: requests.get(f"{settings.STRING_DB_API_URL}/json/interaction_partners?identifiers=TP53&species=9606&limit=10")
        )
        results["string_db"] = {
            "status": "ok" if string_response.status_code == 200 else "error",
            "status_code": string_response.status_code
        }
        
        return {
            "status": "ok" if all(api["status"] == "ok" for api in results.values()) else "partial",
            "services": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API check error: {str(e)}")