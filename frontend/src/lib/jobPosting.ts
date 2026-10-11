/** Schema.org JobPosting built only from fields the scanner stored. */

export type PublicJob = {
  id: string;
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
};

export function jobSummary(job: PublicJob): string {
  const place = job.country || job.company_country;
  const parts = [
    `${job.title} at ${job.company_name}.`,
    job.location ? `Location: ${job.location}.` : null,
    place ? `Country: ${place}.` : null,
    job.employment_type ? `Employment type: ${job.employment_type}.` : null,
    job.work_mode ? `Work mode: ${job.work_mode}.` : null,
    job.salary ? `Pay as published: ${job.salary}.` : null,
    "Apply on the employer's site. Sospana Sonke does not take the application.",
  ];
  return parts.filter((part): part is string => Boolean(part)).join(" ");
}

/** One JobPosting node. Salary and dates are omitted when the source has none. */
export function jobPosting(job: PublicJob): Record<string, unknown> {
  const place = job.country || job.company_country;
  const address: Record<string, unknown> = { "@type": "PostalAddress", addressCountry: place };
  if (job.location) address.addressLocality = job.location;
  const node: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "JobPosting",
    title: job.title,
    description: jobSummary(job),
    datePosted: job.posting_date || job.first_seen_at.slice(0, 10),
    hiringOrganization: { "@type": "Organization", name: job.company_name },
    jobLocation: { "@type": "Place", address },
    directApply: false,
  };
  if (job.closing_date) node.validThrough = job.closing_date;
  if (job.employment_type) node.employmentType = job.employment_type;
  if (job.application_url) node.url = job.application_url;
  if (job.salary_min != null || job.salary_max != null) {
    const value: Record<string, unknown> = { "@type": "QuantitativeValue", unitText: "MONTH" };
    if (job.salary_min != null) value.minValue = job.salary_min;
    if (job.salary_max != null) value.maxValue = job.salary_max;
    const salary: Record<string, unknown> = { "@type": "MonetaryAmount", value };
    if (job.salary_currency) salary.currency = job.salary_currency;
    node.baseSalary = salary;
  }
  return node;
}
