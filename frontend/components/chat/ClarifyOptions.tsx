import { Button } from "@/components/ui/button";

export function ClarifyOptions({
  options,
  onPick,
  disabled,
}: {
  options: string[];
  onPick: (label: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((label) => (
        <Button key={label} size="sm" variant="outline" dir="auto" disabled={disabled} onClick={() => onPick(label)}>
          {label}
        </Button>
      ))}
    </div>
  );
}
