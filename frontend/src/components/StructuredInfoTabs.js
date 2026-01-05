import PropTypes from 'prop-types';
import React, { useState } from 'react';

import ProtocolSection from './ProtocolSection';
import ResultsSection from './ResultSection';
// import AnnotationSection from './AnnotationSection';
import DocumentSection from './DocumentSection';
import DerivedSection from './DerivedSection';

/**
 * StructuredInfoTabs:
 * - Provides top-level tabs for each structured section.
 * - On tab click, renders FoldableNode tree for that section.
 * - Root label is hidden (nodeKey=""), rendering starts from depth 0.
 */

const StructuredInfoTabs = ({ structuredInfo }) => {
  const [active, setActive] = useState('Protocol');

  const tabs = [
    { key: 'Protocol', label: 'Protocol Section' },
    { key: 'Results', label: 'Results Section' },
    // { key: 'Annotation', label: 'Annotation Section' },
    { key: 'Document', label: 'Document Section' },
    { key: 'Derived', label: 'Derived Section' },
  ];

  if (!structuredInfo) return <div>No structured info available.</div>;

  // Check if this is an excluded secondary literature type
  if (structuredInfo._excluded_type && structuredInfo._message) {
    return (
      <div className="flex justify-center items-center text-custom-text-subtle p-6">
        <div className="text-center">
          <p className="text-sm font-medium">{structuredInfo._message}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col">
      <nav className="border-b border-custom-border mb-4">
        <ul className="flex space-x-4">
          {tabs.map(t => (
            <li key={t.key}>
              <button
                className={`pb-2 ${
                  active === t.key
                    ? 'border-b-2 border-custom-blue-deep text-custom-blue-deep'
                    : 'text-custom-text-subtle'
                }`}
                onClick={() => setActive(t.key)}
              >
                {t.label}
              </button>
            </li>
          ))}
        </ul>
      </nav>

      <div className="flex-1 min-w-0 overflow-x-auto overflow-y-hidden">
        {active === 'Protocol' && (
          <ProtocolSection data={structuredInfo.protocolSection} />
        )}
        {active === 'Results' && (
          <ResultsSection data={structuredInfo.resultsSection} />
        )}
        {/* {active === 'Annotation' && (
          <AnnotationSection data={structuredInfo.annotationSection} />
        )} */}
        {active === 'Document' && (
          <DocumentSection data={structuredInfo.documentSection} />
        )}
        {active === 'Derived' && (
          <DerivedSection data={structuredInfo.derivedSection} />
        )}
      </div>
    </div>
  );
};

StructuredInfoTabs.propTypes = {
  structuredInfo: PropTypes.object.isRequired,
};

export default StructuredInfoTabs;