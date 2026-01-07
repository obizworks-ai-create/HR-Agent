import React from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, FileText, Users, MessageSquare, Calendar, Target } from 'lucide-react';
import clsx from 'clsx';

const NavItem = ({ to, icon: Icon, label }) => {
    const location = useLocation();
    const isActive = location.pathname === to;

    return (
        <Link
            to={to}
            className={clsx(
                "flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors",
                isActive
                    ? "bg-blue-600 text-white"
                    : "text-gray-600 hover:bg-gray-100"
            )}
        >
            <Icon size={20} />
            <span className="font-medium">{label}</span>
        </Link>
    );
};

const Layout = () => {
    return (
        <div className="min-h-screen bg-gray-50 flex">
            {/* Sidebar */}
            <aside className="w-64 bg-white border-r border-gray-200 fixed h-full z-10">
                <div className="p-6 border-b border-gray-200">
                    <h1 className="text-xl font-bold text-blue-600 flex items-center gap-2">
                        <LayoutDashboard />
                        HR Pipeline
                    </h1>
                </div>

                <nav className="p-4 space-y-2">
                    <NavItem to="/dashboard" icon={LayoutDashboard} label="Dashboard" />
                    <NavItem to="/" icon={FileText} label="Job Description" />
                    <NavItem to="/candidates" icon={Users} label="Import & View Results" />
                    <NavItem to="/analysis" icon={Target} label="Run Analysis and Results" />
                    <NavItem to="/questions" icon={MessageSquare} label="HR Questions" />
                    <NavItem to="/interviews" icon={Calendar} label="Interviews" />
                </nav>
            </aside>

            {/* Main Content */}
            <main className="ml-64 flex-1 p-8">
                <div className="max-w-6xl mx-auto">
                    <Outlet />
                </div>
            </main>
        </div>
    );
};

export default Layout;
