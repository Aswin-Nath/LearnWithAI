import React, { useState } from 'react';
import './PDFViewer.css';

interface PDFViewerProps {
  url: string;
}

const DownloadIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
  </svg>
);

export const PDFViewer: React.FC<PDFViewerProps> = ({ url }) => {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = url;
    link.download = 'editorial.pdf';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="pdf-viewer-container">
      <div className="pdf-toolbar">
        <div className="toolbar-left">
          <span className="pdf-title">Editorial PDF</span>
        </div>

        <div className="toolbar-right">
          <a 
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="toolbar-btn"
            title="Open in new tab"
          >
            🔗
          </a>
          
          <button 
            className="toolbar-btn" 
            onClick={handleDownload}
            title="Download PDF"
          >
            <DownloadIcon />
          </button>
        </div>
      </div>

      <div className="pdf-content">
        {error ? (
          <div className="pdf-error">
            <p>{error}</p>
            <p className="error-hint">Try opening the PDF in a new tab.</p>
            <a href={url} target="_blank" rel="noopener noreferrer" className="error-link">
              Open PDF in New Tab →
            </a>
          </div>
        ) : (
          <>
            {isLoading && (
              <div className="pdf-loading">Loading PDF...</div>
            )}
            <iframe
              src={`${url}#toolbar=1&navpanes=0&scrollbar=1`}
              className="pdf-iframe"
              onLoad={() => setIsLoading(false)}
              onError={() => {
                setIsLoading(false);
                setError('Failed to load PDF');
              }}
              title="Editorial PDF Viewer"
            />
          </>
        )}
      </div>
    </div>
  );
};
