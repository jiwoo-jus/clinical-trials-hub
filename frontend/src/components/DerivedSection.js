import React from 'react';
import PropTypes from 'prop-types';
import { ObjectTable, Collapsible } from './StructuredInfoFunctions';

const DerivedSection = ({ data = {} }) => {
  const { 
    conditionBrowseModule = {},
    interventionBrowseModule = {},
  } = data;

  // Helper function to rename 'id' to 'MeSH ID' in each object of the array
  const renameIdField = (arr) => {
    if (!Array.isArray(arr)) return arr;
    return arr.map(({ id, ...rest }) => ({
      ...(id !== undefined ? { 'MeSH ID': id } : {}),
      ...rest,
    }));
  };

  return (
    <div>
      <Collapsible title="Condition Browse" defaultOpen>
        <ObjectTable field="Condition MeSH Terms" data={renameIdField(conditionBrowseModule?.meshes)} />
        <ObjectTable field="Condition MeSH Ancestor Terms" data={renameIdField(conditionBrowseModule?.ancestors)} />
        <ObjectTable field="Condition Leaf Browsing Topics" data={renameIdField(conditionBrowseModule?.browseLeaves)} />
        <ObjectTable field="Condition Branch Browsing Topics" data={renameIdField(conditionBrowseModule?.browseBranches)} />
      </Collapsible>

      <Collapsible title="Intervention Browse" defaultOpen>
        <ObjectTable field="Intervention MeSH Terms" data={renameIdField(interventionBrowseModule?.meshes)} />
        <ObjectTable field="Intervention MeSH Ancestor Terms" data={renameIdField(interventionBrowseModule?.ancestors)} />
        <ObjectTable field="Intervention Leaf Browsing Topics" data={renameIdField(interventionBrowseModule?.browseLeaves)} />
        <ObjectTable field="Intervention Branch Browsing Topics" data={renameIdField(interventionBrowseModule?.browseBranches)} />
      </Collapsible>
    </div>
  );
}

DerivedSection.propTypes = {
  data: PropTypes.object
};
DerivedSection.defaultProps = {
  data: {}
};

export default DerivedSection;