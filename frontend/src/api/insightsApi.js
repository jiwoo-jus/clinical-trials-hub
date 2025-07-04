import api from './index';

// Generate AI insights for search results
export const generateInsights = async (searchKey, page = 1, appliedFilters = null) => {
  try {
    const response = await api.post('/api/insights/generate-insights', {
      search_key: searchKey,
      page: page,
      applied_filters: appliedFilters
    });
    return response.data;
  } catch (error) {
    console.error('Error generating insights:', error);
    throw error;
  }
};

// Chat about insights and search results
export const chatWithInsights = async (searchKey, message, page = 1, chatHistory = [], appliedFilters = null) => {
  try {
    const response = await api.post('/api/insights/chat', {
      search_key: searchKey,
      message: message,
      page: page,
      chat_history: chatHistory,
      applied_filters: appliedFilters
    });
    return response.data;
  } catch (error) {
    console.error('Error in chat:', error);
    throw error;
  }
};
