import { addDoc, collection, serverTimestamp } from "firebase/firestore";
import _isEqual from 'lodash/isEqual';
import { StepBack, StepForward } from 'lucide-react';
import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {ArrowLeft, ArrowRight } from 'lucide-react';
import { filterSearchResults, getPatientQueries, getPatientNextPage, getSearchNextPage, searchClinicalTrials } from '../api/searchApi'; //
import DetailSidebar from '../components/DetailSidebar';
import QueryList from '../components/QueryList';
import { FilterPanel } from '../components/FilterPanel';
import { PatientFilterPanel } from '../components/PatientFilterPanel';
import FilterSidebar from '../components/FilterSidebar';
import Header from '../components/Header';
import { SearchBar } from '../components/SearchBar';
import EligibilityCriteria from '../components/EligibilityCriteria';
//import SearchInsights from '../components/SearchInsights';
import SearchResults from '../components/SearchResults';
import { auth, db } from "../firebase";
import { searchLogger, cacheLogger, filterLogger, detailLogger } from '../utils/logger';

const SESSION_KEY = "searchState";
const NEW_TAB_CACHE_KEY = "searchStateSharedForNewTab";

const buildUrlParams = (filtersObj) => {
  const allowedKeys = ['cond', 'intr', 'sources'];
  const params = {};
  allowedKeys.forEach((key) => {
    const value = filtersObj[key];
    if (value === undefined || value === null || value === '') return;
    if (key === 'sources') {
      params[key] = Array.isArray(value) ? value.join(',') : value;
    } else {
      params[key] = value;
    }
  });
  return params;
};

const saveSearch = async (searchEntry) => {
  const user = auth.currentUser;
  if (!user) return;

  try {
    await addDoc(collection(db, "users", user.uid, "searchHistory"), {
      ...searchEntry,
      createdAt: serverTimestamp()
    });
  } catch (error) {
    searchLogger.error("Error saving search:", error);
  }
};

const defaultFilters = () => ({
  cond: null,
  intr: null,
  other_term: null,
  location: null,
  status: null,
  pubmed_query: null,
  ctg_query: null,
  sources: ["PM", "CTG"]
});

const createFilters = (params = {}) => ({
  cond: params.cond || null,
  intr: params.intr || null,
  other_term: null,
  location: null,
  status: null,
  pubmed_query: null,
  ctg_query: null,
  sources: params.sources ? params.sources.split(',') : ["PM", "CTG"]
});

// Helper function to check if any search criteria are provided
const hasSearchCriteria = (query, filters) => {
  // Check if main query has content
  if (query && query.trim()) {
    return true;
  }
  
  // Check if any of the filter fields have values
  const searchableFields = ['cond', 'intr', 'other_term', 'pubmed_query', 'ctg_query'];
  return searchableFields.some(field => filters[field] && filters[field].trim());
};

