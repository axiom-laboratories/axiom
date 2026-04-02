import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TooltipProvider } from '@radix-ui/react-tooltip';
import { Toaster } from 'sonner';
import { ThemeProvider, useTheme } from './hooks/useTheme';
import AppRoutes from './AppRoutes';
import './index.css';

const queryClient = new QueryClient();

function AppContent() {
    const { theme } = useTheme();
    return (
        <QueryClientProvider client={queryClient}>
            <TooltipProvider>
                <BrowserRouter>
                    <AppRoutes />
                </BrowserRouter>
            </TooltipProvider>
            <Toaster theme={theme} position="bottom-right" richColors />
        </QueryClientProvider>
    );
}

function App() {
    return (
        <ThemeProvider>
            <AppContent />
        </ThemeProvider>
    );
}

export default App;
