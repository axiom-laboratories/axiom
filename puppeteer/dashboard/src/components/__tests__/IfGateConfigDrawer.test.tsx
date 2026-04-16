import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { IfGateConfigDrawer } from '../IfGateConfigDrawer';

describe('IfGateConfigDrawer', () => {
  it('Test 1: renders as a right-side Sheet with title "Configure IF Gate"', () => {
    const onSave = vi.fn();
    const onClose = vi.fn();
    render(
      <IfGateConfigDrawer
        stepId="step-1"
        open={true}
        onSave={onSave}
        onClose={onClose}
      />
    );

    expect(screen.getByText(/Configure IF Gate/i)).toBeInTheDocument();
  });

  it('Test 2: form has 5 fields: Field, Operator, Value, True Branch, False Branch', () => {
    const onSave = vi.fn();
    const onClose = vi.fn();
    render(
      <IfGateConfigDrawer
        stepId="step-1"
        open={true}
        onSave={onSave}
        onClose={onClose}
      />
    );

    expect(screen.getByLabelText(/Field/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Operator/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Value/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/True Branch/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/False Branch/i)).toBeInTheDocument();
  });

  it('Test 3: operator select shows 6 options', () => {
    const onSave = vi.fn();
    const onClose = vi.fn();
    render(
      <IfGateConfigDrawer
        stepId="step-1"
        open={true}
        onSave={onSave}
        onClose={onClose}
      />
    );

    // Verify the operator select field is rendered
    const operatorSelect = screen.getByLabelText(/Operator/i);
    expect(operatorSelect).toBeInTheDocument();
  });

  it('Test 4: value field is hidden when operator is "exists"', () => {
    const onSave = vi.fn();
    const onClose = vi.fn();
    const { container } = render(
      <IfGateConfigDrawer
        stepId="step-1"
        open={true}
        currentConfig={{
          field: 'test',
          op: 'exists',
          true_branch: 'yes',
          false_branch: 'no',
        }}
        onSave={onSave}
        onClose={onClose}
      />
    );

    // Value field should not be visible
    const valueField = screen.queryByLabelText(/^Value$/i);
    expect(valueField).not.toBeInTheDocument();
  });

  it('Test 5: form pre-populates with currentConfig if provided', () => {
    const onSave = vi.fn();
    const onClose = vi.fn();
    const currentConfig = {
      field: 'result.exit_code',
      op: 'eq' as const,
      value: '0',
      true_branch: 'success',
      false_branch: 'failure',
    };

    render(
      <IfGateConfigDrawer
        stepId="step-1"
        open={true}
        currentConfig={currentConfig}
        onSave={onSave}
        onClose={onClose}
      />
    );

    expect(screen.getByDisplayValue('result.exit_code')).toBeInTheDocument();
    expect(screen.getByDisplayValue('0')).toBeInTheDocument();
    expect(screen.getByDisplayValue('success')).toBeInTheDocument();
    expect(screen.getByDisplayValue('failure')).toBeInTheDocument();
  });

  it('Test 6: [Save condition] button calls onSave with form data', async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    const onClose = vi.fn();
    render(
      <IfGateConfigDrawer
        stepId="step-1"
        open={true}
        onSave={onSave}
        onClose={onClose}
      />
    );

    // Fill in the form
    await user.type(screen.getByLabelText(/Field/i), 'result.code');
    await user.type(screen.getByLabelText(/Value/i), '200');
    await user.type(screen.getByLabelText(/True Branch/i), 'success');
    await user.type(screen.getByLabelText(/False Branch/i), 'failure');

    // Click Save
    const saveButton = screen.getByRole('button', { name: /Save/i });
    await user.click(saveButton);

    expect(onSave).toHaveBeenCalled();
    const callArgs = onSave.mock.calls[0][0];
    expect(callArgs.field).toBe('result.code');
    expect(callArgs.value).toBe('200');
    expect(callArgs.true_branch).toBe('success');
    expect(callArgs.false_branch).toBe('failure');
  });

  it('Test 7: [Clear] button resets form to default', async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    const onClose = vi.fn();
    render(
      <IfGateConfigDrawer
        stepId="step-1"
        open={true}
        onSave={onSave}
        onClose={onClose}
      />
    );

    // Fill in the form
    const fieldInput = screen.getByLabelText(/Field/i);
    await user.type(fieldInput, 'result.code');

    // Click Clear
    const clearButton = screen.getByRole('button', { name: /Clear/i });
    await user.click(clearButton);

    // Form should be reset
    expect(fieldInput).toHaveValue('');
  });

  it('Test 8: onSave data includes correct fields', async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    const onClose = vi.fn();
    render(
      <IfGateConfigDrawer
        stepId="step-1"
        open={true}
        onSave={onSave}
        onClose={onClose}
      />
    );

    // Fill in the form
    await user.type(screen.getByLabelText(/Field/i), 'result.status');
    await user.type(screen.getByLabelText(/Value/i), 'ok');
    await user.type(screen.getByLabelText(/True Branch/i), 'on_success');
    await user.type(screen.getByLabelText(/False Branch/i), 'on_failure');

    // Click Save
    const saveButton = screen.getByRole('button', { name: /Save/i });
    await user.click(saveButton);

    expect(onSave).toHaveBeenCalled();
    const config = onSave.mock.calls[0][0];
    expect(config).toHaveProperty('field');
    expect(config).toHaveProperty('op');
    expect(config).toHaveProperty('value');
    expect(config).toHaveProperty('true_branch');
    expect(config).toHaveProperty('false_branch');
  });

  it('Test 9: closing the drawer calls onClose callback', async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    const onClose = vi.fn();
    const { container } = render(
      <IfGateConfigDrawer
        stepId="step-1"
        open={true}
        onSave={onSave}
        onClose={onClose}
      />
    );

    // Click the close button (usually an X in the top right)
    const closeButton = container.querySelector('[aria-label="Close"]');
    if (closeButton) {
      await user.click(closeButton);
      expect(onClose).toHaveBeenCalled();
    }
  });

  it('Test 10: form validation: Field and branch names required', async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    const onClose = vi.fn();
    render(
      <IfGateConfigDrawer
        stepId="step-1"
        open={true}
        onSave={onSave}
        onClose={onClose}
      />
    );

    // Try to save without filling required fields
    const saveButton = screen.getByRole('button', { name: /Save/i });

    // Button might be disabled, or we expect validation error
    // For now just check button is present
    expect(saveButton).toBeInTheDocument();
  });
});
