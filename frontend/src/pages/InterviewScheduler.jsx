import React, { useState, useEffect } from 'react';
import api from '../lib/api';
import {
    Calendar, CheckCircle, Clock, Mail,
    Briefcase, User, ChevronRight, RefreshCw, Send
} from 'lucide-react';
import clsx from 'clsx';

const InterviewScheduler = () => {
    const [availableJobs, setAvailableJobs] = useState([]);
    const [selectedJob, setSelectedJob] = useState("");
    const [candidates, setCandidates] = useState([]);
    const [loading, setLoading] = useState(false);
    const [sendingInvite, setSendingInvite] = useState(null); // Candidate Name being processed
    const [sendingBatch, setSendingBatch] = useState(false); // Batch operation in progress
    const [scheduleStatus, setScheduleStatus] = useState(null); // success or error msg

    // NEW: Date Filtering State
    const [timePeriod, setTimePeriod] = useState("ALL"); // ALL, LAST_7_DAYS, LAST_30_DAYS, CUSTOM
    const [customDate, setCustomDate] = useState("");

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

    const fetchJobs = async () => {
        try {
            const res = await api.get('/jobs');
            setAvailableJobs(res.data);
        } catch (err) {
            console.error("Failed to fetch jobs:", err);
        }
    };

    const fetchCandidates = async () => {
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
            // Filter only 'PASS' candidates
            const qualified = res.data.filter(c => c.Verdict === 'PASS');
            setCandidates(qualified.reverse());
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    // --- MANUAL SCHEDULING UI STATE ---
    const [scheduleModalOpen, setScheduleModalOpen] = useState(false);
    const [targetCandidate, setTargetCandidate] = useState(null);
    const [inviteDate, setInviteDate] = useState("");
    const [inviteTime, setInviteTime] = useState("");
    const [useAutoSchedule, setUseAutoSchedule] = useState(true);

    const openInviteModal = (candidate) => {
        let email = candidate['Email'] || "";
        if (!email && candidate['Contact']) {
            const match = candidate['Contact'].match(/[\w\.-]+@[\w\.-]+\.\w+/);
            if (match) email = match[0];
        }

        if (!email) {
            alert("No email found for this candidate.");
            return;
        }

        setTargetCandidate({ ...candidate, email });
        setInviteDate("");
        setInviteTime("");
        setUseAutoSchedule(true);
        setScheduleModalOpen(true);
    }

    const confirmInvite = async () => {
        if (!targetCandidate) return;

        // Validation for manual
        if (!useAutoSchedule) {
            if (!inviteDate || !inviteTime) {
                alert("Please select both Date and Time, or switch to Automatic Scheduling.");
                return;
            }
        }

        const candidateName = targetCandidate['Candidate Name'];
        setSendingInvite(candidateName);
        setScheduleModalOpen(false); // Close UI immediately

        try {
            const payload = {
                candidate_name: candidateName,
                candidate_email: targetCandidate.email,
                job_title: selectedJob
            };

            if (!useAutoSchedule) {
                payload.date = inviteDate;
                payload.time = inviteTime;
            }

            const res = await api.post('/schedule-interview', payload);
            alert(`✅Invitation Sent!\n${res.data.message}`);
        } catch (err) {
            alert(`❌ Failed: ${err.response?.data?.detail || err.message}`);
        } finally {
            setSendingInvite(null);
            setTargetCandidate(null);
        }
    };

    const handleInviteAll = async () => {
        const validCandidates = candidates.filter(c => {
            let email = c['Email'] || "";
            if (!email && c['Contact']) {
                const match = c['Contact'].match(/[\w\.-]+@[\w\.-]+\.\w+/);
                if (match) email = match[0];
            }
            return email;
        });

        if (validCandidates.length === 0) {
            alert("No candidates with valid emails found!");
            return;
        }

        if (!confirm(`Send invitations to ALL ${validCandidates.length} candidates (Automatic Allocation)?`)) return;

        setSendingBatch(true);
        try {
            const batch = validCandidates.map(c => {
                let email = c['Email'] || "";
                if (!email && c['Contact']) {
                    const match = c['Contact'].match(/[\w\.-]+@[\w\.-]+\.\w+/);
                    if (match) email = match[0];
                }
                return {
                    candidate_name: c['Candidate Name'],
                    candidate_email: email,
                    job_title: selectedJob
                };
            });

            const res = await api.post('/schedule-interview/batch', batch);

            const successful = res.data.results.filter(r => r.status === 'success').length;
            const failed = res.data.results.filter(r => r.status === 'failed').length;

            alert(`✅ Batch Complete!\n${successful} invitations sent successfully.\n${failed} failed.`);

        } catch (err) {
            alert(`❌ Batch Failed: ${err.response?.data?.detail || err.message}`);
        } finally {
            setSendingBatch(false);
        }
    };

    return (
        <div className="max-w-7xl mx-auto p-6 space-y-8 h-[calc(100vh-2rem)] flex flex-col relative">

            {/* INVITATION MODAL */}
            {scheduleModalOpen && targetCandidate && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
                    <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6 space-y-4 animate-in fade-in zoom-in duration-200">
                        <div className="flex items-center gap-3 border-b border-gray-100 pb-4">
                            <div className="p-2 bg-green-100 rounded-full text-green-600">
                                <Calendar size={20} />
                            </div>
                            <div>
                                <h3 className="text-lg font-bold text-gray-900">Schedule Interview</h3>
                                <p className="text-xs text-gray-500">Candidate: {targetCandidate['Candidate Name']}</p>
                            </div>
                        </div>

                        <div className="space-y-4">
                            {/* Toggle Mode */}
                            <div className="flex bg-gray-100 p-1 rounded-lg">
                                <button
                                    onClick={() => setUseAutoSchedule(true)}
                                    className={clsx(
                                        "flex-1 py-1.5 text-sm font-bold rounded-md transition-all",
                                        useAutoSchedule ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
                                    )}
                                >
                                    Auto Slot (Next 5 Days)
                                </button>
                                <button
                                    onClick={() => setUseAutoSchedule(false)}
                                    className={clsx(
                                        "flex-1 py-1.5 text-sm font-bold rounded-md transition-all",
                                        !useAutoSchedule ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
                                    )}
                                >
                                    Select Date & Time
                                </button>
                            </div>

                            {!useAutoSchedule && (
                                <div className="space-y-3 bg-gray-50 p-4 rounded-xl border border-gray-100">
                                    <div>
                                        <label className="block text-xs font-bold text-gray-500 mb-1">Date</label>
                                        <input
                                            type="date"
                                            value={inviteDate}
                                            onChange={(e) => setInviteDate(e.target.value)}
                                            className="w-full text-sm border-gray-200 rounded-lg p-2 focus:ring-green-500 focus:border-green-500"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-xs font-bold text-gray-500 mb-1">Time (Start)</label>
                                        <input
                                            type="time"
                                            value={inviteTime}
                                            onChange={(e) => setInviteTime(e.target.value)}
                                            className="w-full text-sm border-gray-200 rounded-lg p-2 focus:ring-green-500 focus:border-green-500"
                                        />
                                    </div>
                                </div>
                            )}

                            {useAutoSchedule && (
                                <div className="p-4 bg-green-50 border border-green-100 rounded-xl">
                                    <p className="text-xs text-green-800 flex gap-2">
                                        <CheckCircle size={14} className="shrink-0 mt-0.5" />
                                        System will automatically find the first available 45-min slot in the next 5 working days (9 AM - 5 PM).
                                    </p>
                                </div>
                            )}
                        </div>

                        <div className="flex gap-3 pt-2">
                            <button
                                onClick={() => setScheduleModalOpen(false)}
                                className="flex-1 px-4 py-2 text-sm font-bold text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-xl transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={confirmInvite}
                                className="flex-1 px-4 py-2 text-sm font-bold text-white bg-green-600 hover:bg-green-700 rounded-xl shadow-lg shadow-green-200 transition-all active:scale-95"
                            >
                                Send Invite
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Header */}
            <div className="bg-white/80 backdrop-blur-xl rounded-3xl shadow-lg border border-white/20 p-8 flex flex-col md:flex-row justify-between items-center gap-6 relative overflow-hidden">
                <div className="absolute top-0 right-0 w-64 h-64 bg-green-100 rounded-full blur-3xl opacity-50 -mr-16 -mt-16 pointer-events-none" />

                <div className="z-10">
                    <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
                        <span className="p-2 bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl text-white shadow-lg shadow-green-500/20">
                            <Calendar size={24} className="text-white" />
                        </span>
                        Interview Scheduler
                    </h1>
                    <p className="text-gray-500 font-medium ml-14 mt-1">Manage invitations for shortlisted candidates.</p>
                </div>

                <div className="flex flex-col md:flex-row items-center gap-4 z-10 w-full md:w-auto">
                    {/* Time Period Selector */}
                    <div className="flex items-center gap-2 bg-white/50 px-3 py-2 rounded-xl border border-green-200/50 shadow-sm backdrop-blur-sm">
                        <span className="text-sm font-medium text-green-800"><Clock className="w-4 h-4 inline mr-1" />Period:</span>
                        <select
                            value={timePeriod}
                            onChange={(e) => setTimePeriod(e.target.value)}
                            className="bg-transparent border-none text-sm font-bold text-green-900 focus:ring-0 cursor-pointer"
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
                                className="ml-2 border border-green-200 rounded-lg px-2 py-1 text-sm bg-white/80"
                            />
                        )}
                    </div>

                    <div className="relative flex-1 md:w-72">
                        <div className="absolute left-4 top-1/2 -translate-y-1/2 text-green-600 pointer-events-none">
                            <Briefcase size={18} />
                        </div>
                        <select
                            className="w-full pl-12 pr-4 py-3 bg-white/50 border border-gray-200 text-gray-900 rounded-xl focus:ring-2 focus:ring-green-500 focus:border-transparent cursor-pointer font-semibold shadow-sm transition-all hover:bg-white"
                            value={selectedJob}
                            onChange={(e) => setSelectedJob(e.target.value)}
                        >
                            <option value="">Select Job to Schedule...</option>
                            {availableJobs.map((j, i) => <option key={i} value={j}>{j}</option>)}
                        </select>
                    </div>

                    {selectedJob && candidates.length > 0 && (
                        <button
                            onClick={handleInviteAll}
                            disabled={sendingBatch}
                            className={clsx(
                                "flex items-center gap-2 px-6 py-3 rounded-xl font-bold transition-all shadow-md whitespace-nowrap",
                                "bg-gradient-to-r from-green-600 to-emerald-600 text-white hover:shadow-green-300 hover:scale-105",
                                sendingBatch && "opacity-50 cursor-wait"
                            )}
                        >
                            {sendingBatch ? (
                                <>
                                    <RefreshCw size={18} className="animate-spin" />
                                    Sending...
                                </>
                            ) : (
                                <>
                                    <Send size={18} />
                                    Invite All ({candidates.filter(c => c['Email'] || (c['Contact'] && c['Contact'].match(/[\w\.-]+@[\w\.-]+\.\w+/))).length})
                                </>
                            )}
                        </button>
                    )}
                </div>
            </div>

            {/* Content Area */}
            <div className="bg-white rounded-3xl shadow-xl shadow-gray-200/50 border border-gray-100 flex-1 overflow-hidden flex flex-col relative">

                {/* Table Header */}
                <div className="grid grid-cols-12 gap-4 p-5 bg-gray-50/50 border-b border-gray-100 text-xs font-bold text-gray-400 uppercase tracking-wider">
                    <div className="col-span-4 pl-4">Candidate</div>
                    <div className="col-span-3">Status</div>
                    <div className="col-span-3">Score</div>
                    <div className="col-span-2 text-right pr-4">Action</div>
                </div>

                {/* List */}
                <div className="overflow-y-auto flex-1 custom-scrollbar">
                    {loading ? (
                        <div className="flex flex-col items-center justify-center h-64 text-gray-400 gap-3">
                            <RefreshCw size={32} className="animate-spin text-green-500" />
                            <p>Loading qualified candidates...</p>
                        </div>
                    ) : !selectedJob ? (
                        <div className="flex flex-col items-center justify-center h-64 text-gray-400 gap-4">
                            <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center">
                                <Briefcase size={32} className="text-gray-300" />
                            </div>
                            <p className="font-medium">Please select a job role above to view candidates.</p>
                        </div>
                    ) : candidates.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-64 text-gray-400 gap-4">
                            <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center">
                                <User size={32} className="text-gray-300" />
                            </div>
                            <p className="font-medium">No candidates have been marked as PASS for this role yet.</p>
                        </div>
                    ) : (
                        candidates.map((c, i) => {
                            // Determine email availability for UI feedback
                            let hasEmail = c['Email'] || (c['Contact'] && c['Contact'].match(/[\w\.-]+@[\w\.-]+\.\w+/));

                            return (
                                <div key={i} className="grid grid-cols-12 gap-4 p-4 border-b border-gray-50 hover:bg-green-50/30 transition-colors items-center group">
                                    <div className="col-span-4 pl-4">
                                        <div className="font-bold text-gray-900">{c['Candidate Name']}</div>
                                        <div className="text-xs text-gray-500 flex items-center gap-1 mt-0.5">
                                            <Mail size={10} />
                                            {hasEmail ? <span className="truncate max-w-[200px]">{hasEmail}</span> : <span className="text-rose-500">Missing Email</span>}
                                        </div>
                                    </div>
                                    <div className="col-span-3">
                                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-green-100 text-green-700 border border-green-200">
                                            <CheckCircle size={12} />
                                            PASSED
                                        </span>
                                    </div>
                                    <div className="col-span-3">
                                        <div className="flex items-center gap-2">
                                            <span className="font-mono font-bold text-gray-700">{c['Match Score'] || 'N/A'}</span>
                                            <div className="h-1.5 w-24 bg-gray-100 rounded-full overflow-hidden">
                                                <div
                                                    className="h-full bg-green-500 rounded-full"
                                                    style={{ width: `${Math.min(parseInt(c['Match Score'] || 0), 100)}%` }}
                                                />
                                            </div>
                                        </div>
                                    </div>
                                    <div className="col-span-2 text-right pr-4">
                                        <button
                                            onClick={() => openInviteModal(c)}
                                            disabled={sendingInvite === c['Candidate Name'] || !hasEmail}
                                            className={clsx(
                                                "inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold transition-all shadow-sm",
                                                !hasEmail
                                                    ? "bg-gray-100 text-gray-400 cursor-not-allowed border border-gray-200"
                                                    : sendingInvite === c['Candidate Name']
                                                        ? "bg-green-100 text-green-700 cursor-wait border border-green-200"
                                                        : "bg-gray-900 text-white hover:bg-green-600 hover:shadow-green-200 hover:scale-105"
                                            )}
                                        >
                                            {sendingInvite === c['Candidate Name'] ? (
                                                <RefreshCw size={16} className="animate-spin" />
                                            ) : (
                                                <Send size={16} />
                                            )}
                                            {sendingInvite === c['Candidate Name'] ? 'Sending...' : 'Invite'}
                                        </button>
                                    </div>
                                </div>
                            )
                        })
                    )}
                </div>
            </div>
        </div>
    );
};

export default InterviewScheduler;
