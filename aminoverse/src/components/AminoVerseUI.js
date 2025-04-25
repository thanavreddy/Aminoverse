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

// KnowledgeGraphVisualizer component for the knowledge graph visualization
const KnowledgeGraphVisualizer = ({ graphData, entityId, entityType = "Protein" }) => {
  const [visualState, setVisualState] = useState({
    loading: true,
    error: null,
    initialized: false
  });
  const cyRef = useRef(null);
  const containerRef = useRef(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [hoveredNode, setHoveredNode] = useState(null);
  const [legendVisible, setLegendVisible] = useState(true);
  
  // Track if component is mounted to prevent state updates after unmounting
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
      if (!nodes || !edges || !Array.isArray(nodes) || !Array.isArray(edges)) {
        console.warn("Invalid knowledge graph data structure");
        return [];
      }

      console.log(`Processing ${nodes.length} nodes and ${edges.length} edges`);

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
            case 'targets': return { color: '#34D399', width: 2.5 }; // green-400
            case 'associated_with': return { color: '#F87171', width: 2 }; // red-400
            case 'treats': return { color: '#60A5FA', width: 3 }; // blue-400
            case 'part_of': return { color: '#A78BFA', width: 2 }; // purple-400
            default: return { color: '#CBD5E1', width: 1 }; // slate-300
          }
        };

        const edgeStyle = getEdgeStyle(edge.type);

        return {
          data: {
            id: edge.id,
            source: edge.source,
            target: edge.target,
            type: edge.type || 'unknown',
            color: edge.color || edgeStyle.color,
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

  // Define Cytoscape stylesheet with enhanced styling
  const stylesheet = [
    // Node styling with improved visual appeal
    {
      selector: 'node',
      style: {
        'label': 'data(label)',
        'text-valign': 'center',
        'text-halign': 'center',
        'background-color': 'data(color)',
        'width': 'data(size)',
        'height': 'data(size)',
        'color': '#111827', // text color - gray-900
        'font-size': '10px',
        'text-wrap': 'wrap',
        'text-max-width': '80px',
        'text-outline-width': 2,
        'text-outline-color': '#ffffff',
        'text-outline-opacity': 0.9,
        'z-index': 10,
        'border-width': 1,
        'border-color': '#ffffff',
        'border-opacity': 0.8,
        'transition-property': 'background-color, border-color, border-width',
        'transition-duration': '0.3s'
      }
    },
    // Special styling for the main entity node
    {
      selector: 'node[centrality = 1]',
      style: {
        'border-width': 3,
        'border-color': '#2563EB', // blue-600
        'font-weight': 'bold',
        'font-size': '12px',
        'z-index': 20,
        'text-outline-width': 3,
        'text-background-opacity': 0.7,
        'text-background-color': '#ffffff',
        'text-background-padding': '2px',
        'text-border-opacity': 0.7,
        'box-shadow': '0 0 4px 2px rgba(59, 130, 246, 0.5)' // Subtle glow effect
      }
    },
    // Edge styling with improved visibility
    {
      selector: 'edge',
      style: {
        'width': 'data(width)',
        'line-color': 'data(color)',
        'target-arrow-color': 'data(color)',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        'opacity': 0.7,
        'transition-property': 'opacity, width, line-color',
        'transition-duration': '0.3s'
      }
    },
    // Hover states with smooth transitions
    {
      selector: 'node.hover',
      style: {
        'border-width': 3,
        'border-color': '#2563EB', // blue-600
        'border-opacity': 1,
        'background-color': function(ele) {
          return ele.data('color');
        },
        'background-opacity': 1,
        'z-index': 30,
        'overlay-opacity': 0.2,
        'overlay-color': '#ffffff'
      }
    },
    {
      selector: 'edge.hover',
      style: {
        'width': function(ele) {
          return ele.data('width') * 1.5;
        },
        'opacity': 1,
        'z-index': 30,
        'line-color': function(ele) {
          return ele.data('color');
        }
      }
    },
    // Selected node style
    {
      selector: 'node.selected',
      style: {
        'border-width': 4,
        'border-color': '#EA580C', // orange-600
        'border-opacity': 1,
        'box-shadow': '0 0 6px 3px rgba(234, 88, 12, 0.5)',
        'z-index': 999
      }
    },
    // Connected edges highlight
    {
      selector: 'edge.connected',
      style: {
        'opacity': 1,
        'width': function(ele) {
          return ele.data('width') * 1.5;
        },
        'z-index': 20
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
        const layoutOptions = elements.length <= 20 ? {
          name: 'concentric',
          fit: true,
          padding: 50,
          avoidOverlap: true,
          minNodeSpacing: 50,
          concentric: function(node) {
            // Central entity in the middle
            if (node.data('centrality') === 1) return 10;
            
            // Group by node type
            switch(node.data('type')?.toLowerCase()) {
              case 'protein': return 8;
              case 'disease': return 6;
              case 'drug': return 4;
              case 'pathway': return 2;
              default: return 0;
            }
          },
          levelWidth: function() { return 1; }
        } : {
          name: 'cose',
          fit: true,
          padding: 50,
          nodeRepulsion: 800000,
          nodeOverlap: 10,
          idealEdgeLength: 100,
          edgeElasticity: 100,
          nestingFactor: 5,
          gravity: 80,
          numIter: 1000,
          initialTemp: 200,
          coolingFactor: 0.95,
          minTemp: 1.0,
          animate: true,
          animationDuration: 800
        };
        
        // Apply the layout with animation
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
  
  // Add event handlers for interaction (hover, click)
  useEffect(() => {
    if (!cyRef.current) return;
    
    const cy = cyRef.current;
    
    // Hover events for nodes
    const onNodeMouseOver = (event) => {
      const node = event.target;
      node.addClass('hover');
      
      // Also highlight connected edges
      node.connectedEdges().addClass('hover');
      
      // Update hover state
      setHoveredNode(node.data());
    };
    
    const onNodeMouseOut = (event) => {
      const node = event.target;
      node.removeClass('hover');
      
      // Remove highlight from edges
      node.connectedEdges().removeClass('hover');
      
      // Clear hover state
      setHoveredNode(null);
    };
    
    // Click event for nodes
    const onNodeClick = (event) => {
      const node = event.target;
      
      // Clear previous selection
      cy.nodes().removeClass('selected');
      cy.edges().removeClass('connected');
      
      // Set new selection
      node.addClass('selected');
      
      // Highlight connected edges
      node.connectedEdges().addClass('connected');
      
      // Set selected node data for the info panel
      setSelectedNode(node.data());
    };
    
    // Background click to deselect
    const onBackgroundClick = () => {
      cy.nodes().removeClass('selected');
      cy.edges().removeClass('connected');
      setSelectedNode(null);
    };
    
    // Register event listeners
    cy.on('mouseover', 'node', onNodeMouseOver);
    cy.on('mouseout', 'node', onNodeMouseOut);
    cy.on('tap', 'node', onNodeClick);
    cy.on('tap', function(event) {
      if (event.target === cy) {
        onBackgroundClick();
      }
    });
    
    // Cleanup on unmount
    return () => {
      cy.removeListener('mouseover', 'node', onNodeMouseOver);
      cy.removeListener('mouseout', 'node', onNodeMouseOut);
      cy.removeListener('tap', 'node', onNodeClick);
      cy.removeListener('tap');
    };
  }, []);
  
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

  // No entity ID provided
  if (!entityId) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center bg-gray-50 border border-gray-200 rounded-lg">
        <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 text-gray-300 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M13.5 10.5L21 3m0 0l-7.5 7.5M21 3h-7.5m0 0v7.5M10.5 13.5L3 21m0 0l7.5-7.5M3 21h7.5m0 0v-7.5" />
        </svg>
        <p className="text-gray-600 font-medium">Select a protein to view its knowledge graph</p>
        <p className="text-gray-500 text-sm mt-2">The knowledge graph shows relationships between proteins and other biological entities.</p>
      </div>
    );
  }
  
  // Loading state
  if (visualState.loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 bg-white border border-gray-200 rounded-lg">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        <p className="text-gray-700 mt-4 font-medium">Loading knowledge graph...</p>
        <p className="text-gray-500 mt-2 text-sm">Building network for {entityId}</p>
        <div className="mt-6 bg-blue-50 p-3 rounded-md max-w-xs text-center">
          <p className="text-xs text-blue-700">Knowledge graphs provide insights into relationships between biological entities.</p>
        </div>
      </div>
    );
  }
  
  // Error state
  if (visualState.error) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center bg-white border border-gray-200 rounded-lg">
        <div className="mb-4 text-red-500">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <p className="text-gray-800 font-medium text-lg">Error showing knowledge graph</p>
        <p className="text-sm text-gray-600 mt-2 max-w-md">{visualState.error}</p>
        
        <div className="mt-6">
          <button 
            onClick={() => {
              setVisualState(prev => ({...prev, loading: true, error: null}));
              // This will trigger the useEffect to try reinitializing
              setTimeout(() => {
                if (cyRef.current) {
                  const layout = cyRef.current.layout({ name: 'cose' });
                  layout.run();
                }
              }, 500);
            }}
            className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  // No graph data
  if (!elements.length) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center bg-white border border-gray-200 rounded-lg">
        <div className="mb-4 text-gray-400">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M12 14h.01" />
          </svg>
        </div>
        <p className="text-gray-800 font-medium text-lg">No knowledge graph data found</p>
        <p className="text-sm text-gray-600 mt-2 max-w-md">
          No knowledge graph data is available for {entityId}.
        </p>
        
        <div className="mt-8 p-4 bg-blue-50 rounded-lg max-w-md">
          <h3 className="text-sm font-medium text-blue-800 mb-2">What is a Knowledge Graph?</h3>
          <p className="text-xs text-blue-700">
            A knowledge graph represents connections between proteins, diseases, genes, and other biological entities.
            It helps visualize how different biological components relate to each other.
          </p>
        </div>
      </div>
    );
  }

  // Success state - knowledge graph visualization
  return (
    <div className="h-full border border-gray-200 rounded-lg overflow-hidden bg-white shadow-sm flex flex-col">
      {/* Header with entity info */}
      <div className="p-2 border-b border-gray-200 flex justify-between items-center bg-gray-50">
        <div className="flex flex-col">
          <div className="flex items-center">
            <span className="font-medium text-gray-800">{entityId}</span>
            <span className="ml-2 px-2 py-0.5 bg-blue-100 text-blue-800 text-xs rounded-full font-medium">
              {graphData?.nodes?.length || 0} nodes
            </span>
            <span className="ml-1 px-2 py-0.5 bg-gray-100 text-gray-800 text-xs rounded-full">
              {graphData?.edges?.length || 0} connections
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            {entityType === "Protein" ? "Knowledge graph showing relationships for this protein" : 
             `Knowledge graph for ${entityType}`}
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          <button 
            onClick={() => setLegendVisible(!legendVisible)}
            className="text-xs text-blue-600 hover:bg-blue-50 px-2 py-1 rounded flex items-center"
            title="Toggle legend"
          >
            {legendVisible ? 'Hide Legend' : 'Show Legend'}
          </button>
        </div>
      </div>
      
      {/* Color legend */}
      {legendVisible && (
        <div className="px-3 py-2 border-b border-gray-200 bg-gray-50 flex flex-wrap justify-center gap-x-4 gap-y-2">
          <div className="flex items-center">
            <div className="w-3 h-3 rounded-full bg-blue-500 mr-1"></div>
            <span className="text-xs">Protein</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 rounded-full bg-red-500 mr-1"></div>
            <span className="text-xs">Disease</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 rounded-full bg-green-500 mr-1"></div>
            <span className="text-xs">Drug</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 rounded-full bg-purple-500 mr-1"></div>
            <span className="text-xs">Pathway</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 rounded-full bg-amber-500 mr-1"></div>
            <span className="text-xs">Gene</span>
          </div>
        </div>
      )}
      
      {/* Main content area: Graph + Info Panel */}
      <div className="flex flex-1 min-h-0">
        {/* Graph container */}
        <div className="flex-1 relative">
          <div ref={containerRef} className="h-full w-full">
            <CytoscapeComponent
              elements={elements}
              stylesheet={stylesheet}
              style={{ width: '100%', height: '100%' }} // Explicit dimensions
              layout={{ name: 'preset' }} // Initial layout, real layout applied in useEffect
              cy={(cy) => {
                cyRef.current = cy;
              }}
              className="h-full w-full"
              minZoom={0.15}
              maxZoom={3}
              wheelSensitivity={0.3}
              boxSelectionEnabled={false}
            />
            
            {/* Loading overlay while the graph is rendering */}
            {!visualState.initialized && (
              <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-75">
                <div className="flex flex-col items-center">
                  <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
                  <p className="mt-4 text-blue-800 font-medium">Generating graph visualization...</p>
                </div>
              </div>
            )}
            
            {/* Info tooltip for hovered node */}
            {hoveredNode && !selectedNode && (
              <div className="absolute bottom-4 right-4 bg-white p-3 shadow-lg rounded-lg border border-blue-100 z-50 max-w-xs">
                <p className="font-medium text-sm text-gray-800">{hoveredNode.label}</p>
                <p className="text-xs text-gray-600 mt-1">Type: <span className="font-medium capitalize">{hoveredNode.type || "Unknown"}</span></p>
                <p className="text-xs text-blue-500 mt-2">Click for more details</p>
              </div>
            )}
          </div>
        </div>
        
        {/* Info panel for selected node */}
        {selectedNode && (
          <div className="w-72 bg-gray-50 border-l border-gray-200 overflow-y-auto p-0">
            <div className="sticky top-0 bg-gray-100 p-3 border-b border-gray-200 flex justify-between items-center">
              <h3 className="font-medium text-gray-900 text-sm">Entity Details</h3>
              <button 
                onClick={() => setSelectedNode(null)}
                className="text-gray-500 hover:text-gray-700 p-1 rounded-full hover:bg-gray-200"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-3">
              <div className="flex items-center mb-3">
                <div 
                  className="w-5 h-5 rounded-full mr-2" 
                  style={{ backgroundColor: selectedNode.color }}
                ></div>
                <h4 className="text-sm font-bold text-gray-900 truncate">{selectedNode.label}</h4>
              </div>
              
              <div className="space-y-3">
                <div className="bg-white p-3 rounded-md border border-gray-200 shadow-sm">
                  <p className="text-xs text-gray-500 mb-1">ID:</p>
                  <p className="text-sm font-medium text-gray-900 break-all">{selectedNode.id}</p>
                </div>
                
                <div className="bg-white p-3 rounded-md border border-gray-200 shadow-sm">
                  <p className="text-xs text-gray-500 mb-1">Type:</p>
                  <div className="flex items-center">
                    <div className="w-3 h-3 rounded-full mr-2" style={{ backgroundColor: selectedNode.color }}></div>
                    <p className="text-sm font-medium capitalize">{selectedNode.type || "Unknown"}</p>
                  </div>
                </div>
                
                {selectedNode.description && (
                  <div className="bg-white p-3 rounded-md border border-gray-200 shadow-sm">
                    <p className="text-xs text-gray-500 mb-1">Description:</p>
                    <p className="text-sm">{selectedNode.description}</p>
                  </div>
                )}
                
                {selectedNode.type?.toLowerCase() === 'protein' && (
                  <div className="bg-blue-50 p-3 rounded-md border border-blue-100">
                    <p className="text-xs text-blue-800 font-medium mb-2">External Resources:</p>
                    <div className="flex flex-col space-y-2">
                      <a 
                        href={`https://www.uniprot.org/uniprotkb/${selectedNode.id.split('-')[0]}/entry`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-blue-600 hover:underline flex items-center"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 mr-1" viewBox="0 0 20 20" fill="currentColor">
                          <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
                          <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
                        </svg>
                        View in UniProt
                      </a>
                      <a 
                        href={`https://www.rcsb.org/search?q=${selectedNode.id.split('-')[0]}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-blue-600 hover:underline flex items-center"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 mr-1" viewBox="0 0 20 20" fill="currentColor">
                          <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
                          <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
                        </svg>
                        Find structures in PDB
                      </a>
                    </div>
                  </div>
                )}
                
                {selectedNode.type?.toLowerCase() === 'disease' && (
                  <div className="bg-red-50 p-3 rounded-md border border-red-100">
                    <a 
                      href={`https://www.ncbi.nlm.nih.gov/medgen/?term=${encodeURIComponent(selectedNode.label)}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-red-600 hover:underline flex items-center"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 mr-1" viewBox="0 0 20 20" fill="currentColor">
                        <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
                        <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
                      </svg>
                      Find on MedGen
                    </a>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
      
      {/* Control panel */}
      <div className="border-t border-gray-200 p-2 bg-gray-50 flex justify-between items-center">
        <div className="text-xs text-gray-500">
          {!selectedNode ? 
            'Click on nodes to see details' : 
            `Showing details for: ${selectedNode.label}`
          }
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => {
              if (cyRef.current) {
                cyRef.current.fit(undefined, 40);
              }
            }}
            className="px-2 py-1 bg-blue-100 hover:bg-blue-200 text-blue-700 rounded-md text-xs flex items-center transition-colors"
            title="Fit all nodes in view"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5v-4m0 4h-4m4 0l-5-5" />
            </svg>
            Fit
          </button>
          <button
            onClick={() => {
              if (cyRef.current) {
                cyRef.current.zoom(cyRef.current.zoom() * 1.5);
              }
            }}
            className="w-6 h-6 bg-blue-100 hover:bg-blue-200 text-blue-700 rounded-md text-xs flex items-center justify-center transition-colors"
            title="Zoom in"
          >
            +
          </button>
          <button
            onClick={() => {
              if (cyRef.current) {
                cyRef.current.zoom(cyRef.current.zoom() / 1.5);
              }
            }}
            className="w-6 h-6 bg-blue-100 hover:bg-blue-200 text-blue-700 rounded-md text-xs flex items-center justify-center transition-colors"
            title="Zoom out"
          >
            −
          </button>
          <button
            onClick={() => {
              if (cyRef.current) {
                // Reset everything to initial state
                cyRef.current.elements().removeClass('selected hover');
                cyRef.current.fit(undefined, 40);
                setSelectedNode(null);
                setHoveredNode(null);
                
                // Re-apply the layout
                const layout = cyRef.current.layout({
                  name: elements.length <= 20 ? 'concentric' : 'cose',
                  animate: true,
                  animationDuration: 800
                });
                layout.run();
              }
            }}
            className="px-2 py-1 bg-blue-100 hover:bg-blue-200 text-blue-700 rounded-md text-xs flex items-center transition-colors"
            title="Reset and relayout"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Reset
          </button>
        </div>
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

  // Handle the interactions API response properly with support for all response formats
  const handleInteractionsResponse = async (proteinId) => {
    try {
      console.log(`Fetching interactions for ${proteinId}...`);
      const response = await apiService.getProteinInteractions(proteinId);
      console.log("Interactions response received:", response);
      
      // Define initial variable to hold interaction data
      let processedInteractions = [];
      
      // Handle different response formats
      if (response && response.interactions && Array.isArray(response.interactions)) {
        // Format 1: Nested object with interactions array
        console.log("Found interactions in nested format:", response.interactions.length);
        processedInteractions = response.interactions;
      } else if (response && Array.isArray(response)) {
        // Format 2: Direct array format
        console.log("Found interactions in direct array format:", response.length);
        processedInteractions = response;
      } else if (typeof response === 'string') {
        // Format 3: String response that might be JSON
        try {
          const parsedData = JSON.parse(response);
          if (parsedData && parsedData.interactions && Array.isArray(parsedData.interactions)) {
            console.log("Parsed interactions from string:", parsedData.interactions.length);
            processedInteractions = parsedData.interactions;
          } else if (parsedData && Array.isArray(parsedData)) {
            console.log("Parsed interactions array from string:", parsedData.length);
            processedInteractions = parsedData;
          }
        } catch (parseError) {
          console.error("Error parsing interaction response string:", parseError);
        }
      } else if (response && typeof response === 'object') {
        // Format 4: Object but not in expected format, try to extract any array properties
        const potentialArrays = Object.values(response).filter(val => Array.isArray(val));
        
        if (potentialArrays.length > 0) {
          // Use the largest array found as likely being the interactions
          const largestArray = potentialArrays.reduce((prev, current) => 
            (current.length > prev.length) ? current : prev, []);
            
          if (largestArray.length > 0) {
            console.log("Found potential interactions array in response:", largestArray.length);
            processedInteractions = largestArray;
          }
        }
      }
      
      // If no valid interactions found, wait for API to fetch from LLM
      if (processedInteractions.length === 0) {
        console.log("No interactions found in initial response, might be loading from LLM. Displaying loading state.");
        // Set loading state to true while we wait for the LLM to generate data
        setIsLoading(true);
        
        try {
          // Try again with a slight delay to allow backend LLM to generate data
          console.log("Waiting for LLM-generated interactions...");
          await new Promise(resolve => setTimeout(resolve, 5000));
          
          // Second attempt to get interactions
          const secondResponse = await apiService.getProteinInteractions(proteinId);
          console.log("Second interaction response received:", secondResponse);
          
          // Process the second response
          if (secondResponse && Array.isArray(secondResponse)) {
            processedInteractions = secondResponse;
          } else if (secondResponse && secondResponse.interactions && Array.isArray(secondResponse.interactions)) {
            processedInteractions = secondResponse.interactions;
          }
        } catch (retryError) {
          console.error("Error during retry for interactions:", retryError);
        } finally {
          setIsLoading(false);
        }
        
        // If still no data, show an error state
        if (processedInteractions.length === 0) {
          console.error("No interaction data available for protein:", proteinId);
          setMessages(prev => [...prev, {
            type: 'system',
            content: `Could not retrieve interaction data for ${proteinId}. Please try again later.`
          }]);
        }
      }
      
      // Final validation and conversion of data
      const validatedInteractions = processedInteractions.map(interaction => {
        // Ensure all interactions have required fields with valid types
        return {
          protein_id: interaction.protein_id || interaction.id || `unknown-${Math.random().toString(36).substring(7)}`,
          protein_name: interaction.protein_name || interaction.name || "Unknown Protein",
          score: typeof interaction.score === 'number' ? interaction.score : 
                 parseFloat(interaction.score) || 0.5,
          evidence: interaction.evidence || interaction.source || "Not specified",
          is_llm_generated: Boolean(interaction.source && interaction.source.includes("LLM"))
        };
      });
      
      console.log(`Processed ${validatedInteractions.length} valid interactions`);
      
      // Set the interactions data and switch to the interactions tab
      setInteractionsData(validatedInteractions);
      
      // Check if the response also contains knowledge graph data
      if (response && response.knowledge_graph) {
        console.log("Knowledge graph data found in interactions response");
        setKnowledgeGraphData(response.knowledge_graph);
      }
      
      // Switch to the interactions tab
      setActiveTab(1);
    } catch (error) {
      console.error("Error fetching or processing interactions:", error);
      
      // Show error message to user
      setMessages(prev => [...prev, {
        type: 'system',
        content: `Error fetching interaction data: ${error.message}. Please try again later.`
      }]);
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