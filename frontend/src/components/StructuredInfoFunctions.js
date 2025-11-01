import PropTypes from 'prop-types';
import React, { useState } from 'react';

// Simple collapsible section component
export const MeasurePanel = ({ title, subtitle, children, defaultOpen = false }) => {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className=" mt-2 rounded ">
      <div className="flex items-center bg-blue-50 justify-between hover:bg-blue-200 px-3 py-3 cursor-pointer" onClick={() => setOpen(o => !o)}>
        <div className="flex flex-col "><span className="text-sm font-semibold text-custom-text">{title}</span>
        <span className="text-sm text-custom-text-subtle">{subtitle}</span></div>
        <span className="text-lg font-bold text-custom-blue-deep ml-2 mr-1 mb-1 select-none">
          {open ? '−' : '+'}
        </span>
      </div>
      {open && <div className="py-1 text-sm">{children}</div>}
    </div>
  );
};
MeasurePanel.propTypes = {
  title: PropTypes.string.isRequired, subtitle: PropTypes.string.isRequired,
  children: PropTypes.node,
  defaultOpen: PropTypes.bool,
};

export const Collapsible = ({ title, children, defaultOpen = true }) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="mb-2 border rounded">
      <button
        className="w-full text-left text-sm px-3 py-2 bg-gray-100 font-semibold text-black hover:text-white hover:bg-custom-blue-hover transition-colors" 
        onClick={() => setOpen((o) => !o)}
        type="button"
      >
        {open ? '▽   ' : '▷   '} {title} 
      </button>
      {open && <div className="pt-2 pb-3 px-3 bg-white">{children}</div>}
    </div>
  );
};
Collapsible.propTypes = {
  title: PropTypes.string.isRequired,
  children: PropTypes.node,
  defaultOpen: PropTypes.bool,
};

export function PairsList({ title, obj }) {
  if (!obj || typeof obj !== 'object' || Object.keys(obj).length === 0) return null;
  // Helper to capitalize each word in a string
  const capitalizeWords = str =>
    str.replace(/\w\S*/g, word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase());
  return (
    <div className="text-sm mb-2">
      <div className="font-medium text-custom-blue-deep">{title}</div>
      <div className="border-b border-gray-200 my-1"></div>
      <div className="space-y-1">
        {Object.entries(obj).map(([key, value]) =>
          value !== undefined && value !== null && value !== '' ? (
            <div key={key}>
              <span className="font-semibold">{capitalizeWords(key)}:</span>{' '}
              <span className="text-custom-text">{String(value)}</span>
            </div>
          ) : null
        )}
      </div>
    </div>
  );
}
PairsList.propTypes = { title: PropTypes.string.isRequired, obj: PropTypes.object.isRequired };

