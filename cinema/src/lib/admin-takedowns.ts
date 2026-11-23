import "server-only";

import { listTakedowns } from "./store";
import { listTakedownsRemote, serviceKeySet, supabaseUrlSet } from "./supabase-admin";
import type { Takedown } from "./types";

export async function adminTakedowns(): Promise<{ items: Takedown[]; origin: "supabase" | "demonstration"; warning: string | null }> {
  if (supabaseUrlSet()) {
    if (!serviceKeySet()) {
      return {
        items: [],
        origin: "supabase",
        warning: "Complaints are stored in Supabase. Set SUPABASE_SERVICE_ROLE_KEY on the server to list them here.",
      };
    }
    try {
      return { items: await listTakedownsRemote(), origin: "supabase", warning: null };
    } catch (error) {
      return { items: [], origin: "supabase", warning: error instanceof Error ? error.message : String(error) };
    }
  }
  try {
    return { items: listTakedowns(), origin: "demonstration", warning: null };
  } catch (error) {
    return { items: [], origin: "demonstration", warning: error instanceof Error ? error.message : String(error) };
  }
}
