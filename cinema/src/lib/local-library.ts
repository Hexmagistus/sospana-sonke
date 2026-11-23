export type Progress = {
  slug: string;
  title: string;
  position: number;
  duration: number;
  updatedAt: string;
  player: "mp4" | "embed" | "hls";
};

export type LibraryState = {
  favourites: string[];
  progress: Progress[];
  searches: string[];
  country: string;
};

type StorageLike = {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
};

const KEY = "sospana-cinema-library-v1";

const empty = (): LibraryState => ({
  favourites: [],
  progress: [],
  searches: [],
  country: "South Africa",
});

export function createLibrary(storage: StorageLike) {
  function read(): LibraryState {
    try {
      const raw = storage.getItem(KEY);
      if (!raw) return empty();
      const parsed = JSON.parse(raw) as Partial<LibraryState>;
      return {
        favourites: Array.isArray(parsed.favourites) ? parsed.favourites.filter((item) => typeof item === "string") : [],
        progress: Array.isArray(parsed.progress) ? parsed.progress : [],
        searches: Array.isArray(parsed.searches) ? parsed.searches.filter((item) => typeof item === "string").slice(0, 8) : [],
        country: typeof parsed.country === "string" && parsed.country ? parsed.country : "South Africa",
      };
    } catch {
      return empty();
    }
  }

  function write(state: LibraryState) {
    storage.setItem(KEY, JSON.stringify(state));
  }

  return {
    read,
    toggleFavourite(slug: string) {
      const state = read();
      state.favourites = state.favourites.includes(slug)
        ? state.favourites.filter((item) => item !== slug)
        : [slug, ...state.favourites];
      write(state);
      return state;
    },
    saveProgress(entry: Progress) {
      const state = read();
      state.progress = [entry, ...state.progress.filter((item) => item.slug !== entry.slug)].slice(0, 20);
      write(state);
      return state;
    },
    rememberSearch(query: string) {
      const clean = query.trim();
      if (clean.length < 2) return read();
      const state = read();
      state.searches = [clean, ...state.searches.filter((item) => item.toLowerCase() !== clean.toLowerCase())].slice(0, 8);
      write(state);
      return state;
    },
    setCountry(country: string) {
      const state = read();
      state.country = country;
      write(state);
      return state;
    },
    clear() {
      storage.removeItem(KEY);
      return empty();
    },
  };
}

export function browserLibrary() {
  if (typeof window === "undefined") {
    const memory = new Map<string, string>();
    return createLibrary({
      getItem: (key) => memory.get(key) ?? null,
      setItem: (key, value) => memory.set(key, value),
      removeItem: (key) => memory.delete(key),
    });
  }
  return createLibrary(window.localStorage);
}

export const LIBRARY_KEY = KEY;
