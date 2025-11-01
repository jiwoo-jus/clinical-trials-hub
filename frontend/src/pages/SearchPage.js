import { addDoc, collection, serverTimestamp } from "firebase/firestore";
import _isEqual from 'lodash/isEqual';
import { StepBack, StepForward } from 'lucide-react';
import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {ArrowLeft, ArrowRight } from 'lucide-react';
import { filterSearchResults, getPatientQueries, getPatientNextPage, searchClinicalTrials } from '../api/searchApi'; //
import DetailSidebar from '../components/DetailSidebar';
import QueryList from '../components/QueryList';
import { FilterPanel } from '../components/FilterPanel';
import { PatientFilterPanel } from '../components/PatientFilterPanel';
import FilterSidebar from '../components/FilterSidebar';
import Header from '../components/Header';
import { SearchBar } from '../components/SearchBar';
//import SearchInsights from '../components/SearchInsights';
import SearchResults from '../components/SearchResults';
import { auth, db } from "../firebase";

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
    console.error("Error saving search:", error);
  }
};

const defaultFilters = () => ({
  cond: null,
  intr: null,
  other_term: null,
  journal: null,
  sex: null,
  age: null,
  studyType: null,
  sponsor: null,
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
  journal: null,
  sex: null,
  age: null,
  studyType: null,
  sponsor: null,
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
  const [isRefined, setIsRefined] = useState(false);
  const [refinedQuery, setRefinedQuery] = useState(null);
  const [appliedQueries, setAppliedQueries] = useState(null);
  const [ctgTokenHistory, setCtgTokenHistory] = useState({});
  const [results, setResults] = useState(null);
  const [patientResults, setPatientResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [searchHistory, setSearchHistory] = useState([]);
  const [selectedResult, setSelectedResult] = useState(null);
  const [mergedItemFocus, setMergedItemFocus] = useState({});

  // Remove URL query parameters on initial load
  useEffect(() => {
    if (window.location.search) {
      console.log('[Initial] Removing URL query parameters on first mount.');
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
        console.log('[Cache] Loaded cache:', parsed);
        return parsed;
      } catch (e) {
        console.error('[Cache] Failed parsing cache:', e);
        return null;
      }
    }
    return null;
  };

  // Cache saving helper
  const saveCache = (cacheObj) => {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(cacheObj));
    console.log('[Cache] Saved cache:', cacheObj);
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
        console.log('[Initial] Found shared new-tab cache in localStorage:', parsedShared);
        if (parsedShared && parsedShared.dynamicQueries) {
          setDynamicQueries(parsedShared.dynamicQueries);
          restoredFromShared = true;
        }
        // consume it once restored
        localStorage.removeItem(NEW_TAB_CACHE_KEY);
      }
    } catch (e) {
      console.error('[Initial] Failed to read shared new-tab cache:', e);
    }
    if (location.state && location.state.searchState) {
      console.log('[Initial] Restoring state from location.state:', location.state.searchState);
      cameFromDetailRef.current = true;
      const state = location.state.searchState;
      setFilters(state.filters);
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
        console.log('[Initial] Restoring searchKey from location.state:', state.searchKey);
        setSearchKey(state.searchKey);
      }
      
      saveCache({
        filters: state.filters,
        pageSize: state.pageSize,
        searchHistory: state.searchHistory || [],
        currentPage: state.page,
        lastSearchedQuery: state.lastSearchedQuery || '',
        appliedQueries: state.appliedQueries || null,
        query: state.query || '',
        searchKey: state.searchKey, // Add searchKey to cache
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
      console.log('[Initial] Setting URL parameters from location.state:', newParams);
      setSearchParams(newParams);
      navigate({ search: "?" + new URLSearchParams(newParams).toString() }, { replace: true });
      
      // Mark as restored
      restoredRef.current = true;
      return;
    }

    const cachedState = loadCache();
      if (cachedState) {
      console.log('[Initial] Restoring state from session cache.');
      setFilters(cachedState.filters);
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
      
      // Restore filter application state
      if (cachedState.hasAppliedFilters) {
        setHasAppliedFilters(true);
        setActiveFilters(cachedState.activeFilters);
        console.log('[Initial] Restored filter state - hasAppliedFilters:', true, 'activeFilters:', cachedState.activeFilters);
      }
      
      // Restore searchKey from cache
      if (cachedState.searchKey) {
        console.log('[Initial] Restoring searchKey from cache:', cachedState.searchKey);
        setSearchKey(cachedState.searchKey);
      }
      if (cachedState.pageCache && cachedState.pageCache[cachedState.currentPage]) {
        const pageData = cachedState.pageCache[cachedState.currentPage];
        setResults(pageData.results);
        setRefinedQuery(pageData.refinedQuery);
        setCtgTokenHistory(pageData.ctgTokenHistory);
      }
      const newParams = buildUrlParams({
        ...cachedState.filters,
        isRefined: cachedState.pageCache &&
                   cachedState.pageCache[cachedState.currentPage] &&
                   cachedState.pageCache[cachedState.currentPage].refinedQuery
          ? "true"
          : "false"
      });
      console.log('[Initial] Setting URL parameters from cache:', newParams);
      setSearchParams(newParams);
      navigate({ search: "?" + new URLSearchParams(newParams).toString() }, { replace: true });
      
      restoredRef.current = true;
      return;
    }

    // First entry (no cache or location.state)
    console.log('[Initial] First entry with URL params:', initialParams);
    setFilters(createFilters(initialParams));
    setPage(Number(initialParams.page) || 1);
    setPageSize(Number(initialParams.pageSize) || 10);
    setIsRefined(initialParams.isRefined === 'true');
    setRefinedQuery(initialParams.refinedQuery ? JSON.parse(initialParams.refinedQuery) : null);

    // Restore user_query from URL
    if (initialParams.user_query) {
      setQuery(initialParams.user_query);
      console.log('[Initial] Restored user_query from URL:', initialParams.user_query);
    }

    if (initialParams.cond || initialParams.intr || initialParams.other_term || initialParams.user_query) {
      console.log('[Initial] Auto-triggering search on first entry.');
      handleSearch({
        ...createFilters(initialParams),
        user_query: initialParams.user_query || '',
        page: Number(initialParams.page) || 1,
        pageSize: Number(initialParams.pageSize) || 10,
        isRefined: initialParams.isRefined === 'true',
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
      console.log('[Filters] Skipping reset due to automatic backend update.');
      autoUpdateRef.current = false;
      prevFiltersRef.current = filters;
      return;
    }

    // Skip reset logic if updated by restoration
    if (restoredRef.current) {
      console.log('[Filters] Skipping effect due to restoration of state.');
      prevFiltersRef.current = filters;
      restoredRef.current = false;
      return;
    }

    // Exclude initial mount from change detection
    if (initialMountRef.current) {
      initialMountRef.current = false;
      console.log('[Filters] Initial mount completed.');
      prevFiltersRef.current = filters;
      return;
    }

    console.log('[Filters] Filters changed:', filters);

    const prevFilters = prevFiltersRef.current;
    console.log('[Filters] Previous filters:', prevFilters);
    console.log('[Filters] Current filters:', filters);

    const changedKeys = Object.keys(filters).filter((key) => {
      if (key === 'refinedQuery') {
        return !_isEqual(filters[key], prevFilters[key]);
      }
      return filters[key] !== prevFilters[key];
    });
    console.log('[Filters] Changed keys:', changedKeys);

    prevFiltersRef.current = filters;

    if (cameFromDetailRef.current) {
      console.log('[Filters] Skipping page reset due to return from detail page.');
      cameFromDetailRef.current = false;
      return;
    }

    if (
      changedKeys.length === 0 ||
      (changedKeys.length <= 3 && changedKeys.every((key) => ['page', 'refinedQuery', 'ctgPageToken'].includes(key)))
    ) {
      console.log('[Filters] Only page, refinedQuery, or ctgPageToken changed (or no changes), skipping reset.');
      return;
    }

    console.log('[Filters] Resetting page, refined query, and CTG token history due to manual filter change.');
    setIsRefined(false);
    setRefinedQuery(null);
    setPage(1);
    setCtgTokenHistory({});
  }, [filters, sourcesString]);

  const handleViewDetails = (item) => {
    console.log('[Detail] View details for item:', item);

    const stateToPass = {
      filters,
      results,
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
        page: page,
        index: results?.results?.findIndex(r => r.id === item.id) || 0,
        source: item.type
      };
    }

    // Update sessionStorage cache
    const cached = loadCache() || { pageCache: {} };
    cached.filters = filters;
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
      if (value === undefined || value === null || value === '') {
        return acc;
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
    console.log('[Search] API response:', data);
      
    console.log('[Search] API response type:', typeof data.results);
    console.log('[Search] API response results:', data.results);

    let rawFilters = { ...filters, user_query: query, page: 1, pageSize, ctgPageToken: null };
    const updatedFilters = { ...rawFilters };
    
    // Save search_key
    if (data.search_key) {
      console.log('[Search] Setting searchKey:', data.search_key);
      setSearchKey(data.search_key);
      setActiveFilters(null);
      setHasAppliedFilters(false);
    } else {
      console.log('[Search] No search_key received in response');
    }

    // Save applied queries information (actual queries sent to API)
    if (data.appliedQueries) {
      setAppliedQueries(data.appliedQueries);
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
      ...updatedFilters,
      isRefined: updatedFilters.isRefined ? "true" : "false"
    });
    console.log('[Search] Updating URL and cache with newParams:', newParams);
    setSearchParams(newParams);
    navigate({ search: "?" + new URLSearchParams(newParams).toString() }, { replace: true });

    const cached = loadCache() || {};
    cached.filters = updatedFilters;
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
    saveCache(cached);
    console.log('[Search] Search completed, current page:', updatedFilters.page);
    
  } 
  const handlePatientQuerySelect = (data) => {
    console.log('[Search] API response:', data);
      
    console.log('[Search] API response type:', typeof data.results);
    console.log('[Search] API response results:', data.results);

    let rawFilters = { ...filters, user_query: query, page: 1, pageSize, ctgPageToken: null };
    const updatedFilters = { ...rawFilters };
    
    // Save search_key
    if (data.search_key) {
      console.log('[Search] Setting searchKey:', data.search_key);
      setSearchKey(data.search_key);
      setActiveFilters(null);
      setHasAppliedFilters(false);
    } else {
      console.log('[Search] No search_key received in response');
    }

    // Save applied queries information (actual queries sent to API)
    if (data.appliedQueries) {
      setAppliedQueries(data.appliedQueries);
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
      ...updatedFilters,
      isRefined: updatedFilters.isRefined ? "true" : "false"
    });
    console.log('[Search] Updating URL and cache with newParams:', newParams);
    setSearchParams(newParams);
    navigate({ search: "?" + new URLSearchParams(newParams).toString() }, { replace: true });
    
    const cached = loadCache() || {};
    cached.filters = updatedFilters;
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
    saveCache(cached);
    console.log('[Search] Search completed, current page:', updatedFilters.page);
  }

  

  // Search API call and cache update (with refinedQuery applied)
  const handleSearch = async (customParams = null, forceNewSearch = false) => {
    console.log('[Search] handleSearch called with params:', customParams, 'forceNewSearch:', forceNewSearch);
    
    // Force new search: completely reset all states like initial entry
    if (forceNewSearch) {
      console.log('[Search] Force new search - completely resetting all states like initial entry');
      
      // Save current query for restoration after backend response
      const currentUserQuery = query.trim();
      
      // Reset all search-related states
      setResults(null);
      setIsRefined(false);
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
        page: 1,
        pageSize: pageSize
      };
      
      console.log('[Search] Force new search with payload:', searchPayload);
      
      setLoading(true);
      try {
        let data = await searchClinicalTrials(searchPayload);
        console.log('[Search] Force new search API response:', data);
          
          // Set search_key
          if (data.search_key) {
            console.log('[Search] Setting searchKey from force new search:', data.search_key);
            setSearchKey(data.search_key);
          }
        
        console.log('[Search] Force new search API response:', data);
        
        // Save applied queries information
        if (data.appliedQueries) {
          setAppliedQueries(data.appliedQueries);
        }
        
        // Store refinedQuery but don't apply to filters (protect user input fields)
        let finalFilters = resetFilters;
        if (data.refinedQuery) {
          console.log('[Search] Received refinedQuery from API (not applying to filters):', data.refinedQuery);
          setRefinedQuery(data.refinedQuery);
          setIsRefined(true);
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
        
        console.log('[Search] Force new search completed successfully');
        
      } catch (error) {
        console.error('[Search] Force new search error:', error);
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

      console.log('[Search] Getting patient query using filters:', effectiveFilters);
      setLoading(true);
      let data = {}
      try {
        data = await getPatientQueries(effectiveFilters);
      } catch (error) {
        data = null
        console.log('[Search] Patient search error:', effectiveFilters);
      } finally {
        setLoading(false)
      }
      console.log('[Search] received response:', data)
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
      rawFilters = { ...filters, user_query: query, page: 1, pageSize, ctgPageToken: null };
      console.log('[Search] Using current filters with query:', rawFilters);
    } else {
      rawFilters = customParams;
    }
    
    const effectiveFilters = preparePayload(rawFilters);
    console.log('[Search] Prepared effective filters for API:', effectiveFilters);
    setLoading(true);
    try {
      effectiveFilters.ctgPageToken = ctgTokenHistory[effectiveFilters.page] || null;
      const data = await searchClinicalTrials(effectiveFilters);
      console.log('[Search] API response:', data);
      
      console.log('[Search] API response type:', typeof data.results);
      console.log('[Search] API response results:', data.results);

      setBaseResults({
        results: Array.isArray(data.results) ? data.results : [],
        counts: data.counts || { total: 0, merged: 0, pm_only: 0, ctg_only: 0 },
        total: data.total || 0,
        totalPages: data.totalPages || 1,
        filter_stats: data.filter_stats,
        refinedQuery: data.refinedQuery,
        appliedQueries: data.appliedQueries
      })
      
      // Save search_key
      if (data.search_key) {
        console.log('[Search] Setting searchKey:', data.search_key);
        setSearchKey(data.search_key);
        setActiveFilters(null);
        setHasAppliedFilters(false);
      } else {
        console.log('[Search] No search_key received in response');
      }

      // Save applied queries information (actual queries sent to API)
      if (data.appliedQueries) {
        setAppliedQueries(data.appliedQueries);
      }
      
      // Store refinedQuery but don't apply to filters (protect user input fields)
      const updatedFilters = { ...rawFilters };
      if (data.refinedQuery) {
        console.log('[Search] Received refinedQuery from API (not applying to filters):', data.refinedQuery);
        updatedFilters.refinedQuery = data.refinedQuery;
        updatedFilters.isRefined = true;
        setRefinedQuery(data.refinedQuery);
        setIsRefined(true);
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
            console.error('Failed to save search history:', error);
          }
        }
      }
      
      const newParams = buildUrlParams({
        ...updatedFilters,
        isRefined: updatedFilters.isRefined ? "true" : "false"
      });
      console.log('[Search] Updating URL and cache with newParams:', newParams);
      setSearchParams(newParams);
      navigate({ search: "?" + new URLSearchParams(newParams).toString() }, { replace: true });
      
      const cached = loadCache() || {};
      if (cached.dynamicQueries) {
        setDynamicQueries(cached.dynamicQueries);
      }

      cached.filters = updatedFilters;
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
      saveCache(cached);
      console.log('[Search] Search completed, current page:', updatedFilters.page);
    } catch (error) {
      console.error('[Search] Error during search:', error);
      setResults(null);
    } finally {
      setLoading(false);
    }
  };

    // Filter application function
  const handleApplyFilters = async (filterParams) => {
    setLoading(true);
    try {
      console.log('[Filter] Applying filters:', filterParams);
      const data = await filterSearchResults(filterParams);
      console.log('[Filter] Filter response received:', data);
      
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
      setPage(data.page || 1);
      
      // Update cache - include filter application state
      const cacheToSave = {
        filters,
        pageSize,
        searchHistory,
        currentPage: data.page || 1,
        lastSearchedQuery,
        appliedQueries,
        query,
        searchKey,
        activeFilters: data.filters_applied,
        hasAppliedFilters: true,
        pageCache: {
          [data.page || 1]: {
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
      saveCache(cacheToSave);
      
    } catch (error) {
      console.error('Filter error:', error);
      alert('Failed to apply filters. Please try again.');
    } finally {
      setLoading(false);
    }
  };


  // Page navigation: use cache if available, otherwise make API call
  const goToPage = async (newPage) => {
    console.log('[Pagination] goToPage called. Current page:', page, 'New page:', newPage);
    console.log('[Pagination] Has applied filters:', hasAppliedFilters, 'Active filters:', activeFilters);
    
    if (patientMode) {
      console.log("NEXT PAGE FOR SEARCH:", patientResults[selectedQuery])
      // Update page for selectedQuery
      let currentResults = patientResults[selectedQuery]
      currentResults.page = newPage
      setLoading(true)
      const newResults = await getPatientNextPage(currentResults)
      currentResults.results = newResults
      console.log("[Pagination] setting patient query", currentResults)
      handlePatientQuerySelect(currentResults)
      setLoading(false)
      return;
    }

    const cached = loadCache();
    if (cached && cached.pageCache && cached.pageCache[newPage]) {
      const pageData = cached.pageCache[newPage];
      console.log('[Pagination] Found cached data for page', newPage, ':', pageData);
      setPage(newPage);
      setResults(pageData.results);
      setRefinedQuery(pageData.refinedQuery);
      setCtgTokenHistory(pageData.ctgTokenHistory);
      setPatientMode(cached.patientMode);
      setPatientResults(cached.patientResults);
      setDynamicQueries(cached.dynamicQueries);
      setSelectedQuery(cached.selectedQuery);
      const newParams = buildUrlParams({
        ...cached.filters,
        isRefined: pageData.refinedQuery ? "true" : "false"
      });
      console.log('[Pagination] Updating URL for cached page change:', newParams);
      setSearchParams(newParams);
      navigate({ search: "?" + new URLSearchParams(newParams).toString() }, { replace: true });
      return;
    }
    
    console.log('[Pagination] No cache for page', newPage, '- triggering search.');
    setPage(newPage);
    
    // Call filter API if filters are applied, otherwise call regular search API
    if (hasAppliedFilters && activeFilters && searchKey) {
      console.log('[Pagination] Applying filters for page', newPage, 'with searchKey:', searchKey);
      handleApplyFilters({
        search_key: searchKey,
        ...activeFilters,
        page: newPage
      });
    } else {
      console.log('[Pagination] Regular search for page', newPage);
      handleSearch({
        ...filters,
        page: newPage,
        pageSize,
        isRefined,
        refinedQuery,
        ctgPageToken: ctgTokenHistory[newPage] || null
      });
    }
  };

  // Handle result item selection
  const handleResultSelect = (result) => {
    console.log('[Result] Selected result:', result);
    
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
    
    console.log('[Result] Transformed result for sidebar:', transformedResult);
    setSelectedResult(transformedResult);
  };

  // Total pages (based on integrated results)
  const totalPages = results ? results.totalPages : 1;
  console.log('[Pagination] Calculated total pages:', totalPages);

  // Reset all states when logo is clicked
  const handleLogoClick = () => {
    console.log('[Logo] Clicked logo. Resetting all states to initial values.');
    setFilters(defaultFilters());
    setQuery('');
    setLastSearchedQuery('');
    setPage(1);
    setPageSize(10);
    setIsRefined(false);
    setRefinedQuery(null);
    setAppliedQueries(null);
    setCtgTokenHistory({});
    setSearchHistory([]);
    setResults(null);
    sessionStorage.removeItem(SESSION_KEY);
    console.log('[Logo] State reset complete. Reloading page and navigating to root.');
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
        {/* Left Filter Sidebar */}
        <FilterSidebar
          isVisible={!!(results && searchKey && !patientMode)}
          onApplyFilters={handleApplyFilters}
          isLoading={loading}
          searchKey={searchKey}
          filterStats={results?.filter_stats}
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
                console.log('[SearchBar] Search triggered from SearchBar with filters');
                handleSearch();
              }
            }}
            patientMode={patientMode} 
          />

          { !patientMode && ( <FilterPanel filters={filters} setFilters={setFilters} />)}

          { patientMode && ( <PatientFilterPanel filters={filters} setFilters={setFilters} />)}

          <div className="w-full max-w-7xl mx-auto px-4">
            <div className="flex text-sm items-center ml-1  gap-1">
              <span className={`"text-custom-text font-semibold mr-2 " `}>Select Browsing Mode: </span>
              <button
                onClick={function handleClick() {
                  setPatientMode(false) 
                  setFilters(createFilters())
                  setResults(null)
                  setPatientResults(null)
                  }}
                className={`hover:bg-gray-200 hover:text-gray-800 mr-1 text-custom-text-subtle py-1 px-4 transition-colors font-semibold rounded-sm ${
                      !patientMode ? ' bg-green-100 text-green-800' : 'text-custom-text-subtle' }`}
              >
                
                Default
              </button>
              <button
                onClick={function handleClick() {
                  setPatientMode(true) 
                  setFilters(createFilters())
                  setResults(null)
                  setPatientResults(null)
                  }}
                className={`hover:bg-gray-200 hover:text-gray-800  py-1 px-4 transition-colors font-semibold rounded-sm ${
                     patientMode ? 'bg-blue-100 text-custom-blue-deep' : 'text-custom-text-subtle' }`}
              >
                Patient
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

            
            
              
              {/* AI Insights Section */}
            { /* {!patientMode && results && results.results && results.results.length > 0 && (
                <SearchInsights
                  searchKey={searchKey}
                  page={page}
                  appliedFilters={activeFilters}
                  results={results}
                />
              )} */ }
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
        />
      </div>
    </>
  );
};

export default SearchPage;