# AminoVerse Backend API

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.95+-009688?style=flat&logo=fastapi&logoColor=white)
![Neo4j](https://img.shields.io/badge/Neo4j-5.8+-008CC1?style=flat&logo=neo4j&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-4.5+-DC382D?style=flat&logo=redis&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

AminoVerse Backend is a high-performance FastAPI-based REST API that powers the AminoVerse protein research platform. It provides comprehensive protein information retrieval, knowledge graph management, and AI-powered chat capabilities for biological research.

## Features

### Core API Functionality
- **RESTful API**: FastAPI-based REST API with automatic OpenAPI documentation
- **Chat Interface**: Natural language processing for protein queries using LLM integration
- **Protein Information Retrieval**: Comprehensive data from UniProt, PDB, and other databases
- **Knowledge Graph Management**: Neo4j-powered protein relationship networks
- **Caching Layer**: Redis-based high-performance caching for optimal response times

### Database Integration
- **Neo4j Knowledge Graph**: Advanced graph database for protein relationships and pathways
- **Redis Caching**: In-memory caching for frequently accessed protein data
- **Multi-source Data Aggregation**: Integration with UniProt, PDB, STRING-DB, and ChEMBL APIs

### AI and Machine Learning
- **LLM Integration**: Google Gemini API for intelligent protein analysis
- **Natural Language Processing**: Context-aware protein research assistance
- **Smart Query Processing**: Automatic protein ID recognition and data enrichment

### Service Architecture
- **Microservices Design**: Modular service architecture for scalability
- **Health Monitoring**: Comprehensive service status checking and monitoring
- **Error Handling**: Robust error management with detailed logging
- **CORS Support**: Cross-Origin Resource Sharing for frontend integration

## Technology Stack

### Backend Framework
- **FastAPI 0.95+**: Modern, fast web framework for building APIs
- **Uvicorn**: ASGI server for production deployment
- **Pydantic**: Data validation using Python type annotations

### Databases
- **Neo4j 5.8+**: Graph database for knowledge graph management
- **Redis 4.5+**: In-memory data store for caching and session management

### External Integrations
- **Google Gemini API**: Advanced language model for AI-powered responses
- **UniProt API**: Protein sequence and functional information
- **RCSB PDB API**: Protein structure data
- **STRING-DB API**: Protein-protein interaction networks
- **ChEMBL API**: Bioactivity database integration

### Development Tools
- **Python 3.8+**: Core programming language
- **Asyncio**: Asynchronous programming for high performance
- **HTTPX**: Modern HTTP client for external API calls
- **Python-dotenv**: Environment variable management

## Prerequisites

Before running the backend, ensure you have:

- **Python**: Version 3.8 or higher
- **pip**: Python package manager
- **Neo4j**: Database instance (local or cloud)
- **Redis**: Cache server (local or cloud)
- **API Keys**: Google Gemini API key for LLM functionality

## Installation

### 1. Clone and Navigate
```bash
git clone https://github.com/pradeepmajji853/aminoverse.git
cd aminoverse/backend
```

### 2. Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
Create a `.env` file in the backend directory:

```env
# API Configuration
DEBUG=True
HOST=0.0.0.0
PORT=8000

# Neo4j Database Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password
REDIS_USERNAME=

# LLM Configuration
GEMINI_API_KEY=your_gemini_api_key
GEMINI_API_URL=https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent

# External API URLs (optional - defaults provided)
UNIPROT_API_URL=https://rest.uniprot.org/uniprotkb
PDB_API_URL=https://data.rcsb.org
STRING_DB_API_URL=https://string-db.org/api
CHEMBL_API_URL=https://www.ebi.ac.uk/chembl/api/data
```

## Database Setup

### Neo4j Setup
1. **Install Neo4j Desktop** or use **Neo4j Aura Cloud**
2. **Create a new database** with the credentials from your `.env` file
3. **Start the database** and ensure it's accessible at the configured URI

### Redis Setup
1. **Install Redis** locally or use **Redis Cloud**
2. **Start Redis server** with the configured port and password
3. **Test connection** using redis-cli or a Redis client

## Running the Application

### Development Mode

1. **Start the development server**
   ```bash
   python run.py
   ```

2. **Verify the server is running**
   - API will be available at: [http://localhost:8000](http://localhost:8000)
   - Interactive API docs: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)
   - ReDoc documentation: [http://localhost:8000/api/redoc](http://localhost:8000/api/redoc)

### Production Mode

1. **Using Uvicorn directly**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

2. **Using Gunicorn (Linux/macOS)**
   ```bash
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   ```

### Database Initialization

The application automatically initializes the Neo4j knowledge graph with sample data on first startup. Sample data includes:

- **Protein nodes**: TP53, BRCA1, MDM2, EGFR, KRAS
- **Disease associations**: Cancer-related conditions
- **Pathways**: Cell cycle, DNA repair, apoptosis
- **Relationships**: Protein-protein interactions, disease associations

## API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root health check endpoint |
| GET | `/api/docs` | Interactive API documentation |
| GET | `/api/status` | Comprehensive service status |

### Chat and Query Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Natural language protein queries |
| GET | `/api/protein/{protein_id}` | Retrieve specific protein information |
| GET | `/api/protein/{protein_id}/structure` | Get protein structure data |
| GET | `/api/protein/{protein_id}/interactions` | Protein interaction networks |

### Knowledge Graph Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/knowledge-graph/{entity_id}` | Entity-centered knowledge graph |
| GET | `/api/knowledge-graph/search` | Search knowledge graph |
| POST | `/api/knowledge-graph/query` | Custom Cypher queries |

### Service Status Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status/health` | Overall system health |
| GET | `/api/status/neo4j` | Neo4j database status |
| GET | `/api/status/redis` | Redis cache status |
| GET | `/api/status/llm` | LLM service status |

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── api/                    # API route handlers
│   │   ├── __init__.py
│   │   ├── routes.py           # Main API routes
│   │   └── status_routes.py    # Health check routes
│   ├── core/                   # Core configuration
│   │   ├── __init__.py
│   │   └── config.py           # Application settings
│   ├── db/                     # Database connections
│   │   ├── __init__.py
│   │   ├── neo4j.py           # Neo4j database client
│   │   └── schema/            # Database schema and seed data
│   │       ├── init_graph.cypher
│   │       └── seed_kg_data.cypher
│   ├── cache/                  # Caching layer
│   │   ├── __init__.py
│   │   └── redis_client.py     # Redis client wrapper
│   ├── services/               # Business logic services
│   │   ├── protein_service.py      # Protein data retrieval
│   │   ├── llm_service.py          # LLM integration
│   │   └── knowledge_graph_service.py  # Graph operations
│   └── schemas/                # Pydantic data models
│       ├── __init__.py
│       └── protein.py          # API request/response models
├── requirements.txt            # Python dependencies
├── run.py                     # Development server launcher
└── .env                       # Environment variables (create this)
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DEBUG` | Enable debug mode | `False` | No |
| `HOST` | Server host address | `0.0.0.0` | No |
| `PORT` | Server port | `8000` | No |
| `NEO4J_URI` | Neo4j database URI | `bolt://localhost:7687` | Yes |
| `NEO4J_USER` | Neo4j username | `neo4j` | Yes |
| `NEO4J_PASSWORD` | Neo4j password | - | Yes |
| `REDIS_HOST` | Redis server host | `localhost` | Yes |
| `REDIS_PORT` | Redis server port | `6379` | No |
| `REDIS_PASSWORD` | Redis password | - | No |
| `GEMINI_API_KEY` | Google Gemini API key | - | Yes |

### Service Dependencies

1. **Neo4j Database**
   - Version 5.8 or higher
   - APOC procedures recommended
   - Minimum 2GB RAM allocation

2. **Redis Cache**
   - Version 4.5 or higher
   - Minimum 512MB memory allocation
   - Persistence enabled for production

3. **External APIs**
   - Google Gemini API access
   - Internet connectivity for external data sources

## Development

### Adding New Features

1. **Service Layer**: Add new services in `app/services/`
2. **API Routes**: Define new endpoints in `app/api/`
3. **Data Models**: Create Pydantic schemas in `app/schemas/`
4. **Database Operations**: Extend database clients in `app/db/`

### Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/

# Run with coverage
pytest --cov=app tests/
```

### Code Quality

```bash
# Install development tools
pip install black isort flake8

# Format code
black app/
isort app/

# Check code quality
flake8 app/
```

## Monitoring and Logging

### Health Checks
- **Service Status**: Real-time monitoring of all connected services
- **Database Connectivity**: Automatic Neo4j and Redis connection testing
- **External API Status**: Monitoring of third-party service availability

### Logging
- **Structured Logging**: JSON-formatted logs for production
- **Log Levels**: Configurable logging levels (DEBUG, INFO, WARNING, ERROR)
- **Request Tracking**: Comprehensive API request and response logging

## Troubleshooting

### Common Issues

1. **Neo4j Connection Failed**
   ```bash
   # Check Neo4j status
   neo4j status
   
   # Verify credentials and URI in .env file
   # Ensure Neo4j is running and accessible
   ```

2. **Redis Connection Error**
   ```bash
   # Check Redis status
   redis-cli ping
   
   # Verify Redis configuration
   # Check firewall and network settings
   ```

3. **LLM API Errors**
   ```bash
   # Verify API key in .env file
   # Check API quota and billing status
   # Test API connectivity
   ```

4. **Port Already in Use**
   ```bash
   # Windows
   netstat -ano | findstr :8000
   taskkill /PID <PID> /F
   
   # Linux/macOS
   lsof -ti:8000 | xargs kill -9
   ```

### Performance Optimization

- **Database Indexing**: Ensure proper Neo4j indexes for frequently queried properties
- **Cache Configuration**: Optimize Redis memory allocation and eviction policies
- **Connection Pooling**: Configure appropriate connection pool sizes
- **Request Timeout**: Set reasonable timeout values for external API calls

## Deployment

### Docker Deployment
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Considerations
- Use environment-specific configuration files
- Implement proper logging and monitoring
- Set up SSL/TLS certificates
- Configure reverse proxy (Nginx/Apache)
- Implement rate limiting and security headers
