// src/api/searchApi.js
import axios from 'axios';

const BASE_URL = (() => {
  const url = process.env.REACT_APP_API_URL;
  console.log('SearchAPI Environment URL:', url);
  console.log('SearchAPI Node Environment:', process.env.NODE_ENV);
  
  if (process.env.NODE_ENV === 'development') {
    return url || 'http://localhost:5050';
  }
  
  if (!url || url.startsWith('http://')) {
    return 'https://cth-backend-103266204202.us-central1.run.app';
  }
  
  return url;
})();

console.log('SearchAPI Final BASE_URL:', BASE_URL);

export const searchClinicalTrials = async (params) => {
  try {
    console.log('Making request to:', `${BASE_URL}/api/search`);
    const response = await axios.post(`${BASE_URL}/api/search`, params);
    return response.data;
  } catch (error) {
    console.error('API request failed:', error);
    throw error;
  }
};

export const filterSearchResults = async (params) => {
  try {
    console.log('Making filter request to:', `${BASE_URL}/api/search/filter`);
    const response = await axios.post(`${BASE_URL}/api/search/filter`, params);
    return response.data;
  } catch (error) {
    console.error('Filter API request failed:', error);
    throw error;
  }
};