import type { ChatResponse, Lang } from "@/lib/api/types";
import { type Segment, type Source, segmentAnswer } from "@/lib/citations";
import { CitationMarker } from "./CitationMarker";

function Markers({ sources, lang, onOpen }: { sources: Source[]; lang: Lang; onOpen?: (n: number) => void }) {
  return (
    <>
      {sources.map((s) => (
        <CitationMarker key={s.id} source={s} lang={lang} onOpen={onOpen} />
      ))}
    </>
  );
}

/** The verified answer: each claim followed by the numbered sources it cites. */
export function AnswerBody({
  response,
  sources,
  lang,
  onOpenSource,
}: {
  response: ChatResponse;
  sources: Source[];
  lang: Lang;
  onOpenSource?: (n: number) => void;
}) {
  const segments = segmentAnswer(response, sources);
  // Consecutive bullet claims become one list; prose claims flow as one paragraph.
  const blocks: Segment[][] = [];
  for (const seg of segments) {
    const last = blocks.at(-1);
    const kind = (s: Segment) => (s.kind === "claim" ? (s.bullet ? "bullet" : "prose") : "text");
    if (last && kind(last[0]) === kind(seg) && seg.kind === "claim") last.push(seg);
    else blocks.push([seg]);
  }
  return (
    <div dir="auto" className="flex flex-col gap-3 text-[15px] leading-7">
      {blocks.map((block, i) => {
        const first = block[0];
        if (first.kind === "text") {
          return (
            <p key={i} className="whitespace-pre-wrap">
              {first.text}
            </p>
          );
        }
        if (first.kind === "claim" && first.bullet) {
          return (
            <ul key={i} className="flex list-disc flex-col gap-1 ps-5 marker:text-muted-foreground">
              {block.map((seg, j) =>
                seg.kind === "claim" ? (
                  <li key={j}>
                    {seg.text}
                    <Markers sources={seg.sources} lang={lang} onOpen={onOpenSource} />
                  </li>
                ) : null,
              )}
            </ul>
          );
        }
        return (
          <p key={i}>
            {block.map((seg, j) =>
              seg.kind === "claim" ? (
                <span key={j}>
                  {j > 0 ? " " : null}
                  {seg.text}
                  <Markers sources={seg.sources} lang={lang} onOpen={onOpenSource} />
                </span>
              ) : null,
            )}
          </p>
        );
      })}
    </div>
  );
}
