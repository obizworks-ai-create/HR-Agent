import React, { useState } from 'react';
import api from '../lib/api';
import { FileText, CheckCircle, UploadCloud, RefreshCw, Briefcase, Zap } from 'lucide-react';
import clsx from 'clsx';

// Simple Error Boundary for debugging
class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null };
    }
    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }
    componentDidCatch(error, errorInfo) {
        console.error("ErrorBoundary caught an error", error, errorInfo);
    }
    render() {
        if (this.state.hasError) {
            return (
                <div className="p-8 text-center">
                    <h2 className="text-xl font-bold text-red-600">Something went wrong.</h2>
                    <pre className="mt-4 text-left bg-gray-100 p-4 rounded text-sm overflow-auto text-red-800">
                        {this.state.error && this.state.error.toString()}
                    </pre>
                    <button
                        onClick={() => this.setState({ hasError: false })}
                        className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                    >
                        Try Again
                    </button>
                    <p className="mt-4 text-sm text-gray-500">Check console for more details.</p>
                </div>
            );
        }
        return this.props.children;
    }
}

const JobDescriptionPageContent = () => {
    const [jdText, setJdText] = useState('');
    const [status, setStatus] = useState('idle'); // idle, loading, success, error
    const [result, setResult] = useState(null);
    const [activeJobs, setActiveJobs] = useState([]);

    React.useEffect(() => {
        fetchActiveJobs();
    }, []);

    const fetchActiveJobs = async () => {
        try {
            const res = await api.get('/jobs/details');
            if (Array.isArray(res.data)) {
                setActiveJobs(res.data);
            } else {
                console.error("API returned invalid data format:", res.data);
                setActiveJobs([]);
            }
        } catch (err) {
            console.error("Failed to fetch jobs:", err);
            // Don't set error state here to allow manual retry or ignore
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!jdText.trim()) return;

        setStatus('loading');
        try {
            const res = await api.post('/submit-jd', { jd_text: jdText });
            setResult(res.data.jd_requirements);
            setStatus('success');
            fetchActiveJobs(); // Refresh list
        } catch (err) {
            console.error(err);
            setStatus('error');
        }
    };

    return (
        <div className="max-w-7xl mx-auto space-y-8 p-6">
            <div className="text-center space-y-2">
                <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight flex items-center justify-center gap-3">
                    <span className="bg-blue-100 p-2 rounded-xl text-blue-600"><Briefcase size={28} /></span>
                    Job Profiles & Requirements
                </h1>
                <p className="text-slate-500 text-lg">Define new roles or view existing criteria used by the AI Agent.</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Input Panel */}
                <div className={clsx("lg:col-span-1 bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden transition-all duration-500 h-fit")}>
                    <div className="p-1 bg-gradient-to-r from-blue-500 to-indigo-600"></div>
                    <div className="p-8">
                        <h2 className="text-xl font-bold text-gray-900 mb-4">Add New Role</h2>
                        <form onSubmit={handleSubmit} className="space-y-6">
                            <div className="relative group">
                                <textarea
                                    className="relative w-full h-64 p-4 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none font-sans text-sm bg-gray-50 shadow-inner leading-relaxed transition-all"
                                    placeholder="Paste Job Description text here..."
                                    value={jdText}
                                    onChange={(e) => setJdText(e.target.value)}
                                    disabled={status === 'loading'}
                                />
                            </div>

                            <button
                                type="submit"
                                disabled={status === 'loading' || !jdText.trim()}
                                className="w-full px-6 py-3 rounded-xl font-bold text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:shadow-lg hover:shadow-blue-500/30 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center gap-2"
                            >
                                {status === 'loading' ? <><RefreshCw className="animate-spin" /> Extracting...</> : <><Zap size={18} fill="currentColor" /> Analyze & Save</>}
                            </button>
                        </form>
                    </div>
                </div>

                {/* Status / Result Panel OR Active Jobs List */}
                <div className="lg:col-span-2 space-y-6">

                    {/* Result Card (Visible only on success) */}
                    {(status === 'success' && result) && (
                        <div className="bg-white rounded-2xl shadow-xl border border-green-100 overflow-hidden animate-in fade-in slide-in-from-top-4 duration-500 mb-8">
                            <div className="p-1 bg-gradient-to-r from-emerald-400 to-green-500"></div>
                            <div className="p-6 space-y-4">
                                <div className="flex items-center justify-between">
                                    <h3 className="text-emerald-800 font-bold text-lg flex items-center gap-2">
                                        <CheckCircle size={20} className="fill-emerald-500 text-white" />
                                        Extraction Successful
                                    </h3>
                                    <button onClick={() => setStatus('idle')} className="text-sm text-gray-400 hover:text-gray-600">Dismiss</button>
                                </div>
                                <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-100">
                                    <p className="font-bold text-emerald-900">{result.job_title || "New Job Role"}</p>
                                    <div className="flex flex-wrap gap-2 mt-2">
                                        {result.required_skills?.map((skill, i) => (
                                            <span key={i} className="px-2 py-1 bg-white text-emerald-700 text-xs font-bold rounded shadow-sm border border-emerald-100">{skill}</span>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Active Jobs Grid */}
                    <div className="space-y-4">
                        <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                            <Briefcase size={20} className="text-gray-400" />
                            Active Job Profiles ({activeJobs.length})
                        </h2>

                        {activeJobs.length === 0 ? (
                            <div className="text-center p-12 bg-gray-50 rounded-2xl border-2 border-dashed border-gray-200">
                                <p className="text-gray-400 font-medium">No active job profiles found.</p>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {activeJobs.map((job, idx) => {
                                    // SAFETY: Ensure string types to prevent crashes
                                    const jobTitle = String(job.job_title || "Unknown");
                                    const rawSkills = String(job.skills || "");
                                    const rawNotes = String(job.notes || "");

                                    return (
                                        <div key={idx} className="bg-white p-5 rounded-2xl border border-gray-200 shadow-sm hover:shadow-md transition-all group">
                                            <div className="flex justify-between items-start mb-3">
                                                <h3 className="font-bold text-gray-900 text-lg group-hover:text-blue-600 transition-colors">{jobTitle}</h3>
                                                <span className="bg-gray-100 text-gray-600 text-xs font-bold px-2 py-1 rounded-lg">Active</span>
                                            </div>

                                            <div className="space-y-3">
                                                <div>
                                                    <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">Skills</p>
                                                    <div className="flex flex-wrap gap-1.5">
                                                        {rawSkills && rawSkills.split(',').slice(0, 5).map((s, i) => (
                                                            <span key={i} className="px-2 py-1 bg-blue-50 text-blue-700 text-xs font-medium rounded-md border border-blue-100">
                                                                {s.trim()}
                                                            </span>
                                                        ))}
                                                        {rawSkills && rawSkills.split(',').length > 5 && (
                                                            <span className="px-2 py-1 bg-gray-50 text-gray-500 text-xs font-medium rounded-md">+{rawSkills.split(',').length - 5}</span>
                                                        )}
                                                    </div>
                                                </div>

                                                {rawNotes && (
                                                    <div>
                                                        <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">Key Criteria</p>
                                                        <p className="text-xs text-gray-600 line-clamp-2">{rawNotes.replace("MUST HAVE:", "").replace("MUST HAVE", "")}</p>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

// Wrap the export
const JobDescriptionPageSafe = () => (
    <ErrorBoundary>
        <JobDescriptionPageContent />
    </ErrorBoundary>
);

export default JobDescriptionPageSafe;