export function transformTextToReadableElements(text) {
  if (!text) return null;

  // Normalize line endings and split into lines
  const lines = text.replace(/\\>/g, "≥").replace(/\\</g, "≤").replace(/\r\n/g, '\n').split('\n');

  const elements = [];
  let currentList = [];

  lines.forEach((line, idx) => {
    const trimmed = line.trim();

    // Bullet list detection: match lines starting with '*' or '-'
    if (/^(\*|-)\s?/.test(trimmed)) {
      currentList.push(trimmed.replace(/^(\*|-)\s?/, ''));
    } else {
      // If we were building a list, push it as a <ul>
      if (currentList.length > 0) {
        elements.push(
          <ul key={`ul-${idx}`} className="list-disc pl-6 mb-1">
            {currentList.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        );
        currentList = [];
      }
      // Numbered list detection: match lines starting with "1. ", "2. ", etc.
      const numberedMatch = /^(\d+)\.\s+(.+)/.exec(trimmed);
      if (numberedMatch) {
        // Start or continue a numbered list
        if (!elements.length || elements[elements.length - 1].type !== 'ol') {
          elements.push(
        <ol key={`ol-${idx}`} className="list-decimal pl-6 mb-1">
          <li>{numberedMatch[2]}</li>
        </ol>
          );
        } else {
          // Append to the last <ol>
          const lastOl = elements[elements.length - 1];
          const newChildren = React.Children.toArray(lastOl.props.children).concat(
        <li key={lastOl.props.children.length}>{numberedMatch[2]}</li>
          );
          elements[elements.length - 1] = React.cloneElement(lastOl, {}, newChildren);
        }
      } else if (trimmed.endsWith(':')) {
        // Special underline for "Inclusion criteria:" or "Exclusion Criteria:"
        if (
          /inclusion criteria\s*:|exclusion criteria\s*:/i.test(trimmed)
        ) {
          elements.push(
            <div
              key={`colon-${idx}`}
              className="mt-1 mb-1 underline "
            >
              {trimmed}
            </div>
          );
        } else {
          elements.push(
            <div key={`colon-${idx}`} className="mt-1 mb-1">{trimmed}</div>
          );
        }
      } else if (trimmed) {
        // Paragraphs (skip empty lines)
        elements.push(
          <p key={`p-${idx}`} className="mb-0">{trimmed}</p>
        );
      }
    }
  });

  // If the text ends with a list, push it
  if (currentList.length > 0) {
    elements.push(
      <ul key={`ul-last`} className="list-disc pl-6 mb-2">
        {currentList.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    );
  }

  return elements;
}

export function PlainTextField({ field, value }) {
  if (!value) return null;
  return (
    <div className=" text-sm mb-2">
      <div className="font-medium text-custom-blue-deep">{field}</div>
      <div className="border-b border-gray-200 my-1"></div>
      <div className="text-custom-text break-words">{transformTextToReadableElements(value)}</div>
    </div>
  );
}
PlainTextField.propTypes = { field: PropTypes.string.isRequired, value: PropTypes.string };

export function ShortTextField({ field, value }) {
  if (!value) return null;
  return (
    <div className="flex items-center mr-9">
      <span className="bg-blue-50 text-center text-custom-blue-deep font-semibold px-2 py-1 rounded text-sm">
        {field}
      </span>
      <span className="text-custom-text px-2 py-1 text-sm">
       {value}
      </span>
    </div>
  );
}
ShortTextField.propTypes = { field: PropTypes.string.isRequired, value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]) };

