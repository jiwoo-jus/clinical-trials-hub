import React from 'react';
import PropTypes from 'prop-types';
import { CheckCircle, XCircle, HelpCircle } from 'lucide-react';

/**
 * EligibilityCheckResults Component
 * 
 * Displays the results of systematic review eligibility criteria checking.
 * Shows compliance status, confidence scores, and evidence for each criterion.
 */
const EligibilityCheckResults = ({ results, isLoading }) => {
  if (isLoading) {
    return (
      <div className="py-4 px-4 bg-blue-50 rounded-lg border border-blue-200">
        <div className="flex items-center gap-2">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-custom-blue"></div>
          <span className="text-sm text-gray-600">Checking eligibility criteria...</span>
        </div>
      </div>
    );
  }

  if (!results) {
    return null;
  }

  const { inclusion_results, exclusion_results } = results;

  const hasResults = (inclusion_results && inclusion_results.length > 0) || 
                    (exclusion_results && exclusion_results.length > 0);

  if (!hasResults) {
    return null;
  }

  // Helper function to get status badge
  const getStatusBadge = (status, isExclusion = false) => {
    if (status === 'met') {
      return isExclusion ? (
        <div className="flex items-center gap-1 text-red-600">
          <XCircle size={16} />
          <span className="text-xs font-medium">Violated</span>
        </div>
      ) : (
        <div className="flex items-center gap-1 text-green-600">
          <CheckCircle size={16} />
          <span className="text-xs font-medium">Met</span>
        </div>
      );
    } else if (status === 'not_met') {
      return isExclusion ? (
        <div className="flex items-center gap-1 text-green-600">
          <CheckCircle size={16} />
          <span className="text-xs font-medium">Not violated</span>
        </div>
      ) : (
        <div className="flex items-center gap-1 text-red-600">
          <XCircle size={16} />
          <span className="text-xs font-medium">Not Met</span>
        </div>
      );
    } else {
      return (
        <div className="flex items-center gap-1 text-gray-500">
          <HelpCircle size={16} />
          <span className="text-xs font-medium">Unclear</span>
        </div>
      );
    }
  };

  // Helper function to render confidence bar
  const renderConfidenceBar = (confidence, status, isExclusion = false) => {
    const percentage = Math.round(confidence * 100);
    
    // Determine color based on status and criterion type
    let colorClass = 'bg-orange-500'; // default for unclear
    if (status === 'met') {
      colorClass = isExclusion ? 'bg-red-500' : 'bg-green-500';
    } else if (status === 'not_met') {
      colorClass = isExclusion ? 'bg-green-500' : 'bg-red-500';
    }

    return (
      <div className="flex items-center gap-2 mt-1">
        <div className="flex-1 bg-gray-200 rounded-full h-1.5">
          <div
            className={`h-1.5 rounded-full ${colorClass}`}
            style={{ width: `${percentage}%` }}
          />
        </div>
        <span className="text-xs text-gray-600 font-medium">{percentage}%</span>
      </div>
    );
  };

  // Calculate counts from results
  const calculateCounts = () => {
    let metCount = 0;
    let notMetCount = 0;
    let unclearCount = 0;

    // Inclusion criteria: met = good, not_met = bad
    (inclusion_results || []).forEach(result => {
      if (result.status === 'met') metCount++;
      else if (result.status === 'not_met') notMetCount++;
      else unclearCount++;
    });

    // Exclusion criteria: not_met = good (not violated), met = bad (should exclude)
    (exclusion_results || []).forEach(result => {
      if (result.status === 'not_met') metCount++; // Not violated = good
      else if (result.status === 'met') notMetCount++; // Violated = bad
      else unclearCount++;
    });

    return { metCount, notMetCount, unclearCount };
  };

  const { metCount, notMetCount, unclearCount } = calculateCounts();

  return (
    <div className="space-y-4">
      {/* Overall Recommendation */}
      <div className="bg-white rounded-lg p-4">
        <h4 className="text-sm font-medium text-gray-900 mb-3">Eligibility Assessment</h4>
        
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-green-500"></div>
            <span className="text-gray-700">Met {metCount}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-red-500"></div>
            <span className="text-gray-700">Not met {notMetCount}</span>
          </div>
          {unclearCount > 0 && (
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-orange-500"></div>
              <span className="text-gray-700">Unclear {unclearCount}</span>
            </div>
          )}
        </div>
      </div>

      {/* Inclusion Criteria Results */}
      {inclusion_results && inclusion_results.length > 0 && (
        <div>
          <h4 className="font-semibold text-gray-900 mb-2">Inclusion Criteria</h4>
          <div className="space-y-3">
            {inclusion_results.map((result, index) => (
              <div
                key={`inclusion-${index}`}
                className="bg-white rounded-lg p-3 border border-gray-200 shadow-sm"
              >
                <div className="flex items-start justify-between mb-2">
                  <p className="text-sm text-gray-900 font-semibold flex-1">{result.criterion}</p>
                  {getStatusBadge(result.status, false)}
                </div>
                {/* Truth value chip */}
                <div className="mb-2">
                  <span className="text-xs text-gray-500 mr-1">Truth:</span>
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${
                    result.status === 'unclear'
                      ? 'bg-orange-50 text-orange-700 border-orange-200'
                      : result.is_true
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : 'bg-rose-50 text-rose-700 border-rose-200'
                  }`}>
                    {result.status === 'unclear' ? 'Unclear' : result.is_true ? 'True' : 'False'}
                  </span>
                </div>
                
                {/* Confidence */}
                <div className="mb-2">
                  <span className="text-xs text-gray-500">Confidence:</span>
                  {renderConfidenceBar(result.confidence, result.status, false)}
                </div>

                {/* Evidence */}
                {result.evidence && (
                  <div className="mb-2">
                    <div className="text-[13px] text-gray-700 font-medium">Evidence</div>
                    <p className="text-sm text-gray-800 mt-1 pl-3 border-l border-gray-300 leading-relaxed">
                      {result.evidence}
                    </p>
                  </div>
                )}

                {/* Reasoning */}
                {result.reasoning && (
                  <div>
                    <div className="text-[13px] text-gray-700 font-medium">Reasoning</div>
                    <p className="text-sm text-gray-800 mt-1 leading-relaxed">{result.reasoning}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Exclusion Criteria Results */}
      {exclusion_results && exclusion_results.length > 0 && (
        <div>
          <h4 className="font-semibold text-gray-900 mb-2">Exclusion Criteria</h4>
          <div className="space-y-3">
            {exclusion_results.map((result, index) => (
              <div
                key={`exclusion-${index}`}
                className="bg-white rounded-lg p-3 border border-gray-200 shadow-sm"
              >
                <div className="flex items-start justify-between mb-2">
                  <p className="text-sm text-gray-900 font-semibold flex-1">{result.criterion}</p>
                  {getStatusBadge(result.status, true)}
                </div>
                {/* Truth value chip */}
                <div className="mb-2">
                  <span className="text-xs text-gray-500 mr-1">Truth:</span>
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${
                    result.status === 'unclear'
                      ? 'bg-orange-50 text-orange-700 border-orange-200'
                      : result.is_true
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : 'bg-rose-50 text-rose-700 border-rose-200'
                  }`}>
                    {result.status === 'unclear' ? 'Unclear' : result.is_true ? 'True' : 'False'}
                  </span>
                </div>
                
                {/* Confidence */}
                <div className="mb-2">
                  <span className="text-xs text-gray-500">Confidence:</span>
                  {renderConfidenceBar(result.confidence, result.status, true)}
                </div>

                {/* Evidence */}
                {result.evidence && (
                  <div className="mb-2">
                    <div className="text-[13px] text-gray-700 font-medium">Evidence</div>
                    <p className="text-sm text-gray-800 mt-1 pl-3 border-l border-gray-300 leading-relaxed">
                      {result.evidence}
                    </p>
                  </div>
                )}

                {/* Reasoning */}
                {result.reasoning && (
                  <div>
                    <div className="text-[13px] text-gray-700 font-medium">Reasoning</div>
                    <p className="text-sm text-gray-800 mt-1 leading-relaxed">{result.reasoning}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

EligibilityCheckResults.propTypes = {
  results: PropTypes.shape({
    pmcid: PropTypes.string,
    inclusion_results: PropTypes.arrayOf(
      PropTypes.shape({
        criterion: PropTypes.string.isRequired,
        status: PropTypes.string.isRequired,
        meets_criterion: PropTypes.bool,
  is_true: PropTypes.oneOfType([PropTypes.bool, PropTypes.oneOf([null])]),
        confidence: PropTypes.number.isRequired,
        evidence: PropTypes.string,
        reasoning: PropTypes.string,
      })
    ),
    exclusion_results: PropTypes.arrayOf(
      PropTypes.shape({
        criterion: PropTypes.string.isRequired,
        status: PropTypes.string.isRequired,
        meets_criterion: PropTypes.bool,
  is_true: PropTypes.oneOfType([PropTypes.bool, PropTypes.oneOf([null])]),
        confidence: PropTypes.number.isRequired,
        evidence: PropTypes.string,
        reasoning: PropTypes.string,
      })
    ),
    overall_recommendation: PropTypes.string.isRequired,
    summary: PropTypes.shape({
      inclusion_met: PropTypes.bool,
      exclusion_met: PropTypes.bool,
      avg_inclusion_confidence: PropTypes.number,
      avg_exclusion_confidence: PropTypes.number,
      has_unclear: PropTypes.bool,
      total_criteria: PropTypes.number,
      unclear_count: PropTypes.number,
    }),
  }),
  isLoading: PropTypes.bool,
};

export default EligibilityCheckResults;
