/* eslint-disable react/prop-types */

import React, { useState } from 'react';
import { Plus, X, ChevronDown, ChevronUp } from 'lucide-react';
import PropTypes from 'prop-types';

/**
 * EligibilityCriteria (refined)
 * - 리스트를 번호/불릿 마커로 간결하게 표현
 * - 과도한 박스/배경 제거, 색상 포인트만 유지
 */
const EligibilityCriteria = ({ 
  inclusionCriteria, 
  setInclusionCriteria, 
  exclusionCriteria, 
  setExclusionCriteria 
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [newInclusion, setNewInclusion] = useState('');
  const [newExclusion, setNewExclusion] = useState('');

  const hasAnyCriteria = inclusionCriteria.length > 0 || exclusionCriteria.length > 0;

  const addInclusionCriterion = () => {
    if (newInclusion.trim()) {
      setInclusionCriteria([...inclusionCriteria, newInclusion.trim()]);
      setNewInclusion('');
    }
  };

  const removeInclusionCriterion = (index) => {
    setInclusionCriteria(inclusionCriteria.filter((_, i) => i !== index));
  };

  const addExclusionCriterion = () => {
    if (newExclusion.trim()) {
      setExclusionCriteria([...exclusionCriteria, newExclusion.trim()]);
      setNewExclusion('');
    }
  };

  const removeExclusionCriterion = (index) => {
    setExclusionCriteria(exclusionCriteria.filter((_, i) => i !== index));
  };

  const handleKeyDown = (e, addFunction) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addFunction();
    }
  };

  // 리스트 공통 렌더러 (numbered=true면 1.2.3. 번호, false면 불릿)
  const CriteriaList = ({ items, onRemove, accent, numbered = true }) => {
    const markerColor =
      accent === 'inclusion' ? 'marker:text-emerald-600' : 'marker:text-rose-600';

    const ListTag = numbered ? 'ol' : 'ul';
    const listClasses = [
      numbered ? 'list-decimal' : 'list-disc',
      'pl-6',                   // 마커 여백
      'space-y-2',              // 항목 간격 (가독성 개선)
      markerColor,              // 마커 색상
    ].join(' ');

    return (
      <ListTag className={listClasses}>
        {items.map((criterion, index) => (
          <li
            key={`${accent}-${index}`}
            className="relative pr-8 text-[14px] text-custom-text leading-relaxed"
          >
            {/* 텍스트 영역 */}
            <div className="whitespace-pre-wrap break-words">
              {criterion}
            </div>

            {/* 삭제 버튼: 호버 시 강조, 평소엔 은은하게 */}
            <button
              onClick={() => onRemove(index)}
              className="absolute right-0 top-0 text-gray-300 hover:text-gray-600"
              aria-label={`Remove ${accent} criterion ${index + 1}`}
            >
              <X size={16} />
            </button>

            {/* 항목 간 얇은 구분선 */}
            {index < items.length - 1 && (
              <div className="mt-2 border-b border-custom-border/70" />
            )}
          </li>
        ))}
      </ListTag>
    );
  };

  return (
    <div className="w-full bg-white rounded-2xl shadow-sm border border-custom-border mb-4 overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-5 py-3.5 flex items-center justify-between text-left hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-custom-text text-base">Eligibility Criteria</h3>
          {hasAnyCriteria && !isExpanded && (
            <span className="text-[11px] bg-gray-100 text-gray-700 px-2 py-0.5 rounded-md border border-custom-border">
              {inclusionCriteria.length + exclusionCriteria.length}
            </span>
          )}
        </div>
        {isExpanded ? <ChevronUp size={18} className="text-custom-text-subtle" /> : <ChevronDown size={18} className="text-custom-text-subtle" />}
      </button>

      {/* Expandable Content */}
      {isExpanded && (
        <div className="px-5 pb-5 pt-0 border-t border-custom-border rounded-b-2xl">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Inclusion Column */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <h4 className="font-medium text-custom-text text-[15px] mt-2.5">Inclusion</h4>
              </div>

              {/* 리스트: 번호표 스타일 */}
              <CriteriaList
                items={inclusionCriteria}
                onRemove={removeInclusionCriterion}
                accent="inclusion"
                numbered={true} // ← 불릿으로 바꾸려면 false
              />

              {/* 입력 영역 (미니멀) */}
              <div className="mt-3 flex gap-3 items-center pl-2">
                <input
                  type="text"
                  value={newInclusion}
                  onChange={(e) => setNewInclusion(e.target.value)}
                  onKeyDown={(e) => handleKeyDown(e, addInclusionCriterion)}
                  placeholder="Add new inclusion criterion..."
                  className="flex-1 px-0 py-2 border-b border-custom-border focus:outline-none focus:border-gray-400 text-[14px]"
                />
                <button
                  onClick={addInclusionCriterion}
                  className="text-custom-text-subtle rounded-md hover:bg-gray-50 transition-colors flex items-center justify-center"
                  aria-label="Add inclusion criterion"
                >
                  <Plus size={16} />
                </button>
              </div>
            </div>

            {/* Exclusion Column */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <h4 className="font-medium text-custom-text text-[15px] mt-2.5">Exclusion</h4>
              </div>

              {/* 리스트: 번호표 스타일 (불릿 원하면 numbered={false}) */}
              <CriteriaList
                items={exclusionCriteria}
                onRemove={removeExclusionCriterion}
                accent="exclusion"
                numbered={true}
              />

              {/* 입력 영역 (미니멀) */}
              <div className="mt-3 flex gap-3 items-center pl-2">
                <input
                  type="text"
                  value={newExclusion}
                  onChange={(e) => setNewExclusion(e.target.value)}
                  onKeyDown={(e) => handleKeyDown(e, addExclusionCriterion)}
                  placeholder="Add new exclusion criterion..."
                  className="flex-1 px-0 py-2 border-b border-custom-border focus:outline-none focus:border-gray-400 text-[14px]"
                />
                <button
                  onClick={addExclusionCriterion}
                  className="text-custom-text-subtle rounded-md hover:bg-gray-50 transition-colors flex items-center justify-center"
                  aria-label="Add exclusion criterion"
                >
                  <Plus size={16} />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

EligibilityCriteria.propTypes = {
  inclusionCriteria: PropTypes.arrayOf(PropTypes.string).isRequired,
  setInclusionCriteria: PropTypes.func.isRequired,
  exclusionCriteria: PropTypes.arrayOf(PropTypes.string).isRequired,
  setExclusionCriteria: PropTypes.func.isRequired,
};

export default EligibilityCriteria;
