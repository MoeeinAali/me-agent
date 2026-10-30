import { Badge } from "@/components/ui/badge";
import type { Capability, Lang } from "@/lib/api/types";
import { CAPABILITY_LABELS } from "@/lib/i18n";

const REFUSALS: Capability[] = ["refuse_unpublished", "refuse_action", "out_of_scope"];

export function CapabilityBadge({ capability, lang }: { capability: Capability; lang: Lang }) {
  const variant = REFUSALS.includes(capability) || capability === "clarify" ? "outline" : "secondary";
  return (
    <Badge variant={variant} data-capability={capability} className="font-mono">
      {CAPABILITY_LABELS[capability][lang]}
    </Badge>
  );
}

export const isRefusal = (c: Capability) => REFUSALS.includes(c);
