"use client";

import { useEffect, useState } from "react";
import { Spinner } from "./ui";

// A little levity for what can otherwise be an anxious silent wait: our free
// hosting tier dozes off when nobody's around, so the first request after a
// quiet spell can take a minute or two. Rotates so a longer wait doesn't just
// repeat the same line at you. Shared by Guard (the auth check on every
// guarded page) and any page-level fetch that can hit the same cold start
// (Companies, Universities, Coverage, …).
const LOADING_JOKES = [
  "This can take 1–2 minutes if our server dozed off. It's not ignoring you, it's just introverted.",
  "Still here — putting the kettle on is a great use of the next minute or so.",
  "Waking the server up. It's not a morning person either.",
  "Almost there. Good things (and cold-start servers) take a little time.",
];

export function FunSpinner({ label }: { label?: string }) {
  const [joke, setJoke] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setJoke((j) => (j + 1) % LOADING_JOKES.length), 8000);
    return () => clearInterval(id);
  }, []);
  return (
    <div className="p-8 text-center">
      <Spinner label={label} />
      <p className="mx-auto mt-3 max-w-xs text-xs text-gray-400">{LOADING_JOKES[joke]}</p>
    </div>
  );
}
