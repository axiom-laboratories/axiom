import { Routes, Route, Navigate } from 'react-router-dom';
import Login from './views/Login';
import Dashboard from './views/Dashboard';
import Nodes from './views/Nodes';
import Jobs from './views/Jobs';
import Admin from './views/Admin';
import MainLayout from './layouts/MainLayout';
import { getUser } from './auth';

const PrivateRoute = ({ children }) => {
    const user = getUser();
    return user ? children : <Navigate to="/login" />;
};

const AppRoutes = () => {
    return (
        <Routes>
            <Route path="/login" element={<Login />} />

            <Route path="/" element={<PrivateRoute><MainLayout /></PrivateRoute>}>
                <Route index element={<Dashboard />} />
                <Route path="nodes" element={<Nodes />} />
                <Route path="jobs" element={<Jobs />} />
                <Route path="admin" element={<Admin />} />
            </Route>
        </Routes>
    );
};

export default AppRoutes;
