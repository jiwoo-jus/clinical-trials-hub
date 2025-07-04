import React, { useState, useEffect } from 'react';
import Header from '../components/Header';
import { useNavigate } from 'react-router-dom';
import { db, auth } from "../firebase";
import { collection, getDocs, query, orderBy, doc, deleteDoc } from "firebase/firestore";

function History() {
  const navigate = useNavigate();
  const [history, setHistory] = useState([]);
  const [selectedIndexes, setSelectedIndexes] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  
  const toggleSelect = (index) => {
  setSelectedIndexes((prev) =>
    prev.includes(index)
      ? prev.filter((i) => i !== index)
      : [...prev, index]
    );
  };

  const loadSearchHistory = async () => {
    const user = auth.currentUser;
    if (!user) return [];

    const q = query(
      collection(db, "users", user.uid, "searchHistory"),
      orderBy("createdAt", "desc")
    );

    const snapshot = await getDocs(q);
    return snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
  };

  const deleteSelected = async () => {
    const toDelete = history.filter((_, idx) => selectedIndexes.includes(idx));
    const user = auth.currentUser;
    await Promise.all(
      toDelete.map(entry =>
        deleteDoc(doc(db, "users", user.uid, "searchHistory", entry.id))
      )
    );
    // Refresh local state
    const updatedHistory = history.filter((_, idx) => !selectedIndexes.includes(idx));
    setHistory(updatedHistory);
    setSelectedIndexes([]);
  };

  const filteredHistory = history.filter((entry) =>
    entry.user_query?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleViewResults = (entry) => {
      const params = new URLSearchParams();
      if (entry.cond) params.append('cond', entry.cond);
      if (entry.intr) params.append('intr', entry.intr);
      if (entry.other_term) params.append('other_term', entry.other_term);
      if (entry.journal) params.append('journal', entry.journal);
      if (entry.sex) params.append('sex', entry.sex);
      if (entry.age) params.append('age', entry.age);
      if (entry.studyType) params.append('studyType', entry.studyType);
      if (entry.sponsor) params.append('sponsor', entry.sponsor);
      if (entry.location) params.append('location', entry.location);
      if (entry.status) params.append('status', entry.status);
      if (entry.sources) {
        params.append('sources', entry.sources.join(','));
      }
      if (entry.user_query) params.append('user_query', entry.user_query);
      
      navigate(`/?${params.toString()}`);
  };

  const clearHistory = async () => {
    const user = auth.currentUser;
    const snapshot = await getDocs(collection(db, "users", user.uid, "searchHistory"));
    const deleteOps = snapshot.docs.map(docRef =>
      deleteDoc(doc(db, "users", user.uid, "searchHistory", docRef.id))
    );

    await Promise.all(deleteOps);

    setHistory([]);
    setSelectedIndexes([]);
  };

  useEffect(() => {
    const fetchHistory = async () => {
      const data = await loadSearchHistory();
      setHistory(data);
    };

    fetchHistory();
  }, []);

  return (
    <><Header/>
    <div className="px-6 py-8 max-w-screen-2xl mx-auto">
      <h1
        className="text-3xl text-left font-bold text-black tracking-tight  cursor-pointer mb-6 hover:opacity-80 transition"
      >
        Recent Activity
      </h1>
    
      <div className="bg-blue-50 border   px-4 py-3 mb-4  text-sm text-blue-900">
  
      {/* Display Settings */}
      <div className="flex flex-wrap items-center gap-4 mb-2">
        <div className="font-semibold">Display Settings:</div>
        <div className="flex items-center gap-3">
          <span className="hover:underline cursor-pointer">Sort by date</span>
        </div>
      </div>

      {/* Actions */}
      <div className="flex flex-wrap items-center gap-3">
        <span className="font-semibold">Select:</span>
        <button
          className="underline text-blue-700 hover:text-blue-900"
          onClick={() =>
            setSelectedIndexes(history.map((_, idx) => idx))
          }
        >
          All
        </button>
        <button
          className="underline text-blue-700 hover:text-blue-900"
          onClick={() => setSelectedIndexes([])}
        >
          None
        </button>
        <span>{selectedIndexes.length} item{selectedIndexes.length !== 1 ? 's' : ''} selected</span>

        {/* Action Buttons */}
        <button
          onClick={deleteSelected}
          disabled={selectedIndexes.length === 0}
          className="px-3 py-1 bg-red-500 text-white rounded-md text-xs hover:bg-red-600 disabled:opacity-50 disabled:hover:bg-red-500"
        >
          Delete Selected
        </button>
        <button className="px-3 py-1 bg-blue-100 text-blue-800 rounded-md text-xs hover:bg-blue-200"
        onClick={clearHistory}>
          Clear History
        </button>
      </div>
  
</div>

      <div className="flex items-center gap-3 mt-auto border-custom-border pt-1 mb-3">
        <input
          type="text"
          placeholder="Search Recent Activity"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="border border-custom-border rounded px-4 py-2 text-sm focus:outline-none  w-1/2"
        />
        
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm table-auto text-custom-text border border-gray-300">
          <thead className="bg-gray-100">
            <tr>
              <th className="px-4 py-2 border-b text-left w-[15%]">Date</th>
              <th className="px-4 py-2 border-b text-left w-[18%]">Query</th>
              <th className="px-4 py-2 border-b text-left w-[35%]">Search Filters</th>
              <th className = "px-4 py-2 border-b text-left w-[20%]">Results</th>
              <th className="px-4 py-2 border-b text-left w-[7%]">Action</th>
              <th className="border-b px-4 w-[5%]"></th>
            </tr>
          </thead>
          <tbody>
            {history.length === 0 ? (
              <tr>
                <td colSpan="6" className="text-left px-4 py-4 text-gray-500">
                  No search history available.
                </td>
              </tr>
            ) : (
              filteredHistory.map((entry, idx) => (
                <React.Fragment key={idx}>
                  {/* Row 1: Date, Query, Results */}
                  <tr className="hover:bg-gray-50 border-b">
                    <td className="px-4 py-2">
                      {(new Date(entry.createdAt.seconds * 1000)).toLocaleString('en-US', {
                        timeZone: 'America/New_York',
                        year: '2-digit',
                        month: '2-digit',
                        day: '2-digit',
                        hour: '2-digit',
                        minute: '2-digit',
                        hour12: true,
                      })}
                    </td>
                    <td className="px-4 py-2 ">
                      {entry.user_query || <span className="text-gray-400">N/A</span>}
                    </td> 
                    <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-2">
                      {[
                        { label: 'Condition', value: entry.cond },
                        { label: 'Intervention', value: entry.intr },
                        { label: 'Other Terms', value: entry.other_term },
                        { label: 'Journal', value: entry.journal },
                        { label: 'Sex', value: entry.sex },
                        { label: 'Age', value: entry.age },
                        { label: 'Study Type', value: entry.studyType },
                        { label: 'Sponsor', value: entry.sponsor },
                        { label: 'Location', value: entry.location },
                        { label: 'Status', value: entry.status },
                        { label: 'Sources', value: entry.sources?.join(', ') },
                      ]
                        .filter(({ value }) => value !== null && value !== undefined && value !== '')
                        .map(({ label, value }) => (
                          <span
                            key={label}
                            className="inline-block px-3 py-1 text-sm rounded-full border border-gray-300"
                          >
                            <strong className="text-custom-blue-deep font-semibold">{label}:</strong> {value}
                          </span>
                        ))}
                    </div>
                  </td>
                   <td className="px-4 py-2">
                      <div className="text-sm">
                        {entry.results_count !== undefined ? (
                          <div className="space-y-1">
                            <div className="font-semibold text-gray-900">
                              Total: {entry.results_count}
                            </div>
                            {entry.counts && (
                              <div className="text-xs text-gray-600 space-y-0.5">
                                {entry.counts.merged > 0 && <div>Merged: {entry.counts.merged}</div>}
                                {entry.counts.pm_only > 0 && <div>PubMed: {entry.counts.pm_only}</div>}
                                {entry.counts.ctg_only > 0 && <div>CTG: {entry.counts.ctg_only}</div>}
                              </div>
                            )}
                            {entry.applied_queries && (
                              <div className="text-xs text-blue-600 mt-1">
                                {entry.applied_queries.pubmed && (
                                  <div title={entry.applied_queries.pubmed}>
                                    PM: {entry.applied_queries.pubmed.length > 30 ? 
                                      entry.applied_queries.pubmed.substring(0, 30) + '...' : 
                                      entry.applied_queries.pubmed}
                                  </div>
                                )}
                                {entry.applied_queries.clinicaltrials && (
                                  <div title={entry.applied_queries.clinicaltrials}>
                                    CTG: {entry.applied_queries.clinicaltrials.length > 30 ? 
                                      entry.applied_queries.clinicaltrials.substring(0, 30) + '...' : 
                                      entry.applied_queries.clinicaltrials}
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        ) : (
                          <span className="text-gray-400">N/A</span>
                        )}
                      </div>
                    </td>
                   <td className="px-4 py-2 ">
                      <button  
                        className="text-blue-600 hover:underline text-sm"
                        onClick={() => handleViewResults(entry)}
                      >
                        View Results 
                      </button>
                    </td>
                   <td className="px-2 py-2 border-b text-center">
                    <input
                      type="checkbox"
                      checked={selectedIndexes.includes(idx)}
                      onChange={() => toggleSelect(idx)}
                      className="form-checkbox h-4 w-4 text-blue-600"
                    />
                  </td>
                  </tr>
              </React.Fragment>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div></>
  );
}

export default History;