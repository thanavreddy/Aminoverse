# AminoVerse

![React](https://img.shields.io/badge/React-19+-61DAFB?style=flat&logo=react&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.95+-009688?style=flat&logo=fastapi&logoColor=white)
![Neo4j](https://img.shields.io/badge/Neo4j-5.8+-008CC1?style=flat&logo=neo4j&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-4.5+-DC382D?style=flat&logo=redis&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3+-06B6D4?style=flat&logo=tailwindcss&logoColor=white)

AminoVerse is an advanced protein research platform that combines AI-powered natural language processing with comprehensive protein databases and interactive visualizations. The platform enables researchers to explore protein structures, analyze relationships through knowledge graphs, and obtain insights through intelligent chat interactions.

## Overview

AminoVerse consists of two main components:

- **Frontend (React)**: Interactive web application with modern UI/UX for protein research
- **Backend (FastAPI)**: High-performance REST API with AI integration and database management

### Key Capabilities

- **AI-Powered Research Assistant**: Natural language protein queries with Google Gemini integration
- **3D Structure Visualization**: Interactive protein structure viewers with PDB and AlphaFold integration
- **Knowledge Graph Exploration**: Network visualization of protein relationships and pathways
- **Multi-Database Integration**: Seamless access to UniProt, PDB, STRING-DB, and ChEMBL databases
- **Real-Time Caching**: High-performance Redis caching for optimal response times
- **Service Monitoring**: Comprehensive health checks and status monitoring

## Architecture

```
AminoVerse/
├── aminoverse/                 # React Frontend Application
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── services/          # API integration services
│   │   └── ...
│   ├── package.json
│   └── README.md
├── backend/                    # FastAPI Backend Server
│   ├── app/
│   │   ├── api/               # API routes
│   │   ├── services/          # Business logic
│   │   ├── db/                # Database connections
│   │   └── ...
│   ├── requirements.txt
│   └── README.md
├── start-app.bat              # Windows batch script
├── start-app.ps1              # PowerShell script
└── README.md                  # This file
```

## Technology Stack

### Frontend Technologies
- **React 19+**: Modern frontend framework with latest features
- **Tailwind CSS**: Utility-first CSS framework with scientific theme
- **Chakra UI**: Component library for enhanced UI elements
- **Cytoscape.js**: Network graph visualization
- **MolStar**: Advanced molecular structure visualization
- **Axios**: HTTP client for API communication

### Backend Technologies
- **FastAPI**: Modern Python web framework for building APIs
- **Neo4j**: Graph database for knowledge graph management
- **Redis**: In-memory caching and session management
- **Google Gemini**: AI language model for intelligent responses
- **Uvicorn**: ASGI server for production deployment

### External Integrations
- **UniProt API**: Protein sequence and functional information
- **RCSB PDB API**: Protein structure data
- **STRING-DB API**: Protein-protein interaction networks
- **ChEMBL API**: Bioactivity database integration

## Quick Start

### Prerequisites

Before running AminoVerse, ensure you have:

- **Node.js**: Version 18.0 or higher
- **Python**: Version 3.8 or higher
- **Neo4j**: Database instance (local or cloud)
- **Redis**: Cache server (local or cloud)
- **Google Gemini API Key**: For AI functionality

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/pradeepmajji853/aminoverse.git
   cd aminoverse
   ```

2. **Backend Setup**
   ```bash
   cd backend
   
   # Create virtual environment
   python -m venv venv
   
   # Activate virtual environment (Windows)
   venv\Scripts\activate
   # For Linux/macOS: source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Create .env file with your configuration
   # See backend/README.md for detailed configuration
   ```

3. **Frontend Setup**
   ```bash
   cd ../aminoverse
   
   # Install dependencies
   npm install
   ```

4. **Database Setup**
   - Set up Neo4j database (local or Neo4j Aura Cloud)
   - Set up Redis server (local or Redis Cloud)
   - Configure connection details in backend/.env file

### Running the Application

#### Option 1: Quick Start Scripts (Recommended)

**For Windows (Batch):**
```bash
# Double-click or run from command prompt
start-app.bat
```

**For Windows (PowerShell):**
```powershell
# Run from PowerShell
./start-app.ps1
```

#### Option 2: Manual Start

**Terminal 1 - Backend:**
```bash
cd backend
python run.py
```

**Terminal 2 - Frontend:**
```bash
cd aminoverse
npm start
```

### Access the Application

- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **API Documentation**: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)

## Features

### Interactive Chat Interface
- Natural language protein queries
- Context-aware responses using Google Gemini
- Follow-up suggestions for deeper research
- Session-based conversation history

### Protein Visualization
- **3D Structure Viewer**: Embedded PDB and AlphaFold structure viewers
- **Interactive Knowledge Graphs**: Cytoscape.js-powered network visualizations
- **Protein Information Panel**: Comprehensive protein data display
- **Real-time Structure Loading**: Dynamic structure data retrieval

### Data Integration
- **UniProt Integration**: Protein sequences, functions, and annotations
- **PDB Integration**: 3D structure data and visualization
- **STRING-DB Integration**: Protein-protein interaction networks
- **ChEMBL Integration**: Bioactivity and drug interaction data

### Performance Features
- **Redis Caching**: Sub-second response times for cached data
- **Asynchronous Processing**: High-performance concurrent API calls
- **Smart Data Aggregation**: Intelligent merging of data from multiple sources
- **Error Recovery**: Robust error handling with graceful fallbacks

## Configuration

### Environment Variables

Create a `.env` file in the `backend/` directory:

```env
# API Configuration
DEBUG=True
HOST=0.0.0.0
PORT=8000

# Database Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password

# AI Configuration
GEMINI_API_KEY=your_gemini_api_key

# External APIs (optional - defaults provided)
UNIPROT_API_URL=https://rest.uniprot.org/uniprotkb
PDB_API_URL=https://data.rcsb.org
STRING_DB_API_URL=https://string-db.org/api
CHEMBL_API_URL=https://www.ebi.ac.uk/chembl/api/data
```

### Service Setup

1. **Neo4j Setup**
   - Install Neo4j Desktop or use Neo4j Aura Cloud
   - Create a database with the configured credentials
   - The application will automatically populate sample data on first run

2. **Redis Setup**
   - Install Redis locally or use Redis Cloud
   - Configure connection details in the .env file
   - Ensure Redis is running and accessible

3. **Google Gemini API**
   - Obtain API key from Google AI Studio
   - Add the key to your .env file
   - Ensure sufficient API quota for your usage

## Development

### Project Structure

```
AminoVerse/
├── aminoverse/                 # Frontend React Application
│   ├── public/                # Static assets
│   ├── src/
│   │   ├── components/        # React components
│   │   │   ├── AminoVerseUI.js    # Main UI component
│   │   │   └── ErrorBoundary.js   # Error handling
│   │   ├── services/          # API integration
│   │   │   ├── api.js         # Backend API client
│   │   │   └── statusChecker.js   # Service monitoring
│   │   ├── App.js             # Root component
│   │   ├── index.js           # Entry point
│   │   └── theme.js           # UI theme configuration
│   ├── tailwind.config.js     # Tailwind CSS config
│   └── package.json           # Frontend dependencies
├── backend/                    # Backend FastAPI Application
│   ├── app/
│   │   ├── api/               # API route handlers
│   │   │   ├── routes.py      # Main API routes
│   │   │   └── status_routes.py   # Health check routes
│   │   ├── core/              # Core configuration
│   │   │   └── config.py      # Application settings
│   │   ├── db/                # Database connections
│   │   │   ├── neo4j.py       # Neo4j client
│   │   │   └── schema/        # Database schema
│   │   ├── cache/             # Caching layer
│   │   │   └── redis_client.py    # Redis client
│   │   ├── services/          # Business logic
│   │   │   ├── protein_service.py     # Protein data
│   │   │   ├── llm_service.py         # AI integration
│   │   │   └── knowledge_graph_service.py # Graph ops
│   │   ├── schemas/           # Data models
│   │   │   └── protein.py     # Pydantic models
│   │   └── main.py            # FastAPI app entry
│   ├── requirements.txt       # Python dependencies
│   └── run.py                 # Development server
├── start-app.bat              # Windows batch launcher
├── start-app.ps1              # PowerShell launcher
└── README.md                  # Main documentation
```

### Adding New Features

1. **Frontend Features**
   - Add new components in `aminoverse/src/components/`
   - Extend API services in `aminoverse/src/services/`
   - Update UI themes in `aminoverse/src/theme.js`

2. **Backend Features**
   - Add new services in `backend/app/services/`
   - Define new API routes in `backend/app/api/`
   - Create data models in `backend/app/schemas/`

### Testing

**Frontend Testing:**
```bash
cd aminoverse
npm test
```

**Backend Testing:**
```bash
cd backend
pip install pytest pytest-asyncio
pytest tests/
```

## API Documentation

The backend provides comprehensive API documentation:

- **Interactive Docs**: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)
- **ReDoc**: [http://localhost:8000/api/redoc](http://localhost:8000/api/redoc)

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Natural language protein queries |
| GET | `/api/protein/{id}` | Retrieve protein information |
| GET | `/api/protein/{id}/structure` | Get protein structure data |
| GET | `/api/knowledge-graph/{id}` | Entity knowledge graph |
| GET | `/api/status` | Service health status |

## Deployment

### Development Deployment
1. Use the provided start scripts for local development
2. Both frontend and backend run with hot-reload enabled
3. Service status monitoring available in the UI

### Production Deployment

**Frontend (React):**
```bash
cd aminoverse
npm run build
# Deploy build/ directory to your web server
```

**Backend (FastAPI):**
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
# Or use Gunicorn for production
```

### Docker Deployment

**Backend Dockerfile:**
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Frontend Dockerfile:**
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY aminoverse/package*.json ./
RUN npm install
COPY aminoverse/ .
RUN npm run build
FROM nginx:alpine
COPY --from=0 /app/build /usr/share/nginx/html
```

## Troubleshooting

### Common Issues

1. **Backend won't start**
   - Check if Neo4j and Redis are running
   - Verify .env file configuration
   - Ensure Python dependencies are installed

2. **Frontend connection errors**
   - Verify backend is running on port 8000
   - Check CORS configuration
   - Review browser console for errors

3. **Database connection failures**
   - Verify Neo4j and Redis connection strings
   - Check firewall and network settings
   - Ensure databases are accessible

4. **API rate limiting**
   - Check Google Gemini API quota
   - Verify API key configuration
   - Monitor external API usage

### Performance Optimization

- **Database Indexing**: Ensure proper Neo4j indexes
- **Cache Configuration**: Optimize Redis memory settings
- **Bundle Optimization**: Use production React builds
- **API Optimization**: Implement request batching where applicable

## Contributing

We welcome contributions to AminoVerse! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Guidelines

- Follow existing code style and conventions
- Add comprehensive tests for new features
- Update documentation for any API changes
- Ensure all tests pass before submitting PR

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **UniProt** for providing comprehensive protein data
- **RCSB PDB** for protein structure information
- **STRING-DB** for protein interaction networks
- **Google** for Gemini AI capabilities
- **Neo4j** and **Redis** for database technologies
- **FastAPI** and **React** communities for excellent frameworks

## Support

For support and questions:

- **Issues**: Create an issue on GitHub
- **Documentation**: Check individual component READMEs
- **API Docs**: Visit [http://localhost:8000/api/docs](http://localhost:8000/api/docs) when running

---

**AminoVerse** - Advancing protein research through AI-powered insights and interactive visualizations.
