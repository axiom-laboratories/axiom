import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TooltipProvider } from '@radix-ui/react-tooltip';
import { Toaster } from 'sonner';
import AppRoutes from './AppRoutes';
import './index.css';

const queryClient = new QueryClient();

function App() {
    return (
        <QueryClientProvider client={queryClient}>
            <TooltipProvider>
                <BrowserRouter>
                    <AppRoutes />
                </BrowserRouter>
            </TooltipProvider>
            <Toaster theme="dark" position="bottom-right" richColors />
        </QueryClientProvider>
    );
}

export default App;
