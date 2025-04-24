import React from 'react';
import './App.css';
import AminoVerseUI from './components/AminoVerseUI';
import ErrorBoundary from './components/ErrorBoundary';

function App() {
  return (
    <div className="App">
      <ErrorBoundary>
        <AminoVerseUI />
      </ErrorBoundary>
    </div>
  );
}

export default App;
