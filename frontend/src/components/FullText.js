// src/components/FullText.js
import React, { forwardRef, useImperativeHandle, useRef } from 'react';
import PropTypes from 'prop-types';

function escapeRegExp(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

const FullText = forwardRef(({ fullText }, ref) => {
  const iframeRef = useRef(null);

  useImperativeHandle(ref, () => ({
    highlightEvidence: (evidenceText) => {
      const iframeEl = iframeRef.current;
      if (!iframeEl) return;
      const iDoc = iframeEl.contentDocument;
      if (!iDoc) return;

      let html = iDoc.body.innerHTML;
      // remove existing evidence highlights
      html = html.replace(/<span class="evidence-highlight" id="targetEvidence">(.*?)<\/span>/gi, '$1');

      // modify to include inline styles
      const pattern = new RegExp(`(${escapeRegExp(evidenceText)})`, 'i');
      const replacement = `<span id="targetEvidence" style="background-color: yellow; transition: background-color 0.5s ease;">$1</span>`;
      const newHtml = html.replace(pattern, replacement);

      iDoc.body.innerHTML = newHtml;
      const target = iDoc.getElementById("targetEvidence");
      if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'center' });
        setTimeout(() => {
          target.removeAttribute('id');
          // if want to remove the style after highlighting, target.removeAttribute('style');
        }, 3000);
      }
    }
  }));

  return (
    <iframe
      ref={iframeRef}
      srcDoc={fullText}
      title="PMC Article"
      style={{ width: '100%', height: '80vh', border: 'none' }}
    />
  );
});

FullText.displayName = 'FullText';

FullText.propTypes = {
  fullText: PropTypes.string.isRequired,
};

export default FullText;
