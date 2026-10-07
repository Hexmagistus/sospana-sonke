"use client";

/** One explorer page for a group of directory categories: /universities, /colleges,
 * /hospitals, /ngos and /government all render this with their entry from
 * lib/explorer/categoryGroups.ts. Same split explorer (country list, map, name list
 * "Name (n)" / "Name (NCY)"), How to use card, Balungile loader and cards as the
 * other explorer pages; no ads (those live on /login only). */

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Card, Input, Button, Alert, Spinner, EmptyState } from "@/components/ui";
import { Banner } from "@/components/Banner";
import { HowToUseCard } from "@/lib/explorer/HowToUseCard";
import { guideStepsFor } from "@/lib/directoryFilters";
import { CompanyLogo, isAtsPortal } from "@/components/CompanyLogo";
import { CompanyActionsRow, NotCountedNotice, OpenVacancyCount, TrendingBadge, ShortlistStar } from "@/components/CompanyActions";
import { CompanyPreviewModal } from "@/components/CompanyPreviewModal";
import { AnimatedNumber } from "@/components/AnimatedNumber";
import { FunSpinner } from "@/components/FunSpinner";
import { COUNTRY_FLAGS } from "@/lib/countryFlags";
import { CountryExplorer, type ExplorerStats } from "@/components/CountryExplorer";
import { CategoryListPanel } from "@/lib/explorer/CategoryListPanel";
import { categoryListItems } from "@/lib/explorer/categoryList";
import { KNOWN_COUNTRY_NAMES } from "@/lib/countryCodes";
import { buildCountryRows, countryFromQuery, searchForSelection } from "@/lib/countryExplorer";
import {
  emptyStateFor, fetchGroupRows, groupByName, groupCategoryOptions, rowsInCategory, shownRows, typeBadgeFor,
  type CategoryGroup,
} from "@/lib/explorer/categoryGroups";
import { getShortlist, SHORTLIST_EVENT } from "@/lib/shortlist";
import type { Company, TrendingCompany } from "@/lib/types";

const AVATAR_GRADIENTS = [
  "from-sky to-purple",
  "from-brand to-brand-dark",
  "from-gold to-coral",
  "from-purple to-sky",
  "from-coral to-gold",
  "from-navy to-brand",
];

// A restrained pull from the Ndebele strip's palette, used as a rotating
// per-card left-edge accent so colour carries through the whole grid.
const CARD_ACCENTS = ["#e4322b", "#f5b301", "#2f9bf6", "#1a9e5f", "#ff7a1a"];

function hashCode(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h << 5) - h + s.charCodeAt(i) | 0;
  return h;
}

