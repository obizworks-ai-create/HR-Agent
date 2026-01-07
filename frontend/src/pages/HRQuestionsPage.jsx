import React, { useState, useEffect } from 'react';
import api from '../lib/api';
import { MessageSquare, User, Briefcase, ChevronRight, HelpCircle, RefreshCw, Clock } from 'lucide-react';
import clsx from 'clsx';

const HRQuestionsPage = () => {
    const [candidates, setCandidates] = useState([]);
    const [availableJobs, setAvailableJobs] = useState([]);
    const [selectedJob, setSelectedJob] = useState("");
    const [selectedCandidate, setSelectedCandidate] = useState(null);
    const [questions, setQuestions] = useState(null);
    const [loading, setLoading] = useState(false);
    const [generating, setGenerating] = useState(false);

    // NEW: Date Filtering State
    const [timePeriod, setTimePeriod] = useState("ALL"); // ALL, LAST_7_DAYS, LAST_30_DAYS, CUSTOM
    const [customDate, setCustomDate] = useState("");

    const fetchJobs = async () => {
        try {
            const res = await api.get('/jobs');
            setAvailableJobs(res.data);
            // Optional: Auto-select first job if available to improve UX
            // if (res.data.length > 0) setSelectedJob(res.data[0]);
        } catch (err) {
            console.error("Failed to fetch jobs:", err);
        }
    };

    const fetchCandidates = async () => {
        if (!selectedJob) {
            setCandidates([]);
            return;
        }

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

            const res = await api.get(`/candidates?job_title=${encodeURIComponent(selectedJob)}${dateParams}`);
            // Filter 'PASS' candidates
            const qualified = res.data.filter(c => c.Verdict === 'PASS');
            setCandidates(qualified.reverse());
        } catch (err) {
            console.error("Failed to fetch candidates:", err);
            setCandidates([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchJobs();
    }, []);

    useEffect(() => {
        if (selectedJob) {
            fetchCandidates();
        } else {
            setCandidates([]);
        }
    }, [selectedJob, timePeriod, customDate]);

    const handleSelect = async (candidateName) => {
        setSelectedCandidate(candidateName);
        setLoading(true);
        try {
            const res = await api.get(`/questions/${encodeURIComponent(candidateName)}`);
            setQuestions(res.data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    // Filter displayed candidates by Job 
    // (Note: Backend now filters by job, so 'candidates' array is already specific to selectedJob. 
    //  We can remove the filtering logic or keep it as specific safeguard, but simpler is better.)
    const displayedCandidates = candidates;

    return (
        <div className="max-w-7xl mx-auto p-6 space-y-6 h-[calc(100vh-2rem)] flex flex-col">

            {/* Header */}
            <div className="bg-white/80 backdrop-blur-xl rounded-3xl shadow-lg border border-white/20 p-8 flex flex-col md:flex-row justify-between items-center gap-6 relative overflow-hidden">
                {/* Decorative Background Blob */}
                <div className="absolute top-0 left-0 w-64 h-64 bg-purple-100 rounded-full blur-3xl opacity-50 -ml-16 -mt-16 pointer-events-none" />

                <div className="z-10">
                    <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
                        <span className="p-2 bg-gradient-to-br from-purple-600 to-blue-600 rounded-xl text-white shadow-lg shadow-purple-500/20">
                            <HelpCircle size={24} className="text-white" />
                        </span>
                        Interview Guides
                    </h1>
                    <p className="text-gray-500 font-medium ml-14 mt-1">AI-generated questions tailored for qualified candidates.</p>
                </div>

                <div className="flex flex-col md:flex-row items-center gap-4 z-10 w-full md:w-auto">
                    {/* Time Period Selector */}
                    <div className="flex items-center gap-2 bg-white/50 px-3 py-2 rounded-xl border border-purple-200/50 shadow-sm backdrop-blur-sm">
                        <span className="text-sm font-medium text-purple-800"><Clock className="w-4 h-4 inline mr-1" />Period:</span>
                        <select
                            value={timePeriod}
                            onChange={(e) => setTimePeriod(e.target.value)}
                            className="bg-transparent border-none text-sm font-bold text-purple-900 focus:ring-0 cursor-pointer"
                        >
                            <option value="ALL">All Time</option>
                            <option value="LAST_7_DAYS">Last 7 Days</option>
                            <option value="LAST_30_DAYS">Last 30 Days</option>
                            <option value="CUSTOM">Custom Date</option>
                        </select>
                        {timePeriod === "CUSTOM" && (
                            <input
                                type="date"
                                value={customDate}
                                onChange={(e) => setCustomDate(e.target.value)}
                                className="ml-2 border border-purple-200 rounded-lg px-2 py-1 text-sm bg-white/80"
                            />
                        )}
                    </div>

                    <div className="relative w-full md:w-72">
                        <div className="absolute left-4 top-1/2 -translate-y-1/2 text-purple-500 pointer-events-none">
                            <Briefcase size={18} />
                        </div>
                        <select
                            className="w-full pl-12 pr-4 py-3 bg-white/50 border border-gray-200 text-gray-900 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent cursor-pointer font-semibold shadow-sm transition-all hover:bg-white"
                            value={selectedJob}
                            onChange={(e) => setSelectedJob(e.target.value)}
                        >
                            <option value="">Select a Job Role...</option>
                            {availableJobs.map((j, i) => <option key={i} value={j}>{j}</option>)}
                        </select>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 min-h-0">
                {/* Sidebar List */}
                <div className="bg-white rounded-3xl shadow-xl shadow-gray-200/50 border border-gray-100 overflow-hidden flex flex-col">
                    <div className="p-5 border-b border-gray-100 bg-gray-50/30">
                        <h3 className="font-bold text-gray-400 text-xs uppercase tracking-wider flex items-center gap-2">
                            <User size={14} /> Qualified Candidates
                        </h3>
                    </div>
                    <div className="overflow-y-auto flex-1 p-4 space-y-3 custom-scrollbar">
                        {loading ? (
                            <div className="text-center p-8 text-gray-400 text-sm animate-pulse"><RefreshCw className="animate-spin mx-auto mb-2" /> Loading candidates...</div>
                        ) : displayedCandidates.length === 0 ? (
                            <div className="text-center p-8 text-gray-400 text-sm flex flex-col items-center gap-3">
                                <div className="p-3 bg-gray-100 rounded-full text-gray-300">
                                    <User size={24} />
                                </div>
                                <p>No qualified candidates found {selectedJob ? 'for this role' : ''}.</p>
                            </div>
                        ) : (
                            displayedCandidates.map((c, i) => (
                                <button
                                    key={i}
                                    onClick={() => handleSelect(c['Candidate Name'])}
                                    className={clsx(
                                        "w-full text-left p-4 rounded-2xl text-sm transition-all duration-300 group relative border",
                                        selectedCandidate === c['Candidate Name']
                                            ? "bg-gradient-to-r from-purple-500 to-indigo-600 text-white border-transparent shadow-lg shadow-purple-200 scale-[1.02]"
                                            : "bg-white hover:bg-purple-50 text-gray-700 border-gray-100 hover:border-purple-200 shadow-sm hover:shadow-md"
                                    )}
                                >
                                    <div className="font-bold flex items-center justify-between">
                                        <span className="truncate">{c['Candidate Name']}</span>
                                        {selectedCandidate === c['Candidate Name'] && <ChevronRight size={16} className="text-white ml-2" />}
                                    </div>
                                    <div className={clsx(
                                        "text-xs mt-1.5 flex items-center gap-1.5",
                                        selectedCandidate === c['Candidate Name'] ? "text-purple-100" : "text-gray-400 group-hover:text-purple-400"
                                    )}>
                                        <Briefcase size={12} />
                                        <span className="truncate max-w-[180px]">{c['Job Applied For']}</span>
                                    </div>
                                </button>
                            ))
                        )}
                    </div>
                </div>

                {/* Main Panel */}
                <div className="lg:col-span-2 bg-white rounded-3xl shadow-xl shadow-gray-200/50 border border-gray-100 flex flex-col overflow-hidden relative">
                    {!selectedCandidate ? (
                        <div className="flex-1 flex flex-col items-center justify-center text-gray-400 p-12 space-y-6">
                            <div className="relative">
                                <div className="w-24 h-24 bg-purple-50 rounded-full flex items-center justify-center animate-pulse-slow">
                                    <MessageSquare size={40} className="text-purple-200" />
                                </div>
                                <div className="absolute top-0 right-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center animate-bounce">
                                    <HelpCircle size={16} className="text-blue-400" />
                                </div>
                            </div>
                            <div className="text-center max-w-sm">
                                <p className="text-xl font-bold text-gray-800">Ready to Interview?</p>
                                <p className="text-gray-500 mt-2">Select a qualified candidate from the list to reveal their personalized AI interview guide.</p>
                            </div>
                        </div>
                    ) : loading ? (
                        <div className="flex-1 flex flex-col items-center justify-center text-purple-600 gap-6">
                            <div className="relative">
                                <RefreshCw size={48} className="animate-spin text-purple-600" />
                                <div className="absolute inset-0 bg-purple-100 rounded-full blur-xl opacity-50 animate-pulse"></div>
                            </div>
                            <p className="font-bold text-lg animate-pulse tracking-wide">Consulting AI Hiring Manager...</p>
                        </div>
                    ) : questions && questions.questions ? (
                        <div className="p-8 overflow-y-auto h-full space-y-8 animate-in fade-in slide-in-from-right-4 duration-500 custom-scrollbar">
                            <div className="flex items-start justify-between border-b border-gray-100 pb-8">
                                <div>
                                    <h2 className="text-4xl font-extrabold text-gray-900 tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-gray-900 to-gray-600">
                                        {questions.candidate}
                                    </h2>
                                    <p className="text-gray-500 font-medium text-lg flex items-center gap-2 mt-2">
                                        <Briefcase size={18} className="text-purple-500" />
                                        {questions.job}
                                    </p>
                                </div>
                                <span className="bg-gradient-to-r from-purple-500 to-indigo-600 text-white px-5 py-2 rounded-full text-xs font-bold shadow-lg shadow-purple-200 uppercase tracking-widest">
                                    AI Guide
                                </span>
                            </div>

                            <div className="space-y-6">
                                {questions.questions.map((q, i) => (
                                    <div key={i} className="group bg-white p-6 rounded-2xl border border-gray-100 hover:border-purple-200 hover:shadow-xl hover:shadow-purple-100/50 transition-all duration-300 relative overflow-hidden">
                                        <div className="absolute top-0 left-0 w-1 h-full bg-purple-500 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                                        <div className="flex gap-5">
                                            <span className="flex-shrink-0 w-10 h-10 flex items-center justify-center bg-gray-50 text-gray-400 border border-gray-200 rounded-xl font-bold text-lg shadow-sm group-hover:bg-purple-600 group-hover:text-white group-hover:border-purple-600 transition-all duration-300">
                                                {i + 1}
                                            </span>
                                            <p className="text-gray-700 pt-1 leading-relaxed text-lg font-medium group-hover:text-gray-900">{q}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <div className="flex-1 flex items-center justify-center text-gray-500">
                            Question data not found.
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default HRQuestionsPage;
