from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import asyncio
import os
import pathlib

from app.core.config import settings
from app.api.routes import router as api_router
from app.api.status_routes import check_all_services
from app.db.neo4j import Neo4jConnection, Neo4jDatabase
from app.cache.redis_client import RedisClient
from app.services.llm_service import LLMService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Set up CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API routes
app.include_router(api_router, prefix=settings.API_PREFIX)

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint for health check"""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "docs": "/api/docs"
    }

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )

async def initialize_database():
    """Initialize the Neo4j database with sample data if it's empty."""
    try:
        db = Neo4jDatabase()
        
        # Check if the database is empty
        query = "MATCH (n) RETURN count(n) as count"
        result = await db.execute_query(query)
        
        if not result or result[0].get('count', 0) <= 2:
            # Database is empty or has only the default nodes, load sample data
            logger.info("Knowledge graph is empty. Loading sample data...")
            
            # Get the path to the seed data file
            base_dir = pathlib.Path(__file__).parent.absolute()
            seed_file = os.path.join(base_dir, "db", "schema", "seed_kg_data.cypher")
            
            if os.path.exists(seed_file):
                logger.info(f"Loading sample data from {seed_file}")
                result = await db.import_graph_data(seed_file)
                
                if result:
                    logger.info("✅ Knowledge graph initialized successfully with sample data!")
                else:
                    logger.error("Failed to initialize knowledge graph with sample data.")
            else:
                logger.error(f"Seed file not found at {seed_file}")
        else:
            logger.info(f"Knowledge graph already contains {result[0].get('count')} nodes. Skipping initialization.")
            
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
    finally:
        if 'db' in locals():
            await db.close()

# Add an event handler for application startup
@app.on_event("startup")
async def startup_event():
    """Check all services on startup and log their status"""
    logger.info("🚀 AminoVerse API server starting...")
    logger.info(f"📌 Neo4j Database URI: {settings.NEO4J_URI}")
    logger.info(f"📌 Redis Host: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    logger.info(f"📌 External APIs: UniProt, PDB, STRING-DB")
    
    # Show a message while checking services
    logger.info("⏳ Checking service connections...")
    
    try:
        # Get the status of all services
        statuses = await check_all_services()
        
        # Create a nice formatted log output
        logger.info("==== SERVICE STATUS ====")
        
        # Server status
        logger.info(f"🖥️  Server: {'✅ OK' if statuses.get('server') == 'ok' else '❌ ERROR'}")
        
        # Neo4j status
        neo4j_status = statuses.get('neo4j')
        if neo4j_status == 'ok':
            logger.info("📊 Neo4j Aura: ✅ Connected")
            
            # Initialize the database if Neo4j is available
            await initialize_database()
        else:
            error_msg = statuses.get('neo4j_error', 'Unknown error')
            logger.error(f"📊 Neo4j Aura: ❌ Connection Error - {error_msg}")
        
        # Redis status
        redis_status = statuses.get('redis')
        if redis_status == 'ok':
            logger.info("🗄️  Redis Cloud: ✅ Connected")
        else:
            error_msg = statuses.get('redis_error', 'Unknown error')
            logger.error(f"🗄️  Redis Cloud: ❌ Connection Error - {error_msg}")
        
        # LLM status
        llm_status = statuses.get('llm')
        if llm_status == 'ok':
            logger.info("🧠 Gemini LLM API: ✅ Connected")
        else:
            error_msg = statuses.get('llm_error', 'Unknown error')
            logger.error(f"🧠 Gemini LLM API: ❌ Connection Error - {error_msg}")
        
        # API integrations status
        api_status = statuses.get('api_integrations')
        if api_status == 'ok':
            logger.info("🔌 External APIs: ✅ All Connected")
        else:
            api_details = statuses.get('api_details', {})
            logger.warning(f"🔌 External APIs: ⚠️ Some services may be unavailable")
            
            if api_details:
                for api, status in api_details.items():
                    if isinstance(status, dict):
                        api_ok = status.get('status') == 'ok'
                        logger.info(f"  - {api}: {'✅ OK' if api_ok else '❌ ERROR'}")
        
        # Overall status
        all_ok = all(status == 'ok' for status in [
            statuses.get('neo4j'), 
            statuses.get('redis'), 
            statuses.get('llm'), 
            statuses.get('api_integrations')
        ])
        
        if all_ok:
            logger.info("✅ All services are connected and working properly!")
        else:
            logger.warning("⚠️ Some services have connection issues. Check logs above for details.")
            
    except Exception as e:
        logger.error(f"Error checking services: {str(e)}")
        logger.warning("⚠️ Could not verify service connections. Application may not function correctly.")
    
    logger.info("=======================")
    logger.info("🌐 API is now running at http://localhost:8000")
    logger.info("📚 API documentation available at http://localhost:8000/api/docs")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)