import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { PanelLeft, PanelRight } from 'lucide-react';
import SearchFiltersSidebar from './SearchFiltersSidebar';

const FilterSidebar = ({ 
  isVisible, 
  onApplyFilters, 
  isLoading, 
  searchKey, 
  filterStats,
  expandedWidth = "25%",
  collapsedWidth = "2rem",
  onToggle,
  otherSidebarOpen = false
}) => {
  const [isOpen, setIsOpen] = useState(true);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkIfMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };

    checkIfMobile();
    window.addEventListener('resize', checkIfMobile);
    
    return () => window.removeEventListener('resize', checkIfMobile);
  }, []);

  // Notify parent component when sidebar is toggled
  useEffect(() => {
    if (onToggle) {
      onToggle(isOpen);
    }
  }, [isOpen, onToggle]);

  // Don't render sidebar if not visible (no search results or searchKey)
  if (!isVisible) {
    return null;
  }

  // If on mobile and other sidebar is open, hide this sidebar
  if (isMobile && otherSidebarOpen && !isOpen) {
    return null;
  }

  const toggleSidebar = () => {
    setIsOpen(prev => !prev);
  };

  return (
    <div
      className={`bg-white shadow-lg border-r border-gray-200 transition-all duration-300 ease-in-out ${isOpen ? 'rounded-l-2xl' : 'rounded-r-lg'} flex-shrink-0 ${
        isMobile ? (isOpen ? 'fixed left-0 top-0 z-50' : 'fixed left-0 top-16 z-50') : 'sticky top-0'
      }`}
      style={{
        width: isOpen ? 
          (isMobile ? '100%' : expandedWidth) : 
          collapsedWidth,
        height: isMobile && !isOpen ? 'auto' : 
          isMobile && isOpen ? '100vh' : 
          'calc(100vh - 64px)'
      }}
    >
      {/* Header Section */}
      <div className={`flex items-center ${isOpen ? 'justify-between' : 'justify-center'} p-2 border-b border-gray-200`}>
        {isOpen && (
          <h3 className="font-bold text-lg ml-2">Search Filters</h3>
        )}
        {!isOpen && <div />}

        <button
          type="button"
          aria-controls="filter-sidebar"
          aria-expanded={isOpen}
          className="p-1 text-primary-44 hover:text-primary-100 duration-short ease-curve-a cursor-pointer transition-colors"
          aria-label="Toggle filter sidebar"
          onClick={toggleSidebar}
        >
          {isOpen ? <PanelLeft size={18} /> : <PanelRight size={18} />}
        </button>
      </div>

      {isOpen && (
        <div 
          className="px-4 py-2 text-sm text-gray-700" 
          style={{ 
            height: isMobile ? 'calc(100vh - 41px)' : 'calc(100vh - 64px - 41px)', 
            overflowY: 'auto' 
          }}
        >
          <SearchFiltersSidebar
            onApplyFilters={onApplyFilters}
            isLoading={isLoading}
            searchKey={searchKey}
            filterStats={filterStats}
          />
        </div>
      )}
    </div>
  );
};

FilterSidebar.propTypes = {
  isVisible: PropTypes.bool.isRequired,
  onApplyFilters: PropTypes.func.isRequired,
  isLoading: PropTypes.bool,
  searchKey: PropTypes.string,
  filterStats: PropTypes.object,
  expandedWidth: PropTypes.string,
  collapsedWidth: PropTypes.string,
  onToggle: PropTypes.func,
  otherSidebarOpen: PropTypes.bool
};

export default FilterSidebar;
