/**
 * Official South African statistics shown on the homepage. Every figure was read from the
 * Stats SA release linked here (checked 4 November 2026). Do not add a number without its
 * release, period and link. Update when Stats SA publishes the next release.
 */
export type Source = { label: string; period: string; url: string };

export const QLFS: Source = {
  label: "Stats SA, Quarterly Labour Force Survey (P0211)",
  period: "Q2 2026 (Apr–Jun), released 11 Aug 2026",
  url: "https://www.statssa.gov.za/publications/P0211/P02112ndQuarter2026.pdf",
};
export const MYPE: Source = {
  label: "Stats SA, Mid-year population estimates (P0302)",
  period: "mid-2026, released 30 Jul 2026",
  url: "https://www.statssa.gov.za/publications/P0302/P03022026.pdf",
};
export const GHS: Source = {
  label: "Stats SA, General Household Survey (P0318)",
  period: "2025, released 26 May 2026",
  url: "https://www.statssa.gov.za/publications/P0318/P03182025.pdf",
};

/** National figures. */
export const NATIONAL = {
  populationMillions: 63.52, // MYPE 2026: "63,52 million people"
  employedThousands: 16739, // QLFS Q2 2026 Table A: Employed 16 739 (thousand)
  unemploymentRate: 33.6, // QLFS Q2 2026 LU1
  /** Official unemployment rate (LU1), QLFS Table A / Table E. */
  unemploymentTrend: [
    { label: "Q2 2025", value: 33.2 },
    { label: "Q1 2026", value: 32.7 },
    { label: "Q2 2026", value: 33.6 },
  ],
  /** GHS 2025 Figure 8.1 text: formal 84,2%, informal 12,1%, traditional 3,4% of households. */
  dwellings: { formal: 84.2, informal: 12.1, traditional: 3.4 },
  /** GHS 2025 section 11.1: households connected to mains electricity, 76,7% (2002) to 90,6% (2025). */
  electricity: [
    { label: "2002", value: 76.7 },
    { label: "2025", value: 90.6 },
  ],
};

/** Per province: MYPE 2026 Appendix (population) and QLFS Q2 2026 Table E (official unemployment rate). */
export const PROVINCE_OFFICIAL: Record<string, { population: number; unemployment: number }> = {
  GP: { population: 16295325, unemployment: 34.6 },
  KZN: { population: 12282836, unemployment: 32.5 },
  WC: { population: 7722158, unemployment: 19.5 },
  EC: { population: 7031109, unemployment: 47.5 },
  LP: { population: 6358667, unemployment: 32.0 },
  MP: { population: 5161746, unemployment: 36.6 },
  NW: { population: 4227795, unemployment: 38.1 },
  FS: { population: 3060972, unemployment: 37.3 },
  NC: { population: 1381772, unemployment: 28.7 },
};

/** Real Stats SA reports to read (no research of our own is claimed). */
export const READING: { title: string; blurb: string; source: Source }[] = [
  { title: "Who is working, who is looking", blurb: "Jobs, unemployment and job-seekers by province.", source: QLFS },
  { title: "How many of us, and where", blurb: "Population by province, age and migration.", source: MYPE },
  { title: "How households live", blurb: "Housing, water, electricity and other services.", source: GHS },
];
