import React, { useState, useEffect } from 'react';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from './ui/sheet';
import { Button } from './ui/button';
import { Input } from './ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import { Label } from './ui/label';

export interface IfGateConfig {
  field: string;
  op: 'eq' | 'neq' | 'gt' | 'lt' | 'contains' | 'exists';
  value?: string;
  true_branch: string;
  false_branch: string;
}

export interface IfGateConfigDrawerProps {
  stepId: string;
  open: boolean;
  currentConfig?: IfGateConfig;
  onSave: (config: IfGateConfig) => void;
  onClose: () => void;
}

const OPERATORS = [
  { value: 'eq', label: 'Equals (==)' },
  { value: 'neq', label: 'Not Equals (!=)' },
  { value: 'gt', label: 'Greater Than (>)' },
  { value: 'lt', label: 'Less Than (<)' },
  { value: 'contains', label: 'Contains' },
  { value: 'exists', label: 'Exists' },
];

export const IfGateConfigDrawer: React.FC<IfGateConfigDrawerProps> = ({
  stepId,
  open,
  currentConfig,
  onSave,
  onClose,
}) => {
  const [field, setField] = useState('');
  const [op, setOp] = useState<'eq' | 'neq' | 'gt' | 'lt' | 'contains' | 'exists'>('eq');
  const [value, setValue] = useState('');
  const [trueBranch, setTrueBranch] = useState('');
  const [falseBranch, setFalseBranch] = useState('');

  useEffect(() => {
    if (currentConfig) {
      setField(currentConfig.field);
      setOp(currentConfig.op);
      setValue(currentConfig.value || '');
      setTrueBranch(currentConfig.true_branch);
      setFalseBranch(currentConfig.false_branch);
    } else {
      setField('');
      setOp('eq');
      setValue('');
      setTrueBranch('');
      setFalseBranch('');
    }
  }, [currentConfig, open]);

  const handleSave = () => {
    const config: IfGateConfig = {
      field,
      op,
      value: op === 'exists' ? undefined : value,
      true_branch: trueBranch,
      false_branch: falseBranch,
    };
    onSave(config);
  };

  const handleClear = () => {
    setField('');
    setOp('eq');
    setValue('');
    setTrueBranch('');
    setFalseBranch('');
  };

  return (
    <Sheet open={open} onOpenChange={(newOpen) => !newOpen && onClose()}>
      <SheetContent side="right" className="w-96">
        <SheetHeader>
          <SheetTitle>Configure IF Gate</SheetTitle>
        </SheetHeader>

        <div className="space-y-6 py-6">
          {/* Field */}
          <div className="space-y-2">
            <Label htmlFor="field">Field</Label>
            <Input
              id="field"
              placeholder="e.g. result.exit_code"
              value={field}
              onChange={(e) => setField(e.target.value)}
            />
          </div>

          {/* Operator */}
          <div className="space-y-2">
            <Label htmlFor="operator">Operator</Label>
            <Select value={op} onValueChange={(v) => setOp(v as any)}>
              <SelectTrigger id="operator">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {OPERATORS.map(opt => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Value (conditionally hidden for 'exists' operator) */}
          {op !== 'exists' && (
            <div className="space-y-2">
              <Label htmlFor="value">Value</Label>
              <Input
                id="value"
                placeholder="e.g. 0 or success"
                value={value}
                onChange={(e) => setValue(e.target.value)}
              />
            </div>
          )}

          {/* True Branch */}
          <div className="space-y-2">
            <Label htmlFor="true-branch">True Branch</Label>
            <Input
              id="true-branch"
              placeholder="e.g. success"
              value={trueBranch}
              onChange={(e) => setTrueBranch(e.target.value)}
            />
          </div>

          {/* False Branch */}
          <div className="space-y-2">
            <Label htmlFor="false-branch">False Branch</Label>
            <Input
              id="false-branch"
              placeholder="e.g. failure"
              value={falseBranch}
              onChange={(e) => setFalseBranch(e.target.value)}
            />
          </div>

          {/* Actions */}
          <div className="flex gap-2 pt-4">
            <Button
              variant="default"
              onClick={handleSave}
              className="flex-1"
            >
              Save condition
            </Button>
            <Button
              variant="outline"
              onClick={handleClear}
              className="flex-1"
            >
              Clear
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
};
