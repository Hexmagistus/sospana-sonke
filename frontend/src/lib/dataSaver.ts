// Data saver: skips external logo downloads so browsing costs far less mobile data.
const KEY = "ss-data-saver";
export const DATA_SAVER_EVENT = "ss-data-saver-changed";

export function isDataSaver(): boolean {
  try {
    const v = window.localStorage.getItem(KEY);
    if (v !== null) return v === "1";
    const conn = (navigator as Navigator & { connection?: { saveData?: boolean } }).connection;
    return !!conn?.saveData;
  } catch {
    return false;
  }
}

export function setDataSaver(on: boolean) {
  try { window.localStorage.setItem(KEY, on ? "1" : "0"); } catch { /* ignore */ }
  window.dispatchEvent(new Event(DATA_SAVER_EVENT));
}
