// src/api/index.js
import axios from 'axios';

// Ensure BASE_URL defaults to HTTPS if it's missing or starts with HTTP
const BASE_URL = (() => {
  const url = process.env.REACT_APP_API_URL;
  console.log('Environment API URL:', url);
  console.log('Node Environment:', process.env.NODE_ENV);
  
  // If the environment variable is not set, default to localhost
  if (process.env.NODE_ENV === 'development') {
    return url || 'http://localhost:5050';
  }
  
  // Within production, enforce HTTPS
  if (!url || url.startsWith('http://')) {
    return 'https://cth-backend-103266204202.us-central1.run.app';
  }
  
  return url;
})();

console.log('Final BASE_URL:', BASE_URL);

const api = axios.create({
  baseURL: BASE_URL,
});

export default api;
