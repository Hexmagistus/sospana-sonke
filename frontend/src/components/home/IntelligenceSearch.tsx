"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { API_BASE } from "@/lib/api";
import CountOutboundLink from "@/components/CountOutboundLink";
import { privacyHeaders } from "@/lib/usageSignal";

/**
 * Example questions that returned stored roles from the public jobs API on
 * 11 October 2026: nursing in South Africa (63), intern (301), learnership (30),
 * Mediclinic (80). They are filters, not a claim that the same count is still there.
 */
const EXAMPLES = [
  "Nursing jobs in South Africa",
  "Internships in South Africa",
  "Learnerships in South Africa",
  "Open roles at Mediclinic",
  "Unemployment in Limpopo",
];

type Employer = {
  id: string;
  company_name: string;
  country: string;
  source_type: string;
  careers_url: string | null;
  last_checked: string | null;
  url_looks_like_careers: boolean | null;
  open_vacancies: number;
  open_vacancies_known: boolean;
};

type Vacancy = {
  id: string;
  company_id?: string;
  title: string;
  company_name: string;
  company_country: string;
  location: string | null;
  application_url: string | null;
  first_seen_at: string;
  last_seen_at: string;
  closing_date: string | null;
};

type Citation = {
  publisher: string;
  title: string;
  url: string;
  licence_url: string;
  release_date: string;
  table: string;
  place: string;
  series: string;
  points: { period: string; label: string; rate: string }[];
};

type Answer = {
  llm: string;
  enough_data: boolean;
  summary: string;
  reading: string;
  limitations: string[];
  follow_ups: string[];
  vacancies: Vacancy[];
  vacancy_count: number;
  employers: Employer[];
  employer_count: number;
  counted_at: string;
  citation?: Citation | null;
};

function day(value: string | null | undefined): string | null {
  if (!value) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value.slice(0, 10);
  return parsed.toLocaleDateString("en-ZA", { day: "numeric", month: "short", year: "numeric" });
}

function roleLine(employer: Employer): string {
  if (employer.open_vacancies > 0) {
    const word = employer.open_vacancies === 1 ? "role" : "roles";
    return `${employer.open_vacancies} open ${word} stored`;
  }
  if (employer.open_vacancies_known) return "0 open roles stored";
  return "Open roles not counted yet";
}

function checkLine(employer: Employer): string {
  const when = day(employer.last_checked);
  if (employer.url_looks_like_careers === true && when) {
    return `URL check on ${when} recorded this as a careers page`;
  }
  if (employer.url_looks_like_careers === false && when) {
    return `URL check on ${when} did not record this as a careers page`;
  }
  if (when) return `Last checked ${when}`;
  return "No URL check recorded yet";
}

