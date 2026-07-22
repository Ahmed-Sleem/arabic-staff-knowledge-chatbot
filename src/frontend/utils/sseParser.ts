export interface ParsedSseEvent {
  event: string;
  data: string;
  id?: string;
  retry?: string;
}

export function createSseParser(onEvent: (event: ParsedSseEvent) => void) {
  let buffer = "";
  let eventName = "message";
  let eventId: string | undefined;
  let retry: string | undefined;
  let dataLines: string[] = [];

  const dispatch = () => {
    if (dataLines.length === 0) {
      eventName = "message";
      eventId = undefined;
      retry = undefined;
      return;
    }
    onEvent({ event: eventName || "message", data: dataLines.join("\n"), id: eventId, retry });
    eventName = "message";
    eventId = undefined;
    retry = undefined;
    dataLines = [];
  };

  const processLine = (line: string) => {
    if (line.endsWith("\r")) line = line.slice(0, -1);
    if (line === "") {
      dispatch();
      return;
    }
    if (line.startsWith(":")) return;
    const colonIndex = line.indexOf(":");
    const field = colonIndex === -1 ? line : line.slice(0, colonIndex);
    let value = colonIndex === -1 ? "" : line.slice(colonIndex + 1);
    if (value.startsWith(" ")) value = value.slice(1);
    if (field === "event") eventName = value;
    else if (field === "data") dataLines.push(value);
    else if (field === "id") eventId = value;
    else if (field === "retry") retry = value;
  };

  return {
    feed(chunk: string) {
      buffer += chunk;
      const lines = buffer.split(/\n/);
      buffer = lines.pop() || "";
      lines.forEach(processLine);
    },
    end() {
      if (buffer) {
        processLine(buffer);
        buffer = "";
      }
      dispatch();
    }
  };
}
