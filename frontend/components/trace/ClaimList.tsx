import type { Claim, Evidence, Lang } from "@/lib/api/types";
import { ProofChip } from "./ProofChip";

/** Each kept claim with the proofs it cites. Ids the response doesn't carry are not rendered. */
export function ClaimList({ claims, evidence, lang }: { claims: Claim[]; evidence: Evidence[]; lang: Lang }) {
  const byId = new Map(evidence.map((e) => [e.id, e]));
  if (claims.length === 0) return null;
  return (
    <ol className="flex flex-col gap-2">
      {claims.map((claim, i) => (
        <li key={i} className="flex flex-col gap-1">
          <p dir="auto" className="text-sm">
            {claim.text}
          </p>
          <div className="flex flex-wrap gap-1">
            {claim.evidence.map((id) => {
              const item = byId.get(id);
              return item ? <ProofChip key={id} evidence={item} lang={lang} /> : null;
            })}
          </div>
        </li>
      ))}
    </ol>
  );
}