export default function IntelligenceSearch({ showAccountLinks = true }: { showAccountLinks?: boolean }) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [answer, setAnswer] = useState<Answer | null>(null);

  async function run(text: string) {
    const q = text.trim();
    setQuestion(text);
    if (!q) {
      setAnswer(null);
      setError("Type a question. The examples below are ones this search can run.");
      return;
    }
    setLoading(true);
    setError(null);
    setAnswer(null);
    try {
      const res = await fetch(`${API_BASE}/intelligence/search?q=${encodeURIComponent(q)}`, {
        cache: "no-store",
        credentials: "omit",
        headers: privacyHeaders(typeof navigator === "undefined" ? null : navigator),
      });
      if (res.status === 429) {
        setAnswer(null);
        setError("Too many searches from this network. Wait a minute and try again.");
        return;
      }
      if (!res.ok) {
        setAnswer(null);
        setError("The directory is not answering, so there is no result. Nothing here was guessed.");
        return;
      }
      const data = (await res.json()) as Answer;
      if (!data || typeof data.summary !== "string" || !Array.isArray(data.vacancies)) {
        setAnswer(null);
        setError("The directory is not answering, so there is no result. Nothing here was guessed.");
        return;
      }
      setAnswer(data);
    } catch {
      setAnswer(null);
      setError("The directory is not answering, so there is no result. Nothing here was guessed.");
    } finally {
      setLoading(false);
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void run(question);
  }

  return (
    <section aria-label="Sospana Intelligence" className="ss-intel-card mt-8">
      <p className="text-xs font-bold uppercase tracking-widest" style={{ color: "var(--ss-intel-teal-deep)" }}>
        Sospana Intelligence
      </p>
      <form role="search" onSubmit={onSubmit} className="mt-3">
        <label htmlFor="ss-intel-q" className="block text-base font-semibold" style={{ color: "var(--ss-intel-ink)" }}>
          What opportunity, trend or question do you want to explore?
        </label>
        <div className="mt-3 flex flex-col gap-2 sm:flex-row">
          <input
            id="ss-intel-q"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            maxLength={200}
            placeholder="Nursing jobs in South Africa"
            className="min-w-0 flex-1 rounded-xl border px-3.5 py-2.5 text-base"
            style={{
              borderColor: "rgba(12, 27, 51, 0.2)",
              background: "#ffffff",
              color: "var(--ss-intel-ink)",
            }}
          />
          <button type="submit" className="ss-intel-button" disabled={loading}>
            {loading ? "Searching" : "Search"}
          </button>
        </div>
      </form>

      <div className="mt-3 flex flex-wrap gap-2">
        {EXAMPLES.map((example) => (
          <button
            key={example}
            type="button"
            onClick={() => void run(example)}
            className="rounded-full border px-3 py-1.5 text-left text-sm font-medium"
            style={{
              borderColor: "rgba(12, 27, 51, 0.2)",
              color: "var(--ss-intel-ink)",
              background: "#ffffff",
            }}
          >
            {example}
          </button>
        ))}
      </div>

      <div aria-live="polite" aria-busy={loading} className="mt-4">
        {loading ? (
          <p className="text-sm" style={{ color: "var(--ss-intel-card-muted)" }}>
            Searching the roles and employers we have stored.
          </p>
        ) : null}
        {error ? (
          <p className="text-sm font-semibold" style={{ color: "var(--ss-intel-ink)" }} role="status">
            {error}
          </p>
        ) : null}
        {answer ? <AnswerBody answer={answer} onFollowUp={(next) => void run(next)} /> : null}
      </div>

      {showAccountLinks ? (
        <p className="mt-5 flex flex-wrap gap-x-4 gap-y-2 text-sm font-semibold">
          <Link href="/register" style={{ color: "var(--ss-intel-teal-deep)" }}>
            Create your free account
          </Link>
          <Link href="/companies" style={{ color: "var(--ss-intel-teal-deep)" }}>
            Browse companies
          </Link>
          <Link href="/jobs" style={{ color: "var(--ss-intel-teal-deep)" }}>
            Search stored roles
          </Link>
        </p>
      ) : null}
    </section>
  );
}

