import React, { useState, useEffect, useRef } from 'react';
import apiService from '../services/api';
import statusChecker from '../services/statusChecker';
import { v4 as uuidv4 } from 'uuid'; // For generating unique session IDs
import theme from '../theme';
// Removing direct import of MolStar as it's causing errors
import Cytoscape from 'cytoscape';
import CytoscapeComponent from 'react-cytoscapejs';

// Define a MotionBox component without relying on framer-motion
const MotionBox = ({ children, className, ...props }) => {
  return <div className={className} {...props}>{children}</div>;
};

// Service Status Indicator component
const ServiceStatusIndicator = ({ status }) => {
  const getStatusColor = () => {
    switch (status) {
      case 'ok':
        return 'bg-green-500';
      case 'error':
      case 'unknown':
        return 'bg-red-500';
      case 'partial':
        return 'bg-yellow-500';
      case 'checking':
        return 'bg-blue-300 animate-pulse';
      default:
        return 'bg-gray-300';
    }
  };

  return (
    <div className={`w-3 h-3 rounded-full ${getStatusColor()}`}></div>
  );
};

// Service Status Panel Component
const ServiceStatusPanel = ({ isVisible, onClose }) => {
  const [servicesStatus, setServicesStatus] = useState({
    server: 'checking',
    neo4j: 'checking',
    redis: 'checking',
    llm: 'checking',
    api_integrations: 'checking'
  });
  const [isLoading, setIsLoading] = useState(true);
  const [connectionErrors, setConnectionErrors] = useState({});
  
  useEffect(() => {
    if (isVisible) {
      checkServices();
    }
  }, [isVisible]);
  
  const checkServices = async () => {
    setIsLoading(true);
    try {
      const statusData = await statusChecker.checkAllServices();
      setServicesStatus(statusData);
      
      // Extract error information
      const errors = {};
      Object.entries(statusData).forEach(([key, value]) => {
        const errorKey = `${key}_error`;
        if (statusData[errorKey]) {
          errors[key] = statusData[errorKey];
        }
      });
      setConnectionErrors(errors);
    } catch (error) {
      console.error("Failed to fetch service status:", error);
      // Set all services as error since we couldn't connect to the backend
      setServicesStatus({
        server: 'error',
        neo4j: 'error',
        redis: 'error',
        llm: 'error',
        api_integrations: 'error',
        error: error.message
      });
    } finally {
      setIsLoading(false);
    }
  };
  
  const getErrorMessage = (service) => {
    if (connectionErrors[service]) {
      return connectionErrors[service];
    }
    
    if (servicesStatus[service] === 'error') {
      switch(service) {
        case 'neo4j':
          return 'Could not connect to Neo4j Aura. Check network connectivity and database status.';
        case 'redis':
          return 'Could not connect to Redis Cloud. Check network connectivity and service status.';
        case 'llm':
          return 'Could not connect to LLM API. Check API key and network connectivity.';
        case 'api_integrations':
          return 'Could not connect to one or more external APIs.';
        default:
          return 'Connection error';
      }
    }
    
    return null;
  };
  
  if (!isVisible) return null;
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
      <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-bold">System Status</h3>
          <button 
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700"
          >
            ✕
          </button>
        </div>
        
        {isLoading ? (
          <div className="flex justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center space-x-2 p-2 border rounded">
                <ServiceStatusIndicator status={servicesStatus.server} />
                <span>Server</span>
              </div>
              <div className="flex items-center space-x-2 p-2 border rounded">
                <ServiceStatusIndicator status={servicesStatus.neo4j} />
                <span>Neo4j Aura</span>
              </div>
              <div className="flex items-center space-x-2 p-2 border rounded">
                <ServiceStatusIndicator status={servicesStatus.redis} />
                <span>Redis Cloud</span>
              </div>
              <div className="flex items-center space-x-2 p-2 border rounded">
                <ServiceStatusIndicator status={servicesStatus.llm} />
                <span>Gemini LLM</span>
              </div>
              <div className="flex items-center space-x-2 p-2 border rounded col-span-2">
                <ServiceStatusIndicator status={servicesStatus.api_integrations} />
                <span>External APIs</span>
              </div>
            </div>
            
            {/* Display errors */}
            {Object.keys(servicesStatus).map(service => {
              const errorMessage = getErrorMessage(service);
              if (errorMessage) {
                return (
                  <div key={service} className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-sm">
                    <p className="font-semibold">{service === 'api_integrations' ? 'External APIs' : service}: Error</p>
                    <p className="text-red-600">{errorMessage}</p>
                  </div>
                );
              }
              return null;
            })}
              
            <div className="flex justify-between mt-4">
              <div className="text-xs text-gray-500">
                <p>Using cloud services: Neo4j Aura & Redis Cloud</p>
              </div>
              <button
                onClick={checkServices}
                className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded"
              >
                Refresh Status
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Updated Protein Structure Viewer with direct PDB and AlphaFold integration
const ProteinStructureVisualizer = ({ proteinId, structureData }) => {
  const [viewerState, setViewerState] = useState({
    loading: true,
    error: null,
    viewerUrl: null
  });
  const iframeRef = useRef(null);
  const [iframeLoaded, setIframeLoaded] = useState(false);

  // Process the structure data and set up the viewer
  useEffect(() => {
    console.log("Structure data received:", structureData);
    
    // If no protein ID, show initial state
    if (!proteinId) {
      setViewerState({
        loading: false,
        error: null,
        viewerUrl: null
      });
      return;
    }
    
    // If no structure data yet, show loading state
    if (!structureData) {
      setViewerState({
        loading: true,
        error: null,
        viewerUrl: null
      });
      return;
    }
    
    try {
      // Case 1: Backend already provided a viewer URL
      if (structureData.viewer_url) {
        setViewerState({
          loading: false,
          error: null,
          viewerUrl: structureData.viewer_url
        });
        return;
      }
      
      // Case 2: PDB ID is available - create a viewer URL
      if (structureData.pdb_id) {
        const pdbId = structureData.pdb_id;
        // Use RCSB PDB's embedded viewer - it's more reliable across browsers
        // Direct link to the 3D view
        setViewerState({
          loading: false,
          error: null,
          viewerUrl: `https://www.rcsb.org/3d-view/${pdbId}/`
        });
        return;
      }
      
      // Case 3: AlphaFold ID is available - create a viewer URL
      if (structureData.alphafold_id || structureData.uniprot_id) {
        const uniprotId = structureData.alphafold_id || structureData.uniprot_id;
        // Extract just the UniProt ID without any species prefixes
        const cleanId = uniprotId.split('-')[0].split('.')[0];
        setViewerState({
          loading: false,
          error: null,
          viewerUrl: `https://alphafold.ebi.ac.uk/entry/${cleanId}`
        });
        return;
      }
      
      // Case 4: If we just have the protein ID but no structure data with details, 
      // try a direct link to AlphaFold (most proteins have AlphaFold models)
      if (proteinId) {
        const cleanId = proteinId.split('-')[0].split('.')[0];
        setViewerState({
          loading: false, 
          error: null,
          viewerUrl: `https://alphafold.ebi.ac.uk/entry/${cleanId}`
        });
        return;
      }
      
      // Case 5: Structure data indicates it's unavailable
      if (structureData.status === 'unavailable') {
        setViewerState({
          loading: false,
          error: structureData.message || 'No structure data available for this protein',
          viewerUrl: null
        });
        return;
      }
      
      // Default case: No recognizable structure format
      setViewerState({
        loading: false,
        error: 'Could not determine how to display this protein structure',
        viewerUrl: null
      });
      
    } catch (err) {
      console.error("Error processing structure data:", err);
      // Even if there's an error, try to provide a fallback viewer option
      try {
        const cleanId = proteinId.split('-')[0].split('.')[0];
        setViewerState({
          loading: false,
          error: null,
          viewerUrl: `https://alphafold.ebi.ac.uk/entry/${cleanId}`
        });
      } catch (fallbackErr) {
        setViewerState({
          loading: false,
          error: `Error processing structure: ${err.message}`,
          viewerUrl: null
        });
      }
    }
  }, [structureData, proteinId]);

  // Handle iframe load success
  const handleIframeLoad = () => {
    setIframeLoaded(true);
    console.log("Structure viewer loaded successfully");
  };

  // Handle iframe load error
  const handleIframeError = () => {
    console.error("Error loading structure viewer iframe");
    // Try to gracefully recover by using PDB or AlphaFold search
    const cleanId = proteinId.split('-')[0].split('.')[0];
    
    // Try AlphaFold directly as a fallback
    setViewerState(prevState => ({
      ...prevState,
      viewerUrl: `https://alphafold.ebi.ac.uk/entry/${cleanId}`,
      error: null
    }));
  };
  
  // When no protein is selected
  if (!proteinId) {
    return (
      <div className="flex flex-col items-center justify-center h-full border border-gray-200 rounded-md p-8 text-center">
        <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 text-gray-300 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
        </svg>
        <p className="text-gray-500">Select a protein to view its 3D structure</p>
      </div>
    );
  }

  // Loading state
  if (viewerState.loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        <p className="text-gray-500 mt-4 font-medium">Loading structure data...</p>
        <p className="text-gray-400 mt-2 text-sm">Retrieving data for {proteinId}</p>
      </div>
    );
  }

  // Error state
  if (viewerState.error) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center">
        <div className="mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M12 14h.01" />
          </svg>
        </div>
        <p className="text-gray-700 font-medium">{viewerState.error}</p>
        <p className="text-sm text-gray-500 mt-2 max-w-md">
          Try searching for a different protein with known experimental or predicted structures.
        </p>
        
        {/* Alternative viewing options */}
        <div className="mt-6">
          <p className="text-sm font-medium text-gray-700 mb-3">Try viewing this protein externally:</p>
          <div className="flex flex-wrap justify-center gap-3">
            <a 
              href={`https://www.rcsb.org/structure/${proteinId}`}
              target="_blank" 
              rel="noopener noreferrer"
              className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 text-sm"
            >
              View in RCSB PDB
            </a>
            <a 
              href={`https://alphafold.ebi.ac.uk/entry/${proteinId.split('-')[0]}`}
              target="_blank" 
              rel="noopener noreferrer"
              className="px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 text-sm"
            >
              View in AlphaFold
            </a>
          </div>
        </div>
      </div>
    );
  }

  // Success state - display the structure using a direct iframe
  if (viewerState.viewerUrl) {
    return (
      <div className="h-full relative border border-gray-200 rounded-md">
        {/* Header with protein info */}
        <div className="p-2 border-b border-gray-200 flex justify-between items-center bg-gray-50">
          <div className="text-sm">
            <span className="font-medium text-gray-700">{proteinId}</span>
            {structureData && structureData.pdb_id && (
              <span className="ml-2 text-xs text-blue-500 font-medium">PDB: {structureData.pdb_id}</span>
            )}
            {structureData && structureData.alphafold_id && (
              <span className="ml-2 text-xs text-green-500 font-medium">AlphaFold</span>
            )}
            {!structureData?.pdb_id && !structureData?.alphafold_id && (
              <span className="ml-2 text-xs text-green-500 font-medium">AlphaFold prediction</span>
            )}
          </div>
          {/* External link */}
          <a 
            href={viewerState.viewerUrl}
            target="_blank"
            rel="noopener noreferrer" 
            className="text-xs text-blue-500 hover:underline flex items-center"
          >
            Open Externally
            <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        </div>
        
        {/* Iframe container */}
        <div className="h-[calc(100%-36px)] w-full relative">
          <iframe 
            ref={iframeRef}
            src={viewerState.viewerUrl}
            title={`3D Structure of ${proteinId}`}
            className="w-full h-full border-0"
            sandbox="allow-scripts allow-same-origin allow-popups"
            loading="lazy"
            onLoad={handleIframeLoad}
            onError={handleIframeError}
            allow="fullscreen"
          />
          {/* Loading overlay while iframe is loading */}
          {!iframeLoaded && (
            <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-75">
              <div className="flex flex-col items-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                <p className="mt-2 text-sm text-gray-600">Loading viewer...</p>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Fallback state - direct to external sites
  return (
    <div className="flex flex-col items-center justify-center h-full p-8 text-center">
      <div className="mb-4">
        <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <p className="text-gray-700 font-medium">Unable to display 3D structure</p>
      <p className="text-sm text-gray-500 mt-2 max-w-md">
        You can view this structure on external sites:
      </p>
      
      <div className="mt-6 flex flex-wrap justify-center gap-3">
        <a 
          href={`https://www.rcsb.org/structure/${proteinId}`}
          target="_blank" 
          rel="noopener noreferrer"
          className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 text-sm"
        >
          View in RCSB PDB
        </a>
        <a 
          href={`https://alphafold.ebi.ac.uk/entry/${proteinId.split('-')[0]}`}
          target="_blank" 
          rel="noopener noreferrer"
          className="px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 text-sm"
        >
          View in AlphaFold
        </a>
      </div>
    </div>
  );
};

// KnowledgeGraphVisualizer component for the new knowledge graph visualization
const KnowledgeGraphVisualizer = ({ graphData, entityId, entityType = "Protein" }) => {
  const [visualState, setVisualState] = useState({
    loading: true,
    error: null,
    initialized: false
  });
  const cyRef = useRef(null);
  const containerRef = useRef(null);

  // Track if the component is mounted to prevent state updates after unmounting
  const isMounted = useRef(true);
  useEffect(() => {
    return () => { isMounted.current = false; };
  }, []);

  // Log the knowledge graph data received
  useEffect(() => {
    console.log("Knowledge graph data received:", { 
      entityId, 
      entityType,
      nodesCount: graphData?.nodes?.length || 0,
      edgesCount: graphData?.edges?.length || 0 
    });

    if (entityId) {
      setVisualState(prev => ({ ...prev, loading: !graphData }));
    }
  }, [entityId, graphData]);

  // Process the graph data into Cytoscape elements
  const elements = React.useMemo(() => {
    if (!graphData || !entityId) return [];

    try {
      const { nodes, edges } = graphData;
      if (!nodes || !edges || nodes.length === 0) {
        console.warn("Invalid knowledge graph data structure");
        return [];
      }

      console.log(`Processing ${nodes.length} nodes and ${edges.length} edges`);

      // Check if nodes have the expected structure
      if (!nodes[0].id) {
        console.error("Nodes don't have expected ID property", nodes[0]);
        return [];
      }

      // Map nodes to Cytoscape format
      const cyNodes = nodes.map(node => {
        // Generate a color based on node type
        const getNodeColor = (type) => {
          switch(type?.toLowerCase()) {
            case 'protein': return '#3B82F6'; // blue-500
            case 'disease': return '#EF4444'; // red-500
            case 'drug': return '#10B981';    // green-500
            case 'pathway': return '#8B5CF6'; // purple-500
            case 'gene': return '#F59E0B';    // amber-500
            default: return '#6B7280';        // gray-500
          }
        };

        // Get node size based on type and whether it's the central entity
        const getNodeSize = (nodeId, type) => {
          const isMainEntity = nodeId === entityId;
          switch(type?.toLowerCase()) {
            case 'protein': return isMainEntity ? 60 : 40;
            case 'disease': return 45;
            case 'drug': return 40;
            case 'pathway': return 50;
            case 'gene': return 35;
            default: return 30;
          }
        };

        return {
          data: {
            id: node.id,
            label: node.label || node.name || node.id,
            type: node.type || 'unknown',
            color: getNodeColor(node.type),
            size: getNodeSize(node.id, node.type),
            centrality: node.id === entityId ? 1 : 0,
            ...node // Include all original properties
          }
        };
      });

      // Map edges to Cytoscape format
      const cyEdges = edges.map(edge => {
        // Generate edge style based on relationship type
        const getEdgeStyle = (type) => {
          switch(type?.toLowerCase()) {
            case 'interacts_with': return { color: '#93C5FD', width: 2 }; // blue-300
            case 'targets': return { color: '#6EE7B7', width: 3 };        // green-300
            case 'treats': return { color: '#FCD34D', width: 3 };         // amber-300
            case 'associated_with': return { color: '#FDA4AF', width: 2 }; // red-300
            case 'part_of': return { color: '#C4B5FD', width: 2 };        // purple-300
            default: return { color: '#D1D5DB', width: 1 };               // gray-300
          }
        };

        const edgeStyle = getEdgeStyle(edge.type);

        return {
          data: {
            id: edge.id || `edge-${edge.source}-${edge.target}`,
            source: edge.source,
            target: edge.target,
            label: edge.type || '',
            type: edge.type || 'RELATED_TO',
            color: edgeStyle.color,
            width: edge.weight ? Math.max(edge.weight * 5, 1) : edgeStyle.width,
            ...edge // Include all original properties
          }
        };
      });

      if (isMounted.current) {
        setVisualState(prev => ({ ...prev, loading: false, error: null }));
      }
      return [...cyNodes, ...cyEdges];
    } catch (err) {
      console.error("Error processing knowledge graph data:", err);
      if (isMounted.current) {
        setVisualState(prev => ({ 
          ...prev, 
          loading: false, 
          error: `Error processing knowledge graph data: ${err.message}` 
        }));
      }
      return [];
    }
  }, [graphData, entityId]);

  // Define Cytoscape stylesheet
  const stylesheet = [
    // Node styling
    {
      selector: 'node',
      style: {
        'label': 'data(label)',
        'text-valign': 'center',
        'text-halign': 'center',
        'background-color': 'data(color)',
        'text-outline-width': 2,
        'text-outline-color': '#FFF',
        'color': '#000',
        'font-size': 12,
        'width': 'data(size)',
        'height': 'data(size)',
        'text-wrap': 'wrap',
        'text-max-width': '80px'
      }
    },
    // Special styling for the main entity node
    {
      selector: 'node[centrality = 1]',
      style: {
        'border-width': 3,
        'border-color': '#1E40AF', // blue-800
        'font-weight': 'bold',
        'font-size': 14
      }
    },
    // Node type specific styling
    {
      selector: 'node[type = "Protein"]',
      style: {
        'shape': 'ellipse'
      }
    },
    {
      selector: 'node[type = "Disease"]',
      style: {
        'shape': 'diamond'
      }
    },
    {
      selector: 'node[type = "Drug"]',
      style: {
        'shape': 'round-rectangle'
      }
    },
    {
      selector: 'node[type = "Pathway"]',
      style: {
        'shape': 'hexagon'
      }
    },
    // Edge styling
    {
      selector: 'edge',
      style: {
        'width': 'data(width)',
        'line-color': 'data(color)',
        'target-arrow-color': 'data(color)',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        'opacity': 0.8
      }
    },
    // Edge labels for important relationships
    {
      selector: 'edge[type = "TARGETS"], edge[type = "TREATS"]',
      style: {
        'label': 'data(type)',
        'font-size': 10,
        'text-background-color': '#FFFFFF',
        'text-background-opacity': 0.7,
        'text-background-padding': 2,
        'text-background-shape': 'round-rectangle'
      }
    }
  ];

  // Initialize and apply layout when elements or container dimensions change
  useEffect(() => {
    // Skip if conditions aren't met
    if (!cyRef.current || elements.length === 0 || visualState.error) {
      return;
    }

    const initializeGraph = () => {
      // Ensure container has dimensions before initializing
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) {
        console.warn("Container has zero dimensions, deferring knowledge graph layout");
        
        // Try again after a short delay to allow container to render
        setTimeout(initializeGraph, 250);
        return;
      }

      const cy = cyRef.current;
      console.log(`Initializing knowledge graph with ${elements.length} elements`);
      
      // Clean up before adding new elements
      cy.elements().remove();
      cy.add(elements);

      try {
        // Choose an appropriate layout based on graph size
        const layoutName = elements.length <= 20 ? 'concentric' : 'cose';
        
        let layoutOptions = {};
        if (layoutName === 'concentric') {
          layoutOptions = {
            name: 'concentric',
            concentric: function(node) {
              // Main entity in center, then by type importance
              if (node.data('centrality') === 1) return 10;
              switch(node.data('type').toLowerCase()) {
                case 'protein': return 8;
                case 'disease': return 6;
                case 'drug': return 4;
                case 'pathway': return 2;
                default: return 0;
              }
            },
            levelWidth: function() { return 1; },
            animate: true,
            animationDuration: 500,
            padding: 50
          };
        } else {
          layoutOptions = {
            name: 'grid', // Using grid instead of cose for better reliability
            animate: true,
            animationDuration: 500,
            nodeDimensionsIncludeLabels: true,
            padding: 50,
            avoidOverlap: true,
            fit: true
          };
        }
        
        // Apply the layout
        const layout = cy.layout(layoutOptions);
        layout.run();
        
        // Center and fit the graph in the container
        cy.center();
        cy.fit(undefined, 40);
        
        // Mark as initialized
        if (isMounted.current) {
          setVisualState(prev => ({ ...prev, initialized: true }));
        }
        
        console.log("Knowledge graph layout applied successfully");
      } catch (err) {
        console.error("Error applying knowledge graph layout:", err);
        
        // Try a simple circle layout as fallback
        try {
          const fallbackLayout = cy.layout({ 
            name: 'circle',
            animate: false
          });
          fallbackLayout.run();
          cy.center();
          cy.fit();
          
          if (isMounted.current) {
            setVisualState(prev => ({ ...prev, initialized: true }));
          }
        } catch (fallbackErr) {
          console.error("Fallback layout also failed:", fallbackErr);
        }
      }
    };

    // Start initialization process
    initializeGraph();
  }, [elements, visualState.loading]);

  // Fix layout when container size changes
  useEffect(() => {
    const handleResize = () => {
      if (cyRef.current && elements.length && containerRef.current) {
        cyRef.current.resize();
        cyRef.current.center();
        cyRef.current.fit(undefined, 40);
      }
    };
    
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [elements]);

  // Empty state - no entity selected
  if (!entityId) {
    return (
      <div className="flex flex-col items-center justify-center h-full border border-gray-200 rounded-md p-8 text-center">
        <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 text-gray-300 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M13.5 10.5L21 3m0 0l-7.5 7.5M21 3h-7.5m0 0v7.5M10.5 13.5L3 21m0 0l7.5-7.5M3 21h7.5m0 0v-7.5" />
        </svg>
        <p className="text-gray-500">Select a protein to view its knowledge graph</p>
      </div>
    );
  }
  
  // Loading state
  if (visualState.loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        <p className="text-gray-500 mt-4 font-medium">Loading knowledge graph...</p>
        <p className="text-gray-400 mt-2 text-sm">Building network for {entityId}</p>
      </div>
    );
  }
  
  // Error state
  if (visualState.error) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center">
        <div className="mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <p className="text-gray-700 font-medium">Error showing knowledge graph</p>
        <p className="text-sm text-gray-500 mt-2 max-w-md">{visualState.error}</p>
      </div>
    );
  }

  // No graph data
  if (!elements.length) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center">
        <div className="mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M12 14h.01" />
          </svg>
        </div>
        <p className="text-gray-700 font-medium">No knowledge graph data found</p>
        <p className="text-sm text-gray-500 mt-2 max-w-md">
          No knowledge graph data is available for {entityId}.
        </p>
      </div>
    );
  }

  // Success state - knowledge graph visualization
  return (
    <div className="h-full border border-gray-200 rounded-md">
      {/* Header with entity info */}
      <div className="p-2 border-b border-gray-200 flex justify-between items-center bg-gray-50">
        <div className="text-sm">
          <span className="font-medium text-gray-700">{entityId}</span>
          <span className="ml-2 text-xs text-blue-500">
            {graphData?.nodes?.length || 0} nodes, {graphData?.edges?.length || 0} connections
          </span>
        </div>
        <div className="flex items-center text-xs space-x-3">
          <div className="flex items-center">
            <div className="w-3 h-3 rounded-full bg-blue-500 mr-1"></div>
            <span>Protein</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 rounded-full bg-red-500 mr-1"></div>
            <span>Disease</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 rounded-full bg-green-500 mr-1"></div>
            <span>Drug</span>
          </div>
        </div>
      </div>
      
      {/* Graph container */}
      <div ref={containerRef} className="h-[calc(100%-36px)] w-full relative">
        <CytoscapeComponent
          elements={elements}
          stylesheet={stylesheet}
          style={{ width: '100%', height: '100%' }} // Explicit dimensions
          layout={{ name: 'preset' }} // Initial layout, real layout applied in useEffect
          cy={(cy) => {
            cyRef.current = cy;
            
            // Add hover interactivity for nodes
            cy.on('mouseover', 'node', function(e) {
              e.target.style({
                'border-width': 2,
                'border-color': '#2563EB',
                'border-opacity': 1
              });
            });
            
            cy.on('mouseout', 'node', function(e) {
              if (e.target.data('centrality') !== 1) {
                e.target.style({
                  'border-width': 0
                });
              }
            });
            
            // Show info on node click
            cy.on('tap', 'node', function(e) {
              const node = e.target;
              const data = node.data();
              
              // Show info about the node when clicked
              console.log("Node clicked:", data);
              // Future enhancement: Show a tooltip or modal with node details
            });
          }}
          className="h-full w-full"
          minZoom={0.5}
          maxZoom={2.5}
          boxSelectionEnabled={false}
        />
        
        {/* Loading overlay while the graph is rendering */}
        {!visualState.initialized && (
          <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-75">
            <div className="flex flex-col items-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
              <p className="mt-2 text-sm text-gray-600">Generating knowledge graph visualization...</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Improved InteractionNetworkVisualizer with simplified layout for better stability
const InteractionNetworkVisualizer = ({ interactions = [], proteinId }) => {
  const [visualState, setVisualState] = useState({
    loading: true,
    error: null,
    initialized: false
  });
  const cyRef = useRef(null);
  const containerRef = useRef(null);
  
  // Track if the component is mounted to prevent state updates after unmounting
  const isMounted = useRef(true);
  useEffect(() => {
    return () => { isMounted.current = false; };
  }, []);
  
  // Log the interaction data received
  useEffect(() => {
    console.log("Interaction data received:", { proteinId, interactionsCount: interactions?.length || 0 });
    
    if (proteinId) {
      setVisualState(prev => ({ ...prev, loading: !interactions }));
    }
  }, [proteinId, interactions]);
  
  // Set up Cytoscape elements from interactions data
  const elements = React.useMemo(() => {
    if (!interactions || interactions.length === 0 || !proteinId) return [];
    
    const nodes = [];
    const edges = [];
    const seenNodes = new Set();
    
    try {
      // Add the main protein node
      nodes.push({
        data: { 
          id: proteinId, 
          label: proteinId.split('.').pop() || proteinId,
          type: 'main',
          score: 1.0,
          size: 60
        }
      });
      seenNodes.add(proteinId);
      
      // Add interacting proteins and their edges
      interactions.forEach(interaction => {
        // Safety check for required data
        if (!interaction) return;
        
        // Different APIs might return protein IDs with different key names
        const interactorId = interaction.protein_id || interaction.id || interaction.interactor_id;
        if (!interactorId) return;
        
        const interactorName = interaction.protein_name || interaction.name || interactorId.split('.').pop() || interactorId;
        
        // Skip duplicates
        if (seenNodes.has(interactorId)) return;
        seenNodes.add(interactorId);
        
        // Scale node size based on interaction score (confidence)
        const score = parseFloat(interaction.score) || 0.5;
        const nodeSize = 30 + (score * 20); // Scale between 30-50px
        
        nodes.push({
          data: { 
            id: interactorId, 
            label: interactorName,
            score: score,
            type: 'interactor',
            size: nodeSize
          }
        });
        
        // Edge thickness based on score
        const edgeWidth = Math.max(score * 5, 1); // Min width of 1px
        
        edges.push({
          data: {
            id: `edge-${proteinId}-${interactorId}`,
            source: proteinId,
            target: interactorId,
            weight: score,
            width: edgeWidth
          }
        });
      });
      
      if (isMounted.current) {
        setVisualState(prev => ({ ...prev, loading: false, error: null }));
      }
      return [...nodes, ...edges];
    } catch (err) {
      console.error("Error processing interaction data:", err);
      if (isMounted.current) {
        setVisualState(prev => ({ 
          ...prev, 
          loading: false, 
          error: `Error processing network data: ${err.message}` 
        }));
      }
      return [];
    }
  }, [interactions, proteinId]);

  // Define Cytoscape stylesheet
  const stylesheet = [
    {
      selector: 'node',
      style: {
        'label': 'data(label)',
        'text-valign': 'center',
        'text-halign': 'center',
        'background-color': '#6B7280', // gray-500
        'text-outline-width': 2,
        'text-outline-color': '#FFF',
        'color': '#000',
        'font-size': 12,
        'width': 'data(size)',
        'height': 'data(size)'
      }
    },
    {
      selector: 'node[type="main"]',
      style: {
        'background-color': '#3B82F6', // blue-500
        'font-weight': 'bold',
        'font-size': 14,
        'width': 60,
        'height': 60
      }
    },
    {
      selector: 'edge',
      style: {
        'width': 'data(width)',
        'line-color': '#93C5FD', // blue-300
        'opacity': 0.8,
        'curve-style': 'bezier'
      }
    }
  ];

  // Initialize and apply layout when elements or container dimensions change
  useEffect(() => {
    // Skip if conditions aren't met
    if (!cyRef.current || elements.length === 0 || visualState.error) {
      return;
    }
    
    const initializeGraph = () => {
      // Ensure container has dimensions before initializing
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) {
        console.warn("Container has zero dimensions, deferring network layout");
        
        // Try again after a short delay to allow container to render
        setTimeout(initializeGraph, 250);
        return;
      }

      const cy = cyRef.current;
      console.log(`Initializing interaction network with ${elements.length} elements`);
      
      // Clean up before adding new elements
      cy.elements().remove();
      cy.add(elements);

      try {
        // Use a simple circle or grid layout which is more reliable
        const useCircleLayout = elements.length <= 20;
        const layout = cy.layout({
          name: useCircleLayout ? 'circle' : 'grid',
          animate: true,
          animationDuration: 500,
          padding: 40,
          avoidOverlap: true,
          spacingFactor: 1.5,
          fit: true
        });
        
        layout.run();
        
        // Center and fit
        cy.center();
        cy.fit(undefined, 40);
        
        if (isMounted.current) {
          setVisualState(prev => ({ ...prev, initialized: true }));
        }
        
        console.log("Network layout applied successfully");
      } catch (err) {
        console.error("Error applying network layout:", err);
        
        // Try a very simple preset layout
        try {
          const fallbackLayout = cy.layout({ 
            name: 'preset',
            animate: false
          });
          fallbackLayout.run();
          cy.center();
          cy.fit();
          
          if (isMounted.current) {
            setVisualState(prev => ({ ...prev, initialized: true }));
          }
        } catch (fallbackErr) {
          console.error("Fallback layout also failed:", fallbackErr);
        }
      }
    };

    // Start initialization process
    initializeGraph();
  }, [elements, visualState.loading]);
  
  // Fix layout when container size changes
  useEffect(() => {
    const handleResize = () => {
      if (cyRef.current && elements.length && containerRef.current) {
        cyRef.current.resize();
        cyRef.current.center();
        cyRef.current.fit(undefined, 40);
      }
    };
    
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [elements]);

  // Empty state - no protein selected
  if (!proteinId) {
    return (
      <div className="flex flex-col items-center justify-center h-full border border-gray-200 rounded-md p-8 text-center">
        <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 text-gray-300 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M13.5 10.5L21 3m0 0l-7.5 7.5M21 3h-7.5m0 0v7.5M10.5 13.5L3 21m0 0l7.5-7.5M3 21h7.5m0 0v-7.5" />
        </svg>
        <p className="text-gray-500">Select a protein to view its interaction network</p>
      </div>
    );
  }
  
  // Loading state
  if (visualState.loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        <p className="text-gray-500 mt-4 font-medium">Loading interaction data...</p>
        <p className="text-gray-400 mt-2 text-sm">Retrieving interactions for {proteinId}</p>
      </div>
    );
  }
  
  // Error state
  if (visualState.error) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center">
        <div className="mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <p className="text-gray-700 font-medium">Error showing interaction network</p>
        <p className="text-sm text-gray-500 mt-2 max-w-md">{visualState.error}</p>
        
        <div className="mt-6">
          <a 
            href={`https://string-db.org/network/${proteinId}`}
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 text-sm"
          >
            View in STRING-db
          </a>
        </div>
      </div>
    );
  }

  // No interactions found
  if (!elements.length) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center">
        <div className="mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M12 14h.01" />
          </svg>
        </div>
        <p className="text-gray-700 font-medium">No interactions found</p>
        <p className="text-sm text-gray-500 mt-2 max-w-md">
          No protein interaction data is available for {proteinId}.
          This could be because the protein has no known interactions or there was an error retrieving the data.
        </p>
        <a 
          href={`https://string-db.org/network/${proteinId}`}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 text-sm"
        >
          Check STRING-db
        </a>
      </div>
    );
  }

  // Success state - network visualization
  return (
    <div className="h-full border border-gray-200 rounded-md">
      {/* Header with protein info */}
      <div className="p-2 border-b border-gray-200 flex justify-between items-center bg-gray-50">
        <div className="text-sm">
          <span className="font-medium text-gray-700">{proteinId}</span>
          <span className="ml-2 text-xs text-blue-500">
            {interactions.length} interaction{interactions.length !== 1 ? 's' : ''}
          </span>
        </div>
        <a 
          href={`https://string-db.org/network/${proteinId.split('-')[0]}`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-blue-500 hover:underline flex items-center"
        >
          View in STRING-db
          <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
        </a>
      </div>
      
      {/* Network graph container */}
      <div ref={containerRef} className="h-[calc(100%-36px)] w-full relative">
        <CytoscapeComponent
          elements={elements}
          stylesheet={stylesheet}
          style={{ width: '100%', height: '100%' }} // Explicit dimensions
          layout={{ name: 'preset' }} // Initial layout, real layout applied in useEffect
          cy={(cy) => {
            cyRef.current = cy;
            
            // Add hover interactivity for nodes
            cy.on('mouseover', 'node', function(e) {
              e.target.style({
                'border-width': 2,
                'border-color': '#2563EB',
                'border-opacity': 1
              });
            });
            
            cy.on('mouseout', 'node', function(e) {
              e.target.style({
                'border-width': 0
              });
            });
            
            // Show info on node click
            cy.on('tap', 'node', function(e) {
              const node = e.target;
              const data = node.data();
              
              // Show info about the protein when clicked
              if (data.id !== proteinId) {
                window.open(`https://www.uniprot.org/uniprotkb/${data.id.split('-')[0]}/entry`, '_blank');
              }
            });
          }}
          className="h-full w-full"
          minZoom={0.5}
          maxZoom={2.5}
          boxSelectionEnabled={false}
        />
        
        {/* Loading overlay while the network is rendering */}
        {!visualState.initialized && (
          <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-75">
            <div className="flex flex-col items-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
              <p className="mt-2 text-sm text-gray-600">Generating network visualization...</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Enhanced ChatMessage component for better data presentation
const ChatMessage = ({ message, isLast }) => {
  const isUser = message.type === 'user';
  const bgColor = isUser ? 'bg-blue-500' : 'bg-white';
  const textColor = isUser ? 'text-white' : 'text-gray-800';
  const alignClass = isUser ? 'self-end' : 'self-start';
  const borderRadius = isUser 
    ? 'rounded-lg rounded-br-none' 
    : 'rounded-lg rounded-bl-none';
  
  // Helper function to format protein sequences with styling
  const formatSequence = (sequence) => {
    if (!sequence) return null;
    
    return (
      <div className="overflow-x-auto mt-2 mb-2">
        <code className="font-mono text-xs bg-gray-800 text-white p-3 rounded block whitespace-pre-wrap max-h-48 overflow-y-auto">
          {sequence.replace(/^"/, '').replace(/"$/, '')}
        </code>
      </div>
    );
  };

  // Helper function to format protein attributes for better display
  const formatProteinData = (data) => {
    // Check if this is a protein structure response
    if (data.pdb_id || data.alphafold_id) {
      return (
        <div className="bg-blue-50 p-3 rounded-md border border-blue-100">
          <h3 className="text-blue-800 font-medium text-sm mb-2">Structure Information</h3>
          <table className="w-full text-sm">
            <tbody>
              {data.pdb_id && (
                <tr>
                  <td className="font-medium pr-4 py-1 text-gray-600 align-top">PDB ID:</td>
                  <td className="py-1">
                    <a 
                      href={`https://www.rcsb.org/structure/${data.pdb_id}`}
                      target="_blank"
                      rel="noopener noreferrer" 
                      className="text-blue-600 hover:underline"
                    >
                      {data.pdb_id}
                    </a>
                  </td>
                </tr>
              )}
              {data.resolution && (
                <tr>
                  <td className="font-medium pr-4 py-1 text-gray-600 align-top">Resolution:</td>
                  <td className="py-1">{data.resolution} Å</td>
                </tr>
              )}
              {data.method && (
                <tr>
                  <td className="font-medium pr-4 py-1 text-gray-600 align-top">Method:</td>
                  <td className="py-1">{data.method}</td>
                </tr>
              )}
              {data.alphafold_id && (
                <tr>
                  <td className="font-medium pr-4 py-1 text-gray-600 align-top">AlphaFold:</td>
                  <td className="py-1">
                    <a 
                      href={`https://alphafold.ebi.ac.uk/entry/${data.alphafold_id}`}
                      target="_blank"
                      rel="noopener noreferrer" 
                      className="text-blue-600 hover:underline"
                    >
                      {data.alphafold_id}
                    </a>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      );
    }

    // Check if this is a full protein response
    if (data.id && data.name) {
      return (
        <div>
          <div className="bg-blue-50 p-3 rounded-md border border-blue-100">
            <div className="flex justify-between items-start">
              <h3 className="text-blue-800 font-medium mb-2">Protein Information</h3>
              {data.uniprot_id && (
                <a 
                  href={`https://www.uniprot.org/uniprotkb/${data.uniprot_id}/entry`}
                  target="_blank"
                  rel="noopener noreferrer" 
                  className="text-xs text-blue-600 hover:underline flex items-center"
                >
                  View in UniProt
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
              )}
            </div>

            <table className="w-full text-sm">
              <tbody>
                <tr>
                  <td className="font-medium pr-4 py-1 text-gray-600 align-top">ID:</td>
                  <td className="py-1">{data.id}</td>
                </tr>
                <tr>
                  <td className="font-medium pr-4 py-1 text-gray-600 align-top">Name:</td>
                  <td className="py-1 font-medium">{data.name}</td>
                </tr>
                {data.gene_name && (
                  <tr>
                    <td className="font-medium pr-4 py-1 text-gray-600 align-top">Gene:</td>
                    <td className="py-1">{data.gene_name}</td>
                  </tr>
                )}
                {data.organism && (
                  <tr>
                    <td className="font-medium pr-4 py-1 text-gray-600 align-top">Organism:</td>
                    <td className="py-1">{data.organism}</td>
                  </tr>
                )}
                {data.function && (
                  <tr>
                    <td className="font-medium pr-4 py-1 text-gray-600 align-top">Function:</td>
                    <td className="py-1">{data.function}</td>
                  </tr>
                )}
                {data.length && (
                  <tr>
                    <td className="font-medium pr-4 py-1 text-gray-600 align-top">Length:</td>
                    <td className="py-1">{data.length} amino acids</td>
                  </tr>
                )}
              </tbody>
            </table>
            
            {data.diseases && data.diseases.length > 0 && (
              <div className="mt-3">
                <p className="font-medium text-gray-600">Associated diseases:</p>
                <ul className="list-disc pl-5 mt-1 text-sm">
                  {data.diseases.map((disease, idx) => (
                    <li key={idx}>{disease}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Display sequence if available */}
          {data.sequence && (
            <div className="mt-3">
              <div className="flex justify-between items-center">
                <p className="font-medium text-gray-600 text-sm">Protein Sequence:</p>
                <button 
                  onClick={() => navigator.clipboard.writeText(data.sequence)}
                  className="text-xs text-blue-600 hover:bg-blue-50 px-2 py-1 rounded"
                  title="Copy sequence to clipboard"
                >
                  Copy
                </button>
              </div>
              {formatSequence(data.sequence)}
            </div>
          )}
        </div>
      );
    }

    // Generic display for other data objects
    return (
      <pre className="bg-gray-50 p-3 rounded text-xs overflow-x-auto">
        {JSON.stringify(data, null, 2)}
      </pre>
    );
  };
  
  // Helper function to format content with proper markup
  const formatContent = (content) => {
    if (typeof content !== 'string') return content;
    
    // Format protein sequences with monospace font
    if (content.startsWith('"MEEP') || content.includes('PROTEIN SEQUENCE:')) {
      return formatSequence(content);
    }
    
    // Format special annotations within text
    let formattedContent = content;
    
    // Highlight protein IDs
    formattedContent = formattedContent.replace(
      /\b([A-Z][0-9][A-Z0-9]{2}[0-9]|[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2})\b/g,
      '<span class="bg-blue-100 text-blue-800 px-1 rounded text-sm font-medium">$1</span>'
    );
    
    // Split content by paragraph markers and render as separate paragraphs
    return (
      <div className="chat-message-content" dangerouslySetInnerHTML={{ 
        __html: formattedContent
          .split('\n\n')
          .map(p => `<p class="mb-2">${p}</p>`)
          .join('')
      }} />
    );
  };

  return (
    <div
      className={`${alignClass} ${bgColor} ${textColor} ${borderRadius} max-w-3/4 mb-4 shadow-sm ${isUser ? 'p-4' : 'p-4 border border-gray-200'}`}
    >
      <div className="flex items-center mb-3">
        {!isUser && (
          <div className="w-8 h-8 rounded-full bg-teal-500 text-white mr-2 flex items-center justify-center text-xs">
            AV
          </div>
        )}
        <p className="font-bold text-sm">
          {isUser ? 'You' : 'AminoVerse'}
        </p>
      </div>

      {isUser ? (
        <p>{message.content}</p>
      ) : (
        <div className="flex flex-col space-y-3 items-start">
          {/* Normal text response */}
          {typeof message.content === 'string' ? (
            formatContent(message.content)
          ) : (
            /* Structured data response */
            <div className="w-full">
              {/* Display text content if any */}
              {message.content.text && (
                <div className="mb-4">{formatContent(message.content.text)}</div>
              )}
              
              {/* Display protein data if present */}
              {message.content.data && formatProteinData(message.content.data)}
              
              {/* Map through other entries */}
              {Object.entries(message.content).map(([key, value]) => {
                if (key === 'text' || key === 'data') return null; // Already handled
                
                return (
                  <div key={key} className="w-full border-t border-gray-200 pt-3 mt-3">
                    <p className={`font-medium text-sm ${isUser ? 'text-white' : 'text-blue-600'} capitalize mb-2`}>
                      {key.replace(/_/g, ' ')}
                    </p>
                    {Array.isArray(value) ? (
                      <div className="flex flex-col items-start">
                        {value.map((item, i) => (
                          <div key={i} className="text-sm mb-1 flex items-start">
                            <span className="mr-2">•</span>
                            <span>{item}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      typeof value === 'object' && value !== null ? (
                        formatProteinData(value)
                      ) : (
                        <p className="text-sm">{formatContent(value)}</p>
                      )
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Follow-up suggestion chip component
const FollowUpChip = ({ question, onClick }) => {
  return (
    <button
      className="text-xs py-1 px-3 m-1 border border-blue-500 text-blue-500 rounded-full hover:bg-blue-500 hover:text-white"
      onClick={() => onClick(question)}
    >
      {question}
    </button>
  );
};

const AminoVerseUI = () => {
  // States for the application
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState([
    {
      type: 'system',
      content: "Welcome to AminoVerse! I'm your protein research assistant. Try searching for a protein like 'TP53' to get started."
    }
  ]);
  const [activeProtein, setActiveProtein] = useState(null);
  const [proteinData, setProteinData] = useState(null);
  const [structureData, setStructureData] = useState(null);
  const [interactionsData, setInteractionsData] = useState([]);
  const [knowledgeGraphData, setKnowledgeGraphData] = useState(null); // New state for knowledge graph data
  const [isLoading, setIsLoading] = useState(false);
  const [followUpSuggestions, setFollowUpSuggestions] = useState([]);
  const [activeTab, setActiveTab] = useState(0);
  const [sessionId, setSessionId] = useState(uuidv4()); // Generate unique session ID
  const [isStatusPanelVisible, setIsStatusPanelVisible] = useState(false);

  const messagesEndRef = useRef(null);

  // Scroll to bottom of messages when new messages are added
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Handle search function that will be called when user submits search
  const handleSearch = async (searchQuery) => {
    setIsLoading(true);
    
    // Add user message to chat
    const userMessage = {
      type: 'user',
      content: searchQuery
    };
    
    setMessages(prevMessages => [...prevMessages, userMessage]);
    
    try {
      // Call the API with the search query
      const response = await apiService.sendChatMessage(searchQuery, sessionId);
      console.log("Full API response:", response);
      
      // Process the response
      const responseMessage = {
        type: 'system',
        content: response.message || "I couldn't find specific information about your query."
      };
      
      setMessages(prevMessages => [...prevMessages, responseMessage]);
      
      // If we have protein data in the response
      if (response.data && response.data.id) {
        setActiveProtein(response.data.id);
        setProteinData(response.data);
        
        // If structure data is included
        if (response.data.structure) {
          setStructureData(response.data.structure);
          console.log("Structure data from main response:", response.data.structure);
        } else {
          // Otherwise fetch it separately
          try {
            const structureResponse = await apiService.getProteinStructure(response.data.id);
            setStructureData(structureResponse);
            console.log("Structure data fetched separately:", structureResponse);
          } catch (error) {
            console.error("Error fetching structure data:", error);
            setStructureData(null);
          }
        }
        
        // If interactions are included in the response
        if (response.visualization_data && response.visualization_type === 'interactions') {
          console.log("Interaction data from visualization_data:", response.visualization_data);
          setInteractionsData(response.visualization_data);
          setActiveTab(1); // Switch to Interaction Network tab
        } else if (response.data.interactions && response.data.interactions.length > 0) {
          setInteractionsData(response.data.interactions);
          console.log("Interactions from main response:", response.data.interactions);
        } else {
          // Fetch interactions separately
          await handleInteractionsResponse(response.data.id);
        }
        
        // If knowledge graph is included in the response
        if (response.visualization_data && response.visualization_type === 'knowledge_graph') {
          console.log("Knowledge graph from visualization_data:", response.visualization_data);
          setKnowledgeGraphData(response.visualization_data);
          setActiveTab(2); // Switch to Knowledge Graph tab
        } else {
          // Always fetch knowledge graph data separately
          try {
            console.log("Fetching knowledge graph separately for:", response.data.id);
            // Add a timeout to prevent hanging and multiple identical requests
            const knowledgeGraphPromise = apiService.getKnowledgeGraph(response.data.id, 'Protein');
            const timeoutPromise = new Promise((_, reject) => 
              setTimeout(() => reject(new Error('Knowledge graph request timed out')), 15000)
            );
            
            const knowledgeGraphResponse = await Promise.race([knowledgeGraphPromise, timeoutPromise]);
            console.log("Knowledge graph API response:", knowledgeGraphResponse);
            
            if (knowledgeGraphResponse && 
                knowledgeGraphResponse.nodes && 
                Array.isArray(knowledgeGraphResponse.nodes) && 
                knowledgeGraphResponse.edges && 
                Array.isArray(knowledgeGraphResponse.edges)) {
                
              console.log("Valid knowledge graph data structure with:", 
                knowledgeGraphResponse.nodes.length, "nodes and", 
                knowledgeGraphResponse.edges.length, "edges");
              setKnowledgeGraphData(knowledgeGraphResponse);
            } else {
              console.warn("Invalid knowledge graph data structure:", knowledgeGraphResponse);
              setKnowledgeGraphData(null);
            }
          } catch (error) {
            console.error("Error or timeout fetching knowledge graph:", error);
            setKnowledgeGraphData(null);
          }
        }
        
        // Determine which visualization tab to show based on query content
        if (searchQuery.toLowerCase().includes('interaction') || 
            searchQuery.toLowerCase().includes('network')) {
          setActiveTab(1); // Interaction Network tab
        } else if (searchQuery.toLowerCase().includes('knowledge graph') || 
                   searchQuery.toLowerCase().includes('graph')) {
          setActiveTab(2); // Knowledge Graph tab
        }
        
        // Set follow-up suggestions based on the protein
        setFollowUpSuggestions([
          `How does ${response.data.id} relate to cancer?`,
          `What drugs target ${response.data.id}?`,
          `Show me the knowledge graph for ${response.data.id}`,
          `Show interactions for ${response.data.id}`
        ]);
        
      } else if (response.follow_up_suggestions && response.follow_up_suggestions.length > 0) {
        setFollowUpSuggestions(response.follow_up_suggestions);
      } else {
        // Default suggestions
        setFollowUpSuggestions([
          'Tell me about TP53',
          'What is a protein?',
          'Show me the structure of BRCA1'
        ]);
      }
      
    } catch (error) {
      console.error("API call failed:", error);
      
      // Add error message to chat
      setMessages(prevMessages => [
        ...prevMessages,
        {
          type: 'system',
          content: "Sorry, I encountered an error processing your request. Please try again later."
        }
      ]);
      
      // Set default suggestions
      setFollowUpSuggestions([
        'Try searching for TP53',
        'What is a protein?',
        'Show structures'
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle fetching protein diseases
  const fetchProteinDiseases = async (proteinId) => {
    try {
      console.log("Fetching diseases for:", proteinId);
      const response = await apiService.getProteinDiseases(proteinId);
      console.log("Disease API response:", response);
      
      // Check if the response contains visualization data for knowledge graph
      if (response && response.knowledge_graph && 
          response.knowledge_graph.nodes && 
          response.knowledge_graph.edges) {
        console.log("Knowledge graph data found in diseases response:", response.knowledge_graph);
        // Update the knowledge graph data and switch to that tab
        setKnowledgeGraphData(response.knowledge_graph);
        setActiveTab(2); // Switch to Knowledge Graph tab
        return response.diseases || []; // Return just the diseases part
      }
      
      // If response is just an array, it's only disease data
      return Array.isArray(response) ? response : [];
    } catch (error) {
      console.error("Error fetching disease data:", error);
      return [];
    }
  };

  // Handle the interactions API response properly with knowledge graph data if available
  const handleInteractionsResponse = async (proteinId) => {
    try {
      console.log("Fetching interactions separately for:", proteinId);
      const interactionsResponse = await apiService.getProteinInteractions(proteinId);
      console.log("Interactions API response:", interactionsResponse);
      
      // Check if the response is a complex object with interactions and knowledge graph
      if (interactionsResponse && typeof interactionsResponse === 'object' && !Array.isArray(interactionsResponse)) {
        // If it has interactions array, extract it
        if (interactionsResponse.interactions && Array.isArray(interactionsResponse.interactions)) {
          setInteractionsData(interactionsResponse.interactions);
          console.log("Interactions data extracted:", interactionsResponse.interactions.length, "interactions");
        }
        
        // If it has knowledge graph data, extract and use it
        if (interactionsResponse.knowledge_graph && 
            interactionsResponse.knowledge_graph.nodes && 
            Array.isArray(interactionsResponse.knowledge_graph.nodes)) {
          console.log("Knowledge graph found in interactions response:", 
            interactionsResponse.knowledge_graph.nodes.length, "nodes",
            interactionsResponse.knowledge_graph.edges.length, "edges");
          setKnowledgeGraphData(interactionsResponse.knowledge_graph);
        }
        
        // If visualization type is specified, switch to that tab
        if (interactionsResponse.visualization_type) {
          if (interactionsResponse.visualization_type === 'knowledge_graph') {
            setActiveTab(2); // Knowledge Graph tab
          } else if (interactionsResponse.visualization_type === 'network_and_graph') {
            // For network_and_graph, prefer the knowledge graph tab if we have data
            if (interactionsResponse.knowledge_graph && 
                interactionsResponse.knowledge_graph.nodes && 
                interactionsResponse.knowledge_graph.nodes.length > 0) {
              setActiveTab(2); // Knowledge Graph tab
            } else {
              setActiveTab(1); // Interaction Network tab
            }
          }
        }
      } 
      // If the response is just an array, it's only interactions data
      else if (Array.isArray(interactionsResponse)) {
        setInteractionsData(interactionsResponse);
        console.log("Simple array of interactions received:", interactionsResponse.length, "interactions");
      } else {
        console.warn("Unexpected interaction data format:", interactionsResponse);
        setInteractionsData([]);
      }
    } catch (error) {
      console.error("Error fetching interaction data:", error);
      setInteractionsData([]);
    }
  };

  // Submit handler for the search form
  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      handleSearch(query);
      setQuery('');
    }
  };

  // Handle clicking on a follow-up suggestion
  const handleFollowUpClick = (question) => {
    setQuery('');
    handleSearch(question);
  };

  // Get current date for the footer
  const getCurrentDate = () => {
    const date = new Date();
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    }).format(date);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-blue-500 text-white py-4 shadow-md">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex flex-col items-center text-center">
            <h1 className="text-3xl font-bold font-display">
              AminoVerse
            </h1>
            <p className="text-md opacity-90 mt-1">
              ChatGPT for Proteins
            </p>
          </div>
        </div>
      </header>
      
      {/* Main content - Two-panel layout */}
      <div className="max-w-7xl mx-auto py-6 px-4">
        <div className="flex flex-col lg:flex-row lg:h-[calc(90vh-100px)] gap-4">
          {/* Left panel: Conversation interface */}
          <div className="flex-1 bg-white rounded-lg shadow-sm overflow-hidden border border-gray-200 flex flex-col">
            {/* Chat messages area */}
            <div className="flex-1 p-4 overflow-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent">
              <div className="flex flex-col space-y-4">
                {messages.map((message, index) => (
                  <ChatMessage 
                    key={index} 
                    message={message} 
                    isLast={index === messages.length - 1} 
                  />
                ))}
                
                {/* Loading spinner */}
                {isLoading && (
                  <div className="flex justify-center py-4">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                  </div>
                )}
                
                {/* Invisible element for scroll reference */}
                <div ref={messagesEndRef} />
              </div>
            </div>
            
            {/* Follow-up suggestions */}
            {followUpSuggestions.length > 0 && !isLoading && (
              <div className="p-4 border-t border-gray-200">
                <p className="text-xs text-gray-500 mb-2">
                  Suggested follow-ups:
                </p>
                <div className="flex flex-wrap">
                  {followUpSuggestions.map((question, index) => (
                    <FollowUpChip
                      key={index}
                      question={question}
                      onClick={handleFollowUpClick}
                    />
                  ))}
                </div>
              </div>
            )}
            
            {/* Input area */}
            <div className="p-4 border-t border-gray-200">
              <form onSubmit={handleSubmit}>
                <div className="flex">
                  <input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Ask about a protein or enter follow-up questions..."
                    className="flex-1 bg-gray-100 rounded-md px-4 py-2 mr-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white disabled:opacity-50"
                    disabled={isLoading}
                  />
                  <button
                    type="submit"
                    className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-md disabled:opacity-50"
                    disabled={isLoading}
                  >
                    {isLoading ? 'Processing...' : 'Send'}
                  </button>
                </div>
              </form>
            </div>
          </div>
          
          {/* Right panel: Visualization area */}
          <div className="flex-1 bg-white rounded-lg shadow-sm overflow-hidden border border-gray-200 flex flex-col">
            {/* Custom tabs implementation */}
            <div className="flex flex-col h-full">
              {/* Tab buttons */}
              <div className="flex">
                <button 
                  className={`flex-1 py-2 ${activeTab === 0 ? 'bg-blue-500 text-white' : 'text-blue-500'} ${activeTab === 0 ? 'border-b-2 border-blue-700' : ''}`}
                  onClick={() => setActiveTab(0)}
                >
                  3D Structure
                </button>
                <button 
                  className={`flex-1 py-2 ${activeTab === 1 ? 'bg-blue-500 text-white' : 'text-blue-500'} ${activeTab === 1 ? 'border-b-2 border-blue-700' : ''}`}
                  onClick={() => setActiveTab(1)}
                >
                  Interaction Network
                </button>
                <button 
                  className={`flex-1 py-2 ${activeTab === 2 ? 'bg-blue-500 text-white' : 'text-blue-500'} ${activeTab === 2 ? 'border-b-2 border-blue-700' : ''}`}
                  onClick={() => setActiveTab(2)}
                >
                  Knowledge Graph
                </button>
              </div>
              
              {/* Tab content */}
              <div className="flex-1 overflow-auto p-4">
                {activeTab === 0 ? (
                  <ProteinStructureVisualizer 
                    proteinId={activeProtein} 
                    structureData={structureData}
                  />
                ) : activeTab === 1 ? (
                  <InteractionNetworkVisualizer 
                    interactions={interactionsData} 
                    proteinId={activeProtein}
                  />
                ) : (
                  <KnowledgeGraphVisualizer 
                    graphData={knowledgeGraphData}
                    entityId={activeProtein}
                    entityType="Protein"
                  />
                )}
              </div>
            </div>
            
            {/* Footer with data sources */}
            <div className="p-3 text-xs text-gray-500 border-t border-gray-200 flex justify-between items-center">
              <div>
                <p>Data sources: UniProt, PDB, STRING-db, Neo4j Knowledge Graph</p>
                <p>Last updated: {getCurrentDate()}</p>
              </div>
              <button
                onClick={() => setIsStatusPanelVisible(true)}
                className="text-blue-500 hover:underline text-sm"
              >
                View System Status
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Service Status Panel */}
      <ServiceStatusPanel 
        isVisible={isStatusPanelVisible} 
        onClose={() => setIsStatusPanelVisible(false)} 
      />
    </div>
  );
};

export default AminoVerseUI;