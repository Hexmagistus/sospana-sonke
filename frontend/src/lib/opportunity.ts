/** Labels for a stored opportunity. Dates are shown only when the source stated them. */

export const OPPORTUNITY_TABS: { value: string; label: string }[] = [
  { value: "", label: "All" },
  { value: "job", label: "Jobs" },
  { value: "internship", label: "Internships" },
  { value: "learnership", label: "Learnerships" },
  { value: "bursary", label: "Bursaries" },
  { value: "graduate_programme", label: "Graduate programmes" },
];

const LABELS: Record<string, string> = {
  job: "Job",
  internship: "Internship",
  learnership: "Learnership",
  bursary: "Bursary",
  graduate_programme: "Graduate programme",
};

export function opportunityLabel(kind: string | null | undefined): string {
  if (!kind) return "Job";
  return LABELS[kind] || "Job";
}

export function statedDate(value: string | null | undefined): string {
  if (!value) return "not stated";
  return value.slice(0, 10);
}
