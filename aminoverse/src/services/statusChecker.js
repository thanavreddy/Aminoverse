// Backend status checking service
import axios from 'axios';

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const statusChecker = {
  /**
   * Check the status of all backend services
   * @returns {Promise<Object>} Status of all services
   */
  checkAllServices: async () => {
    try {
      // First try standard path
      try {
        const response = await axios.get(`${BASE_URL}/api/status`);
        return response.data;
      } catch (firstError) {
        // If that fails, try the root path status
        console.log("First attempt failed, trying fallback endpoint");
        const fallbackResponse = await axios.get(`${BASE_URL}/status`);
        return fallbackResponse.data;
      }
    } catch (error) {
      console.error("Error checking services:", error);
      return {
        server: 'error',
        neo4j: 'error',
        redis: 'error',
        llm: 'error',
        api_integrations: 'error',
        error: error.message
      };
    }
  },

  /**
   * Check a specific service status
   * @param {string} service - Service name ('neo4j', 'redis', 'llm', or 'apis')
   * @returns {Promise<Object>} Status of the specified service
   */
  checkService: async (service) => {
    try {
      // Try both possible paths
      try {
        const response = await axios.get(`${BASE_URL}/api/status/${service}`);
        return response.data;
      } catch (firstError) {
        const fallbackResponse = await axios.get(`${BASE_URL}/status/${service}`);
        return fallbackResponse.data;
      }
    } catch (error) {
      console.error(`Error checking ${service} service:`, error);
      return {
        status: 'error',
        message: error.message
      };
    }
  }
};

export default statusChecker;