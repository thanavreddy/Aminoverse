import axios from 'axios';

// API base URL - adjust this based on your environment
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

// Create axios instance with default configs
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// API service for AminoVerse
const apiService = {
  // Chat endpoint to process natural language queries
  async sendChatMessage(message, sessionId = null) {
    try {
      const response = await apiClient.post('/chat', {
        message,
        session_id: sessionId,
        user_id: 'anonymous' // Could be replaced with actual user ID if authentication is added
      });
      return response.data;
    } catch (error) {
      console.error('Error sending chat message:', error);
      throw error;
    }
  },

  // Get detailed information about a specific protein
  async getProteinInfo(proteinId) {
    try {
      const response = await apiClient.get(`/protein/${proteinId}`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching protein info for ${proteinId}:`, error);
      throw error;
    }
  },

  // Get protein structure data for 3D visualization
  async getProteinStructure(proteinId) {
    try {
      console.log(`Fetching structure data for ${proteinId}...`);
      const response = await apiClient.get(`/protein/${proteinId}/structure`);
      console.log(`Structure data received:`, response.data);
      return response.data;
    } catch (error) {
      console.error(`Error fetching protein structure for ${proteinId}:`, error);
      throw error;
    }
  },

  // Get protein interaction network data
  async getProteinInteractions(proteinId) {
    try {
      console.log(`Fetching interaction data for ${proteinId}...`);
      const response = await apiClient.get(`/protein/${proteinId}/interactions`);
      console.log(`Interaction data received:`, response.data);
      return response.data;
    } catch (error) {
      console.error(`Error fetching protein interactions for ${proteinId}:`, error);
      throw error;
    }
  },

  // Get diseases associated with a protein
  async getProteinDiseases(proteinId) {
    try {
      const response = await apiClient.get(`/protein/${proteinId}/diseases`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching disease associations for ${proteinId}:`, error);
      throw error;
    }
  },

  // Get drugs that target a protein
  async getProteinDrugs(proteinId) {
    try {
      const response = await apiClient.get(`/protein/${proteinId}/drugs`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching drug interactions for ${proteinId}:`, error);
      throw error;
    }
  },

  // Get knowledge graph data for visualization
  async getKnowledgeGraph(entityId, entityType = 'protein') {
    try {
      const response = await apiClient.get(`/knowledge-graph/${entityId}`, {
        params: { entity_type: entityType }
      });
      return response.data;
    } catch (error) {
      console.error(`Error fetching knowledge graph for ${entityId}:`, error);
      throw error;
    }
  }
};

export default apiService;