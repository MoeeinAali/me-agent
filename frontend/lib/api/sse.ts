export type RawEvent = { event: string; data: string };

/** Incremental Server-Sent Events parser: feed chunks, keep `rest` for the next call. */
export function parseSSE(chunk: string, buffer: string): { events: RawEvent[]; rest: string } {
  const text = (buffer + chunk).replace(/\r\n?/g, "\n");
  const blocks = text.split("\n\n");
  const rest = blocks.pop() ?? "";
  const events: RawEvent[] = [];
  for (const block of blocks) {
    let event = "message";
    const data: string[] = [];
    for (const line of block.split("\n")) {
      if (line.startsWith(":")) continue;
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
    }
    if (data.length) events.push({ event, data: data.join("\n") });
  }
  return { events, rest };
}
