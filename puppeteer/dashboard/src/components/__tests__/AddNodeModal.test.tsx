import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import AddNodeModal from '../AddNodeModal';

describe('AddNodeModal Component', () => {
    const mockOnClose = vi.fn();

    it('renders the modal when open', () => {
        render(
            <AddNodeModal
                open={true}
                onOpenChange={mockOnClose}
            />
        );

        expect(screen.getByText(/Deploy New Nodes/i)).toBeInTheDocument();
    });

    it('does not render when closed', () => {
        render(
            <AddNodeModal
                open={false}
                onOpenChange={mockOnClose}
            />
        );

        expect(screen.queryByText(/Deploy New Nodes/i)).not.toBeInTheDocument();
    });

    it('calls onOpenChange when close button clicked', () => {
        render(
            <AddNodeModal
                open={true}
                onOpenChange={mockOnClose}
            />
        );

        // There are two buttons named "Close" (the modal action button and the X-close button)
        const closeButtons = screen.getAllByRole('button', { name: /Close/i });
        fireEvent.click(closeButtons[0]);

        expect(mockOnClose).toHaveBeenCalledWith(false);
    });
});
