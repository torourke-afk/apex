import { useState, useCallback } from "react";
import { apiFetch } from "../api/client";

const TOOL_CHIPS = [
  { name: "query_metrics", color: "var(--cyan)" },
  { name: "simulate_geo", color: "var(--amber)" },
  { name: "propose_action", color: "var(--green)" },
];

interface DirectiveResponse {
  id: string;
  title: string;
  directive_type: string;
  priority: string;
  owner: string;
  status: string;
  notes: string | null;
  created_at: string;
}

export function AgentConsole() {
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [lastResponse, setLastResponse] = useState<DirectiveResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSend = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed || sending) return;

    setSending(true);
    setError(null);
    setInput("");

    try {
      const res = await apiFetch<DirectiveResponse>("/api/directives", {
        method: "POST",
        body: JSON.stringify({
          title: trimmed,
          directive_type: "operational",
          priority: "medium",
          owner: "apex-console",
        }),
      });
      setLastResponse(res);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Directive submission failed";
      setError(msg);
    } finally {
      setSending(false);
    }
  }, [input, sending]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  const dismissResponse = useCallback(() => {
    setLastResponse(null);
    setError(null);
  }, []);

  return (
    <footer aria-label="Agent console" className="flex flex-col border-t border-line bg-gradient-to-b from-panel to-bg2">
      {/* Response / error area */}
      {(lastResponse || error) && (
        <div className="flex items-start gap-3 px-3 md:px-5 pt-2.5 pb-1">
          {error ? (
            <div className="flex-1 flex items-center gap-2">
              <span className="font-mono text-[10px] text-critical">
                Error: {error}
              </span>
              <button
                onClick={dismissResponse}
                className="font-mono text-[9px] text-fg3 hover:text-fg transition-colors cursor-pointer"
              >
                dismiss
              </button>
            </div>
          ) : lastResponse ? (
            <div className="flex-1 flex items-center gap-3">
              <span className="font-mono text-[10px] text-positive">
                Directive created
              </span>
              <span className="font-mono text-[9px] text-fg3">
                {lastResponse.status} | {lastResponse.directive_type} | {lastResponse.priority}
              </span>
              <span
                className="font-mono text-[9px] text-fg3 truncate max-w-[200px]"
                title={lastResponse.id}
              >
                {lastResponse.id.slice(0, 8)}...
              </span>
              <button
                onClick={dismissResponse}
                className="font-mono text-[9px] text-fg3 hover:text-fg transition-colors cursor-pointer"
              >
                dismiss
              </button>
            </div>
          ) : null}
        </div>
      )}

      {/* Input row */}
      <div className="flex items-center gap-2 md:gap-3 px-3 md:px-5 py-2 md:py-3">
        {/* Prompt indicator */}
        <span className="font-mono text-[12px] font-bold text-cyan">
          {sending ? "..." : "›"}
        </span>

        {/* Input */}
        <div className="relative flex-1 flex items-center min-w-0">
          <div aria-hidden="true" className="w-[2px] h-[15px] bg-cyan mr-2 animate-blink flex-none" />
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={sending}
            aria-label="Agent directive"
            placeholder="ask Apex or issue a directive...  e.g. simulate +8% brand budget in DMA 602"
            className="flex-1 min-w-0 bg-transparent border-none outline-none text-fg font-mono text-[12.5px] placeholder:text-fg3 disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-cyan focus-visible:outline-none"
          />
        </div>

        {/* Tool chips -- hidden on small screens */}
        <div className="hidden lg:flex gap-2">
          {TOOL_CHIPS.map(chip => (
            <span
              key={chip.name}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-[7px] bg-panel2 border border-line font-mono text-[10px] text-fg2"
            >
              <span
                className="w-[5px] h-[5px] rounded-full"
                style={{ background: chip.color, boxShadow: `0 0 6px ${chip.color}` }}
              />
              {chip.name}
            </span>
          ))}
        </div>

        {/* Send button */}
        <button
          onClick={handleSend}
          disabled={!input.trim() || sending}
          aria-label="Send directive"
          className="flex-none px-3 md:px-4 py-1.5 rounded-pill bg-cyan text-cyan-ink font-mono text-[11px] font-bold tracking-[.06em] hover:brightness-110 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed focus-visible:ring-2 focus-visible:ring-cyan focus-visible:outline-none"
        >
          {sending ? "SENDING..." : "SEND"}
        </button>
      </div>
    </footer>
  );
}