function GroupDirectoryInner({ group }: { group: CategoryGroup }) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const loadedOnce = useRef(false);
  const pathname = usePathname();
  const [rows, setRows] = useState<Company[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [trending, setTrending] = useState<Set<string>>(new Set());
  const [err, setErr] = useState("");
  const [q, setQ] = useState("");
  const [country, setCountry] = useState("South Africa");
  const [category, setCategory] = useState("all");
  const [shortlistOnly, setShortlistOnly] = useState(false);
  const [shortlistIds, setShortlistIds] = useState<Set<string>>(new Set());
  const [previewCompany, setPreviewCompany] = useState<Company | null>(null);
  const multi = group.types.length > 1;

  useEffect(() => {
    let cancelled = false;
    fetchGroupRows(group.group, (p) => api.get<Company[]>(p))
      .then((r) => { if (!cancelled) { setRows(r); setLoaded(true); } })
      .catch((e) => { if (!cancelled) setErr(e.message); });
    // Best-effort: a quiet directory with no watches yet just shows no badges.
    api.get<TrendingCompany[]>("/companies/trending?days=7&limit=200")
      .then((t) => { if (!cancelled) setTrending(new Set(t.map((r) => r.company_id))); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [group.group]);

  useEffect(() => {
    const sync = () => setShortlistIds(getShortlist());
    sync();
    window.addEventListener(SHORTLIST_EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(SHORTLIST_EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  // Deep link from a "Share" button elsewhere (?company=<id>), from the Coverage
  // map (?country=<code>), or to one category of the group (?type=SETA).
  useEffect(() => {
    const wanted = searchParams.get("company");
    const wantedCountry = searchParams.get("country");
    const wantedType = (searchParams.get("type") || "").toUpperCase();
    setCategory(group.types.some((t) => t.code === wantedType) ? wantedType : "all");
    if (wanted && rows.length) {
      const found = rows.find((c) => c.id === wanted);
      if (found) {
        setCountry(found.country || "South Africa");
        setQ(found.company_name);
        return;
      }
    }
    if (wantedCountry) {
      // ?country= is a short code (ZA), "all" (every country) or, in older links, the full name.
      setCountry(countryFromQuery(wantedCountry, KNOWN_COUNTRY_NAMES) ?? wantedCountry);
      setShortlistOnly(false);
    } else if (loadedOnce.current) {
      // A bare URL after the page has opened (Back/Forward): the default view.
      setCountry("South Africa");
    }
    loadedOnce.current = true;
  }, [searchParams, rows, group.types]);

  // Everything below (map, country list, stats, name list, cards) follows the chosen category.
  const inCategory = useMemo(() => rowsInCategory(rows, category), [rows, category]);

  const explorerRows = useMemo(() => {
    const employers: Record<string, number> = {};
    const withLinks: Record<string, number> = {};
    const counted: Record<string, number> = {};
    const openVacancies: Record<string, number> = {};
    for (const c of inCategory) {
      const k = c.country || "";
      if (!k) continue;
      employers[k] = (employers[k] || 0) + 1;
      if (c.careers_url) withLinks[k] = (withLinks[k] || 0) + 1;
      if (c.open_vacancies_known) counted[k] = (counted[k] || 0) + 1;
      openVacancies[k] = (openVacancies[k] || 0) + (c.open_vacancies || 0);
    }
    return buildCountryRows({ employers, withLinks, counted, openVacancies });
  }, [inCategory]);

  // Picking a country (list or map) updates the page and the address bar
  // (?country=ZA), so Back and a refresh land on the same country. "" is All countries.
  function chooseCountry(name: string) {
    setShortlistOnly(false);
    setCountry(name);
    router.push(`${pathname}${searchForSelection(window.location.search, name)}`, { scroll: false });
  }

  function chooseCategory(id: string) {
    const next = group.types.some((t) => t.code === id) ? id : "all";
    setCategory(next);
    const params = new URLSearchParams(window.location.search);
    params.delete("company");
    if (next === "all") params.delete("type"); else params.set("type", next);
    const qs = params.toString();
    router.push(`${pathname}${qs ? `?${qs}` : ""}`, { scroll: false });
  }

  const shown = useMemo(
    () => shownRows(rows, { category, country, q, shortlistOnly, shortlistIds }),
    [rows, category, country, q, shortlistOnly, shortlistIds],
  );

  function surpriseMe() {
    if (!inCategory.length) return;
    const withLinks = inCategory.filter((c) => c.careers_url);
    const pool = withLinks.length ? withLinks : inCategory;
    const pick = pool[Math.floor(Math.random() * pool.length)];
    setShortlistOnly(false);
    setQ("");
    setCountry(pick.country || "South Africa");
    setPreviewCompany(pick);
  }

  const flag = COUNTRY_FLAGS[country] || "🌍";
  const scoped = inCategory.filter((c) => !country || (c.country || "") === country);
  const explorerStats: ExplorerStats = {
    employers: scoped.length,
    withLinks: scoped.filter((c) => c.careers_url).length,
    counted: scoped.filter((c) => c.open_vacancies_known).length,
    openVacancies: scoped.reduce((n, c) => n + (c.open_vacancies || 0), 0),
  };
  const categoryOptions = multi ? groupCategoryOptions(group, rows, country) : undefined;
  const categoryLabel = category === "all" ? group.allLabel : (group.types.find((t) => t.code === category)?.label ?? group.allLabel);
  const shownNoun = (category !== "all" && group.types.find((t) => t.code === category)?.noun) || group.noun;
  const steps = guideStepsFor(multi);
  const empty = emptyStateFor(group, { shortlistOnly, q, country, category });
  const loadingLabel = `Loading ${group.noun}…`;

  if (err) return <Alert kind="error">{err}</Alert>;
  if (!loaded) {
    return (
      <div className="mx-auto w-full max-w-xl space-y-4">
        <HowToUseCard steps={steps} loading loadingLabel={loadingLabel} />
        <FunSpinner label={loadingLabel} />
      </div>
    );
  }

  return (
    <div className="relative" data-group={group.group}>
      {/* Full-page decoration: the selected country's flag, watermarked across the page */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-0 overflow-hidden">
        <span className="absolute -right-16 top-16 select-none text-[18rem] leading-none opacity-[0.06]">{flag}</span>
        <span className="absolute -left-20 top-1/2 select-none text-[15rem] leading-none opacity-[0.05]">{flag}</span>
        <span className="absolute -right-10 bottom-8 select-none text-[13rem] leading-none opacity-[0.05]">{flag}</span>
      </div>

      <div className="relative z-10 space-y-6">
        {/* Desktop (lg+) drops this hero: the logo, notice, How to use card and Surprise me move into the explorer. */}
        <div className="overflow-hidden rounded-2xl shadow-sm lg:hidden">
          <Banner
            variant="companies"
            aside={<HowToUseCard steps={steps} />}
            eyebrow={group.eyebrow}
            title={group.title}
            subtitle={
              <>
                {group.blurb}{" "}
                <strong className="text-ss-text"><AnimatedNumber value={rows.length} /></strong> {group.noun} ·{" "}
                <strong className="text-ss-text"><AnimatedNumber value={rows.filter((c) => c.careers_url).length} /></strong> with direct careers links.
              </>
            }
          >
            <Button variant="secondary" onClick={surpriseMe} disabled={!inCategory.length}>🎲 Surprise me</Button>
          </Banner>
        </div>

        <CountryExplorer
          notice={<NotCountedNotice companies={shown} />}
          howTo={<HowToUseCard steps={steps} />}
          extraActions={<Button variant="secondary" onClick={surpriseMe} disabled={!inCategory.length}>🎲 Surprise me</Button>}
          rows={explorerRows}
          selected={shortlistOnly ? "" : country}
          onSelect={chooseCountry}
          stats={explorerStats}
          noun={group.noun}
          categories={categoryOptions}
          selectedCategory={category}
          onSelectCategory={chooseCategory}
          viewLabel={`View all ${group.noun}`}
          onView={() => {
            setShortlistOnly(false);
            document.getElementById("explorer-results")?.scrollIntoView({ behavior: "smooth", block: "start" });
          }}
          mapList={
            country && !shortlistOnly ? (
              <CategoryListPanel
                items={categoryListItems(inCategory.filter((c) => (c.country || "") === country))}
                category={categoryLabel}
                country={country}
                noun="employers"
              />
            ) : null
          }
        />

        <Card>
          <div className="mb-3 flex flex-wrap items-center gap-2 border-b border-ss-border pb-3">
            <p className="min-w-[12rem] flex-1 text-xs text-ss-muted">
              {country ? `Showing ${flag} ${country}.` : "All countries. Pick one in the list or on the map to narrow it."}
              {multi && category !== "all" ? ` Category: ${categoryLabel}.` : ""}
            </p>
            <button
              onClick={() => setShortlistOnly((v) => !v)}
              className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-semibold transition ${
                shortlistOnly ? "bg-gold text-navy shadow-sm" : "bg-ss-border text-ss-muted hover:bg-ss-primary-soft hover:text-ss-text"
              }`}
            >
              ⭐ My shortlist
              <span className={`rounded-full px-1.5 py-0.5 text-xs font-bold tabular-nums ${
                shortlistOnly ? "bg-navy/15 text-navy" : "bg-ss-surface text-ss-muted"
              }`}>{shortlistIds.size}</span>
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="min-w-0 flex-1 sm:min-w-[14rem]">
              <Input
                placeholder={`Search ${group.searchNoun}…`}
                aria-label={`Search ${group.searchNoun}`}
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
            </div>
          </div>
        </Card>

        <p id="explorer-results" className="scroll-mt-24 text-sm text-ss-muted">
          Showing <strong className="text-ss-text">{shown.length}</strong> of{" "}
          {shortlistOnly ? shortlistIds.size : scoped.length} {shortlistOnly ? `shortlisted ${group.noun}` : (country ? `${shownNoun} in ${country}` : `${shownNoun} in every country`)}.
        </p>

        <div className="empty:hidden lg:hidden"><NotCountedNotice companies={shown} /></div>

        <div className="grid gap-3 md:grid-cols-2" data-testid="group-results">
          {shown.map((c) => {
            const accent = CARD_ACCENTS[Math.abs(hashCode(c.id)) % CARD_ACCENTS.length];
            const badge = typeBadgeFor(group, c.source_type);
            return (
              <div
                key={c.id}
                onClick={() => setPreviewCompany(c)}
                style={{ borderLeftColor: accent }}
                className="relative min-w-0 cursor-pointer rounded-2xl border border-ss-border border-l-4 bg-ss-surface p-5 shadow-[0_1px_2px_rgba(16,24,40,0.04),0_1px_3px_rgba(16,24,40,0.06)] transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
              >
                <div className="absolute right-3 top-3" onClick={(e) => e.stopPropagation()}>
                  <ShortlistStar companyId={c.id} />
                </div>
                <div className="flex items-start justify-between gap-3 pr-6">
                  <div className="flex min-w-0 items-start gap-3">
                    <CompanyLogo
                      id={c.id}
                      hasIcon={!!c.has_icon}
                      iconVersion={c.icon_version}
                      name={c.company_name}
                      website={c.official_website}
                      careersUrl={c.careers_url}
                      country={c.country}
                      gradient={AVATAR_GRADIENTS[Math.abs(hashCode(c.id)) % AVATAR_GRADIENTS.length]}
                    />
                    <div className="min-w-0">
                      <div className="break-words font-semibold text-ss-text">{c.company_name}</div>
                      <div className="mt-1 flex flex-wrap items-center gap-1">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${badge.cls}`}>{badge.label}</span>
                        {isAtsPortal(c.careers_url) && (
                          <span className="rounded-full bg-navy/10 px-2 py-0.5 text-xs font-semibold text-ss-text">Apply on their portal</span>
                        )}
                        {trending.has(c.id) && <TrendingBadge />}
                        {c.country && <span className="text-xs text-ss-muted">{c.country}</span>}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-3 flex flex-wrap items-center gap-3 border-t border-ss-border pt-3 text-xs">
                  {c.careers_url && (
                    <>
                      <OpenVacancyCount company={c} />
                      <span className="text-ss-border">·</span>
                    </>
                  )}
                  <span className={c.careers_url ? "font-semibold text-brand-dark" : "text-ss-muted"}>
                    {c.careers_url ? "Direct careers link active ✓" : "No careers page yet"}
                  </span>
                </div>

                <div className="mt-3 flex flex-wrap items-stretch gap-3" onClick={(e) => e.stopPropagation()}>
                  {c.careers_url ? (
                    <a href={c.careers_url} target="_blank" rel="noopener noreferrer" className="self-center">
                      <Button>View vacancies →</Button>
                    </a>
                  ) : (
                    <span className="whitespace-nowrap text-xs text-ss-muted">No careers page yet</span>
                  )}
                </div>

                <div onClick={(e) => e.stopPropagation()}>
                  <CompanyActionsRow company={c} shareBasePath={group.path} />
                </div>
              </div>
            );
          })}
          {shown.length === 0 && (
            <div className="md:col-span-2">
              <EmptyState icon={empty.icon} title={empty.title} message={empty.message} />
            </div>
          )}
        </div>

        <p className="text-center text-xs text-ss-muted">
          Wondering how complete this list really is?{" "}
          <Link href="/coverage" className="font-semibold text-brand-dark hover:underline">
            See the coverage map →
          </Link>
        </p>
      </div>

      {previewCompany && (
        <CompanyPreviewModal
          company={previewCompany}
          shareBasePath={group.path}
          onClose={() => setPreviewCompany(null)}
        />
      )}
    </div>
  );
}

/** Page body for one group; the route files only pass the group name. */
export function GroupDirectoryPage({ name }: { name: CategoryGroup["group"] }) {
  const group = groupByName(name);
  return (
    <Guard>
      <Suspense fallback={<Spinner label={`Loading ${group.noun}…`} />}>
        <GroupDirectoryInner group={group} />
      </Suspense>
    </Guard>
  );
}
