import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";

interface SelectOption {
  label: string;
  value: string;
}

interface SelectFieldProps {
  disabled?: boolean;
  emptyLabel?: string;
  label: string;
  onValueChange: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  value?: string | null;
}

export function SelectField({
  disabled,
  emptyLabel,
  label,
  onValueChange,
  options,
  placeholder,
  value
}: SelectFieldProps) {
  const normalizedValue = value ?? undefined;

  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <Select
        key={normalizedValue === undefined ? "__placeholder__" : "__value__"}
        disabled={disabled}
        value={normalizedValue}
        onValueChange={(nextValue) => onValueChange(nextValue)}
      >
        <SelectTrigger>
          <SelectValue placeholder={placeholder ?? label} />
        </SelectTrigger>
        <SelectContent>
          {emptyLabel ? <SelectItem value="__all__">{emptyLabel}</SelectItem> : null}
          {options.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
