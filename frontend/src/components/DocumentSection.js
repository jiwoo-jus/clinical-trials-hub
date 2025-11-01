import React from 'react';
import PropTypes from 'prop-types';
import { ObjectTable, Collapsible } from './StructuredInfoFunctions';

const DocumentSection = ({ data = {} }) => {
  // data may be undefined, default to {}
  const { largeDocumentModule = {} } = data;

  const rmfields=["typeAbbrev", "hasProtocol", "hasSap", "hasIcf", "filename", "size"]
  const cleanup = (arrobj) => {
    if (!Array.isArray(arrobj)) return [];
    return arrobj.map(obj => {
      const b = { ...obj };
      rmfields.forEach(field => {
        delete b[field];
      })
      return b;
    });
  };

  return (
    <div>
      <Collapsible title="Large Documents" defaultOpen>
        <ObjectTable field="Documents" data={cleanup(largeDocumentModule.largeDocs)} />
      </Collapsible>
    </div>
  );
};

DocumentSection.propTypes = {
  data: PropTypes.object
};

DocumentSection.defaultProps = {
  data: {}
};

export default DocumentSection;