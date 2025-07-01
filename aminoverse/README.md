# AminoVerse Frontend

![React](https://img.shields.io/badge/React-18+-61DAFB?style=flat&logo=react&logoColor=white)
![Node.js](https://img.shields.io/badge/Node.js-18+-339933?style=flat&logo=node.js&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3+-06B6D4?style=flat&logo=tailwindcss&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

AminoVerse is an interactive protein research platform that provides comprehensive protein information through an intuitive chat interface. The frontend application offers protein visualization, knowledge graph exploration, and structure analysis capabilities.

## Features

### Core Functionality
- **Interactive Chat Interface**: Natural language queries for protein research
- **Protein Information Retrieval**: Comprehensive protein data from multiple databases
- **3D Structure Visualization**: Integration with PDB and AlphaFold viewers
- **Knowledge Graph Visualization**: Interactive network graphs showing protein relationships
- **Real-time Service Status Monitoring**: Backend service health indicators

### Visualization Components
- **3D Protein Structure Viewer**: Embedded viewers for PDB and AlphaFold structures
- **Interactive Knowledge Graphs**: Cytoscape.js-powered network visualizations
- **Protein Interaction Networks**: Visual representation of protein-protein interactions
- **Service Status Dashboard**: Real-time monitoring of backend services

### User Interface Features
- **Modern Responsive Design**: Tailwind CSS-powered UI with scientific theme
- **Tabbed Interface**: Organized views for different data types
- **Error Handling**: Comprehensive error boundaries and user feedback
- **Loading States**: Smooth loading indicators and skeleton screens

## Technology Stack

### Frontend Framework
- **React 19.1**: Modern React with latest features and hooks
- **Create React App**: Development and build tooling

### UI/UX Libraries
- **Tailwind CSS 3+**: Utility-first CSS framework with custom scientific theme
- **Chakra UI**: Component library for enhanced UI elements
- **Framer Motion**: Animation library for smooth transitions

### Visualization Libraries
- **Cytoscape.js**: Network graph visualization
- **React Cytoscape**: React wrapper for Cytoscape.js
- **MolStar**: Advanced molecular structure visualization

### Networking & State Management
- **Axios**: HTTP client for API communication
- **React Hooks**: Built-in state management with useState and useEffect

### Development Tools
- **Jest**: Testing framework
- **React Testing Library**: Component testing utilities
- **PostCSS**: CSS processing and optimization

## Prerequisites

Before running the application, ensure you have:

- **Node.js**: Version 18.0 or higher
- **npm**: Version 8.0 or higher (comes with Node.js)
- **Backend Services**: AminoVerse backend running on localhost:8000

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/aminoverse.git
   cd aminoverse/aminoverse
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Verify installation**
   ```bash
   npm audit
   ```

## Running the Application

### Development Mode

1. **Start the development server**
   ```bash
   npm start
   ```

2. **Access the application**
   - Open [http://localhost:3000](http://localhost:3000) in your browser
   - The page will automatically reload when you make changes
   - Console will display any lint errors

### Production Build

1. **Create production build**
   ```bash
   npm run build
   ```

2. **Serve production build locally (optional)**
   ```bash
   npx serve -s build
   ```

### Using Batch/PowerShell Scripts

For Windows users, convenience scripts are provided:

- **Batch file**: Double-click `start-app.bat`
- **PowerShell**: Run `./start-app.ps1` in PowerShell

## Environment Configuration

### Development Environment
- **API Base URL**: `http://localhost:8000`
- **Hot Reload**: Enabled
- **Source Maps**: Enabled

### Production Environment
- **API Base URL**: Configurable via environment variables
- **Optimized Bundle**: Minified and optimized for performance
- **Service Worker**: Optional PWA support

## Project Structure

```
aminoverse/
├── public/                 # Static assets
│   ├── index.html         # HTML template
│   ├── favicon.ico        # Application icon
│   └── manifest.json      # PWA manifest
├── src/
│   ├── components/        # React components
│   │   ├── AminoVerseUI.js    # Main application component
│   │   └── ErrorBoundary.js   # Error handling wrapper
│   ├── services/          # API and utility services
│   │   ├── api.js         # Backend API client
│   │   └── statusChecker.js   # Service health monitoring
│   ├── App.js             # Root application component
│   ├── index.js           # Application entry point
│   ├── theme.js           # Custom theme configuration
│   └── index.css          # Global styles
├── package.json           # Project dependencies and scripts
├── tailwind.config.js     # Tailwind CSS configuration
└── postcss.config.js      # PostCSS configuration
```

## Available Scripts

### Development Scripts
- `npm start`: Start development server with hot reload
- `npm test`: Run test suite in interactive watch mode
- `npm run build`: Create optimized production build
- `npm run eject`: Eject from Create React App (irreversible)

### Testing
```bash
# Run all tests
npm test

# Run tests with coverage
npm test -- --coverage

# Run tests in CI mode
CI=true npm test
```

## Backend Integration

The frontend communicates with the AminoVerse backend API:

- **Chat Endpoint**: `/api/chat` - Natural language protein queries
- **Health Check**: `/` - Backend service status
- **Service Status**: `/api/status` - Individual service health monitoring

Ensure the backend is running on `http://localhost:8000` before starting the frontend.

## Browser Support

- **Chrome**: 90+
- **Firefox**: 88+
- **Safari**: 14+
- **Edge**: 90+

## Troubleshooting

### Common Issues

1. **Port 3000 in use**
   ```bash
   # Kill process on port 3000
   npx kill-port 3000
   # Or use different port
   PORT=3001 npm start
   ```

2. **Node modules issues**
   ```bash
   # Clear cache and reinstall
   rm -rf node_modules package-lock.json
   npm install
   ```

3. **Backend connection errors**
   - Verify backend is running on localhost:8000
   - Check service status in the application UI
   - Review browser console for network errors

### Performance Optimization

- Use production build for deployment
- Enable gzip compression on server
- Implement code splitting for large applications
- Monitor bundle size with `npm run build`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

