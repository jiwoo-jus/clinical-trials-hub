import PropTypes from 'prop-types';
import React, { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react'; 

const isArrayOfObjectsWithPrimitiveValues = (array) => {
  return (
    Array.isArray(array) &&
    array.every(
      (item) =>
        (typeof item === 'object' &&
          item !== null &&
          Object.values(item).every(
            (value) =>
              value === null ||
              ['string', 'number', 'boolean'].includes(typeof value) ||
              (Array.isArray(value) && value.every((subItem) => typeof subItem === 'string'))
          )) 
    )
  );
};

/**
 * FoldableNode: Displays JSON structure (object/array/primitive) as a foldable tree
 */
const FoldableNode = ({
  nodeKey,
  data,
  depth,
  defaultCollapsedDepth,
  isArrayItem,
  arrayIndex,
}) => {
  // Initial expand/collapse state
  const isRootWrapper = nodeKey === "";
  const [expanded, setExpanded] = useState(isRootWrapper || depth <= 1 || depth > 2);

  const toggleExpand = (e) => {
    e.stopPropagation();
    setExpanded(!expanded);
  };

  // Indentation (12px * depth)
  const indentStyle = {
    marginLeft: depth/2,
    transition: 'all 0.2s ease-in-out', // Smooth transition
  };

  // Bullet point style for array items
  const bulletStyle = {
    marginRight: '6px',
    marginLeft: '12px',
    fontSize: '1rem',
    fontWeight: 'bold',
    color: '#555555'
  };

  // Object or Array
  if (typeof data === 'object' && data !== null) {
    // [1] Array case
    if (Array.isArray(data)) {
      if (isArrayOfObjectsWithPrimitiveValues(data)) {
        // Check if data[0] exists and is an object
        const headers = data[0] && typeof data[0] === 'object' ? Object.keys(data[0]) : [];
        return (
          <div className="my-1 text-sm" style={{ indentStyle }}>
            {nodeKey && (
              <div
                className={`flex items-center gap-1 cursor-pointer text-custom-blue-deep font-semibold hover:text-custom-blue`}
                onClick={toggleExpand}
              >
                {expanded ? (
                  <ChevronDown size={14} className="inline-block" />
                ) : (
                  <ChevronRight size={14} className="inline-block" />
                )}
                <span>{nodeKey} </span>
              </div>
            )}
            {expanded && (
              <div style={{ width: '100%', overflowX: 'auto' }}>
                <table className="table-auto border-collapse border border-gray-300 w-full mt-3">
                  <thead>
                    <tr>
                      {headers.map((header) => (
                        <th
                          key={header}
                          className="border border-gray-300 px-2 py-1 text-left font-semibold bg-blue-100"
                        >
                          {header}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.map((row, idx) => (
                      <tr key={idx} className="even:bg-gray-50 odd:bg-white">
                        {headers.map((header) => (
                          <td
                            key={header}
                            className="border border-gray-300 px-2 py-1"
                          >
                            {header === "pmid" ? (
                              <a
                                href={`https://pubmed.ncbi.nlm.nih.gov/${row[header]}/`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-600 underline"
                              >
                                {row[header]}
                              </a>
                            ) : (
                              String(row[header])
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        );
      }

      // Default rendering for arrays
      return (
        <div className="my-1 text-sm" style={{ ...indentStyle, marginTop: depth <=1 ? '9px' : '0', marginBottom: depth <=1 ? '9px' : '0' }}>
          {nodeKey && !isArrayItem && (
            <div
              className="flex items-center gap-1 cursor-pointer text-custom-blue-deep font-semibold hover:text-custom-blue"
              onClick={toggleExpand}
            >
              {expanded ? (
                <ChevronDown size={14} className="inline-block" />
              ) : (
                <ChevronRight size={14} className="inline-block" />
              )}
              <span>{nodeKey}</span>
            </div>
          )}
          {expanded && (
            <div style={{ marginLeft: (nodeKey && !isArrayItem) ? 0.5 : 0 }}>
              {data.map((el, idx) => (
                <div key={idx} className={` ${
                  typeof el === 'object' && el !== null
                    ? 'm-2 p-2 border  '
                    : ''
                }`}>
                  <FoldableNode
                    key={idx}
                    nodeKey=""
                    data={el}
                    depth={depth + (nodeKey && !isArrayItem ? 1 : 0)}
                    defaultCollapsedDepth={defaultCollapsedDepth}
                    isArrayItem
                    arrayIndex={idx}
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      );
    } else {
      // [2] Object case
      const entries = Object.entries(data);

      return (
        <div className="my-1 text-sm" style={{ ...indentStyle, marginTop: depth <=1 ? '9px' : '0', marginBottom: depth <=1 ? '9px' : '0' }} >
          {/* Show toggle UI if not root node */}
          { nodeKey && (
            <div
              className={`flex items-center gap-1 cursor-pointer ${ depth === 0 ? "w-full text-left px-4 py-2 bg-custom-blue-deep font-semibold text-white hover:bg-gray-700 transition-colors mt-3" 
                : "text-custom-blue-deep font-semibold" 
              } `}
              style={{
                cursor: depth != 1 ? "pointer" : "default", // Only show pointer cursor for depth === 0
               }}
              onClick={depth !=1 ? toggleExpand : undefined}
            >
              <span>
                {depth === 0 && (expanded ? '▽ ' : '▷ ')} {/* Triangles for depth 0 */}
                {depth > 1 && (
                  expanded ? (
                    <ChevronDown size={14} className="inline-block" />
                  ) : (
                    <ChevronRight size={14} className="inline-block" />
                  )
                )} {/* Chevrons for depth 1+ */}
                {nodeKey}
              </span>
            </div>
          )}
          {expanded && (
            <div className="pl-1" style={{ marginLeft: nodeKey ? depth*2 : 0 }}>
              {entries.map(([key, value]) => (
                <FoldableNode
                  key={key}
                  nodeKey={key} 
                  data={value}
                  depth={depth + (nodeKey ? 1 : 0)}
                  defaultCollapsedDepth={defaultCollapsedDepth}
                />
              ))}
            </div>
          )}
        </div>
      );
    }
  } else {
    // [3] Primitive type (string, number, boolean, null)
    return (
      <div className="my-1 text-sm" style={{ ...indentStyle, marginTop: depth <=1 ? '9px' : '0', marginBottom: depth <=1 ? '9px' : '0' }}> 
        {isArrayItem ? (
          <div>
            <span style={bulletStyle}>•</span>
            {/* Show "key:" only if nodeKey is different from arrayIndex */}
            {nodeKey && nodeKey !== String(arrayIndex) && (
              <strong className="text-custom-blue-deep mr-1 font-semibold">{nodeKey}:</strong>
            )}
            <span className="text-custom-text break-all">{String(data)}</span> 
          </div>
        ) : (
          <div>
            <strong className={`my-1 text-sm ${ depth > 1 ? "text-black" : "text-custom-blue-deep" } font-semibold `}>{nodeKey}:</strong>
            <span className="text-custom-text break-all">
                {
                  (() => {
                    const text = String(data);
                    // Split into sentences
                    const sentences = text.match(/[^.!?]+[.!?]+(\s|$)/g) || [text];
                    if (sentences.length <= 5) return text;
                    // Group every 5 sentences and join with <br />
                    return sentences.reduce((acc, sentence, idx) => {
                      if (idx > 0 && idx % 5 === 0) { 
                        acc.push(<br key={idx}/>);
                        acc.push(<br key={idx}/>);
                      }
                      acc.push(sentence);
                      return acc;
                    }, []);
                  })()
                }
            </span> 
          </div>
        )}
      </div>
    );
  }
};

FoldableNode.propTypes = {
  nodeKey: PropTypes.string.isRequired,
  data: PropTypes.any,
  depth: PropTypes.number,
  defaultCollapsedDepth: PropTypes.number, 
  isArrayItem: PropTypes.bool,            
  arrayIndex: PropTypes.number,           
};

FoldableNode.defaultProps = {
  depth: 0,
  defaultCollapsedDepth: 1,
  isArrayItem: false,
  arrayIndex: 0,
};

export default FoldableNode;