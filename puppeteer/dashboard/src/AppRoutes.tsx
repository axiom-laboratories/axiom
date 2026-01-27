import { Routes, Route } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import Login from './views/Login';
import Dashboard from './views/Dashboard';
import Nodes from './views/Nodes';
import Jobs from './views/Jobs';
import JobDefinitions from './views/JobDefinitions';
import Signatures from './views/Signatures';
import Admin from './views/Admin';
import Docs from './views/Docs';
// import { getUser } from './auth';

// Temporary explicit imports for JS files (if allowed) or placeholder
// Because we haven't migrated everything, we might need to suppress TS errors
// or assume vite handles it.
// Ideally usage of `allowJs` in tsconfig handles these.

// Views correctly imported above

const PrivateRoute = ({ children }: { children: JSX.Element }) => {
    // const user = getUser();
    // TODO: Actually implement getUser() from auth.ts or context
    // For now, checks localStorage directly as a simple verify
    const token = localStorage.getItem('token');
    return token ? children : <Login />;
};

const AppRoutes = () => {
    return (
        <Routes>
            <Route path="/login" element={<Login />} />

            <Route path="/" element={<PrivateRoute><MainLayout /></PrivateRoute>}>
                <Route index element={<Dashboard />} />
                <Route path="nodes" element={<Nodes />} />
                <Route path="jobs" element={<Jobs />} />
                <Route path="scheduled-jobs" element={<JobDefinitions />} />
                <Route path="signatures" element={<Signatures />} />
                <Route path="admin" element={<Admin />} />
                <Route path="docs" element={<Docs />} />
            </Route>
        </Routes>
    );
};

export default AppRoutes;