function AnswerBody({ answer, onFollowUp }: { answer: Answer; onFollowUp: (question: string) => void }) {
  const counted = day(answer.counted_at);
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-bold" style={{ color: "var(--ss-intel-ink)" }}>
          {answer.citation
            ? "From the stored labour table"
            : answer.enough_data
              ? "From the directory and the stored roles"
              : "Not enough data"}
        </h2>
        <p className="mt-2 text-base leading-relaxed" style={{ color: "var(--ss-intel-ink)" }}>
          {answer.summary}
        </p>
        <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--ss-intel-card-muted)" }}>
          {answer.reading}
          {counted ? ` Counted ${counted}.` : ""}
          {answer.llm === "disabled" ? " Language model: off." : ""}
        </p>
      </div>

      {answer.citation ? (
        <div>
          <h3 className="text-base font-bold" style={{ color: "var(--ss-intel-ink)" }}>
            {answer.citation.place}
          </h3>
          <table className="mt-2 w-full border-collapse text-left text-sm">
            <caption className="sr-only">
              {answer.citation.series === "expanded" ? "Combined rate" : "Official unemployment rate"} for {answer.citation.place}
            </caption>
            <thead>
              <tr>
                {answer.citation.points.map((point) => (
                  <th key={point.period} scope="col" className="py-1 pr-3 font-semibold" style={{ color: "var(--ss-intel-ink)" }}>
                    {point.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr>
                {answer.citation.points.map((point) => (
                  <td key={point.period} className="py-1 pr-3 tabular-nums" style={{ color: "var(--ss-intel-ink)" }}>
                    {point.rate}%
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
          <p className="mt-2 text-sm" style={{ color: "var(--ss-intel-card-muted)" }}>
            {answer.citation.publisher}. {answer.citation.title}. {answer.citation.table}. Released {answer.citation.release_date}.{" "}
            <a className="font-semibold underline" style={{ color: "var(--ss-intel-teal-deep)" }} href={answer.citation.url}>
              Statistical release
            </a>
            {" · "}
            <Link href="/data" className="font-semibold underline" style={{ color: "var(--ss-intel-teal-deep)" }}>
              Full table
            </Link>
          </p>
        </div>
      ) : null}

      {answer.vacancies.length > 0 ? (
        <div>
          <h3 className="text-base font-bold" style={{ color: "var(--ss-intel-ink)" }}>
            Stored roles ({answer.vacancy_count.toLocaleString("en-ZA")} match
            {answer.vacancies.length < answer.vacancy_count ? `, showing ${answer.vacancies.length}` : ""})
          </h3>
          <ul className="mt-2 grid gap-2">
            {answer.vacancies.map((role) => (
              <li key={role.id} className="rounded-xl border bg-white px-3 py-3" style={{ borderColor: "rgba(12, 27, 51, 0.14)" }}>
                <p className="font-semibold" style={{ color: "var(--ss-intel-ink)" }}>{role.title}</p>
                <p className="mt-1 text-sm" style={{ color: "var(--ss-intel-card-muted)" }}>
                  {role.company_id ? (
                    <Link href={`/employers/${role.company_id}`} className="font-semibold underline" style={{ color: "var(--ss-intel-teal-deep)" }}>
                      {role.company_name}
                    </Link>
                  ) : role.company_name}
                  {role.company_country ? ` · ${role.company_country}` : ""}
                  {role.location ? ` · ${role.location}` : ""}
                </p>
                <p className="mt-1 text-sm" style={{ color: "var(--ss-intel-card-muted)" }}>
                  Last seen on the employer site {day(role.last_seen_at)}
                  {role.first_seen_at ? `. First seen ${day(role.first_seen_at)}` : ""}
                  {role.closing_date ? `. Closes ${role.closing_date}` : ""}
                </p>
                {role.application_url ? (
                  <CountOutboundLink
                    href={role.application_url}
                    targetKind="vacancy"
                    targetId={role.id}
                    className="mt-2 inline-flex min-h-11 items-center text-sm font-semibold underline"
                    style={{ color: "var(--ss-intel-teal-deep)" }}
                  >
                    Open on the employer site
                  </CountOutboundLink>
                ) : (
                  <p className="mt-2 text-sm" style={{ color: "var(--ss-intel-card-muted)" }}>
                    No application link was stored for this role.
                  </p>
                )}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {answer.employers.length > 0 ? (
        <div>
          <h3 className="text-base font-bold" style={{ color: "var(--ss-intel-ink)" }}>
            Employers ({answer.employer_count.toLocaleString("en-ZA")} match
            {answer.employers.length < answer.employer_count ? `, showing ${answer.employers.length}` : ""})
          </h3>
          <ul className="mt-2 grid gap-2">
            {answer.employers.map((employer) => (
              <li
                key={`${employer.company_name}-${employer.country}`}
                className="rounded-xl border bg-white px-3 py-3"
                style={{ borderColor: "rgba(12, 27, 51, 0.14)" }}
              >
                <p className="font-semibold" style={{ color: "var(--ss-intel-ink)" }}>
                  {employer.careers_url ? (
                    <Link href={`/employers/${employer.id}`} className="underline" style={{ color: "var(--ss-intel-ink)" }}>
                      {employer.company_name}
                    </Link>
                  ) : employer.company_name}
                  <span className="font-medium" style={{ color: "var(--ss-intel-card-muted)" }}>
                    {" "}· {employer.country} · {employer.source_type}
                  </span>
                </p>
                <p className="mt-1 text-sm" style={{ color: "var(--ss-intel-card-muted)" }}>
                  {roleLine(employer)}. {checkLine(employer)}.
                </p>
                {employer.careers_url ? (
                  <CountOutboundLink
                    href={employer.careers_url}
                    targetKind="employer"
                    targetId={employer.id}
                    className="mt-2 inline-flex min-h-11 items-center text-sm font-semibold underline"
                    style={{ color: "var(--ss-intel-teal-deep)" }}
                  >
                    Careers page
                  </CountOutboundLink>
                ) : (
                  <p className="mt-2 text-sm" style={{ color: "var(--ss-intel-card-muted)" }}>No careers link stored.</p>
                )}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {answer.follow_ups.length > 0 ? (
        <div>
          <h3 className="text-sm font-bold" style={{ color: "var(--ss-intel-ink)" }}>
            Narrower questions that still match something we stored
          </h3>
          <div className="mt-2 flex flex-wrap gap-2">
            {answer.follow_ups.map((follow) => (
              <button
                key={follow}
                type="button"
                onClick={() => onFollowUp(follow)}
                className="rounded-full border px-3 py-1.5 text-left text-sm font-medium"
                style={{ borderColor: "rgba(12, 27, 51, 0.2)", color: "var(--ss-intel-ink)", background: "#ffffff" }}
              >
                {follow}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      <ul className="grid gap-1 text-sm leading-relaxed" style={{ color: "var(--ss-intel-card-muted)" }}>
        {answer.limitations.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
    </div>
  );
}
