import * as React from "react"
import { ChevronDown } from "lucide-react"
import { cn } from "@/lib/utils"

// Minimal Select implementation that doesn't require @radix-ui/react-select
// This is a placeholder to restore build functionality.

const Select = ({ children, value, onValueChange }: any) => {
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
    }), [selectedValue, isOpen])

    return (
        <div className="relative w-full">
            {React.Children.map(children, child =>
                React.isValidElement(child) ? React.cloneElement(child as any, contextValue) : child
            )}
        </div>
    )
}

const SelectTrigger = React.forwardRef<HTMLButtonElement, any>(
    ({ className, children, value, onValueChange, isOpen, setIsOpen, ...props }, ref) => (
        <button
            type="button"
            className={cn(
                "flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
                className
            )}
            onClick={() => setIsOpen(!isOpen)}
            {...props}
        >
            {children}
            <ChevronDown className="h-4 w-4 opacity-50" />
        </button>
    )
)

const SelectValue = ({ placeholder, value }: any) => {
    return <span>{value || placeholder}</span>
}

const SelectContent = ({ children, isOpen, value, onValueChange }: any) => {
    if (!isOpen) return null
    return (
        <div className="absolute top-full left-0 z-50 mt-1 min-w-[8rem] overflow-hidden rounded-md border bg-popover text-popover-foreground shadow-md animate-in fade-in-80">
            <div className="p-1">
                {React.Children.map(children, child =>
                    React.isValidElement(child) ? React.cloneElement(child as any, { value: value, onValueChange }) : child
                )}
            </div>
        </div>
    )
}

const SelectItem = React.forwardRef<HTMLDivElement, any>(
    ({ className, children, value, onValueChange, ...props }, ref) => {
        const isSelected = props.value === value
        return (
            <div
                className={cn(
                    "relative flex w-full cursor-default select-none items-center rounded-sm py-1.5 pl-8 pr-2 text-sm outline-none hover:bg-accent hover:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
                    className
                )}
                onClick={() => onValueChange(props.value)}
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
