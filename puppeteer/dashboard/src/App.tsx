import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TooltipProvider } from '@radix-ui/react-tooltip';
import { Toaster } from 'sonner';
import { ThemeProvider } from './hooks/useTheme';
import AppRoutes from './AppRoutes';
import './index.css';

const queryClient = new QueryClient();

function App() {
    return (
        <ThemeProvider>
            <QueryClientProvider client={queryClient}>
                <TooltipProvider>
                    <BrowserRouter>
                        <AppRoutes />
                    </BrowserRouter>
                </TooltipProvider>
                <Toaster theme="dark" position="bottom-right" richColors />
            </QueryClientProvider>
        </ThemeProvider>
    );
}

export default App;
