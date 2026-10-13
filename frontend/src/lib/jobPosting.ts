/** Schema.org JobPosting built only from fields the scanner stored. */

export type PublicJob = {
  id: string;
  company_id?: string;
  title: string;
  company_name: string;
  company_country: string;
  location: string | null;
  country: string | null;
  employment_type: string | null;
  work_mode: string | null;
  salary: string | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  posting_date: string | null;
  closing_date: string | null;
  first_seen_at: string;
  last_seen_at: string;
  application_url: string | null;
  is_open: boolean;
  opportunity_type?: string | null;
  verified_at?: string | null;
  /** Plain text from the stored advert, when the detail page has it. */
  summary?: string | null;
};

const SITE = "https://sospana-sonke.vercel.app";

function schemaEmployment(raw: string | null | undefined): string | undefined {
  if (!raw) return undefined;
  const value = raw.toLowerCase();
  if (value.includes("intern")) return "INTERN";
  if (value.includes("part")) return "PART_TIME";
  if (value.includes("contract")) return "CONTRACTOR";
  if (value.includes("temp") || value.includes("casual")) return "TEMPORARY";
  if (value.includes("volunteer")) return "VOLUNTEER";
  if (value.includes("full") || value.includes("permanent")) return "FULL_TIME";
  return undefined;
}

function salaryUnit(text: string | null): "HOUR" | "MONTH" | "YEAR" | undefined {
  if (!text) return undefined;
  const value = text.toLowerCase();
  if (value.includes("hour")) return "HOUR";
  if (value.includes("year") || value.includes("annum") || /\bpa\b/.test(value)) return "YEAR";
  if (value.includes("month") || /\bpm\b/.test(value)) return "MONTH";
  return undefined;
}

export function jobSummary(job: PublicJob): string {
  const place = job.country || job.company_country;
  const parts = [
    `${job.title} at ${job.company_name}.`,
    job.location ? `Location: ${job.location}.` : null,
    place ? `Country: ${place}.` : null,
    job.employment_type ? `Employment type: ${job.employment_type}.` : null,
    job.work_mode ? `Work mode: ${job.work_mode}.` : null,
    job.salary ? `Pay as published: ${job.salary}.` : null,
    job.opportunity_type && job.opportunity_type !== "job"
      ? `Type: ${job.opportunity_type.replace(/_/g, " ")}.`
      : null,
    "Apply on the source page. Sospana Sonke does not take the application.",
  ];
  return parts.filter((part): part is string => Boolean(part)).join(" ");
}

/** One JobPosting node. Salary and dates are omitted when the source has none. */
export function jobPosting(job: PublicJob): Record<string, unknown> {
  const place = job.country || job.company_country;
  const address: Record<string, unknown> = { "@type": "PostalAddress", addressCountry: place };
  if (job.location) address.addressLocality = job.location;
  const description = job.summary?.trim()
    ? `${job.summary.trim()} Apply on the source page. Sospana Sonke does not take the application.`
    : jobSummary(job);
  const node: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "JobPosting",
    title: job.title,
    description,
    datePosted: job.posting_date || job.first_seen_at.slice(0, 10),
    hiringOrganization: { "@type": "Organization", name: job.company_name },
    jobLocation: { "@type": "Place", address },
    directApply: false,
    url: `${SITE}/jobs/${job.id}`,
    identifier: { "@type": "PropertyValue", name: "Sospana Sonke", value: job.id },
  };
  if (job.closing_date) node.validThrough = job.closing_date;
  const employment = schemaEmployment(job.employment_type);
  if (employment) node.employmentType = employment;
  const unit = salaryUnit(job.salary);
  if (unit && (job.salary_min != null || job.salary_max != null)) {
    const value: Record<string, unknown> = { "@type": "QuantitativeValue", unitText: unit };
    if (job.salary_min != null) value.minValue = job.salary_min;
    if (job.salary_max != null) value.maxValue = job.salary_max;
    const salary: Record<string, unknown> = { "@type": "MonetaryAmount", value };
    if (job.salary_currency) salary.currency = job.salary_currency;
    node.baseSalary = salary;
  }
  return node;
}
