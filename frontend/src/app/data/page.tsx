import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { SITE_NAME } from "@/lib/seo";

export const dynamic = "force-dynamic";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

export const metadata: Metadata = {
  title: "South African unemployment rates",
  description:
    "Official unemployment rates by province, copied from Statistics South Africa Quarterly Labour Force Survey Table E. The source, date, and limits are on the page.",
  alternates: { canonical: "/data" },
  openGraph: {
    title: `South African unemployment rates · ${SITE_NAME}`,
    description: "A sourced table from Statistics South Africa. No estimated figures.",
    url: "/data",
  },
};

type Period = { id: string; label: string; quarter: string };
type Row = { place: string; kind: string; official: string[]; expanded: string[] };
type Table = {
  loaded: boolean;
  publisher?: string;
  title?: string;
  series?: string;
  release_url?: string;
  licence_url?: string;
  release_date?: string;
  embargo?: string;
  isbn?: string;
  table?: string;
  licence?: string;
  coverage?: string;
  official_definition?: string;
  expanded_definition?: string;
  history_note?: string;
  download_permitted?: boolean;
  periods?: Period[];
  rows?: Row[];
};

async function loadTable(): Promise<Table> {
  try {
    const res = await fetch(`${API}/labour/south-africa`, { cache: "no-store" });
    if (!res.ok) return { loaded: false };
    const body = (await res.json()) as Table;
    if (!body.loaded || !body.rows?.length || !body.periods?.length) return { loaded: false };
    return body;
  } catch {
    return { loaded: false };
  }
}

function widthOf(rate: string): string {
  const value = Number(rate.replace(",", "."));
  if (!Number.isFinite(value) || value < 0) return "0%";
  return `${Math.min(value, 100)}%`;
}

