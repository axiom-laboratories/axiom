import * as React from "react"
import { ChevronDown } from "lucide-react"
import { cn } from "@/lib/utils"

// Minimal Select implementation that doesn't require @radix-ui/react-select
// This is a placeholder to restore build functionality.


interface SelectProps {
    children: React.ReactNode;
    value?: string;
    onValueChange?: (value: string) => void;
}

const Select = ({ children, value, onValueChange }: SelectProps) => {
    const [isOpen, setIsOpen] = React.useState(false)
    const [selectedValue, setSelectedValue] = React.useState(value)

    React.useEffect(() => {
        setSelectedValue(value)
    }, [value])

    const contextValue = React.useMemo(() => ({
        value: selectedValue,
        onValueChange: (val: string) => {
            setSelectedValue(val)
            onValueChange?.(val)
            setIsOpen(false)
        },
        isOpen,
        setIsOpen
    }), [selectedValue, isOpen, onValueChange])

    return (
        <div className="relative w-full">
            {React.Children.map(children, child =>
                React.isValidElement(child) ? React.cloneElement(child as React.ReactElement<any>, contextValue) : child
            )}
        </div>
    )
}

interface SelectTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    isOpen?: boolean;
    setIsOpen?: (open: boolean) => void;
}

const SelectTrigger = React.forwardRef<HTMLButtonElement, SelectTriggerProps>(
    ({ className, children, value, onValueChange, isOpen, setIsOpen, ...props }, ref) => (
        <button
            type="button"
            ref={ref}
            className={cn(
                "flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
                className
            )}
            onClick={() => setIsOpen?.(!isOpen)}
            {...props}
        >
            {children}
            <ChevronDown className="h-4 w-4 opacity-50" />
        </button>
    )
)

interface SelectValueProps {
    placeholder?: string;
    value?: string;
}

const SelectValue = ({ placeholder, value }: SelectValueProps) => {
    return <span>{value || placeholder}</span>
}

interface SelectContentProps {
    children: React.ReactNode;
    isOpen?: boolean;
    value?: string;
    onValueChange?: (value: string) => void;
}

const SelectContent = ({ children, isOpen, value, onValueChange }: SelectContentProps) => {
    if (!isOpen) return null
    return (
        <div className="absolute top-full left-0 z-50 mt-1 min-w-[8rem] overflow-hidden rounded-md border bg-popover text-popover-foreground shadow-md animate-in fade-in-80">
            <div className="p-1">
                {React.Children.map(children, child =>
                    React.isValidElement(child) ? React.cloneElement(child as React.ReactElement<any>, { value: value, onValueChange }) : child
                )}
            </div>
        </div>
    )
}

interface SelectItemProps extends React.HTMLAttributes<HTMLDivElement> {
    value: string;
    onValueChange?: (value: string) => void;
}

const SelectItem = React.forwardRef<HTMLDivElement, SelectItemProps>(
    ({ className, children, value, onValueChange, ...props }, ref) => {
        const isSelected = props.value === value
        return (
            <div
                ref={ref}
                className={cn(
                    "relative flex w-full cursor-default select-none items-center rounded-sm py-1.5 pl-8 pr-2 text-sm outline-none hover:bg-accent hover:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
                    className
                )}
                onClick={() => onValueChange?.(value)}
                {...props}
            >
                <span className="absolute left-2 flex h-3.5 w-3.5 items-center justify-center">
                    {isSelected && <div className="h-2 w-2 rounded-full bg-current" />}
                </span>
                {children}
            </div>
        )
    }
)

export { Select, SelectTrigger, SelectValue, SelectContent, SelectItem }
