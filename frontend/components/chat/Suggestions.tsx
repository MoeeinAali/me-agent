import { Button } from "@/components/ui/button";

export function Suggestions({
  suggestions,
  visible,
  onPick,
}: {
  suggestions: string[];
  visible: boolean;
  onPick: (text: string) => void;
}) {
  if (!visible || suggestions.length === 0) return null;
  return (
    <ul aria-label="Suggested questions" className="grid gap-2 sm:grid-cols-2">
      {suggestions.map((s) => (
        <li key={s}>
          <Button
            variant="outline"
            dir="auto"
            className="h-auto w-full justify-start whitespace-normal py-2 text-start"
            onClick={() => onPick(s)}
          >
            {s}
          </Button>
        </li>
      ))}
    </ul>
  );
}