const SearchPage = () => {
  const [searchKey, setSearchKey] = useState(null);
  const [activeFilters, setActiveFilters] = useState(null);
  const [hasAppliedFilters, setHasAppliedFilters] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(false);
  const [rightSidebarOpen, setRightSidebarOpen] = useState(false);
  const [patientMode, setPatientMode] = useState(false)
  
  // PubMed filters state
  const [pubmedFilters, setPubmedFilters] = useState({
    source_type: ['PM', 'CTG'],
    article_type: [],
    species: [],
    age: [],
    publication_date: {
      type: null,
      from_year: '',
      to_year: ''
    },
    pmc_open_access: true,
    ctg_has_results: false,
    ctg_status: []
  });
  const [selectedQuery, setSelectedQuery] = useState(0);
  const [dynamicQueries, setDynamicQueries] = useState({});
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialParams = Object.fromEntries([...searchParams]);
  const [baseResults, setBaseResults] = useState({})

  // Ref to track return from detail page
  const cameFromDetailRef = useRef(false);
  // Flag to distinguish automatic backend filter updates
  const autoUpdateRef = useRef(false);
  // Flag to indicate state was restored from cache or location.state
  const restoredRef = useRef(false);
  // Track initial mount
  const initialMountRef = useRef(true);

  // Search-related state
  const [query, setQuery] = useState('');
  const [lastSearchedQuery, setLastSearchedQuery] = useState('');
  const [filters, setFilters] = useState(defaultFilters());
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [refinedQuery, setRefinedQuery] = useState(null);
  const [appliedQueries, setAppliedQueries] = useState(null);
  const [ctgTokenHistory, setCtgTokenHistory] = useState({});
  const [results, setResults] = useState(null);
  const [patientResults, setPatientResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [searchHistory, setSearchHistory] = useState([]);
  const [selectedResult, setSelectedResult] = useState(null);
  const [mergedItemFocus, setMergedItemFocus] = useState({});

  // Eligibility Criteria state - independent of search/filter/pagination
  const [inclusionCriteria, setInclusionCriteria] = useState([]);
  const [exclusionCriteria, setExclusionCriteria] = useState([]);

  // Remove URL query parameters on initial load
  useEffect(() => {
    if (window.location.search) {
      searchLogger.debug('[Initial] Removing URL query parameters on first mount.');
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  // Mobile detection
  useEffect(() => {
    const checkIfMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };

    checkIfMobile();
    window.addEventListener('resize', checkIfMobile);
    
    return () => window.removeEventListener('resize', checkIfMobile);
  }, []);

  // Close other sidebar when one is opened on mobile
  useEffect(() => {
    if (isMobile) {
      if (leftSidebarOpen && rightSidebarOpen) {
        // Close the right sidebar if both are open on mobile
        setRightSidebarOpen(false);
      }
    }
  }, [isMobile, leftSidebarOpen, rightSidebarOpen]);

  // Cache loading helper
  const loadCache = () => {
    const cacheString = sessionStorage.getItem(SESSION_KEY);
    if (cacheString) {
      try {
        const parsed = JSON.parse(cacheString);
        cacheLogger.debug('[Cache] Loaded cache:', parsed);
        return parsed;
      } catch (e) {
        cacheLogger.error('[Cache] Failed parsing cache:', e);
        return null;
      }
    }
    return null;
  };

  // Cache saving helper
  const saveCache = (cacheObj) => {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(cacheObj));
    cacheLogger.debug('[Cache] Saved cache:', cacheObj);
  };

  // Initial state restoration: location.state → session storage → URL query parameters
  useEffect(() => {
    // If the opener saved a shared cache for a new tab (localStorage is shared across tabs on same origin),
    // read it and restore dynamicQueries so the newly opened tab shows the same dynamic queries.
    let restoredFromShared = false;
    try {
      const shared = localStorage.getItem(NEW_TAB_CACHE_KEY);
      if (shared) {
        const parsedShared = JSON.parse(shared);
        cacheLogger.debug('[Initial] Found shared new-tab cache in localStorage:', parsedShared);
        if (parsedShared && parsedShared.dynamicQueries) {
          setDynamicQueries(parsedShared.dynamicQueries);
          restoredFromShared = true;
        }
        // consume it once restored
        localStorage.removeItem(NEW_TAB_CACHE_KEY);
      }
    } catch (e) {
      cacheLogger.error('[Initial] Failed to read shared new-tab cache:', e);
    }
    if (location.state && location.state.searchState) {
      searchLogger.debug('[Initial] Restoring state from location.state:', location.state.searchState);
      cameFromDetailRef.current = true;
      const state = location.state.searchState;
      setFilters(state.filters);
      
      // Restore PubMed filters if available
      if (state.pubmedFilters) {
        setPubmedFilters(state.pubmedFilters);
        searchLogger.debug('[Initial] Restored pubmedFilters from location.state:', state.pubmedFilters);
      }
      
      setPage(state.page);
      setPageSize(state.pageSize);
      setSearchHistory(state.searchHistory || []);
      setRefinedQuery(state.refinedQuery);
      setCtgTokenHistory(state.ctgTokenHistory);
      setLastSearchedQuery(state.lastSearchedQuery || '');
      setAppliedQueries(state.appliedQueries || null);
      setQuery(state.query || '');
      // Restore searchKey from location.state
      if (state.searchKey) {
        searchLogger.debug('[Initial] Restoring searchKey from location.state:', state.searchKey);
        setSearchKey(state.searchKey);
      }
      // Restore baseResults if passed
      if (state.baseResults) {
        setBaseResults(state.baseResults);
        searchLogger.debug('[Initial] Restored baseResults from location.state');
      } else if (state.results) {
        // Fallback to 'results' if baseResults was not explicitly included
        setBaseResults(state.results);
        searchLogger.debug('[Initial] Restored baseResults from location.state.results fallback');
      }
      
      saveCache({
        filters: state.filters,
        pubmedFilters: state.pubmedFilters || pubmedFilters, // ADD: Save PubMed filters
        pageSize: state.pageSize,
        searchHistory: state.searchHistory || [],
        currentPage: state.page,
        lastSearchedQuery: state.lastSearchedQuery || '',
        appliedQueries: state.appliedQueries || null,
        query: state.query || '',
        searchKey: state.searchKey, // Add searchKey to cache
        baseResults: state.baseResults || state.results,
        pageCache: {
          [state.page]: {
            results: state.results,
            refinedQuery: state.refinedQuery,
            ctgTokenHistory: state.ctgTokenHistory
          }
        },
        patientMode: state.patientMode,
        patientResults: state.patientResults,
        dynamicQueries: state.dynamicQueries,
        selectedQuery: state.selectedQuery
      });

      const newParams = buildUrlParams({
        ...state.filters
      });
      searchLogger.debug('[Initial] Setting URL parameters from location.state:', newParams);
      setSearchParams(newParams);
      navigate({ search: "?" + new URLSearchParams(newParams).toString() }, { replace: true });
      
      // Mark as restored
      restoredRef.current = true;
      return;
    }

    const cachedState = loadCache();
      if (cachedState) {
      cacheLogger.debug('[Initial] Restoring state from session cache.');
      setFilters(cachedState.filters);
      
      // Restore PubMed filters if available
      if (cachedState.pubmedFilters) {
        setPubmedFilters(cachedState.pubmedFilters);
        cacheLogger.debug('[Initial] Restored pubmedFilters from cache:', cachedState.pubmedFilters);
      }
      
      setPage(cachedState.currentPage);
      setPageSize(cachedState.pageSize);
      setSearchHistory(cachedState.searchHistory || []);
      setLastSearchedQuery(cachedState.lastSearchedQuery || '');
      setAppliedQueries(cachedState.appliedQueries || null);
      setQuery(cachedState.query || '');
      setPatientMode(cachedState.patientMode);
      setPatientResults(cachedState.patientResults);
      // Only restore dynamicQueries from the session cache if we did not already restore from shared localStorage
      if (!restoredFromShared && cachedState.dynamicQueries) {
        setDynamicQueries(cachedState.dynamicQueries);
      }
      setSelectedQuery(cachedState.selectedQuery);
      // Restore baseResults from cache if present
      if (cachedState.baseResults) {
        setBaseResults(cachedState.baseResults);
        cacheLogger.debug('[Initial] Restored baseResults from session cache');
      } else if (cachedState.pageCache && cachedState.pageCache[cachedState.currentPage]) {
        setBaseResults(cachedState.pageCache[cachedState.currentPage].results || {});
        cacheLogger.debug('[Initial] Restored baseResults from pageCache fallback');
      }
      
      // Restore filter application state
      if (cachedState.hasAppliedFilters) {
        setHasAppliedFilters(true);
        setActiveFilters(cachedState.activeFilters);
        cacheLogger.debug('[Initial] Restored filter state - hasAppliedFilters:', true, 'activeFilters:', cachedState.activeFilters);
      }
      
      // Restore searchKey from cache
      if (cachedState.searchKey) {
        searchLogger.debug('[Initial] Restoring searchKey from cache:', cachedState.searchKey);
        setSearchKey(cachedState.searchKey);
      }
      if (cachedState.pageCache && cachedState.pageCache[cachedState.currentPage]) {
        const pageData = cachedState.pageCache[cachedState.currentPage];
        setResults(pageData.results);
        setRefinedQuery(pageData.refinedQuery);
        setCtgTokenHistory(pageData.ctgTokenHistory);
      }
      const newParams = buildUrlParams({
        ...cachedState.filters
      });
      searchLogger.debug('[Initial] Setting URL parameters from cache:', newParams);
      setSearchParams(newParams);
      navigate({ search: "?" + new URLSearchParams(newParams).toString() }, { replace: true });
      
      restoredRef.current = true;
      return;
    }

    // First entry (no cache or location.state)
    searchLogger.debug('[Initial] First entry with URL params:', initialParams);
    setFilters(createFilters(initialParams));
    setPage(Number(initialParams.page) || 1);
    setPageSize(Number(initialParams.pageSize) || 10);
    setRefinedQuery(initialParams.refinedQuery ? JSON.parse(initialParams.refinedQuery) : null);

    // Restore user_query from URL
    if (initialParams.user_query) {
      setQuery(initialParams.user_query);
      searchLogger.debug('[Initial] Restored user_query from URL:', initialParams.user_query);
    }

    if (initialParams.cond || initialParams.intr || initialParams.other_term || initialParams.user_query) {
      searchLogger.debug('[Initial] Auto-triggering search on first entry.');
      handleSearch({
        ...createFilters(initialParams),
        user_query: initialParams.user_query || '',
        page: Number(initialParams.page) || 1,
        pageSize: Number(initialParams.pageSize) || 10,
        refinedQuery: initialParams.refinedQuery ? JSON.parse(initialParams.refinedQuery) : null,
        ctgPageToken: initialParams.ctgTokenHistory
          ? JSON.parse(initialParams.ctgTokenHistory)[Number(initialParams.page)] || null
          : null
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Filter change detection (distinguish automatic updates and restoration states)
  const sourcesString = JSON.stringify(filters.sources);
  const prevFiltersRef = useRef(filters);

  useEffect(() => {
    // Skip changes from automatic backend updates
    if (autoUpdateRef.current) {
      filterLogger.debug('[Filters] Skipping reset due to automatic backend update.');
      autoUpdateRef.current = false;
      prevFiltersRef.current = filters;
      return;
    }

    // Skip reset logic if updated by restoration
    if (restoredRef.current) {
      filterLogger.debug('[Filters] Skipping effect due to restoration of state.');
      prevFiltersRef.current = filters;
      restoredRef.current = false;
      return;
    }

    // Exclude initial mount from change detection
    if (initialMountRef.current) {
      initialMountRef.current = false;
      filterLogger.debug('[Filters] Initial mount completed.');
      prevFiltersRef.current = filters;
      return;
    }

    filterLogger.debug('[Filters] Filters changed:', filters);

    const prevFilters = prevFiltersRef.current;
    filterLogger.debug('[Filters] Previous filters:', prevFilters);
    filterLogger.debug('[Filters] Current filters:', filters);

    const changedKeys = Object.keys(filters).filter((key) => {
      if (key === 'refinedQuery') {
        return !_isEqual(filters[key], prevFilters[key]);
      }
      return filters[key] !== prevFilters[key];
    });
    filterLogger.debug('[Filters] Changed keys:', changedKeys);

    prevFiltersRef.current = filters;

    if (cameFromDetailRef.current) {
      filterLogger.debug('[Filters] Skipping page reset due to return from detail page.');
      cameFromDetailRef.current = false;
      return;
    }

    if (
      changedKeys.length === 0 ||
      (changedKeys.length <= 3 && changedKeys.every((key) => ['page', 'refinedQuery', 'ctgPageToken'].includes(key)))
    ) {
      filterLogger.debug('[Filters] Only page, refinedQuery, or ctgPageToken changed (or no changes), skipping reset.');
      return;
    }

    filterLogger.debug('[Filters] Resetting page, refined query, and CTG token history due to manual filter change.');
    setRefinedQuery(null);
    setPage(1);
    setCtgTokenHistory({});
  }, [filters, sourcesString]);

  const handleViewDetails = (item) => {
    detailLogger.debug('[Detail] View details for item:', item);

    const stateToPass = {
      filters,
      pubmedFilters, // ADD: Include pubmedFilters in state to pass to detail page
      results,
      baseResults,
      page,
      pageSize,
      refinedQuery,
      ctgTokenHistory,
      searchHistory,
      lastSearchedQuery,
      appliedQueries,
      query,
      searchKey,
      activeFilters,
      hasAppliedFilters
    };

    // Handle different item types for metadata
    let metadata;
    if (item.type === 'MERGED') {
      // For merged items, include both PM and CTG data
      metadata = {
        type: 'MERGED',
        pm_data: item.pm_data,
        ctg_data: item.ctg_data,
        pmid: item.pmid,
        pmcid: item.pm_data?.pmcid || null,
        nctid: item.nctid,
        title: item.pm_data?.title || item.ctg_data?.title,
        authors: item.pm_data?.authors || [],
        journal: item.pm_data?.journal || null,
        pubDate: item.pm_data?.pubDate || null,
        ref_nctids: item.ctg_data?.ref_nctids || [item.nctid],
        publication_types: item.pm_data?.publication_types || [],
        page: page,
        index: results?.results?.findIndex(r => r.id === item.id) || 0,
        source: item.source || 'PM'
      };
    } else {
      // Handle regular PM/CTG items
      metadata = {
        type: item.type,
        title: item.title,
        pmid: item.pmid || null,
        pmcid: item.pmcid || null,
        nctId: item.id || null,
        doi: item.doi || null,
        studyType: item.studyType || null,
        authors: item.authors || [],
        journal: item.journal || null,
        pubDate: item.pubDate || item.date || null,
        structured_info: item.source === 'CTG' ? item.structured_info : null,
        ref_nctids: item.type === 'CTG' ? [] : (item.ref_nctids || []),
        publication_types: item.publication_types || [],
        page: page,
        index: results?.results?.findIndex(r => r.id === item.id) || 0,
        source: item.type
      };
    }

    // Update sessionStorage cache
    const cached = loadCache() || { pageCache: {} };
    cached.filters = filters;
    cached.pubmedFilters = pubmedFilters; // ADD: Save PubMed filters to cache
    cached.pageSize = pageSize;
    cached.searchHistory = searchHistory;
    cached.currentPage = page;
    cached.lastSearchedQuery = lastSearchedQuery;
    cached.appliedQueries = appliedQueries;
    cached.query = query;
    cached.searchKey = searchKey;
    cached.activeFilters = activeFilters;
    cached.hasAppliedFilters = hasAppliedFilters;
    cached.pageCache[page] = { results, refinedQuery, ctgTokenHistory };
    cached.patientMode = patientMode;
    cached.patientResults = patientResults;
    cached.dynamicQueries = dynamicQueries;
    cached.selectedQuery = selectedQuery;
    // Persist baseResults so QueryList can restore original results on return
    cached.baseResults = baseResults;
    saveCache(cached);

    // Navigate based on item type
    if (item.type === 'CTG' || (item.type === 'MERGED' && item.source === 'CTG')) {
      const nctId = item.type === 'MERGED' ? item.nctid : item.id;
      navigate(`/detail?nctId=${nctId}&source=CTG`, {
        state: {
          searchState: stateToPass,
          metadata: metadata,
        },
      });
    } else {
      // PM or MERGED with PM focus
      const paperId = item.type === 'MERGED' ? item.pmid : item.id;
      const pmcid = item.type === 'MERGED' ? item.pm_data.pmcid : item.pmcid;
      navigate(`/detail?paperId=${paperId}&pmcid=${pmcid}&source=${item.type === 'MERGED' ? 'PM' : item.type}`, {
        state: {
          searchState: stateToPass,
          metadata: metadata,
        },
      });
    }
  };

  // Helper to remove empty values from filter object
  const preparePayload = (filtersObj) => {
    return Object.entries(filtersObj).reduce((acc, [key, value]) => {
      // Always include boolean fields (pmc_open_access, ctg_has_results)
      if (key === 'pmc_open_access' || key === 'ctg_has_results') {
        acc[key] = value !== undefined ? value : (key === 'pmc_open_access' ? true : false);
        return acc;
      }
      
      // Always include ctg_status array (even if empty)
      if (key === 'ctg_status') {
        acc[key] = Array.isArray(value) ? value : [];
        return acc;
      }
      
      // Skip undefined, null, empty string
      if (value === undefined || value === null || value === '') {
        return acc;
      }
      
      // Skip empty arrays
      if (Array.isArray(value) && value.length === 0) {
        return acc;
      }
      
      // Skip empty publication_date objects
      if (key === 'publication_date' && typeof value === 'object') {
        if (!value.type && !value.from_year && !value.to_year) {
          return acc;
        }
      }
      
      acc[key] = value;
      return acc;
    }, {});
  };

  const setAge = (min, max) => {
    const groups = [];

    if (min <= 17) groups.push("child");
    if (max >= 18 && min <= 65) groups.push("adult");
    if (max > 65) groups.push("older adult");

    return groups.join(' ');
  }

  const handleQuerySelect = (data) => {
    searchLogger.debug('query response:', data);
      
    searchLogger.debug('API response type:', typeof data.results);
    searchLogger.debug('API response results:', data.results);

    let rawFilters = { ...filters, user_query: query, page: 1, pageSize, ctgPageToken: null };
    const updatedFilters = { ...rawFilters };

    
    // clear filter sidebar
    try {
      setPubmedFilters( {
      source_type: [],
      article_type: [],
      species: [],
      age: [],
      publication_date: {
        type: null,
        from_year: '',
        to_year: ''
      },
      pmc_open_access: false,
      ctg_has_results: false,
      ctg_status: []
    });
      searchLogger.debug('[Filters] Cleared filters for new query results');
    } catch (e) {
      searchLogger.error('[Filters] Failed to clear filters:', e);
    }
    
    // Save search_key
    if (data.search_key) {
      searchLogger.debug('Setting searchKey:', data.search_key);
      setSearchKey(data.search_key);
      setActiveFilters(null);
      setHasAppliedFilters(false);
    } else {
      searchLogger.debug('No search_key received in response');
    }

    // Save applied queries information (actual queries sent to API)
    if (data.appliedQueries) {
      searchLogger.debug('🔍 [DEBUG] Updating appliedQueries with:', data.appliedQueries);
      setAppliedQueries(data.appliedQueries);
    } else {
      searchLogger.warn('⚠️ [DEBUG] No appliedQueries in response, data:', data);
    }
    setRefinedQuery(data.refinedQuery || null)
    setPage(1);

    setResults({
      results: Array.isArray(data.results) ? data.results : [],
      counts: data.counts || { total: 0, merged: 0, pm_only: 0, ctg_only: 0 },
      total: data.total || 0,
      totalPages: data.totalPages || 1,
      filter_stats: data.filter_stats
    });

    const newParams = buildUrlParams({
      ...updatedFilters
    });
    searchLogger.debug('[Search] Updating URL and cache with newParams:', newParams);
    setSearchParams(newParams);
    navigate({ search: "?" + new URLSearchParams(newParams).toString() }, { replace: true });

    const cached = loadCache() || {};
    cached.filters = updatedFilters;
    // Persist the cleared pubmed filters (we applied them above)
    cached.pubmedFilters =  {
      source_type: [],
      article_type: [],
      species: [],
      age: [],
      publication_date: {
        type: null,
        from_year: '',
        to_year: ''
      },
      pmc_open_access: false,
      ctg_has_results: false,
      ctg_status: []
    }; 
    cached.pageSize = updatedFilters.pageSize;
    cached.searchHistory = [updatedFilters, ...searchHistory];
    cached.currentPage = updatedFilters.page;
    cached.lastSearchedQuery = updatedFilters.user_query || query;
    cached.appliedQueries = data.appliedQueries || null;
    cached.searchKey = data.search_key;
    cached.activeFilters = null;
    cached.hasAppliedFilters = false;
    cached.pageCache = cached.pageCache || {};
    cached.pageCache[updatedFilters.page] = {
      results: {
        results: Array.isArray(data.results) ? data.results : [],
        counts: data.counts || { total: 0, merged: 0, pm_only: 0, ctg_only: 0 },
        total: data.total || 0,
        totalPages: data.totalPages || 1,
        filter_stats: data.filter_stats
      },
      refinedQuery: updatedFilters.refinedQuery,
      ctgTokenHistory: ctgTokenHistory
    };
    cached.patientMode = patientMode;
    cached.patientResults = patientResults;
    cached.dynamicQueries = dynamicQueries;
    cached.selectedQuery = selectedQuery;
    // Persist baseResults for QueryList restore
    cached.baseResults = baseResults;
    saveCache(cached);
    searchLogger.debug('[Search] Search completed, current page:', updatedFilters.page);
    
  } 
  const handlePatientQuerySelect = (data) => {
    searchLogger.debug('[Search] API response:', data);
      
    searchLogger.debug('[Search] API response type:', typeof data.results);
    searchLogger.debug('[Search] API response results:', data.results);

    let rawFilters = { ...filters, user_query: query, page: 1, pageSize, ctgPageToken: null };
    const updatedFilters = { ...rawFilters };
    
    // Save search_key
    if (data.search_key) {
      searchLogger.debug('[Search] Setting searchKey:', data.search_key);
      setSearchKey(data.search_key);
      setActiveFilters(null);
      setHasAppliedFilters(false);
    } else {
      searchLogger.debug('[Search] No search_key received in response');
    }

    // Save applied queries information (actual queries sent to API)
    if (data.appliedQueries) {
      searchLogger.debug('🔍 [DEBUG] Updating appliedQueries with (location 2):', data.appliedQueries);
      setAppliedQueries(data.appliedQueries);
    } else {
      searchLogger.warn('⚠️ [DEBUG] No appliedQueries in response (location 2), data:', data);
    }
    setRefinedQuery(data.refinedQuery || null)
    setPage(data.page);
    // Set results according to backend response structure - already comes as integrated array
    setResults({
      results: Array.isArray(data.results) ? data.results : [],
      counts: data.counts || { total: 0, merged: 0, pm_only: 0, ctg_only: 0 },
      total: data.total || 0,
      totalPages: data.totalPages || 1,
      filter_stats: data.filter_stats
    });

    const newParams = buildUrlParams({
      ...updatedFilters
    });
    searchLogger.debug('[Search] Updating URL and cache with newParams:', newParams);
    setSearchParams(newParams);
    navigate({ search: "?" + new URLSearchParams(newParams).toString() }, { replace: true });
    
    const cached = loadCache() || {};
    cached.filters = updatedFilters;
    cached.pubmedFilters = pubmedFilters; // ADD: Save PubMed filters (location 2)
    cached.pageSize = updatedFilters.pageSize;
    cached.searchHistory = [updatedFilters, ...searchHistory];
    cached.currentPage = updatedFilters.page;
    cached.lastSearchedQuery = updatedFilters.user_query || query;
    cached.appliedQueries = data.appliedQueries || null;
    cached.searchKey = data.search_key;
    cached.activeFilters = null;
    cached.hasAppliedFilters = false;
    cached.pageCache = cached.pageCache || {};
    cached.pageCache[updatedFilters.page] = {
      results: {
        results: Array.isArray(data.results) ? data.results : [],
        counts: data.counts || { total: 0, merged: 0, pm_only: 0, ctg_only: 0 },
        total: data.total || 0,
        totalPages: data.totalPages || 1,
        filter_stats: data.filter_stats
      },
      refinedQuery: updatedFilters.refinedQuery,
      ctgTokenHistory: ctgTokenHistory
    };
    cached.patientMode = patientMode;
    cached.patientResults = patientResults;
    cached.dynamicQueries = dynamicQueries;
    cached.selectedQuery = selectedQuery;
    // Persist baseResults for QueryList restore
    cached.baseResults = baseResults;
    saveCache(cached);
    searchLogger.debug('[Search] Search completed, current page:', updatedFilters.page);
  }

  

  // Search API call and cache update (with refinedQuery applied)
  const handleSearch = async (customParams = null, forceNewSearch = false) => {
    searchLogger.debug('[Search] handleSearch called with params:', customParams, 'forceNewSearch:', forceNewSearch);
    
    // Force new search: completely reset all states like initial entry
    if (forceNewSearch) {
      searchLogger.debug('[Search] Force new search - completely resetting all states like initial entry');
      
      // Save current query for restoration after backend response
      const currentUserQuery = query.trim();
      
      // Reset all search-related states
      setResults(null);
      setRefinedQuery(null);
      setAppliedQueries(null);
      setPage(1);
      setCtgTokenHistory({});
      setSearchHistory([]);
      
      // Reset filters to default values (keeping only sources)
      const resetFilters = defaultFilters();
      
      // Completely remove cache
      sessionStorage.removeItem(SESSION_KEY);
      
      // Remove URL parameters
      setSearchParams({});
      navigate('/', { replace: true });
      
      // Prepare payload for new search (user_query only with default filters)
      const searchPayload = {
        user_query: currentUserQuery,
        sources: resetFilters.sources,
        article_type: filters.article_type || [],
        species: filters.species || [],
        age: filters.age || [],
        publication_date: filters.publication_date || null,
        pmc_open_access: filters.pmc_open_access !== undefined ? filters.pmc_open_access : true,
        ctg_has_results: filters.ctg_has_results || false,
        ctg_status: filters.ctg_status || [],
        page: 1,
        pageSize: pageSize
      };
      
      searchLogger.debug('[Search] Force new search with payload:', searchPayload);
      
      setLoading(true);
      try {
        let data = await searchClinicalTrials(searchPayload);
        searchLogger.debug('[Search] Force new search API response:', data);
          
          // Set search_key
          if (data.search_key) {
            searchLogger.debug('[Search] Setting searchKey from force new search:', data.search_key);
            setSearchKey(data.search_key);
          }
        
        searchLogger.debug('[Search] Force new search API response:', data);
        
        // Save applied queries information
        if (data.appliedQueries) {
          setAppliedQueries(data.appliedQueries);
        }
        
        // Store refinedQuery but don't apply to filters (protect user input fields)
        let finalFilters = resetFilters;
        if (data.refinedQuery) {
          searchLogger.debug('[Search] Received refinedQuery from API (not applying to filters):', data.refinedQuery);
          setRefinedQuery(data.refinedQuery);
        }
        
        // Set filters to default values (protect user input fields)
        autoUpdateRef.current = true;
        setFilters(finalFilters);
        
        // Set search results
        setResults({
          results: Array.isArray(data.results) ? data.results : [],
          counts: data.counts || { total: 0, merged: 0, pm_only: 0, ctg_only: 0 },
          total: data.total || 0,
          totalPages: data.totalPages || 1,
          filter_stats: data.filter_stats
        });

        if (data.additional_queries){
          setDynamicQueries({"queries": data.additional_queries })
        }
        
        // Update lastSearchedQuery only after successful search completion
        setLastSearchedQuery(currentUserQuery);
        
        // Update search history (record actual used filters and result information)
        const historyEntry = {
          ...finalFilters,
          user_query: currentUserQuery,
          page: 1,
          pageSize: pageSize,
          results_count: data.total || 0,
          counts: data.counts || { total: 0, merged: 0, pm_only: 0, ctg_only: 0 },
          applied_queries: data.applied_queries || null,
          refined_query: data.refined_query || null
        };
        await saveSearch(historyEntry);
        setSearchHistory([historyEntry]);
        
        searchLogger.debug('[Search] Force new search completed successfully');
        
      } catch (error) {
        searchLogger.error('[Search] Force new search error:', error);
        setResults(null);
      } finally {
        setLoading(false);
      }
      
      return; // Exit here for force new search
    }
    
    if (patientMode) {
      if (filters["age1"] && filters["age2"]) { filters["age"] = setAge(filters["age1"], filters["age2"]) }

      let rawFilters = { ...filters, user_query: query, page: 1, pageSize, ctgPageToken: null };
      const effectiveFilters = preparePayload(rawFilters);

      searchLogger.debug('[Search] Getting patient query using filters:', effectiveFilters);
      setLoading(true);
      let data = {}
      try {
        data = await getPatientQueries(effectiveFilters);
      } catch (error) {
        data = null
        searchLogger.error('[Search] Patient search error:', effectiveFilters);
      } finally {
        setLoading(false)
      }
      searchLogger.debug('[Search] received response:', data)
      const results = data?.final_results?.filter(r => r.total > 0 || r.name === "Default")
      setPatientResults(results)

      // Store refinedQuery but don't apply to filters (protect user input fields)
      const updatedFilters = { ...rawFilters };
      // Update lastSearchedQuery for new searches (not pagination)
      if (!customParams || updatedFilters.page === 1) {
        setLastSearchedQuery(updatedFilters.user_query || query);
      }
      handlePatientQuerySelect(data.final_results[0])
      return;

    }
    
    // Regular search (pagination, etc.)
    let rawFilters;
    if (!customParams) {
      // Include PubMed filters in initial search
      rawFilters = { 
        ...filters, 
        ...pubmedFilters,  // Add PubMed filters
        user_query: query, 
        page: 1,  // Always reset to page 1 for new search
        pageSize, 
        ctgPageToken: null 
      };
      searchLogger.debug('[Search] Current pubmedFilters state:', pubmedFilters);
      searchLogger.debug('[Search] Using current filters with query (including PubMed filters):', rawFilters);
    } else {
      rawFilters = customParams;
      searchLogger.debug('[Search] Using custom params:', rawFilters);
    }
    
    const effectiveFilters = preparePayload(rawFilters);
    searchLogger.debug('[Search] AFTER preparePayload - effective filters for API:', effectiveFilters);
    setLoading(true);
    try {
      effectiveFilters.ctgPageToken = ctgTokenHistory[effectiveFilters.page] || null;
      const data = await searchClinicalTrials(effectiveFilters);
      searchLogger.debug('[Search] API response:', data);
      
      searchLogger.debug('[Search] API response type:', typeof data.results);
      searchLogger.debug('[Search] API response results:', data.results);

      setBaseResults({
        results: Array.isArray(data.results) ? data.results : [],
        counts: data.counts || { total: 0, merged: 0, pm_only: 0, ctg_only: 0 },
        total: data.total || 0,
        totalPages: data.totalPages || 1,
        filter_stats: data.filter_stats,
        search_key: data.search_key,
        refinedQuery: data.refinedQuery,
        appliedQueries: data.appliedQueries
      })
      
      // Save search_key and reset page to 1 for new searches
      if (data.search_key) {
        searchLogger.debug('[Search] Setting searchKey:', data.search_key);
        setSearchKey(data.search_key);
        setActiveFilters(null);
        setHasAppliedFilters(false);
        
        // Reset page to 1 if this is a new search (not pagination)
        if (!customParams || effectiveFilters.page === 1) {
          setPage(1);
          searchLogger.debug('[Search] Reset page to 1 for new search');
        }
      } else {
        searchLogger.debug('[Search] No search_key received in response');
      }

      // Save applied queries information (actual queries sent to API)
      if (data.appliedQueries) {
        setAppliedQueries(data.appliedQueries);
      }
      
      // Store refinedQuery but don't apply to filters (protect user input fields)
      const updatedFilters = { ...rawFilters };
      if (data.refinedQuery) {
        searchLogger.debug('[Search] Received refinedQuery from API (not applying to filters):', data.refinedQuery);
        updatedFilters.refinedQuery = data.refinedQuery;
        setRefinedQuery(data.refinedQuery);
      }
      
      // Set results according to backend response structure - already comes as integrated array
      setResults({
        results: Array.isArray(data.results) ? data.results : [],
        counts: data.counts || { total: 0, merged: 0, pm_only: 0, ctg_only: 0 },
        total: data.total || 0,
        totalPages: data.totalPages || 1,
        filter_stats: data.filter_stats
      });

      if (data.additional_queries){
        setDynamicQueries({"queries": data.additional_queries })    
      }
      
      // Update lastSearchedQuery for new searches (not pagination)
      if (!customParams || updatedFilters.page === 1) {
        setLastSearchedQuery(updatedFilters.user_query || query);
        
        // Save to history only for new searches (include result information)
        if (!customParams) {
          const historyEntry = {
            ...updatedFilters,
            user_query: updatedFilters.user_query || query,
            results_count: data.total || 0,
            counts: data.counts || { total: 0, merged: 0, pm_only: 0, ctg_only: 0 },
            applied_queries: data.appliedQueries || null,
            refined_query: data.refinedQuery || null
          };
          
          // Save to Firebase
          try {
            await saveSearch(historyEntry);
            setSearchHistory([historyEntry, ...searchHistory]);
          } catch (error) {
            searchLogger.error('Failed to save search history:', error);
          }
        }
      }
      
      const newParams = buildUrlParams({
        ...updatedFilters
      });
      searchLogger.debug('[Search] Updating URL and cache with newParams:', newParams);
      setSearchParams(newParams);
      navigate({ search: "?" + new URLSearchParams(newParams).toString() }, { replace: true });
      
      const cached = loadCache() || {};
      if (cached.dynamicQueries) {
        setDynamicQueries(cached.dynamicQueries);
      }

      cached.filters = updatedFilters;
      cached.pubmedFilters = pubmedFilters; // ADD: Save PubMed filters (location 3 - handleSearch)
      cached.pageSize = updatedFilters.pageSize;
      cached.searchHistory = [updatedFilters, ...searchHistory];
      cached.currentPage = updatedFilters.page;
      cached.lastSearchedQuery = updatedFilters.user_query || query;
      cached.appliedQueries = data.appliedQueries || null;
      cached.searchKey = data.search_key;
      cached.activeFilters = null;
      cached.hasAppliedFilters = false;
      cached.pageCache = cached.pageCache || {};
      cached.pageCache[updatedFilters.page] = {
        results: {
          results: Array.isArray(data.results) ? data.results : [],
          counts: data.counts || { total: 0, merged: 0, pm_only: 0, ctg_only: 0 },
          total: data.total || 0,
          totalPages: data.totalPages || 1,
          filter_stats: data.filter_stats
        },
        refinedQuery: updatedFilters.refinedQuery,
        ctgTokenHistory: ctgTokenHistory
      };
      cached.patientMode = patientMode;
      cached.patientResults = patientResults;
      cached.dynamicQueries = dynamicQueries;
      cached.selectedQuery = selectedQuery;
      // Persist baseResults for QueryList restore
      cached.baseResults = baseResults;
      saveCache(cached);
      searchLogger.debug('[Search] Search completed, current page:', updatedFilters.page);
    } catch (error) {
      searchLogger.error('[Search] Error during search:', error);
      setResults(null);
    } finally {
      setLoading(false);
    }
  };

  // Filter application function
  const handleApplyFilters = async (filterParams) => {
    filterLogger.debug('[Filter] Apply filters called with params:', filterParams);
    filterLogger.debug('[Filter] Current searchKey:', searchKey);
    filterLogger.debug('🔍 [DEBUG] Current pubmedFilters state:', pubmedFilters);
    filterLogger.debug('🔍 [DEBUG] Incoming filterParams:', filterParams);
    
    // Update PubMed filters state
    setPubmedFilters(filterParams);
    filterLogger.debug('🔍 [DEBUG] Updated pubmedFilters to:', filterParams);
    
    // If no searchKey exists, perform initial filtered search
    if (!searchKey) {
      filterLogger.debug('[Filter] No searchKey - performing initial filtered search');
      filterLogger.debug('🔍 [DEBUG] About to call handleSearch() with filterParams:', filterParams);
      // Perform new search with filters
      await handleSearch();
      return;
    }
    
    // Otherwise, perform post-filter on existing results
    setLoading(true);
    try {
      filterLogger.debug('[Filter] Applying post-filters with searchKey:', searchKey);
      
      // Always reset to page 1 when filters change
      const filterRequestParams = {
        ...filterParams,
        page: 1,
        page_size: pageSize
      };
      
      const data = await filterSearchResults(filterRequestParams);
      filterLogger.debug('[Filter] Filter response received:', data);
      
      // Update appliedQueries with filtered queries if available
      if (data.appliedQueries) {
        filterLogger.debug('[Filter] Updating appliedQueries with filtered queries:', data.appliedQueries);
        setAppliedQueries(data.appliedQueries);
      }
      
      // Update with filtered results - maintain original search result structure
      setResults({
        ...results,
        results: Array.isArray(data.results) ? data.results : [],
        total: data.total || 0,
        totalPages: data.totalPages || 1,
        counts: data.counts || { 
          total: data.total || 0, 
          merged: 0, 
          pm_only: 0, 
          ctg_only: 0 
        },
        filter_stats: data.filter_stats
      });
      
      setActiveFilters(data.filters_applied);
      setHasAppliedFilters(true);
      setPage(1); // Always reset to page 1 on filter change
      
      // Store filter cache key for future pagination
      sessionStorage.setItem('filterCacheKey', data.filter_cache_key || '');
      
      // Update cache - include filter application state and filtered queries
      const cacheToSave = {
        filters,
        pageSize,
        searchHistory,
        currentPage: 1, // Reset to page 1
        lastSearchedQuery,
        appliedQueries: data.appliedQueries || appliedQueries,
        query,
        searchKey,
        activeFilters: data.filters_applied,
        hasAppliedFilters: true,
        filterCacheKey: data.filter_cache_key,
        pageCache: {
          1: {
            results: {
              ...results,
              results: Array.isArray(data.results) ? data.results : [],
              total: data.total || 0,
              totalPages: data.totalPages || 1,
              counts: data.counts || {
                total: data.total || 0,
                merged: 0,
                pm_only: 0,
                ctg_only: 0
              },
              filter_stats: data.filter_stats
            },
            refinedQuery,
            ctgTokenHistory
          }
        },
        patientMode,
        patientResults,
        dynamicQueries,
        selectedQuery,
      };
      // Ensure baseResults persisted so QueryList can restore original results
      cacheToSave.baseResults = baseResults || (results || null);
      saveCache(cacheToSave);
      
      filterLogger.debug('[Filter] ✅ Filter applied successfully, page reset to 1');
      
    } catch (error) {
      filterLogger.error('Filter error:', error);
      alert('Failed to apply filters. Please try again.');
    } finally {
      setLoading(false);
    }
  };


  // Page navigation: use cache if available, otherwise make API call
  const goToPage = async (newPage) => {
    searchLogger.debug('[Pagination] goToPage called. Current page:', page, 'New page:', newPage);
    searchLogger.debug('[Pagination] Has applied filters:', hasAppliedFilters, 'Active filters:', activeFilters);
    searchLogger.debug('[Pagination] searchKey:', searchKey);
    
    if (patientMode) {
      searchLogger.debug("NEXT PAGE FOR SEARCH:", patientResults[selectedQuery])
      // Update page for selectedQuery
      let currentResults = patientResults[selectedQuery]
      currentResults.page = newPage
      setLoading(true)
      const newResults = await getPatientNextPage(currentResults)
      currentResults.results = newResults
      searchLogger.debug("[Pagination] setting patient query", currentResults);
      handlePatientQuerySelect(currentResults)
      setLoading(false)
      return;
    }

    // For filtered results, use filter API with the same filter parameters
    if (hasAppliedFilters && activeFilters && searchKey) {
      searchLogger.debug('[Pagination] Using filter API for page', newPage, 'with active filters');
      setLoading(true);
      
      try {
        const filterCacheKey = sessionStorage.getItem('filterCacheKey') || '';
        searchLogger.debug('[Pagination] Filter cache key:', filterCacheKey);
        
        // Use the same filter parameters but update page number
        const filterRequestParams = {
          search_key: searchKey,
          ...activeFilters,
          page: newPage,
          page_size: pageSize
        };
        
        const data = await filterSearchResults(filterRequestParams);
        searchLogger.debug('[Pagination] Received filtered page data:', data);
        
        // Update page and results
        setPage(newPage);
        setResults({
          results: Array.isArray(data.results) ? data.results : [],
          counts: data.counts || { total: 0, merged: 0, pm_only: 0, ctg_only: 0 },
          total: data.total || 0,
          totalPages: data.totalPages || 1,
          filter_stats: data.filter_stats
        });
        
        // Update appliedQueries if provided
        if (data.appliedQueries) {
          setAppliedQueries(data.appliedQueries);
        }
        
        searchLogger.debug('[Pagination] ✅ Filtered page changed successfully');
      } catch (error) {
        searchLogger.error('[Pagination] ❌ Filter pagination failed:', error);
        alert('Failed to load page. Please try again.');
      } finally {
        setLoading(false);
      }
      return;
    }

    // For regular search results, use pagination API with search_key
    if (searchKey) {
      searchLogger.debug('[Pagination] Using pagination API with searchKey:', searchKey);
      setLoading(true);
      try {
        const data = await getSearchNextPage({
          search_key: searchKey,
          page: newPage,
          page_size: pageSize
        });
        
        searchLogger.debug('[Pagination] Received paginated data:', data);
        
        // Update state with paginated results
        setPage(newPage);
        setResults({
          results: Array.isArray(data.results) ? data.results : [],
          counts: data.counts || { total: 0, merged: 0, pm_only: 0, ctg_only: 0 },
          total: data.total || 0,
          totalPages: data.totalPages || 1,
          filter_stats: data.filter_stats
        });
        
        // Update appliedQueries if provided
        if (data.appliedQueries) {
          setAppliedQueries(data.appliedQueries);
        }
        
        searchLogger.debug('[Pagination] ✅ Page changed successfully using pagination API');
      } catch (error) {
        searchLogger.error('[Pagination] ❌ Pagination API failed:', error);
        alert('Failed to load page. Please try again.');
      } finally {
        setLoading(false);
      }
      return;
    }

    // No searchKey - this shouldn't happen for pagination after initial search
    searchLogger.warning('[Pagination] No searchKey available - cannot paginate without initial search');
    alert('Search session expired. Please perform a new search.');
  };

  // Handle result item selection
  const handleResultSelect = (result) => {
    searchLogger.debug('[Result] Selected result:', result);
    
    // Transform data to match new integrated structure
    let transformedResult;
    
    if (result.type === 'MERGED') {
      // For MERGED type, determine main data based on current focus
      const focus = mergedItemFocus[result.id] || 'PM';
    
      if (focus === 'PM') {
        transformedResult = {
          ...result,
          source: 'PM',
          id: result.pmid,
          pmid: result.pmid,
          pmcid: result.pm_data?.pmcid,
          title: result.pm_data?.title,
          journal: result.pm_data?.journal,
          authors: result.pm_data?.authors,
          pubDate: result.pm_data?.pubDate,
          abstract: result.pm_data?.abstract,
          doi: result.pm_data?.doi,
          ctg_data: result.ctg_data,
          nctid: result.nctid
        };
      } else {
        transformedResult = {
          ...result,
          source: 'CTG',
          id: result.nctid,
          nctid: result.nctid,
          title: result.ctg_data?.title,
          status: result.ctg_data?.status,
          phase: result.ctg_data?.phase,
          brief_summary: result.ctg_data?.brief_summary,
          lead_sponsor: result.ctg_data?.lead_sponsor,
          conditions: result.ctg_data?.conditions,
          structured_info: result.ctg_data?.structured_info,
          pm_data: result.pm_data,
          pmid: result.pmid
        };
      }
    } else if (result.type === 'PM') {
      transformedResult = {
        ...result,
        source: 'PM',
        id: result.pmid,
        pmid: result.pmid,
        pmcid: result.pmcid,
        title: result.title,
        journal: result.journal,
        authors: result.authors,
        pubDate: result.pubDate,
        abstract: result.abstract,
        doi: result.doi
      };
    } else if (result.type === 'CTG') {
      transformedResult = {
        ...result,
        source: 'CTG',
        id: result.nctid || result.id,
        nctid: result.nctid || result.id,
        title: result.title,
        status: result.status,
        phase: result.phase,
        brief_summary: result.brief_summary,
        lead_sponsor: result.lead_sponsor,
        conditions: result.conditions,
        structured_info: result.structured_info
      };
    }
    
    searchLogger.debug('[Result] Transformed result for sidebar:', transformedResult);
    setSelectedResult(transformedResult);
  };

  // Total pages (based on integrated results)
  const totalPages = results ? results.totalPages : 1;
  searchLogger.debug('[Pagination] Calculated total pages:', totalPages);

  // Reset all states when logo is clicked
  const handleLogoClick = () => {
    searchLogger.debug('[Logo] Clicked logo. Resetting all states to initial values.');
    setFilters(defaultFilters());
    setQuery('');
    setLastSearchedQuery('');
    setPage(1);
    setPageSize(10);
    setRefinedQuery(null);
    setAppliedQueries(null);
    setCtgTokenHistory({});
    setSearchHistory([]);
    setResults(null);
    sessionStorage.removeItem(SESSION_KEY);
    searchLogger.debug('[Logo] State reset complete. Reloading page and navigating to root.');
    navigate('/');
    window.location.reload();
  };

  
  const containerRef = useRef(null);
  const [panelWidth, setPanelWidth] = useState(300);
  const visibleCount = 2;

  useEffect(() => {
    const firstPanel = containerRef.current?.querySelector('.panel');
    if (firstPanel) {
      setPanelWidth(firstPanel.offsetWidth + 16); // +16 for gap
    }
  }, []);

  const scrollByPanels = (direction) => {
    if (containerRef.current) {
      containerRef.current.scrollBy({
        left: direction * panelWidth * visibleCount,
        behavior: 'smooth',
      });
    }
  };

  const filter_mapping = (field) => {
    const mapping = {
      "intr": "intervention",
      "cond": "condition",
      "study_type": "study type",
      "other_term": "other term",
      "locStr": ""
    }

    if (Object.hasOwn(mapping, field)) return mapping[field]
    return field
  }

  const defaultFormat = (refinedQuery) => {
  const allowedKeys = [
    "age", "city", "cond", "country", "intr", "phase",
    "sex", "sponsor", "state", "study_type"
  ];

  const mapping = {
    cond: "condition",
    intr: "intervention",
    study_type: "study type",
    other_term: "other term",
    locStr: "location",
  };

  const filteredEntries = Object.entries(refinedQuery)
    .filter(([key, value]) => allowedKeys.includes(key) && value !== null && value !== undefined && value !== "")
    .map(([key, value]) => {
      const displayValue = Array.isArray(value) ? value.join(", ") : value;
      return [key, displayValue];
    });

  return (
    <div>
      {/* First entry in Style A */}
      {refinedQuery && refinedQuery.query && (
        <div>
          <span className="font-semibold text-custom-text text-sm mr-1">
            your query:
          </span>
          <span className="font-mono text-sm">
            &apos;{refinedQuery.query}&apos;
          </span>
        </div>
      )}

      <span className="font-semibold text-custom-text text-sm py-1">Search Filters:</span>

      {/* Remaining entries in Style B */}
      <div className="flex flex-wrap gap-1 mt-2 ">
      {filteredEntries.map(([key, value]) => (
        
          <span key={key}  className="bg-blue-100 text-blue-800 text-xs flex items-center space-2 px-2 py-1 rounded-full mb-1">
            {mapping[key] || key}: {value}
          </span>
        
      ))}
      </div>
    </div>
  );
};

  return (
    <>
      <div className=""><Header/></div>
      
      <div className="flex" style={{ height: 'calc(100vh - 64px)' }}>
        {/* Left Filter Sidebar - Always visible in non-patient mode */}
        <FilterSidebar
          isVisible={!patientMode}
          onApplyFilters={handleApplyFilters}
          isLoading={loading}
          searchKey={searchKey}
          filterStats={results?.filter_stats}
          filters={pubmedFilters}
          setFilters={setPubmedFilters}
          expandedWidth="20%"
          collapsedWidth="2rem"
          onToggle={setLeftSidebarOpen}
          otherSidebarOpen={rightSidebarOpen}
        />
        
        {/* Main content area */}
        <div className="flex-grow min-w-0 flex flex-col overflow-hidden">
          <div className="flex-grow overflow-y-auto">
            <div className="mb-4 cursor-pointer mt-8" onClick={handleLogoClick}>
            <h1 className="text-3xl font-bold text-center text-black tracking-tight mb-6 hover:opacity-80 transition">
              Clinical Trials Hub
            </h1>
          </div>

          <SearchBar 
            query={query} 
            setQuery={setQuery}
            loading={loading}
            filters={filters}
            onSubmit={() => {
              if (hasSearchCriteria(query, filters)) {
                searchLogger.debug('[SearchBar] Search triggered from SearchBar with filters');
                handleSearch();
              }
            }}
            patientMode={patientMode} 
          />

          { !patientMode && ( <FilterPanel filters={filters} setFilters={setFilters} />)}

          { patientMode && ( <PatientFilterPanel filters={filters} setFilters={setFilters} />)}

          {/* Eligibility Criteria Section - Independent of search/filter/pagination */}
          <div className="w-full max-w-7xl mx-auto px-4 mt-4">
            <EligibilityCriteria
              inclusionCriteria={inclusionCriteria}
              setInclusionCriteria={setInclusionCriteria}
              exclusionCriteria={exclusionCriteria}
              setExclusionCriteria={setExclusionCriteria}
            />
          </div>

          <div className="w-full max-w-7xl mx-auto px-4">
            <div className="flex text-sm items-center ml-1 gap-2">
              <span className="text-custom-text font-semibold mr-2">Select Browsing Mode:</span>
              <button
                onClick={function handleClick() {
                  setPatientMode(false) 
                  setFilters(createFilters())
                  setResults(null)
                  setPatientResults(null)
                }}
                className={`flex items-center gap-1 py-1 px-1 transition-all ${
                  !patientMode 
                    ? 'text-gray-900 font-semibold' 
                    : 'text-gray-400 font-normal hover:text-gray-600'
                }`}
              >
                <span>Expert</span>
                <span className={`text-lg ${!patientMode ? 'opacity-100' : 'opacity-0'}`}>✓</span>
              </button>
              <button
                onClick={function handleClick() {
                  setPatientMode(true) 
                  setFilters(createFilters())
                  setResults(null)
                  setPatientResults(null)
                }}
                className={`flex items-center gap-1 py-1 px-1 transition-all ${
                  patientMode 
                    ? 'text-gray-900 font-semibold' 
                    : 'text-gray-400 font-normal hover:text-gray-600'
                }`}
              >
                <span>Patient</span>
                <span className={`text-lg ${patientMode ? 'opacity-100' : 'opacity-0'}`}>✓</span>
              </button>
            </div>
         
          </div>
            
          {/* Active filters display - HIDDEN */}
          {activeFilters && (
            <div className="mt-2 w-full max-w-7xl mx-auto px-4" style={{display: 'none'}}>
              <div className="text-sm text-gray-600">
                Active filters: 
                {activeFilters.phase && activeFilters.phase.length > 0 && (
                  <span className="ml-2">Phase: {activeFilters.phase.join(', ')}</span>
                )}
                {activeFilters.study_type && activeFilters.study_type.length > 0 && (
                  <span className="ml-2">Type: {activeFilters.study_type.join(', ')}</span>
                )}
                {activeFilters.date_range && (
                  <span className="ml-2">
                    Date: {activeFilters.date_range.from || 'Any'} - {activeFilters.date_range.to || 'Any'}
                  </span>
                )}
              </div>
            </div>
          )}

          
          {/* Search results area */}
          
          { dynamicQueries && dynamicQueries.queries && dynamicQueries.queries.length > 0 && (
            <QueryList
              dynamicQueries={dynamicQueries}
              handleQuerySelect={handleQuerySelect}
              baseResults={baseResults}
              pubmedFilters={pubmedFilters}
             />
          )}

          { patientResults && (
             <>
              <div className="w-full flex max-w-7xl mx-auto px-4 mt-5 mb-10">
                <button
                  onClick={() => scrollByPanels(-1)}
                  className="mr-2  "
                >
                  <ArrowLeft size={25} className="p-1 mr-1 text-gray-500 bg-gray-200 rounded-full" />
                </button>
                <div ref={containerRef}
                    className="flex overflow-x-auto scrollbar scrollbar-w-2 scrollbar-track-transparent space-x-4 p-3">
                {patientResults.map((item, index) => (
                  <div
                    key={index} className={` panel min-w-[300px] flex-shrink-0  p-4 rounded shadow flex flex-col  bg-white light:border-primary-12 light:bg-secondary-100 rounded-2xl light:shadow-splash-chatpgpt-input hover:ring-2 hover:ring-neutral-200 p-4 border ${
                     selectedQuery === index ? 'ring-2 ring-neutral-300' : '' }`}
                 
                    style={{
                      flex: 1 / 4,
                    }}
                    onClick={function handleClick() {
                      handlePatientQuerySelect(item)
                      setSelectedQuery(index)
                  }}
                  >
                    <span className="bg-purple-50 text-purple-700 text-sm font-bold px-2 py-1 w-fit rounded-full">{item.name}</span>
                    <span className=" px-1 py-2 text-custom-text-subtle text-sm">{item.total} trials found</span>
                    <div className="border-b border-gray-200 mx-1 my-1"></div>
                    <div className="px-1 pt-2 pb-1 text-sm text-custom-text ">{item.name === "Default" ? defaultFormat(item.refinedQuery) : item.description}</div>
                    { item.modified.length > 0 && (
                      <>
                        <span className=" px-1 font-semibold text-custom-text text-sm">Modified Search Fields:</span>
                        <div className="flex flex-wrap gap-1 mt-2">
                          {item.modified.map((field, index) => (
                            field !== "locStr" && (
                                <div className="bg-gray-100 text-gray-800 text-xs flex items-center space-x-2 px-2 py-1 rounded-full" key={index}>{filter_mapping(field)}</div>
                            )
                            
                          ))}
                        </div>
                      </>
                    )}
                    
                  </div>
                ))}
                </div>
                <button
                  onClick={() => scrollByPanels(1)}
                  className="ml-5"
                >
                  <ArrowRight size={25} className="p-1 text-gray-500 bg-gray-200 rounded-full" />
                </button>
              </div>
              </>             
            )}
            
          {loading ? (
            <div className="text-center mt-6">Loading...</div>
          ) : (
            <>
              <SearchResults
                results={results}
                onResultSelect={handleResultSelect}
                onViewDetails={handleViewDetails}
                mergedItemFocus={mergedItemFocus}
                setMergedItemFocus={setMergedItemFocus}
                originalQuery={lastSearchedQuery}
                refinedQuery={refinedQuery}
                appliedQueries={appliedQueries}
                filters={filters}
              />

            
            
              
              {/* AI Insights Section   
            {!patientMode && results && results.results && results.results.length > 0 && (
                <SearchInsights
                  searchKey={searchKey}
                  page={page}
                  appliedFilters={activeFilters}
                  results={results}
                />
              )} */}
            </>
          )}

          {/* Pagination buttons */}
          {results && results.total > 0 && (
            <div className="mx-auto w-full max-w-[768px] mb-8 flex justify-center items-center gap-6 mt-8">
              <button
                disabled={page === 1}
                onClick={() => goToPage(page - 1)}
                className="text-sm font-medium rounded-full text-black transition"
              >
                <StepBack size={20} />
              </button>
              <span className="text-sm text-custom-text">
                Page {page} of {totalPages}
              </span>
              <button
                disabled={page === totalPages}
                onClick={() => goToPage(page + 1)}
                className="text-sm font-medium rounded-full text-black transition"
              >
                <StepForward size={20} />
              </button>
            </div>
          )}
          </div>
        </div>

        {/* Right detail sidebar */}
        <DetailSidebar
          selectedResult={selectedResult}
          isVisible={!!(results && searchKey)}
          expandedWidth="30%"    
          collapsedWidth="2rem"
          onToggle={setRightSidebarOpen}
          otherSidebarOpen={leftSidebarOpen}
          inclusionCriteria={inclusionCriteria}
          exclusionCriteria={exclusionCriteria}
        />
      </div>
    </>
  );
};

export default SearchPage;