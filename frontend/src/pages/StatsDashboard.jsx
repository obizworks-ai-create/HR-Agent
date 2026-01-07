import React, { useState, useEffect } from 'react';
import api from '../lib/api';
import {
    LayoutDashboard, Users, FileText, CheckCircle,
    TrendingUp, RefreshCw, BarChart3, PieChart,
    Briefcase
} from 'lucide-react';
import clsx from 'clsx';

const StatsDashboard = () => {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchStats = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await api.get('/dashboard/stats');
            setStats(res.data);
        } catch (err) {
            console.error("Dashboard fetch error:", err);
            setError("Failed to load dashboard statistics.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchStats();
    }, []);

    // Metric Card Component
    const MetricCard = ({ title, value, icon: Icon, colorClass, bgClass }) => (
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 flex items-start justify-between transition-all hover:shadow-md">
            <div>
                <p className="text-gray-500 font-medium text-sm">{title}</p>
                <h3 className="text-3xl font-extrabold text-gray-900 mt-2">{value}</h3>
            </div>
            <div className={clsx("p-3 rounded-xl", bgClass)}>
                <Icon size={24} className={colorClass} />
            </div>
        </div>
    );

    return (
        <div className="max-w-7xl mx-auto space-y-8 p-6">

            {/* Header */}
            <div className="flex flex-col md:flex-row justify-between items-end md:items-center gap-4">
                <div>
                    <h1 className="text-3xl font-extrabold text-gray-900 flex items-center gap-3">
                        <span className="p-2 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl text-white shadow-lg shadow-indigo-500/20">
                            <LayoutDashboard size={24} />
                        </span>
                        Recruitment Overview
                    </h1>
                    <p className="text-gray-500 mt-2 font-medium ml-14">Real-time insights into your hiring pipeline.</p>
                </div>

                <button
                    onClick={fetchStats}
                    className="flex items-center gap-2 px-5 py-2.5 bg-white border border-gray-200 text-gray-700 font-semibold rounded-xl hover:bg-gray-50 hover:border-gray-300 transition-all shadow-sm"
                >
                    <RefreshCw size={18} className={clsx(loading && "animate-spin")} />
                    Refresh Data
                </button>
            </div>

            {loading && !stats ? (
                <div className="h-96 flex flex-col items-center justify-center text-gray-400 gap-4">
                    <RefreshCw size={40} className="animate-spin text-indigo-500" />
                    <p className="font-medium animate-pulse">Aggregating Pipeline Data...</p>
                </div>
            ) : error ? (
                <div className="bg-rose-50 border border-rose-100 p-6 rounded-2xl flex items-center gap-4 text-rose-700">
                    <div className="bg-rose-100 p-2 rounded-full"><TrendingUp className="rotate-180" size={24} /></div>
                    <div>
                        <h3 className="font-bold">Error Loading Dashboard</h3>
                        <p className="text-sm">{error}</p>
                        <button onClick={fetchStats} className="text-sm underline mt-1 font-semibold hover:text-rose-900">Try Again</button>
                    </div>
                </div>
            ) : (
                <>
                    {/* Top Level Metrics */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                        <MetricCard
                            title="Total Received"
                            value={stats?.total_received || 0}
                            icon={UplaodIconWrapper} // Defined below or just use Lucide directly
                            colorClass="text-blue-600"
                            bgClass="bg-blue-50"
                        />
                        <MetricCard
                            title="Processed by AI"
                            value={stats?.total_processed || 0}
                            icon={ZapIconWrapper}
                            colorClass="text-purple-600"
                            bgClass="bg-purple-50"
                        />
                        <MetricCard
                            title="Qualified Candidates"
                            value={stats?.total_passed || 0}
                            icon={CheckCircle}
                            colorClass="text-emerald-600"
                            bgClass="bg-emerald-50"
                        />
                        <MetricCard
                            title="Conversion Rate"
                            value={`${stats?.total_processed ? Math.round((stats.total_passed / stats.total_processed) * 100) : 0}%`}
                            icon={TrendingUp}
                            colorClass="text-orange-600"
                            bgClass="bg-orange-50"
                        />
                    </div>

                    {/* Job Breakdown Table */}
                    <div className="bg-white rounded-3xl shadow-lg border border-gray-100 overflow-hidden">
                        <div className="p-6 border-b border-gray-100 bg-gray-50/50 flex justify-between items-center">
                            <h3 className="font-bold text-gray-800 flex items-center gap-2">
                                <Briefcase size={20} className="text-gray-400" />
                                Funnel by Job Role
                            </h3>
                            <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">{stats?.job_stats?.length || 0} Active Roles</span>
                        </div>

                        <div className="overflow-x-auto">
                            <table className="w-full text-left">
                                <thead className="bg-gray-50/50 text-xs font-bold text-gray-500 uppercase tracking-wider border-b border-gray-100">
                                    <tr>
                                        <th className="px-6 py-4">Job Role</th>
                                        <th className="px-6 py-4 text-center">Received</th>
                                        <th className="px-6 py-4 text-center">Analyzed</th>
                                        <th className="px-6 py-4 text-center">Qualified</th>
                                        <th className="px-6 py-4 text-center">Pass Rate</th>
                                        <th className="px-6 py-4 text-center">Status</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-50">
                                    {stats?.job_stats?.map((job, i) => {
                                        const passRate = job.processed ? Math.round((job.passed / job.processed) * 100) : 0;
                                        return (
                                            <tr key={i} className="hover:bg-gray-50/80 transition-colors">
                                                <td className="px-6 py-4 font-semibold text-gray-800">
                                                    {job.job_title}
                                                </td>
                                                <td className="px-6 py-4 text-center text-gray-600 font-mono">
                                                    {job.received}
                                                </td>
                                                <td className="px-6 py-4 text-center text-gray-600 font-mono">
                                                    {job.processed}
                                                </td>
                                                <td className="px-6 py-4 text-center font-bold text-emerald-600 font-mono">
                                                    {job.passed}
                                                </td>
                                                <td className="px-6 py-4 text-center">
                                                    <div className="flex items-center justify-center gap-2">
                                                        <div className="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                                                            <div
                                                                className={clsx("h-full rounded-full", passRate > 50 ? 'bg-emerald-500' : passRate > 20 ? 'bg-orange-400' : 'bg-rose-400')}
                                                                style={{ width: `${passRate}%` }}
                                                            />
                                                        </div>
                                                        <span className="text-xs text-gray-500 font-medium w-8">{passRate}%</span>
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4 text-center">
                                                    {job.received > 0 ? (
                                                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-green-50 text-green-700">
                                                            Active
                                                        </span>
                                                    ) : (
                                                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-gray-100 text-gray-500">
                                                            Idle
                                                        </span>
                                                    )}
                                                </td>
                                            </tr>
                                        )
                                    })}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
};

// Helper Icons
const UplaodIconWrapper = (props) => <FileText {...props} />;
const ZapIconWrapper = (props) => <div className="relative"><BarChart3 {...props} /></div>;

export default StatsDashboard;
