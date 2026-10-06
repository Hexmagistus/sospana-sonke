export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  mobile_number: string | null;
  preferred_position?: string | null;
  qualification_name?: string | null;
  email_verified: boolean;
  mfa_enabled: boolean;
  role: string;
  policy_accepted_at?: string | null;
  policy_version?: string | null;
  allow_messages?: boolean;
  notify_opportunity_alerts?: boolean;
  allow_tagging?: boolean;
  preferred_post_type?: string | null;
  tagging_state?: "not_chosen" | "yes" | "no";
  preferred_post_state?: "not_chosen" | "chosen";
  alerts_state?: "not_chosen" | "yes" | "no";
  show_consent_banner?: boolean;
}

export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Dashboard {
  vacancies_open: number;
  cvs_generated: number;
  cover_letters_generated: number;
  applications_total: number;
  applications_submitted: number;
  applications_awaiting_action: number;
  interviews: number;
  offers: number;
  listings_updated_at?: string | null;
  // A one-line personalized nudge to complete the profile, referencing the
  // candidate's own "Preferred post"/"Name of qualification" registration
  // answers -- null once they've engaged with their profile.
  profile_nudge: string | null;
}

export interface CareerOption {
  title: string;
  open_vacancies: number;
}

export interface CareerFamily {
  label: string;
  matched_on: string;
  related_careers: CareerOption[];
  note: string;
}

export interface CareerExplorerResult {
  based_on: string | null;
  families: CareerFamily[];
}

export interface CVVersion {
  id: string;
  match_id: string | null;
  vacancy_id: string | null;
  label: string;
  ats_score: number | null;
  ats_breakdown: Record<string, number> | null;
  truthfulness_ok: boolean;
  created_at: string;
}

export interface AppAnswer {
  id: string;
  question: string;
  answer: string | null;
  source: string;
  is_unknown: boolean;
}

export interface AppEvent {
  id: string;
  event_type: string;
  status_from: string | null;
  status_to: string | null;
  detail: string | null;
  actor: string;
  created_at: string;
}

export interface Application {
  id: string;
  vacancy_id: string;
  match_id: string | null;
  cv_version_id: string | null;
  cover_letter_id: string | null;
  mode: string;
  status: string;
  submission_method: string | null;
  application_url: string | null;
  action_required_note: string | null;
  submitted_at: string | null;
  authorised_at: string | null;
  created_at: string;
  // Enrichment -- filled in by the backend (routes_applications.py) so the
  // list/detail pages can show a job title/company without a
  // second round-trip per row. Always present, may be null.
  vacancy_title: string | null;
  company_name: string | null;
  vacancy_location: string | null;
  answers?: AppAnswer[];
  events?: AppEvent[];
}

export interface Subscription {
  status: string;
  has_access: boolean;
  provider: string;
  amount_zar: number;
  currency: string;
  trial_end: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
}

export interface Notification {
  id: string;
  type: string;
  title: string;
  body: string;
  related_type: string | null;
  related_id: string | null;
  // http(s) listing, or a same-app path such as a mention of a company.
  link_url: string | null;
  is_read: boolean;
  created_at: string;
}

export interface AdminDashboard {
  registered_candidates: number;
  active_subscriptions: number;
  paying_subscriptions: number;
  estimated_mrr_zar: number;
  companies_total: number;
  companies_active: number;
  sources_failing: number;
  vacancies_open: number;
  vacancies_total: number;
  applications_total: number;
  applications_by_status: Record<string, number>;
  cv_versions_total: number;
}

export interface Company {
  id: string;
  company_name: string;
  jse_code: string | null;
  source_type: string;
  country: string;
  careers_url: string | null;
  official_website?: string | null;
  active: boolean;
  scraping_status: string;
  last_checked?: string | null;
  last_http_status: number | null;
  url_looks_like_careers: boolean | null;
  notes: string | null;
  content_changed_at?: string | null;
  // When this row was first added to the directory -- powers the "Recently
  // added" badge on the Companies/Universities cards (see CompanyActions.tsx).
  created_at: string;
  // Open vacancies we currently hold. 0 is a real zero from the directory
  // query, not an estimate. Absent on older cached responses.
  open_vacancies?: number;
  // False, or absent, means we have not parsed this board. A displayed 0
  // requires this flag (or a count above zero).
  open_vacancies_known?: boolean;
  // True when the API already has a favicon. Absent or false: do not call /icon.
  has_icon?: boolean;
  // Cache-buster for the icon URL (?v=). Changes when the stored icon does.
  icon_version?: number | null;
}

// One row of the "popular this week" ranking (GET /companies/trending).
export interface TrendingCompany {
  company_id: string;
  watch_count: number;
}

// ---- Notify-me subscriptions & coverage map ----

