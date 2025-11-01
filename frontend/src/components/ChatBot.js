import { ChevronsDownUp, ChevronsUpDown, Clipboard, ClipboardCheck, SendHorizontal, TextSearch } from 'lucide-react';
// Added useEffect
import PropTypes from 'prop-types';
// src/components/ChatBot.js
import React, { useEffect, useState } from 'react';

import api from '../api';

// Assuming api is your configured Axios instance

function copyToClipboard(text) {
  return navigator.clipboard.writeText(text); // Return the promise
}

// Updated ChatMessage component
const ChatMessage = ({ message, onToggle, onEvidenceClick, canHighlightEvidence }) => {
  const [isCopied, setIsCopied] = useState(false);

  const handleCopyAll = () => {
    // Ensure evidence items are stringified for copying if they are objects
    const evidenceString = message.evidence?.map(evi =>
        getEvidenceAsString(evi) // Use the helper which now cleans quotes
      ).join('\n') || '';
    const textToCopy = `Q: ${message.question}\nA: ${message.answer}${evidenceString ? '\nEvidence:\n' + evidenceString : ''}`;
    copyToClipboard(textToCopy).then(() => {
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 1500);
    }).catch(err => console.error('Failed to copy:', err));
  };

  // Helper function to safely convert evidence item to a string AND clean quotes
  const getEvidenceAsString = (evi) => {
    let str = '';
    if (typeof evi === 'string') {
      str = evi;
    } else if (typeof evi === 'object' && evi !== null) {
      try {
        // Return stringified JSON (pretty-printed)
        str = JSON.stringify(evi, null, 2);
      } catch (e) {
        console.error("Failed to stringify evidence object:", evi, e);
        str = "[Object Conversion Error]"; // Return an error string
      }
    } else if (evi === null || evi === undefined) {
        str = ""; // Return empty string
    } else {
      // Fallback for other types
      str = String(evi);
    }
    // Clean surrounding quotes
    return str.trim().replace(/^['"]|['"]$/g, '');
  };

  // Helper function to render the answer, handling potential objects
  const renderAnswer = (answer) => {
    if (typeof answer === 'string') {
      return answer;
    } else if (typeof answer === 'object' && answer !== null) {
      try {
        // Convert object to a readable string format (pretty-printed JSON)
        return JSON.stringify(answer, null, 2);
      } catch (e) {
        console.error("Failed to stringify answer object:", answer, e);
        return "[Invalid Answer Format]";
      }
    }
    // Handle null, undefined, or other types gracefully
    return String(answer ?? ''); // Use nullish coalescing for undefined/null
  };

  return (
    <div className="mb-4 bg-white border border-custom-border rounded-2xl shadow-sm p-4 text-sm group"> {/* Added group class */}
      {/* Question */}
      <div className="flex items-start gap-2 mb-3">
        <strong className="text-custom-blue-deep">Q:</strong>
        <div className="flex-1 whitespace-pre-wrap text-custom-text">{message.question}</div>
      </div>

      {/* Answer & Evidence (Conditional) */}
      {message.expanded ? (
        <>
          <div className="flex items-start gap-2 mb-3">
            <strong className="text-custom-blue-deep">A:</strong>
            {/* Check if the original answer was an object to decide on rendering style */}
            {typeof message.answer === 'object' && message.answer !== null ? (
              <pre className="flex-1 whitespace-pre-wrap text-custom-text bg-gray-50 p-1 rounded text-xs">
                {renderAnswer(message.answer)}
              </pre>
            ) : (
              <div className="flex-1 whitespace-pre-wrap text-custom-text">
                {renderAnswer(message.answer)}
              </div>
            )}
          </div>

          {/* Evidence */}
          {message.evidence?.length > 0 && (
            <div className="mb-3">
              <strong className="block mb-1 text-custom-blue-deep">Evidence:</strong>
              <ul className="list-none space-y-2 pl-0">
                {message.evidence.map((evi, idx) => {
                  // Determine if the original evidence was an object (before cleaning)
                  const isObjectEvidence = typeof evi === 'object' && evi !== null && !Array.isArray(evi);
                  // Get the cleaned string representation using the helper
                  const evidenceString = getEvidenceAsString(evi);

                  // Check if the evidence can be highlighted using the passed function
                  const canHighlight = evidenceString && canHighlightEvidence(evidenceString);

                  return (
                    <li key={idx} className="flex items-start gap-2">
                      <button
                        className={`text-xs mt-1 p-0 leading-none flex-shrink-0 rounded-full focus:outline-none focus:ring-1 focus:ring-offset-1 ${ // Added focus style
                          canHighlight
                            ? 'text-custom-blue hover:text-custom-blue-hover cursor-pointer focus:ring-custom-blue' // Style for highlightable
                            : 'text-gray-400 cursor-not-allowed' // Style for non-highlightable
                        }`}
                        onClick={() => {
                            // Only trigger click if highlightable and string exists
                            if (canHighlight && evidenceString) {
                                onEvidenceClick(evidenceString); // Pass cleaned string
                            }
                        }}
                        disabled={!canHighlight} // Disable button if cannot highlight
                        title={canHighlight ? "Highlight evidence in text" : "Evidence not found in text"} // Dynamic title
                      >
                        <TextSearch size={14} strokeWidth={2} /> {/* Use TextSearch icon */}
                      </button>
                      <div className="flex-1 min-w-0"> {/* Added flex-1 and min-w-0 for proper wrapping */}
                        {/* Conditionally wrap the string output in <pre> if it came from an object */}
                        {isObjectEvidence ? (
                          <pre className="text-xs bg-gray-100 p-1 rounded overflow-x-auto whitespace-pre-wrap break-words">{/* Added whitespace/break */}
                            {evidenceString}
                          </pre>
                        ) : (
                          // Render string directly
                          <span className="whitespace-pre-wrap break-words text-xs">{/* Added text-xs for consistency */}
                            {evidenceString}
                          </span>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </>
      ) : (
        <div className="italic text-custom-text-subtle">(Answer collapsed)</div>
      )}

      {/* Action Buttons */}
      <div className="flex flex-wrap items-center gap-2 mt-4"> {/* Use flex-wrap */}
        <button
          onClick={onToggle}
          className="p-1.5 text-custom-blue-deep rounded-full hover:bg-custom-blue-lightest transition-colors"
          title={message.expanded ? 'Collapse' : 'Expand'}
        >
          {message.expanded ? <ChevronsDownUp size={16} strokeWidth={2.5}/> : <ChevronsUpDown size={16} strokeWidth={2.5}/>} {/* Icons */}
        </button>
        <button
          onClick={handleCopyAll}
          className="p-1.5 text-custom-blue-deep rounded-full hover:bg-custom-blue-lightest transition-colors"
          title="Copy Q&A"
        >
          {isCopied ? <ClipboardCheck size={16} strokeWidth={2.5} className="block" /> : <Clipboard size={16} strokeWidth={2.5} className="block" />} {/* Icons */}
        </button>
      </div>
    </div>
  );
};

// Update ChatBot component to accept and pass down canHighlightEvidence
const ChatBot = ({ paperId, data, source, relevantId, onResponse, onEvidenceClick, canHighlightEvidence }) => {
  const [question, setQuestion] = useState('');
  const [conversation, setConversation] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null); // State for displaying errors

  // Log props whenever they change
  useEffect(() => {
    console.log("ChatBot Props Updated:", { paperId, data: data ? data.substring(0, 50) + '...' : null, source, relevantId });
  }, [paperId, data, source, relevantId]);

  const handleAsk = async () => {
    setError(null); // Clear previous errors
    console.log("handleAsk triggered. Current state/props:", { question, loading, source, relevantId, dataExists: !!data });

    if (!question.trim() || loading) {
        console.warn("Ask prevented: Empty question or already loading.");
        return;
    }
    // --- Crucial Check ---
    if (!source || !relevantId) {
        console.error("ChatBot Error: Missing required props 'source' or 'relevantId'. Cannot send request.");
        setError("Cannot send chat request: Missing required context (source or ID). Please reload or navigate back.");
        return;
    }
    if (!data) {
        console.error("ChatBot Error: Missing 'data' prop (content). Cannot send request.");
        setError("Cannot send chat request: Missing content data. Please reload or navigate back.");
        return;
    }
    // --- End Crucial Check ---

    setLoading(true);
    try {
      // Construct payload matching the backend Pydantic model keys exactly
      const payload = {
        source: source,       // Matches ChatRequest.source
        id: relevantId,       // Matches ChatRequest.id
        userQuestion: question, // Matches ChatRequest.userQuestion
        content: data         // Matches ChatRequest.content
      };

      // console.log("Sending chat payload to /api/chat:", JSON.stringify(payload, null, 2)); // Log the exact payload being sent

      // Ensure the endpoint URL is correct (without trailing slash if router expects that)
      const response = await api.post('/api/chat', payload); // Send payload as JSON body

      console.log("Chat API Response:", response.data); // Log successful response

      const newMessage = {
        question,
        answer: response.data.answer,
        evidence: response.data.evidence || [],
        expanded: true,
      };

      setConversation(prev => [...prev, newMessage]);
      setQuestion('');
      if (onResponse) onResponse(response.data);
    } catch (err) {
      console.error('Chat error:', err);
      let detail = "An unknown error occurred.";
      if (err.response) {
          // The request was made and the server responded with a status code
          // that falls out of the range of 2xx
          console.error("Error Response Data:", err.response.data);
          console.error("Error Response Status:", err.response.status);
          console.error("Error Response Headers:", err.response.headers);
          detail = `Server responded with ${err.response.status}. `;
          if (err.response.data && err.response.data.detail) {
              // Try to get specific detail from FastAPI validation error
              if (Array.isArray(err.response.data.detail)) {
                  detail += err.response.data.detail.map(d => `${d.loc.join('.')} - ${d.msg}`).join('; ');
              } else if (typeof err.response.data.detail === 'string') {
                  detail += err.response.data.detail;
              } else {
                  detail += JSON.stringify(err.response.data.detail);
              }
          } else if (typeof err.response.data === 'string') {
              detail += err.response.data;
          }
      } else if (err.request) {
          // The request was made but no response was received
          console.error("Error Request:", err.request);
          detail = "No response received from server. Check network connection or server status.";
      } else {
          // Something happened in setting up the request that triggered an Error
          console.error('Error Message:', err.message);
          detail = err.message;
      }
      setError(`Chat failed: ${detail}`); // Set user-facing error
    } finally {
      setLoading(false);
    }
  };

  const toggleMessage = (index) => {
    setConversation(prev =>
      prev.map((msg, i) =>
        i === index ? { ...msg, expanded: !msg.expanded } : msg
      )
    );
  };

  return (
    <div className="flex flex-col h-full"> {/* Ensure ChatBot takes height */}
      {/* Conversation Area */}
      <div className="flex-1 overflow-y-auto mb-4 pr-2"> {/* Added padding-right */}
        {conversation.map((msg, index) => (
          <ChatMessage
            key={index}
            message={msg}
            onToggle={() => toggleMessage(index)}
            onEvidenceClick={onEvidenceClick}
            // Pass the function down to each message
            canHighlightEvidence={canHighlightEvidence}
          />
        ))}
        {loading && (
          <div className="flex justify-center items-center p-4">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-custom-blue-deep"></div>
            <span className="ml-2 text-custom-text-subtle">Thinking...</span>
          </div>
        )}
        {error && (
          <div className="p-3 mb-4 bg-red-100 border border-red-400 text-red-700 rounded text-sm">
            <strong>Error:</strong> {error}
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="flex items-center gap-3 mt-auto border-custom-border pt-1"> {/* Added border-top and padding-top */}
        <input
          type="text"
          placeholder={`Ask about ${relevantId || 'current paper'}`}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleAsk()}
          disabled={loading}
          className="flex-1 border border-custom-border rounded px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-custom-blue" // Changed focus ring color
        />
        <button
          onClick={handleAsk}
          disabled={loading}
          className={`p-2 rounded-md transition-colors ${ // Removed background, size classes, adjusted padding
            loading
              ? 'text-custom-disabled cursor-not-allowed' // Use text color for disabled state
              : 'text-custom-blue-deep hover:bg-custom-blue-lightest' // Set text color, add subtle hover background
          }`}
          aria-label="Ask question" // Add aria-label for accessibility
        >
          <SendHorizontal size={20} strokeWidth={2.5} /> {/* Use SendHorizontal icon, adjusted size and strokeWidth for boldness */}
        </button>
      </div>
    </div>
  );
};

// Update PropTypes for ChatBot
ChatBot.propTypes = {
  paperId: PropTypes.string,
  data: PropTypes.string,
  source: PropTypes.string,
  relevantId: PropTypes.string,
  onResponse: PropTypes.func,
  onEvidenceClick: PropTypes.func,
  canHighlightEvidence: PropTypes.func, // Add prop type for the function
};

// Update PropTypes for ChatMessage
ChatMessage.propTypes = {
  message: PropTypes.shape({
    question: PropTypes.string,
    answer: PropTypes.string,
    evidence: PropTypes.arrayOf(PropTypes.oneOfType([PropTypes.string, PropTypes.object])),
    expanded: PropTypes.bool,
  }).isRequired,
  onToggle: PropTypes.func.isRequired,
  onEvidenceClick: PropTypes.func.isRequired,
  canHighlightEvidence: PropTypes.func.isRequired, // Add prop type for the function
};

export default ChatBot;