export function ListField({ field, value }) {
  if (!value || !Array.isArray(value) || value.length === 0) return null;
  return (
    <div className="mb-0 text-sm">
      <div className="font-medium text-custom-blue-deep mt-2">{field}</div>
      <div className="border-b border-gray-200 my-1"></div>
      <div className="flex flex-wrap gap-2">
        {value.map((item, idx) => (
          <span
            key={idx}
            className="bg-gray-100 text-custom-text px-2 py-1 rounded"
          >
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}
ListField.propTypes = { field: PropTypes.string.isRequired, value: PropTypes.array };

export function VerticalTable({ data = {} }) {
  if (!data || typeof data !== 'object' || Object.keys(data).length === 0) return null;
  const entries = Object.entries(data).filter(([, v]) => v != null && v !== '');
  if (!entries.length) return null;

  return (
    <div className="overflow-x-auto">
      <table className="table-auto border-collapse border text-sm border-gray-300 mt-2">
        <colgroup>
          <col style={{ width: 'auto' }} />
          <col style={{ width: 'max-content' }} />
        </colgroup>
        <tbody>
          {entries.map(([field, value], idx) => (
            <tr key={idx} className="border-b last:border-b-0">
              <td className="border border-gray-200 px-2 py-1 bg-blue-50 text-custom-blue-deep font-semibold whitespace-nowrap">
                {field}
              </td>
              <td className="border border-gray-200 px-2 py-1 text-custom-text whitespace-nowrap">
                {value}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
VerticalTable.propTypes = { data: PropTypes.object.isRequired };

export function ObjectTable({ field, data }) {
  if (!Array.isArray(data) || data.length === 0) return null;
  // Collect all unique keys from all objects, omitting null/undefined keys
  const headers = Array.from(
    new Set(
      data.flatMap(obj =>
        obj && typeof obj === 'object'
          ? Object.keys(obj).filter(k => obj[k] !== null && obj[k] !== undefined)
          : []
      )
    )
  );
  if (headers.length === 0) return null;
  return (
    <><div className="font-medium text-sm mt-1 text-custom-blue-deep">{field}</div>
            <div className="border-b border-gray-200 my-1 "></div>
    <div style={{ width: '100%', overflowX: 'auto' }}>
      <table className="table-auto border-collapse mb-1 text-sm text-custom-text border border-gray-300 w-full mt-1 ">
        <thead>
          <tr>
            {headers.map(header => {
              // Convert camelCase or snake_case to separate words and capitalize
              const formattedHeader = header !== "MeSH ID" ? header
                .replace(/([A-Z])/g, ' $1')        // camelCase to space
                .replace(/_/g, ' ')                // snake_case to space
                .replace(/\s+/g, ' ')              // collapse multiple spaces
                .trim()
                .replace(/\b\w/g, c => c.toUpperCase())
                .replace("Num", "#") : header // capitalize first letter of each word
              return (
                <th
                  key={header}
                  className="border border-gray-300 px-2 py-1 text-left font-semibold bg-blue-50 whitespace-nowrap"
                >
                  {formattedHeader}
                </th>
              );
            })}
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
                   
                          {(row[header])}
                        
                      </td>
                    ))}
                  </tr>
                ))}
        </tbody>
      </table>
    </div></>
  );
}
ObjectTable.propTypes = { field: PropTypes.string.isRequired, data: PropTypes.array.isRequired };

export function formatEnum(enumValue) {
  if (typeof enumValue !== 'string') return '';
  if (enumValue === 'NA') return 'NA';
  // Replace underscores with spaces, then capitalize each word (including the first)
  return enumValue
    .replace(/_/g, ' ')
    .replace(/\w\S*/g, word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase());
}

export function LongVerticalTable({ data }) {
  if (!Array.isArray(data) || data.length === 0) return null;
  // Collect all unique subfield keys from all objects
  const subfields = Array.from(
    new Set(
      data.flatMap(obj =>
        obj && typeof obj === 'object'
          ? Object.values(obj).flatMap(inner =>
              inner && typeof inner === 'object'
                ? Object.keys(inner)
                : []
            )
          : []
      )
    )
  );
  return (
    <div className="mb-1">

      <div className="overflow-x-auto">
        <table className="table-auto border-collapse  text-sm  mb-1 mt-2 w-full">
          <thead>
            <tr>
              <th className="text-sm text-custom-blue-deep  border-gray-300 font-semibold text-left pl-1 pr-2 pb-1 ">
                {"Group ID"}
              </th>
              {subfields.map(subfield => (
                <th
                  key={subfield}
                  className="border border-gray-300 px-2 py-1 bg-blue-50 text-custom-text font-semibold text-left"
                >
                  {subfield}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((obj, rowIdx) => {
              const outerfield = Object.keys(obj)[0];
              const subObj = obj[outerfield] || {};
              return (
                <tr key={rowIdx} className="">
                  <td className="border border-gray-300 px-2 py-1 font-semibold  bg-gray-50 text-custom-text align-top ">
                    {outerfield}
                  </td>
                  {subfields.map(subfield => (
                    <td
                      key={subfield}
                      className="border border-gray-300 px-2 py-1 align-top"
                    >
                      {subObj[subfield] !== undefined && subObj[subfield] !== null
                        ? String(subObj[subfield])
                        : ''}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
LongVerticalTable.propTypes = {
  //title: PropTypes.string.isRequired,
  data: PropTypes.array.isRequired,
};