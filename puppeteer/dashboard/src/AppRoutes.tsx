import React, { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import { getToken } from './auth';

const Login = lazy(() => import('./views/Login'));
const Dashboard = lazy(() => import('./views/Dashboard'));
const Nodes = lazy(() => import('./views/Nodes'));
const Jobs = lazy(() => import('./views/Jobs'));
const JobDefinitions = lazy(() => import('./views/JobDefinitions'));
const Signatures = lazy(() => import('./views/Signatures'));
const Admin = lazy(() => import('./views/Admin'));
const Templates = lazy(() => import('./views/Templates'));
const AuditLog = lazy(() => import('./views/AuditLog'));
const History = lazy(() => import('./views/History'));
const Users = lazy(() => import('./views/Users'));
const Account = lazy(() => import('./views/Account'));
const ServicePrincipals = lazy(() => import('./views/ServicePrincipals'));
const Webhooks = lazy(() => import('./views/Webhooks'));
const Queue = lazy(() => import('./views/Queue'));

// Temporary explicit imports for JS files (if allowed) or placeholder
// Because we haven't migrated everything, we might need to suppress TS errors
// or assume vite handles it.
// Ideally usage of `allowJs` in tsconfig handles these.

// Views correctly imported above

const PrivateRoute = ({ children }: { children: React.ReactNode }) => {
    const token = getToken();
    return token ? children : <Login />;
};

const AppRoutes = () => {
    return (
        <Suspense fallback={<div className="flex h-screen items-center justify-center bg-black text-white">Loading...</div>}>
            <Routes>
                <Route path="/login" element={<Login />} />

                <Route path="/" element={<PrivateRoute><MainLayout /></PrivateRoute>}>
                    <Route index element={<Dashboard />} />
                    <Route path="nodes" element={<Nodes />} />
                    <Route path="jobs" element={<Jobs />} />
                    <Route path="queue" element={<Queue />} />
                    <Route path="scheduled-jobs" element={<JobDefinitions />} />
                    <Route path="history" element={<History />} />
                    <Route path="signatures" element={<Signatures />} />
                    <Route path="templates" element={<Templates />} />
                    <Route path="admin" element={<Admin />} />
                    <Route path="audit" element={<AuditLog />} />
                    <Route path="users" element={<Users />} />
                    <Route path="account" element={<Account />} />
                    <Route path="service-principals" element={<ServicePrincipals />} />
                    <Route path="webhooks" element={<Webhooks />} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                </Route>
            </Routes>
        </Suspense>
    );
};

export default AppRoutes;
