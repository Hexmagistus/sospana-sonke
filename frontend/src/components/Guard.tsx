"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Spinner } from "./ui";

// A little levity for what can otherwise be an anxious silent wait: our free
// hosting tier dozes off when nobody's around, and the first request after a
// quiet spell can take a minute or two to nudge it awake. Rotates so a longer
// wait doesn't just repeat the same line at you.
const LOADING_JOKES = [
  "This can take 1–2 minutes if our server dozed off. It's not ignoring you, it's just introverted.",
  "Still here — putting the kettle on is a great use of the next minute or so.",
  "Waking the server up. It's not a morning person either.",
  "Almost there. Good things (and cold-start servers) take a little time.",
];

export default function Guard({ children, admin = false }: { children: React.ReactNode; admin?: boolean }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [joke, setJoke] = useState(0);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
    if (!loading && user && admin && user.role !== "admin") router.replace("/companies");
  }, [loading, user, admin, router]);

  useEffect(() => {
    if (!loading) return;
    const id = setInterval(() => setJoke((j) => (j + 1) % LOADING_JOKES.length), 8000);
    return () => clearInterval(id);
  }, [loading]);

  if (loading) {
    return (
      <div className="p-8 text-center">
        <Spinner />
        <p className="mx-auto mt-3 max-w-xs text-xs text-gray-400">{LOADING_JOKES[joke]}</p>
      </div>
    );
  }
  if (!user) return null;
  if (admin && user.role !== "admin") return null;
  return <>{children}</>;
}
