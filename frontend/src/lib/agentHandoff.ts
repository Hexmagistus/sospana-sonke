/** Small handoff helpers that let a search typed in one place (the public
 * homepage's search console, before login; the Ctrl+K command palette,
 * after login) actually run once the visitor reaches the Career Agent
 * (`/agent`), instead of the query just being thrown away.
 *
 * Two separate keys/storages, deliberately:
 *  - `ss_pending_search` (localStorage): survives the register/login redirect
 *    (which lands on /companies, not /agent -- see login/register pages), so
 *    a banner can offer to continue the search after the visitor signs up.
 *  - `ss_agent_command` (sessionStorage): a same-tab, one-shot instruction
 *    for the agent page to run immediately on mount (used once the visitor
 *    actually clicks through, and by the logged-in command palette).
 */

const PENDING_SEARCH_KEY = "ss_pending_search";
const AGENT_COMMAND_KEY = "ss_agent_command";

export function setPendingSearch(text: string): void {
  try {
    window.localStorage.setItem(PENDING_SEARCH_KEY, text);
  } catch {
    /* best-effort only */
  }
}

export function getPendingSearch(): string | null {
  try {
    return window.localStorage.getItem(PENDING_SEARCH_KEY);
  } catch {
    return null;
  }
}

export function clearPendingSearch(): void {
  try {
    window.localStorage.removeItem(PENDING_SEARCH_KEY);
  } catch {
    /* ignore */
  }
}

export function queueAgentCommand(text: string): void {
  try {
    window.sessionStorage.setItem(AGENT_COMMAND_KEY, text);
  } catch {
    /* ignore */
  }
}

export function consumeAgentCommand(): string | null {
  try {
    const v = window.sessionStorage.getItem(AGENT_COMMAND_KEY);
    if (v) window.sessionStorage.removeItem(AGENT_COMMAND_KEY);
    return v;
  } catch {
    return null;
  }
}