export interface Watch {
  id: string;
  company_id: string | null;
  country: string | null;
  source_type: string | null;
  active: boolean;
  created_at: string;
}

export interface CoverageRow {
  country: string;
  source_type: string;
  total: number;
  active: number;
  with_careers_url: number;
  verified_ok: number;
  pending_verification: number;
  needs_attention: number;
}

// ---- CV upload & auto-import ("system picks it up automatically") ----

export interface UploadedCv {
  id: string;
  original_filename: string;
  content_type: string;
  extension: string;
  size_bytes: number;
  is_original: boolean;
  parse_status: "uploaded" | "extracted" | "parsed" | "failed";
  parse_error: string | null;
  ai_model: string | null;
  created_at: string;
}

export interface CvStructuredSuggestion {
  cv_id: string;
  parse_status: string;
  ai_model: string | null;
  structured: Record<string, unknown> | null;
}

export interface CvApplyResult {
  skills_added: number;
  education_added: number;
  work_experience_added: number;
  certifications_added: number;
  profile_fields_filled: string[];
}

// ---- AI CV Enhancement / Job-Aligned CV Builder ("Tailor my CV to a job") ----

export interface TemplateInfo {
  id: string;
  label: string;
  description: string;
}

export interface RequirementMatch {
  text: string;
  note: string;
}

export interface JobAnalysisSummary {
  id: string;
  job_title: string;
  company_name: string | null;
  match_score: number;
  band: string;
  decision: string;
  ats_score: number | null;
  quality_score: number | null;
  readiness_score: number | null;
  readiness_label: string | null;
  template: string;
  status: string;
  date_applied: string | null;
  cv_version_id: string | null;
  cover_letter_id: string | null;
  created_at: string;
}

export interface JobAnalysisDetail extends JobAnalysisSummary {
  job_description: string;
  extracted: {
    title: string;
    seniority: string;
    keywords: string[];
    action_verbs: string[];
    industries: string[];
    requirement_counts: Record<string, number>;
    requirements: { text: string; kind: string; category: string }[];
  };
  sub_scores: Record<string, number>;
  confidence: string;
  hard_ok: boolean;
  strong_matches: RequirementMatch[];
  partial_matches: RequirementMatch[];
  missing_requirements: RequirementMatch[];
  ats_breakdown: Record<string, number> | null;
  quality_breakdown: Record<string, number> | null;
  quality_suggestions: string[] | null;
  recommended_action: string | null;
  notes: string | null;
}

export interface FactCheck {
  ok: boolean;
  violations: string[];
}

export interface CvExperience {
  employer?: string | null;
  position?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  is_current?: boolean;
  responsibilities?: string | null;
  achievements?: string | null;
  [k: string]: unknown;
}

export interface CvData {
  full_name: string;
  email?: string | null;
  phone?: string | null;
  city?: string | null;
  country?: string | null;
  linkedin_url?: string | null;
  github_url?: string | null;
  portfolio_url?: string | null;
  summary: string;
  skills: string[];
  experience: CvExperience[];
  education: Record<string, unknown>[];
  certifications: Record<string, unknown>[];
  languages: string[];
  drivers_licence?: string | null;
  target_vacancy_title?: string | null;
}

export interface AnalyzeJobResult {
  job_analysis: JobAnalysisDetail;
  draft_cv: CvData;
  fact_check: FactCheck;
}

export interface MasterCv {
  full_name: string;
  email?: string | null;
  phone?: string | null;
  current_occupation?: string | null;
  years_experience?: number | null;
  industries?: string[];
  skills: string[];
  skills_detailed?: { name: string; category: string; confirmed_by_candidate: boolean }[];
  experience: (CvExperience & { confirmed_by_candidate?: boolean })[];
  education: (Record<string, unknown> & { confirmed_by_candidate?: boolean })[];
  certifications: (Record<string, unknown> & { confirmed_by_candidate?: boolean })[];
  professional_memberships?: string[];
  languages: string[];
  [k: string]: unknown;
}

export interface Vacancy {
  id: string;
  company_id: string;
  external_id: string | null;
  title: string;
  department: string | null;
  location: string | null;
  work_mode: string | null;
  employment_type: string | null;
  salary: string | null;
  /** Best-effort fields parsed from `location`/`salary`/title at scan time — a
   * missing value just means it couldn't be inferred, never a wrong one. */
  province: string | null;
  salary_min: number | null;
  salary_max: number | null;
  nqf_level: number | null;
  trust_flags: string[] | null;
  duplicate_of_id: string | null;
  posting_date: string | null;
  closing_date: string | null;
  application_url: string | null;
  source_url: string | null;
  canonical_url?: string | null;
  city?: string | null;
  country?: string | null;
  lifecycle_status?: string | null;
  verification_state?: string | null;
  quality_score?: number | null;
  is_open: boolean;
  first_seen_at: string;
  last_seen_at: string;
}
