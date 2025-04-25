// API Service for connecting to the backend
import axios from 'axios';

// Base URL for API requests (different for development and production)
const apiBaseUrl = process.env.NODE_ENV === 'production' 
  ? 'https://aminoverse-api.example.com'  // Replace with actual production URL when deployed
  : 'http://localhost:8000'; // Local development backend URL

// Create axios instance with common configuration
const apiClient = axios.create({
  baseURL: apiBaseUrl,
  timeout: 30000,  // 30 seconds timeout
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  }
});

// Add request interceptor for logging
apiClient.interceptors.request.use(config => {
  console.log(`API Request to ${config.url}`);
  return config;
});

// Add response interceptor for logging
apiClient.interceptors.response.use(
  response => {
    console.log(`API Response from ${response.config.url} [${response.status}]`);
    return response;
  },
  error => {
    console.error(`API Error: ${error.message}`);
    return Promise.reject(error);
  }
);

// API Service functions
const apiService = {
  // Check backend connectivity
  async checkHealth() {
    try {
      const response = await apiClient.get('/');
      return response.data;
    } catch (error) {
      console.error('Error checking API health:', error);
      throw error;
    }
  },
  
  // Send a chat message and get a response
  async sendChatMessage(message, sessionId = null) {
    try {
      const response = await apiClient.post('/api/chat', { 
        message,
        session_id: sessionId || null
      });
      return response.data;
    } catch (error) {
      console.error('Error sending chat message:', error);
      throw error;
    }
  },
  
  // Get protein information
  async getProtein(proteinId) {
    try {
      console.log(`Fetching protein data for ${proteinId}...`);
      const response = await apiClient.get(`/api/protein/${proteinId}`);
      console.log(`Protein data received:`, response.data);
      return response.data;
    } catch (error) {
      console.error(`Error fetching protein ${proteinId}:`, error);
      throw error;
    }
  },
  
  // Get protein structure data for 3D visualization
  async getProteinStructure(proteinId) {
    try {
      console.log(`Fetching structure data for ${proteinId}...`);
      const response = await apiClient.get(`/api/protein/${proteinId}/structure`);
      console.log(`Structure data received:`, response.data);
      return response.data;
    } catch (error) {
      console.error(`Error fetching protein structure for ${proteinId}:`, error);
      throw error;
    }
  },
  
  // Get protein diseases 
  async getProteinDiseases(proteinId) {
    try {
      console.log(`Fetching disease data for ${proteinId}...`);
      const response = await apiClient.get(`/api/protein/${proteinId}/diseases`);
      console.log(`Disease data received:`, response.data);
      return response.data;
    } catch (error) {
      console.error(`Error fetching protein diseases for ${proteinId}:`, error);
      throw error;
    }
  },
  
  // Get protein interaction network data
  async getProteinInteractions(proteinId) {
    try {
      console.log(`Fetching interaction data for ${proteinId}...`);
      const response = await apiClient.get(`/api/protein/${proteinId}/interactions`);
      console.log(`Interaction data received:`, response.data);
      return response.data;
    } catch (error) {
      console.error(`Error fetching protein interactions for ${proteinId}:`, error);
      throw error;
    }
  },
  
  // Get drugs that target a protein
  async getProteinDrugs(proteinId) {
    try {
      console.log(`Fetching drugs for ${proteinId}...`);
      const response = await apiClient.get(`/api/protein/${proteinId}/drugs`);
      console.log(`Drug data received:`, response.data);
      return response.data;
    } catch (error) {
      console.error(`Error fetching drugs for ${proteinId}:`, error);
      throw error;
    }
  },

  // Get knowledge graph data for visualization
  async getKnowledgeGraph(entityId, entityType = 'Protein') {
    try {
      console.log(`Fetching knowledge graph for ${entityType}:${entityId}...`);
      const response = await apiClient.get(`/api/knowledge-graph/${entityId}`, {
        params: { entity_type: entityType }
      });
      console.log(`Knowledge graph data received:`, response.data);
      return response.data;
    } catch (error) {
      console.error(`Error fetching knowledge graph for ${entityId}:`, error);
      throw error;
    }
  }
};

export default apiService;