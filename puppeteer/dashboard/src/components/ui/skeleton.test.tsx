import { render } from '@testing-library/react';
import { Skeleton } from './skeleton';

describe('Skeleton', () => {
  it('renders with correct classes', () => {
    const { container } = render(<Skeleton className="h-12 w-full" />);
    const skeleton = container.querySelector('div');
    expect(skeleton).toHaveClass('animate-pulse', 'rounded-md', 'bg-muted', 'h-12', 'w-full');
  });

  it('renders with default classes when no className provided', () => {
    const { container } = render(<Skeleton />);
    const skeleton = container.querySelector('div');
    expect(skeleton).toHaveClass('animate-pulse', 'rounded-md', 'bg-muted');
  });

  it('accepts and applies custom className', () => {
    const { container } = render(<Skeleton className="h-4 w-3/4" />);
    const skeleton = container.querySelector('div');
    expect(skeleton).toHaveClass('h-4', 'w-3/4');
  });

  it('accepts html attributes', () => {
    const { container } = render(<Skeleton data-testid="skeleton" />);
    const skeleton = container.querySelector('[data-testid="skeleton"]');
    expect(skeleton).toBeInTheDocument();
  });
});
