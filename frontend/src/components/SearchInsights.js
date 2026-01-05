import React, { useState, useEffect, useCallback } from 'react';
import PropTypes from 'prop-types';
import { generateInsights, chatWithInsights } from '../api/insightsApi';
import { MessageCircle, Send, Lightbulb, TrendingUp, Target, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react';

const SearchInsights = ({ searchKey, page, appliedFilters, results }) => {
  // Cache insights per searchKey
  const [insightsCache, setInsightsCache] = useState({});
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showChat, setShowChat] = useState(false);
  const [chatHistory, setChatHistory] = useState([]);
  const [chatMessage, setChatMessage] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false); // Default to collapsed
  const [currentSearchKey, setCurrentSearchKey] = useState(null);
  const [lastPage, setLastPage] = useState(null);

  // Generate insights asynchronously - only called for new searches
  const generateInsightsData = useCallback(async () => {
    // Check cache first
    if (insightsCache[searchKey]) {
      console.log('[Insights] Using cached insights for:', searchKey);
      setInsights(insightsCache[searchKey]);
      return;
    }

    setLoading(true);
    setError(null);
    // Don't auto-expand, keep collapsed
    
    try {
      console.log('[Insights] Generating NEW insights for:', { searchKey, page: 1, appliedFilters });
      // Always use page 1 for initial insights generation
      const data = await generateInsights(searchKey, 1, appliedFilters);
      console.log('[Insights] Generated insights:', data);
      const newInsights = data.insights;
      setInsights(newInsights);
      
      // Cache the insights
      setInsightsCache(prev => ({
        ...prev,
        [searchKey]: newInsights
      }));
    } catch (err) {
      console.error('[Insights] Error:', err);
      setError('Failed to generate insights. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [searchKey, appliedFilters, insightsCache]);

  // When searchKey changes (new search), generate new insights
  useEffect(() => {
    if (searchKey && searchKey !== currentSearchKey && results?.results?.length > 0) {
      console.log('[Insights] New search detected, searchKey changed from', currentSearchKey, 'to', searchKey);
      setCurrentSearchKey(searchKey);
      setLastPage(page);
      setError(null);
      setChatHistory([]);
      setIsExpanded(false); // Always keep collapsed
      
      // Small delay to allow search results to render first
      setTimeout(() => {
        generateInsightsData();
      }, 100);
    }
  }, [searchKey, currentSearchKey, results?.results?.length, page, generateInsightsData]);

  // When page changes within same search, keep collapsed
  useEffect(() => {
    if (searchKey === currentSearchKey && page !== lastPage && lastPage !== null) {
      console.log('[Insights] Page changed from', lastPage, 'to', page, '- keeping collapsed');
      setIsExpanded(false);
      setLastPage(page);
    }
  }, [page, lastPage, searchKey, currentSearchKey]);

  const handleChatSubmit = async (e) => {
    e.preventDefault();
    if (!chatMessage.trim() || chatLoading) return;

    const userMessage = chatMessage.trim();
    setChatMessage('');
    setChatLoading(true);

    // Add user message to chat history immediately
    const newUserMessage = { role: 'user', message: userMessage };
    const updatedHistory = [...chatHistory, newUserMessage];
    setChatHistory(updatedHistory);

    try {
      // Always use page 1 for chat context (insights are generated from page 1)
      const response = await chatWithInsights(
        searchKey,
        userMessage,
        1, // Use page 1 since insights are based on page 1
        updatedHistory.slice(0, -1), // Don't include the just-added user message
        appliedFilters
      );

      // Add assistant response to chat history
      setChatHistory(response.chat_history);
    } catch (err) {
      console.error('[Chat] Error:', err);
      // Remove the user message if chat failed
      setChatHistory(chatHistory);
      setError('Failed to send message. Please try again.');
    } finally {
      setChatLoading(false);
    }
  };

  const toggleChat = () => {
    setShowChat(!showChat);
  };

  const toggleExpanded = () => {
    setIsExpanded(!isExpanded);
  };

  if (!searchKey || !results?.results?.length) {
    return null;
  }

  return (
    <div className="w-full max-w-7xl mx-auto px-4 mb-6">
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        {/* Header */}
        <div 
          className="flex items-center justify-between p-4 cursor-pointer border-b border-gray-100"
          onClick={toggleExpanded}
        >
          <div className="flex items-center gap-3">
            <Lightbulb className="w-5 h-5 text-blue-600" />
            <h3 className="text-lg font-semibold text-gray-900">
              AI Insights & Analysis
            </h3>
            <span className="text-sm text-gray-500">
              ({results.results.length} items analyzed)
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={(e) => {
                e.stopPropagation();
                toggleChat();
              }}
              className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition"
              title="Chat about results"
            >
              <MessageCircle className="w-4 h-4" />
            </button>
            {isExpanded ? (
              <ChevronUp className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            )}
          </div>
        </div>

        {/* Content */}
        {isExpanded && (
          <div className="p-4">
            {loading && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
                <div className="flex items-center justify-center mb-4">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                  <span className="ml-3 text-blue-800 font-medium">Generating AI insights...</span>
                </div>
                <p className="text-blue-700 text-sm text-center">
                  Analyzing {results.results.length} research items to provide comprehensive insights and trends
                </p>
                <div className="mt-4 text-xs text-blue-600 text-center">
                  This may take 10-30 seconds to complete
                </div>
              </div>
            )}

            {!loading && !insights && !error && (
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 text-center">
                <Lightbulb className="w-8 h-8 text-gray-400 mx-auto mb-3" />
                <p className="text-gray-600">
                  AI insights will appear here once analysis is complete
                </p>
              </div>
            )}

            {error && (
              <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700">
                <AlertCircle className="w-4 h-4" />
                <span>{error}</span>
                <button
                  onClick={generateInsightsData}
                  className="ml-auto px-3 py-1 bg-red-100 hover:bg-red-200 rounded text-sm"
                >
                  Retry
                </button>
              </div>
            )}

            {insights && !loading && (
              <div className="space-y-4">
                {/* Summary */}
                {insights.summary && (
                  <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                    <h4 className="font-medium text-blue-900 mb-2">Research Overview</h4>
                    <p className="text-blue-800">{insights.summary}</p>
                  </div>
                )}

                <div className="grid md:grid-cols-2 gap-4">
                  {/* Key Findings */}
                  {insights.key_findings && insights.key_findings.length > 0 && (
                    <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                      <div className="flex items-center gap-2 mb-3">
                        <Target className="w-4 h-4 text-green-600" />
                        <h4 className="font-medium text-green-900">Key Findings</h4>
                      </div>
                      <ul className="space-y-2">
                        {insights.key_findings.map((finding, index) => (
                          <li key={index} className="text-green-800 text-sm">
                            • {finding}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Trends */}
                  {insights.trends && insights.trends.length > 0 && (
                    <div className="p-4 bg-purple-50 rounded-lg border border-purple-200">
                      <div className="flex items-center gap-2 mb-3">
                        <TrendingUp className="w-4 h-4 text-purple-600" />
                        <h4 className="font-medium text-purple-900">Research Trends</h4>
                      </div>
                      <ul className="space-y-2">
                        {insights.trends.map((trend, index) => (
                          <li key={index} className="text-purple-800 text-sm">
                            • {trend}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Recommendations */}
                  {insights.recommendations && insights.recommendations.length > 0 && (
                    <div className="p-4 bg-amber-50 rounded-lg border border-amber-200">
                      <div className="flex items-center gap-2 mb-3">
                        <Lightbulb className="w-4 h-4 text-amber-600" />
                        <h4 className="font-medium text-amber-900">Recommendations</h4>
                      </div>
                      <ul className="space-y-2">
                        {insights.recommendations.map((rec, index) => (
                          <li key={index} className="text-amber-800 text-sm">
                            • {rec}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Research Gaps */}
                  {insights.research_gaps && insights.research_gaps.length > 0 && (
                    <div className="p-4 bg-red-50 rounded-lg border border-red-200">
                      <div className="flex items-center gap-2 mb-3">
                        <AlertCircle className="w-4 h-4 text-red-600" />
                        <h4 className="font-medium text-red-900">Research Gaps</h4>
                      </div>
                      <ul className="space-y-2">
                        {insights.research_gaps.map((gap, index) => (
                          <li key={index} className="text-red-800 text-sm">
                            • {gap}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Chat Section */}
            {showChat && (
              <div className="mt-6 border-t border-gray-200 pt-4">
                <div className="bg-gray-50 rounded-lg p-4">
                  <h4 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
                    <MessageCircle className="w-4 h-4" />
                    Ask questions about these results
                  </h4>
                  
                  {/* Chat History */}
                  {chatHistory.length > 0 && (
                    <div className="max-h-64 overflow-y-auto mb-4 space-y-3">
                      {chatHistory.map((msg, index) => (
                        <div
                          key={index}
                          className={`p-3 rounded-lg ${
                            msg.role === 'user'
                              ? 'bg-blue-100 text-blue-900 ml-8'
                              : 'bg-white text-gray-900 mr-8 border border-gray-200'
                          }`}
                        >
                          <div className="text-xs font-medium mb-1 opacity-75">
                            {msg.role === 'user' ? 'You' : 'AI Assistant'}
                          </div>
                          <div className="text-sm">{msg.message}</div>
                        </div>
                      ))}
                      {chatLoading && (
                        <div className="bg-white text-gray-900 mr-8 border border-gray-200 p-3 rounded-lg">
                          <div className="text-xs font-medium mb-1 opacity-75">AI Assistant</div>
                          <div className="flex items-center gap-2">
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                            <span className="text-sm">Thinking...</span>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Chat Input */}
                  <form onSubmit={handleChatSubmit} className="flex gap-2">
                    <input
                      type="text"
                      value={chatMessage}
                      onChange={(e) => setChatMessage(e.target.value)}
                      placeholder="Ask about the research patterns, trends, or specific findings..."
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      disabled={chatLoading}
                    />
                    <button
                      type="submit"
                      disabled={!chatMessage.trim() || chatLoading}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                      <Send className="w-4 h-4" />
                    </button>
                  </form>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

SearchInsights.propTypes = {
  searchKey: PropTypes.string,
  page: PropTypes.number,
  appliedFilters: PropTypes.object,
  results: PropTypes.shape({
    results: PropTypes.arrayOf(PropTypes.object),
    total: PropTypes.number,
    counts: PropTypes.object
  })
};

export default SearchInsights;
