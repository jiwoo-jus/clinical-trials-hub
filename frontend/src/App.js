// src/App.js
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import SearchPage from './pages/SearchPage';
import DetailPage from './pages/DetailPage';
import History from './pages/History';
import ManualPage from './pages/ManualPage';
import './styles/index.css';

function App() {
  console.log('Current environment:', process.env.NODE_ENV);
  console.log('API URL:', process.env.REACT_APP_API_URL);
  console.log('All env vars:', Object.keys(process.env).filter(key => key.startsWith('REACT_APP_')));

  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<SearchPage />} />
          <Route path="/detail" element={<DetailPage />} />
          <Route path="/history" element={<History />} />
          <Route path="/about" element={<ManualPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
