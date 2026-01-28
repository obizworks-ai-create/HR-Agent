import React, { useState, useEffect } from 'react';
import api from '../lib/api';
import {
    RefreshCw, Briefcase, Sparkles,
    CheckCircle, Target, XCircle, Clock, Users, ArrowRight, Filter, Loader2
} from 'lucide-react';
import clsx from 'clsx';

const AnalysisPage = () => {
    const [availableJobs, setAvailableJobs] = useState([]);
    const [selectedJob, setSelectedJob] = useState("");
    const [candidates, setCandidates] = useState([]);
    const [loading, setLoading] = useState(false);
    const [analyzing, setAnalyzing] = useState(false);
    const [verdictFilter, setVerdictFilter] = useState("ALL"); // ALL, PASS, FAIL

    // NEW: Date Filtering State
    const [timePeriod, setTimePeriod] = useState("ALL"); // ALL, LAST_24_HOURS, LAST_7_DAYS, LAST_30_DAYS, CUSTOM, CUSTOM_RANGE
    const [customDate, setCustomDate] = useState("");
    const [customEndDate, setCustomEndDate] = useState("");

    // NEW: Filter candidates locally by Verdict if needed (or backend)
    // The requirement is "filter displayed results". Backend /candidates supports date filter.

    useEffect(() => {
        fetchJobs();
    }, []);

    useEffect(() => {
        if (selectedJob) {
            fetchCandidates(selectedJob);
            const interval = setInterval(() => fetchCandidates(selectedJob), 30000);
            return () => clearInterval(interval);
        } else {
            setCandidates([]);
        }
    }, [selectedJob, timePeriod, customDate]); // Depend on timePeriod

    const fetchJobs = async () => {
        try {
            const res = await api.get('/jobs');
            setAvailableJobs(res.data);
        } catch (err) {
            console.error("Failed to fetch jobs:", err);
        }
    };

    const fetchCandidates = async (job) => {
        if (!job) return;
        setLoading(true);
        try {
            // Calculate Date Params
            let dateParams = "";
            const today = new Date();
            let startDateStr = "";

            if (timePeriod === "LAST_7_DAYS") {
                const d = new Date();
                d.setDate(today.getDate() - 7);
                startDateStr = d.toISOString().split('T')[0];
            } else if (timePeriod === "LAST_30_DAYS") {
                const d = new Date();
                d.setDate(today.getDate() - 30);
                startDateStr = d.toISOString().split('T')[0];
            } else if (timePeriod === "CUSTOM" && customDate) {
                startDateStr = customDate;
            }

            if (startDateStr) {
                dateParams = `&start_date=${startDateStr}`;
            }

            const res = await api.get(`/candidates?job_title=${encodeURIComponent(job)}${dateParams}`);
            // Ensure unique candidates by Name
            const unique = [];
            const seen = new Set();
            res.data.forEach(c => {
                const n = c['Candidate Name'] || c['Name'];
                if (n && !seen.has(n)) {
                    seen.add(n);
                    unique.push(c);
                }
            });
            // Reverse to show newest
            setCandidates(unique.reverse());
        } catch (err) {
            console.error("Error fetching analysis:", err);
        } finally {
            setLoading(false);
        }
    };

    const handleSync = async () => {
        if (analyzing) return;
        if (!selectedJob) return alert("Please select a job role first.");

        setAnalyzing(true);
        try {
            // Pass time_period to trigger_sync
            let url = `/trigger-candidate-sync?job_filter=${encodeURIComponent(selectedJob)}`;

            // Add Time Period Params
            if (timePeriod !== "ALL") {
                url += `&time_period=${timePeriod}`;
                if (timePeriod === "CUSTOM" && customDate) {
                    url += `&start_date=${customDate}&end_date=${customDate}`;
                } else if (timePeriod === "CUSTOM_RANGE" && customDate && customEndDate) {
                    url += `&start_date=${customDate}&end_date=${customEndDate}`;
                }
            }

            const res = await api.post(url);
            alert(`Analysis Started!\n${res.data.message}`);
            fetchCandidates(selectedJob);
        } catch (err) {
            alert("Analysis Trigger Failed: " + err.message);
        } finally {
            setAnalyzing(false);
        }
    };

    return (
        <div className="p-6 max-w-7xl mx-auto space-y-8 animate-fade-in pb-20">
            {/* Header Section */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-gray-100 pb-6">
                <div>
                    <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
                        Analysis & Results
                    </h1>
                    <p className="text-gray-500 mt-2">
                        Run AI analysis on imported candidates and view ranking results.
                    </p>
                </div>

                <div className="flex gap-4 items-center">

                    {/* Time Period Selector */}
                    <div className="flex items-center gap-2 bg-white px-3 py-2 rounded-xl border border-gray-200 shadow-sm">
                        <span className="text-sm font-medium text-gray-600"><Clock className="w-4 h-4 inline mr-1" />Period:</span>
                        <select
                            value={timePeriod}
                            onChange={(e) => setTimePeriod(e.target.value)}
                            className="bg-transparent border-none text-sm font-semibold text-gray-700 focus:ring-0 cursor-pointer"
                        >
                            <option value="ALL">All Time</option>
                            <option value="LAST_24_HOURS">Today</option>
                            <option value="LAST_7_DAYS">Last 7 Days</option>
                            <option value="LAST_30_DAYS">Last 30 Days</option>
                            <option value="CUSTOM">Specific Date</option>
                            <option value="CUSTOM_RANGE">Date Range</option>
                        </select>
                        {timePeriod === "CUSTOM" && (
                            <input
                                type="date"
                                value={customDate}
                                onChange={(e) => setCustomDate(e.target.value)}
                                className="ml-2 border border-gray-300 rounded-lg px-2 py-1 text-sm bg-gray-50"
                            />
                        )}
                        {timePeriod === "CUSTOM_RANGE" && (
                            <div className="flex items-center gap-2 ml-2">
                                <input
                                    type="date"
                                    value={customDate}
                                    onChange={(e) => setCustomDate(e.target.value)}
                                    className="border border-gray-300 rounded-lg px-2 py-1 text-sm bg-gray-50"
                                    placeholder="Start"
                                />
                                <span className="text-gray-500 text-sm">to</span>
                                <input
                                    type="date"
                                    value={customEndDate}
                                    onChange={(e) => setCustomEndDate(e.target.value)}
                                    className="border border-gray-300 rounded-lg px-2 py-1 text-sm bg-gray-50"
                                    placeholder="End"
                                />
                            </div>
                        )}
                    </div>

                    <button
                        onClick={handleSync}
                        disabled={analyzing}
                        className={`
                            relative overflow-hidden group px-6 py-2.5 rounded-xl font-bold shadow-lg transition-all
                            ${analyzing
                                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                                : 'bg-gradient-to-r from-purple-600 to-blue-600 text-white hover:shadow-purple-200 hover:scale-105 active:scale-95'
                            }
                        `}
                    >
                        <div className="flex items-center gap-2 relative z-10">
                            {analyzing ? (
                                <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    <span>Analyzing...</span>
                                </>
                            ) : (
                                <>
                                    <Sparkles className="w-5 h-5 group-hover:animate-pulse" />
                                    <span>Run Analysis</span>
                                </>
                            )}
                        </div>
                    </button>
                </div>
            </div>

            {/* Job Selection */}
            <div className="bg-white rounded-3xl shadow-xl shadow-gray-200/50 border border-gray-100 p-8">
                <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <Briefcase size={20} className="text-purple-600" />
                    Select Job Role
                </h2>
                <select
                    className="w-full px-4 py-3 bg-gray-50 border border-gray-200 text-gray-900 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent cursor-pointer font-semibold shadow-sm transition-all hover:bg-white"
                    value={selectedJob}
                    onChange={(e) => setSelectedJob(e.target.value)}
                >
                    <option value="">-- Choose a job role --</option>
                    {availableJobs.map((j, i) => <option key={i} value={j}>{j}</option>)}
                </select>
            </div>

            {/* Analysis Card */}
            <div className="bg-white rounded-3xl shadow-xl shadow-gray-200/50 border border-gray-100 p-8">
                <div className="flex items-center gap-3 mb-4">
                    <div className="p-3 bg-purple-100 rounded-xl">
                        <Sparkles size={24} className="text-purple-600" />
                    </div>
                    <h2 className="text-xl font-bold text-gray-900">AI Evaluation</h2>
                </div>
                <p className="text-gray-600 mb-6">
                    Analyze all imported candidates for the selected job role. The AI will match their skills and experience against the job requirements and provide scores and recommendations.
                </p>
                <button
                    onClick={handleSync}
                    disabled={!selectedJob || analyzing}
                    className={clsx(
                        "w-full flex items-center justify-center gap-2 px-6 py-4 rounded-xl font-bold text-lg transition-all shadow-md",
                        !selectedJob || analyzing
                            ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                            : "bg-gradient-to-r from-purple-600 to-indigo-600 text-white hover:shadow-purple-300 hover:scale-105"
                    )}
                >
                    {analyzing ? (
                        <>
                            <RefreshCw size={20} className="animate-spin" />
                            Analyzing Candidates...
                        </>
                    ) : (
                        <>
                            <Sparkles size={20} />
                            Run AI Evaluation
                        </>
                    )}
                </button>
            </div>

            {/* Info Box */}
            {selectedJob && (
                <div className="bg-gradient-to-r from-purple-50 to-indigo-50 rounded-2xl p-6 border border-purple-100">
                    <div className="flex items-start gap-3">
                        <CheckCircle size={20} className="text-purple-600 mt-0.5" />
                        <div>
                            <h3 className="font-bold text-gray-900 mb-1">Selected: {selectedJob}</h3>
                            <p className="text-sm text-gray-600">
                                Click "Run AI Evaluation" to analyze all imported candidates for this role. Results will appear in the "View Results" tab.
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {/* Analysis Results Table */}
            {selectedJob && (
                <div className="bg-white rounded-3xl shadow-xl shadow-gray-200/50 border border-gray-100 overflow-hidden min-h-[400px] flex flex-col relative">
                    <div className="p-6 border-b border-gray-100">
                        <div className="flex items-center justify-between">
                            <div>
                                <h2 className="text-xl font-bold text-gray-900">Analysis Results</h2>
                                <p className="text-sm text-gray-500 mt-1">Candidates evaluated with AI matching for {selectedJob}</p>
                            </div>

                            {/* Verdict Filter */}
                            <div className="relative">
                                <div className="absolute left-3 top-3 text-gray-400 pointer-events-none">
                                    <Filter size={16} />
                                </div>
                                <select
                                    className="pl-10 pr-8 py-2.5 bg-gray-50 border border-gray-200 text-gray-900 text-sm rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent cursor-pointer font-semibold appearance-none"
                                    value={verdictFilter}
                                    onChange={(e) => setVerdictFilter(e.target.value)}
                                >
                                    <option value="ALL">All Candidates</option>
                                    <option value="PASS">✓ Recommended</option>
                                    <option value="FAIL">✗ Rejected</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm">
                            <thead className="bg-gray-50/80 border-b border-gray-100">
                                <tr>
                                    <th className="px-8 py-5 font-bold text-gray-400 uppercase tracking-wider text-xs">Candidate</th>
                                    <th className="px-8 py-5 font-bold text-gray-400 uppercase tracking-wider text-xs">Role</th>
                                    <th className="px-8 py-5 font-bold text-gray-400 uppercase tracking-wider text-xs">Match Score</th>
                                    <th className="px-8 py-5 font-bold text-gray-400 uppercase tracking-wider text-xs">Verdict</th>
                                    <th className="px-8 py-5 font-bold text-gray-400 uppercase tracking-wider text-xs text-right">Action</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-50">
                                {loading ? (
                                    <tr>
                                        <td colSpan="5" className="p-20 text-center">
                                            <div className="flex flex-col items-center gap-4 animate-pulse">
                                                <RefreshCw size={24} className="animate-spin text-purple-400" />
                                                <p className="text-gray-400 font-medium">Loading Results...</p>
                                            </div>
                                        </td>
                                    </tr>
                                ) : candidates.length === 0 ? (
                                    <tr>
                                        <td colSpan="5" className="p-20 text-center">
                                            <div className="flex flex-col items-center gap-4 text-gray-300">
                                                <Users size={40} className="opacity-20" />
                                                <p className="text-lg font-medium text-gray-500">No analyzed candidates yet</p>
                                                <p className="text-sm text-gray-400">Click "Run AI Evaluation" above to analyze imported candidates</p>
                                            </div>
                                        </td>
                                    </tr>
                                ) : (() => {
                                    // Filter by verdict
                                    const filteredCandidates = verdictFilter === "ALL"
                                        ? candidates
                                        : candidates.filter(c => c['Verdict'] === verdictFilter);

                                    // Limit to 20
                                    const displayCandidates = filteredCandidates.slice(0, 20);

                                    if (displayCandidates.length === 0) {
                                        return (
                                            <tr>
                                                <td colSpan="5" className="p-20 text-center">
                                                    <div className="flex flex-col items-center gap-4 text-gray-300">
                                                        <Users size={40} className="opacity-20" />
                                                        <p className="text-lg font-medium text-gray-500">
                                                            No {verdictFilter === "PASS" ? "recommended" : verdictFilter === "FAIL" ? "rejected" : ""} candidates
                                                        </p>
                                                        <p className="text-sm text-gray-400">Try selecting a different filter</p>
                                                    </div>
                                                </td>
                                            </tr>
                                        );
                                    }

                                    return (
                                        <>
                                            {filteredCandidates.length > 0 && (
                                                <tr>
                                                    <td colSpan="5" className="px-8 py-3 bg-gray-50/50">
                                                        <p className="text-sm text-gray-600">
                                                            Showing {displayCandidates.length} of {filteredCandidates.length} candidates
                                                            {filteredCandidates.length > 20 && <span className="text-purple-600 font-semibold ml-1">(top 20)</span>}
                                                        </p>
                                                    </td>
                                                </tr>
                                            )}
                                            {displayCandidates.map((c, i) => (
                                                <tr key={i} className="hover:bg-purple-50/40 transition-all duration-200">
                                                    <td className="px-8 py-5">
                                                        <div className="flex items-center gap-4">
                                                            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-100 to-blue-100 flex items-center justify-center text-purple-600 font-bold">
                                                                {(c['Candidate Name'] || c['Name'] || '?')[0].toUpperCase()}
                                                            </div>
                                                            <div>
                                                                <p className="font-semibold text-gray-900">{c['Candidate Name'] || c['Name']}</p>
                                                                <p className="text-xs text-gray-400">{c['Email'] || c['Contact'] || 'No contact'}</p>
                                                            </div>
                                                        </div>
                                                    </td>
                                                    <td className="px-8 py-5">
                                                        <span className="bg-gray-100 text-gray-700 px-3 py-1 rounded-lg text-xs font-semibold">
                                                            {c['Job Applied For'] || selectedJob}
                                                        </span>
                                                    </td>
                                                    <td className="px-8 py-5">
                                                        {c['Match Score'] ? (
                                                            <div className="flex items-center gap-3">
                                                                <div className="w-32 bg-gray-100 rounded-full h-3 overflow-hidden">
                                                                    <div
                                                                        className={clsx("h-full rounded-full transition-all duration-1000",
                                                                            c['Match Score'] >= 80 ? "bg-gradient-to-r from-emerald-400 to-emerald-600" :
                                                                                c['Match Score'] >= 50 ? "bg-gradient-to-r from-amber-300 to-amber-500" :
                                                                                    "bg-gradient-to-r from-rose-400 to-rose-600"
                                                                        )}
                                                                        style={{ width: `${c['Match Score']}%` }}
                                                                    />
                                                                </div>
                                                                <span className={clsx("font-bold text-sm",
                                                                    c['Match Score'] >= 80 ? "text-emerald-600" :
                                                                        c['Match Score'] >= 50 ? "text-amber-600" : "text-rose-600"
                                                                )}>{c['Match Score']}%</span>
                                                            </div>
                                                        ) : (
                                                            <span className="text-gray-300">-</span>
                                                        )}
                                                    </td>
                                                    <td className="px-8 py-5">
                                                        {c['Verdict'] === 'PASS' ? (
                                                            <span className="flex items-center gap-1.5 text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-full text-xs font-bold border border-emerald-100">
                                                                <CheckCircle size={14} /> RECOMMENDED
                                                            </span>
                                                        ) : c['Verdict'] === 'FAIL' ? (
                                                            <span className="flex items-center gap-1.5 text-rose-700 bg-rose-50 px-3 py-1.5 rounded-full text-xs font-bold border border-rose-100">
                                                                <XCircle size={14} /> REJECTED
                                                            </span>
                                                        ) : (
                                                            <span className="flex items-center gap-1.5 text-slate-500 bg-slate-50 px-3 py-1.5 rounded-full text-xs font-bold border border-slate-100">
                                                                <Clock size={14} /> PENDING
                                                            </span>
                                                        )}
                                                    </td>
                                                    <td className="px-8 py-5 text-right">
                                                        <button className="text-purple-600 hover:text-purple-700 font-semibold text-sm hover:underline inline-flex items-center gap-1">
                                                            View Details
                                                            <ArrowRight size={14} />
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))}
                                        </>
                                    );
                                })()}
                            </tbody >
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AnalysisPage;