export default async function LabourDataPage() {
  const table = await loadTable();
  const latest = table.periods?.[table.periods.length - 1];

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Official statistics" title="Unemployment rates in South Africa">
        <p>
          This page shows one published table. It does not explain why a rate changed, and it is not a count of
          vacancies {SITE_NAME} has stored.
        </p>
      </PageHeader>

      {!table.loaded || !latest ? (
        <div className="ss-card" role="status">
          <h2 className="text-lg font-bold text-ss-text">The labour table is not loaded</h2>
          <p className="mt-2 text-base text-ss-muted">
            No unemployment figure is shown in its place. Ask again once the stored table is available, or read the
            statistical release on the Statistics South Africa website.
          </p>
        </div>
      ) : (
        <>
          <section className="ss-card" aria-labelledby="latest-heading">
            <h2 id="latest-heading" className="text-lg font-bold text-ss-text">
              Official unemployment rate, {latest.label}
            </h2>
            <p className="mt-2 text-sm text-ss-muted">
              Each bar is the printed rate, out of 100. The number is beside the bar. The order is the order in the
              source table.
            </p>
            <ul className="mt-4 grid gap-3">
              {table.rows!.map((row) => {
                const rate = row.official[row.official.length - 1];
                return (
                  <li key={row.place} className="grid grid-cols-[9.5rem_minmax(0,1fr)] items-center gap-3">
                    <span className="text-sm font-semibold text-ss-text">{row.place}</span>
                    <span className="flex min-w-0 items-center gap-2">
                      <span className="h-3 flex-1 rounded-full bg-ss-bg" aria-hidden="true">
                        <span
                          className="block h-3 rounded-full bg-navy"
                          style={{ width: widthOf(rate) }}
                        />
                      </span>
                      <span className="w-14 shrink-0 text-right text-sm font-semibold tabular-nums text-ss-text">
                        {rate}%
                      </span>
                    </span>
                  </li>
                );
              })}
            </ul>
          </section>

          <RateTable
            id="official-heading"
            title="Official unemployment rate"
            note="People aged 15 to 64 who were not employed, actively looked for work or tried to start a business in the previous four weeks, and were available. The share is of the labour force."
            periods={table.periods!}
            rows={table.rows!}
            series="official"
          />
          <RateTable
            id="expanded-heading"
            title="Combined rate of unemployment and the potential labour force"
            note="The same table's second measure. It includes people who wanted work but were not actively looking, or who were looking and were not available. It is not the official rate."
            periods={table.periods!}
            rows={table.rows!}
            series="expanded"
          />

          <section className="ss-card space-y-3" aria-labelledby="source-heading">
            <h2 id="source-heading" className="text-lg font-bold text-ss-text">Source, date, and limits</h2>
            <dl className="grid gap-2 text-sm text-ss-text">
              <div>
                <dt className="font-semibold">Publisher</dt>
                <dd>{table.publisher}</dd>
              </div>
              <div>
                <dt className="font-semibold">Publication</dt>
                <dd>
                  {table.title}. Statistical release {table.series}. {table.table}. ISBN {table.isbn}.
                </dd>
              </div>
              <div>
                <dt className="font-semibold">Release date</dt>
                <dd>{table.embargo} ({table.release_date}).</dd>
              </div>
              <div>
                <dt className="font-semibold">Where to read it</dt>
                <dd>
                  <a className="font-semibold text-navy underline" href={table.release_url}>
                    Statistical release (PDF)
                  </a>
                  {" · "}
                  <a className="font-semibold text-navy underline" href={table.licence_url}>
                    Metadata, including the reuse terms (PDF)
                  </a>
                </dd>
              </div>
              <div>
                <dt className="font-semibold">Coverage</dt>
                <dd>{table.coverage}</dd>
              </div>
              <div>
                <dt className="font-semibold">Official rate</dt>
                <dd>{table.official_definition}</dd>
              </div>
              <div>
                <dt className="font-semibold">Combined rate</dt>
                <dd>{table.expanded_definition}</dd>
              </div>
              <div>
                <dt className="font-semibold">History</dt>
                <dd>{table.history_note}</dd>
              </div>
              <div>
                <dt className="font-semibold">Reuse</dt>
                <dd>{table.licence}</dd>
              </div>
            </dl>
            <p className="text-sm text-ss-muted">
              This page is {SITE_NAME}&apos;s own presentation of that table. The figures were copied. They were not
              calculated again. A change from one quarter to the next is not a claim about the cause.
            </p>
            <p className="text-sm text-ss-muted">
              A downloadable file is not offered. The notice permits this free display when Statistics South Africa
              is named as the source, and it forbids selling the data.
            </p>
            <p className="text-sm font-semibold">
              <Link href="/jobs" className="text-navy underline">
                Search stored vacancies
              </Link>
            </p>
          </section>
        </>
      )}
    </div>
  );
}

function RateTable({
  id, title, note, periods, rows, series,
}: {
  id: string;
  title: string;
  note: string;
  periods: Period[];
  rows: Row[];
  series: "official" | "expanded";
}) {
  return (
    <section className="ss-card" aria-labelledby={id}>
      <h2 id={id} className="text-lg font-bold text-ss-text">{title}</h2>
      <p className="mt-2 text-sm text-ss-muted">{note}</p>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[36rem] border-collapse text-left text-sm">
          <caption className="sr-only">{title}, percent, as printed</caption>
          <thead>
            <tr className="border-b border-ss-border text-ss-text">
              <th scope="col" className="py-2 pr-3 font-semibold">Place</th>
              {periods.map((period) => (
                <th key={period.id} scope="col" className="py-2 pr-3 font-semibold">
                  {period.label}
                  <span className="mt-0.5 block font-medium text-ss-muted">{period.quarter}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.place} className="border-b border-ss-border">
                <th scope="row" className="py-2 pr-3 font-semibold text-ss-text">{row.place}</th>
                {row[series].map((rate, index) => (
                  <td key={periods[index].id} className="py-2 pr-3 tabular-nums text-ss-text">{rate}%</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
