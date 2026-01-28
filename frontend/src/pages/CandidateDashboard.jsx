import React, { useState, useEffect } from 'react';
import api from '../lib/api';
import {
    RefreshCw, CheckCircle, XCircle, Clock,
    Briefcase, Users, Filter, UploadCloud, ArrowRight,
    Loader2, Download // Added Loader2 and Download for new UI
} from 'lucide-react';
import clsx from 'clsx';

const CandidateDashboard = () => {
    const [selectedJob, setSelectedJob] = useState("");
    const [candidates, setCandidates] = useState([]);
    const [loading, setLoading] = useState(false);
    const [importing, setImporting] = useState(false); // Replaced operationLoading with importing
    const [error, setError] = useState(""); // New state for errors
    const [stats, setStats] = useState(null); // New state for import stats
    const [availableJobs, setAvailableJobs] = useState([]);

    // NEW: Date Filtering State
    const [timePeriod, setTimePeriod] = useState("ALL"); // ALL, LAST_7_DAYS, LAST_30_DAYS, CUSTOM_SINGLE, CUSTOM_RANGE
    const [customStartDate, setCustomStartDate] = useState("");
    const [customEndDate, setCustomEndDate] = useState("");

    useEffect(() => {
        fetchJobs();
    }, []);

    // Re-fetch when Job Selection Changes
    useEffect(() => {
        fetchCandidates(selectedJob); // Pass selectedJob directly
        const interval = setInterval(() => fetchCandidates(selectedJob), 30000); // Pass selectedJob
        return () => clearInterval(interval);
    }, [selectedJob, timePeriod, customStartDate, customEndDate]); // Added customStartDate and customEndDate to dependencies

    const fetchJobs = async () => {
        try {
            const res = await api.get('/jobs');
            setAvailableJobs(res.data);
        } catch (err) {
            console.error("Failed to fetch jobs:", err);
        }
    };

    const fetchCandidates = async (job) => { // Takes job as argument
        // Fetch RAW imported candidates from source sheet (not analyzed)
        if (!job) { // Use job argument
            setCandidates([]);
            return;
        }

        setLoading(true);
        setError(""); // Clear previous errors
        try {
            // Calculate Date Params based on timePeriod
            let dateParams = "";
            const today = new Date();
            let startDateStr = "";
            let endDateStr = "";

            if (timePeriod === "LAST_7_DAYS") {
                const d = new Date();
                d.setDate(today.getDate() - 7);
                startDateStr = d.toISOString().split('T')[0];
                endDateStr = today.toISOString().split('T')[0];
            } else if (timePeriod === "LAST_30_DAYS") {
                const d = new Date();
                d.setDate(today.getDate() - 30);
                startDateStr = d.toISOString().split('T')[0];
                endDateStr = today.toISOString().split('T')[0];
            } else if (timePeriod === "CUSTOM_SINGLE" && customStartDate) {
                startDateStr = customStartDate;
                endDateStr = customStartDate; // Same day
            } else if (timePeriod === "CUSTOM_RANGE" && customStartDate && customEndDate) {
                startDateStr = customStartDate;
                endDateStr = customEndDate;
            }

            if (startDateStr) {
                dateParams = `&start_date=${startDateStr}`;
                if (endDateStr) {
                    dateParams += `&end_date=${endDateStr}`;
                }
            }

            // Fetch from the source sheet for this job
            const res = await api.get(`/candidates/imported?job_title=${encodeURIComponent(job)}${dateParams}`); // Updated API call
            const data = res.data;

            // Filter out empty rows if any
            const validData = data.filter(c => c.Name || c.Source);

            // Reverse to show newest first
            setCandidates(validData.reverse());
        } catch (err) {
            console.error("Failed to fetch imported candidates:", err);
            setError("Failed to load candidates. Please try again."); // Set error state
        } finally {
            setLoading(false);
        }
    };

    const handleImport = async () => {
        if (importing) return; // Use importing state
        if (!selectedJob) return alert("Please SELECT A JOB first to import candidates.");

        setImporting(true); // matches 'importing' state, not operationLoading which was removed/renamed
        try {
            // Pass Job Title Filter AND Time Period
            const params = new URLSearchParams();
            if (selectedJob) params.append("job_title_filter", selectedJob);

            // Add Time Period Params
            if (timePeriod !== "ALL") {
                params.append("time_period", timePeriod);
                if (timePeriod === "CUSTOM_SINGLE" && customStartDate) {
                    params.append("start_date", customStartDate);
                    params.append("end_date", customStartDate); // Same day
                } else if (timePeriod === "CUSTOM_RANGE" && customStartDate && customEndDate) {
                    params.append("start_date", customStartDate);
                    params.append("end_date", customEndDate);
                }
            }

            console.log("Importing with params:", params.toString()); // Debug

            const response = await api.post(`/import-from-drive?${params.toString()}`);

            const result = response.data;
            const stats = result.stats || {};
            const imported = stats.imported || 0;
            const scanned = stats.scanned_folders_count || 0;
            const skippedFiles = stats.skipped_existing_files || 0;

            if (imported > 0) {
                alert(`✨ Success! Imported ${imported} new resumes from ${scanned} folder(s).` + (skippedFiles ? `\n(Skipped ${skippedFiles} already imported files)` : ""));
            } else if (scanned === 0) {
                alert(`⚠️ No relevant folders found for "${selectedJob}".\nPlease check your Google Drive folder names.`);
            } else if (skippedFiles > 0) {
                alert(`✅ Up to Date!\nAll ${skippedFiles} resumes in "${selectedJob}" folders are already imported.`);
            } else {
                alert(`✅ No new resumes found.\nScanned ${scanned} folder(s) for "${selectedJob}".`);
            }

            setStats(result);
            if (selectedJob) fetchCandidates(selectedJob); // Refresh list

        } catch (err) {
            console.error(err);
            alert("Import Failed: " + (err.response?.data?.detail || err.message || "Unknown error"));
            setError("Import process encountered an error.");
        } finally {
            setImporting(false);
        }
    };

    const getStatusBadge = (verdict) => {
        if (verdict === 'PASS') return <span className="flex items-center gap-1.5 text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-full text-xs font-bold border border-emerald-100 shadow-sm"><CheckCircle size={14} className="text-emerald-500" /> RECOMMENDED</span>;
        if (verdict === 'FAIL') return <span className="flex items-center gap-1.5 text-rose-700 bg-rose-50 px-3 py-1.5 rounded-full text-xs font-bold border border-rose-100 shadow-sm"><XCircle size={14} className="text-rose-500" /> REJECTED</span>;
        return <span className="flex items-center gap-1.5 text-slate-500 bg-slate-50 px-3 py-1.5 rounded-full text-xs font-bold border border-slate-100 shadow-sm"><Clock size={14} /> PENDING</span>;
    };

    // Helper to extract email from Contact field
    const getEmail = (candidate) => {
        if (candidate['Email']) return candidate['Email'];
        const contact = candidate['Contact'] || candidate['Phone'] || '';
        const emailMatch = contact.match(/[\w\.-]+@[\w\.-]+\.\w+/);
        return emailMatch ? emailMatch[0] : '';
    };

    // Helper to extract phone numbers from Contact field (excluding email)
    const getPhone = (candidate) => {
        if (candidate['Phone'] && !candidate['Phone'].includes('@')) return candidate['Phone'];
        const contact = candidate['Contact'] || candidate['Phone'] || '';
        // Remove email and split by comma
        const parts = contact.split(',').map(p => p.trim()).filter(p => !p.includes('@'));
        return parts.join(', ') || 'N/A';
    };

    return (
        <div className="max-w-7xl mx-auto space-y-8 p-6">

            {/* Header & Controls */}
            <div className="bg-white/80 backdrop-blur-xl rounded-3xl shadow-lg border border-white/20 p-8 flex flex-col items-start gap-8 relative overflow-hidden">
                {/* Decorative Background Blob */}
                <div className="absolute top-0 right-0 w-64 h-64 bg-purple-100 rounded-full blur-3xl opacity-50 -mr-16 -mt-16 pointer-events-none" />

                <div className="z-10 w-full flex flex-col md:flex-row justify-between items-end md:items-center gap-6">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
                            <span className="p-2 bg-gradient-to-br from-purple-600 to-blue-600 rounded-xl text-white shadow-lg shadow-purple-500/20">
                                <Users size={24} />
                            </span>
                            Import & View Results
                        </h1>
                        <p className="text-gray-500 mt-2 font-medium">Import resumes from Google Drive and view analyzed candidates.</p>
                    </div>

                    <div className="flex flex-col sm:flex-row items-stretch gap-4 w-full md:w-auto">
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
                                <option value="CUSTOM_SINGLE">Specific Date</option>
                                <option value="CUSTOM_RANGE">Date Range</option>
                            </select>
                            {timePeriod === "CUSTOM_SINGLE" && (
                                <input
                                    type="date"
                                    value={customStartDate}
                                    onChange={(e) => setCustomStartDate(e.target.value)}
                                    className="ml-2 border border-gray-300 rounded-lg px-2 py-1 text-sm bg-gray-50"
                                />
                            )}
                            {timePeriod === "CUSTOM_RANGE" && (
                                <div className="flex items-center gap-2 ml-2">
                                    <input
                                        type="date"
                                        value={customStartDate}
                                        onChange={(e) => setCustomStartDate(e.target.value)}
                                        className="border border-gray-300 rounded-lg px-2 py-1 text-sm bg-gray-50"
                                    />
                                    <span className="text-gray-500 text-sm">to</span>
                                    <input
                                        type="date"
                                        value={customEndDate}
                                        onChange={(e) => setCustomEndDate(e.target.value)}
                                        className="border border-gray-300 rounded-lg px-2 py-1 text-sm bg-gray-50"
                                    />
                                </div>
                            )}
                        </div>

                        {/* Job Select */}
                        <div className="relative flex-grow md:w-72 group">
                            <div className="absolute left-4 top-3.5 text-gray-400 group-focus-within:text-purple-600 transition-colors pointer-events-none">
                                <Briefcase size={18} />
                            </div>
                            <select
                                className="w-full pl-12 pr-10 py-3.5 bg-gray-50 border border-gray-200 text-gray-900 text-sm rounded-2xl focus:ring-4 focus:ring-purple-100 focus:border-purple-500 cursor-pointer font-medium appearance-none transition-all hover:bg-white hover:shadow-md"
                                value={selectedJob}
                                onChange={(e) => setSelectedJob(e.target.value)}
                            >
                                <option value="">Select Target Job Role...</option>
                                {availableJobs.map((j, i) => <option key={i} value={j}>{j}</option>)}
                            </select>
                            <div className="absolute right-4 top-4 text-gray-400 pointer-events-none">
                                <Filter size={16} />
                            </div>
                        </div>

                        {/* Import Button */}
                        {selectedJob && (
                            <button
                                onClick={handleImport}
                                disabled={importing}
                                className={clsx(
                                    "flex items-center gap-2 px-6 py-3.5 rounded-2xl font-bold text-sm shadow-md transition-all whitespace-nowrap",
                                    importing
                                        ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                                        : "bg-gradient-to-r from-blue-600 to-cyan-600 text-white hover:shadow-blue-300 hover:scale-105"
                                )}
                            >
                                {importing ? (
                                    <>
                                        <RefreshCw size={18} className="animate-spin" />
                                        Importing...
                                    </>
                                ) : (
                                    <>
                                        <UploadCloud size={18} />
                                        Import Resumes
                                    </>
                                )}
                            </button>
                        )}
                    </div>
                </div>
            </div>

            {/* Candidate Table */}
            <div className="bg-white rounded-3xl shadow-xl shadow-gray-200/50 border border-gray-100 overflow-hidden min-h-[500px] flex flex-col relative">
                {/* Table Header */}
                {candidates.length > 0 && (
                    <div className="px-8 py-4 border-b border-gray-100 bg-gray-50/50">
                        <p className="text-sm text-gray-600">
                            Showing {Math.min(20, candidates.length)} of {candidates.length} imported candidates
                            {candidates.length > 20 && <span className="text-purple-600 font-semibold ml-1">(displaying top 20)</span>}
                        </p>
                    </div>
                )}
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                        <thead className="bg-gray-50/80 border-b border-gray-100 backdrop-blur-sm">
                            <tr>
                                <th className="px-8 py-5 font-bold text-gray-400 uppercase tracking-wider text-xs">Candidate</th>
                                <th className="px-8 py-5 font-bold text-gray-400 uppercase tracking-wider text-xs">Role Applied</th>
                                <th className="px-8 py-5 font-bold text-gray-400 uppercase tracking-wider text-xs">Phone</th>
                                <th className="px-8 py-5 font-bold text-gray-400 uppercase tracking-wider text-xs">Status</th>
                                <th className="px-8 py-5 font-bold text-gray-400 uppercase tracking-wider text-xs text-right">Resume</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-50">
                            {loading ? (
                                <tr>
                                    <td colSpan="5" className="p-20 text-center">
                                        <div className="flex flex-col items-center gap-4 text-gray-400 animate-pulse">
                                            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center">
                                                <RefreshCw size={24} className="animate-spin text-purple-400" />
                                            </div>
                                            <p className="font-medium">Loading Pipeline Data...</p>
                                        </div>
                                    </td>
                                </tr>
                            ) : candidates.length === 0 ? (
                                <tr>
                                    <td colSpan="5" className="p-20 text-center">
                                        <div className="flex flex-col items-center gap-4 text-gray-300">
                                            <div className="w-24 h-24 bg-gray-50 rounded-full flex items-center justify-center mb-2">
                                                <Users size={40} className="opacity-20" />
                                            </div>
                                            <p className="text-lg font-medium text-gray-500">No candidates found {selectedJob ? `for '${selectedJob}'` : ''}.</p>
                                            {selectedJob && (
                                                <button onClick={handleImport} className="text-sm font-semibold text-purple-600 hover:text-purple-700 hover:underline mt-2">
                                                    Start by Importing Candidates
                                                </button>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ) : (
                                candidates.slice(0, 20).map((c, i) => (
                                    <tr key={i} className="hover:bg-purple-50/40 transition-all duration-200 group cursor-default">
                                        {/* Candidate Name & Email */}
                                        <td className="px-8 py-5">
                                            <div className="flex items-center gap-4">
                                                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-100 to-blue-100 flex items-center justify-center text-purple-600 font-bold shadow-inner">
                                                    {(c['Candidate Name'] || c['Name'] || '?')[0].toUpperCase()}
                                                </div>
                                                <div>
                                                    <p className="font-semibold text-gray-900">{c['Candidate Name'] || c['Name'] || 'N/A'}</p>
                                                    <p className="text-xs text-gray-500">{getEmail(c) || 'No email'}</p>
                                                </div>
                                            </div>
                                        </td>

                                        {/* Role */}
                                        <td className="px-8 py-5">
                                            <span className="bg-gray-100 text-gray-700 px-3 py-1 rounded-lg text-xs font-semibold">
                                                {selectedJob || 'N/A'}
                                            </span>
                                        </td>

                                        {/* Phone */}
                                        <td className="px-8 py-5">
                                            <span className="text-gray-600 font-mono text-sm">
                                                {getPhone(c)}
                                            </span>
                                        </td>

                                        {/* Status */}
                                        <td className="px-8 py-5">
                                            <span className="inline-flex items-center gap-1.5 text-blue-700 bg-blue-50 px-3 py-1.5 rounded-full text-xs font-bold border border-blue-100 shadow-sm">
                                                <Clock size={14} />
                                                Imported
                                            </span>
                                        </td>

                                        {/* Resume Link */}
                                        <td className="px-8 py-5 text-right">
                                            {c['Resume Link'] ? (
                                                <a
                                                    href={c['Resume Link']}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="text-purple-600 hover:text-purple-700 font-semibold text-sm hover:underline inline-flex items-center gap-1"
                                                >
                                                    View Resume
                                                    <ArrowRight size={14} />
                                                </a>
                                            ) : (
                                                <span className="text-gray-400 text-sm">No link</span>
                                            )}
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default CandidateDashboard;

