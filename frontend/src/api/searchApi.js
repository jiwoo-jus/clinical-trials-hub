// src/api/searchApi.js
/* eslint-disable no-undef */
import axios from 'axios';
import { apiLogger } from '../utils/logger';

const BASE_URL = (() => {
  const url = process.env.REACT_APP_API_URL;
  apiLogger.debug('Environment URL:', url);
  apiLogger.debug('Node Environment:', process.env.NODE_ENV);
  
  if (process.env.NODE_ENV === 'development') {
    return url || 'http://localhost:5050';
  }
  
  if (!url || url.startsWith('http://')) {
    return 'https://cth-backend-103266204202.us-central1.run.app';
  }
  
  return url;
})();

apiLogger.info('Final BASE_URL:', BASE_URL);

export const searchClinicalTrials = async (params) => {
  try {
    apiLogger.debug('Making request to:', `${BASE_URL}/api/search`);
    apiLogger.debug('🔍 [API] Request payload:', params);
    const response = await axios.post(`${BASE_URL}/api/search`, params);
    return response.data;
  } catch (error) {
    apiLogger.error('API request failed:', error);
    throw error;
  }
};

export const getPatientQueries = async (params) => {
  try {
    apiLogger.debug('Making request to:', `${BASE_URL}/api/search/patient`);
    const response = await axios.post(`${BASE_URL}/api/search/patient`, params);
    return response.data;
  } catch (error) {
    apiLogger.error('API request failed:', error);
    throw error;
  }
};

export const getPatientNextPage = async (params) => {
  try {
    apiLogger.debug('Making request to:', `${BASE_URL}/api/search/patient/paging`);
    apiLogger.debug('Pagination params:', params);
    const response = await axios.post(`${BASE_URL}/api/search/patient/paging`, params);
    apiLogger.debug('Pagination response:', response.data);
    return response.data;
  } catch (error) {
    apiLogger.error('API request failed:', error);
    throw error;
  }
};

export const getSearchNextPage = async (params) => {
  try {
    apiLogger.debug('Making request to:', `${BASE_URL}/api/search/paging`);
    apiLogger.debug('📄 Pagination params:', params);
    const response = await axios.post(`${BASE_URL}/api/search/paging`, params);
    apiLogger.debug('✅ Pagination response:', response.data);
    return response.data;
  } catch (error) {
    apiLogger.error('❌ Pagination API request failed:', error);
    throw error;
  }
};

export const filterSearchResults = async (params) => {
  try {
    apiLogger.debug('Making filter request to:', `${BASE_URL}/api/search/filter`);
    const response = await axios.post(`${BASE_URL}/api/search/filter`, params);
    return response.data;
  } catch (error) {
    apiLogger.error('Filter API request failed:', error);
    throw error;
  }
};