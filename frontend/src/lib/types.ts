export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  mobile_number: string | null;
  email_verified: boolean;
  mfa_enabled: boolean;
  role: string;
}

export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Dashboard {
  subscription_status: string;
  has_access: boolean;
  plan_amount_zar: number;
  vacancies_open: number;
  total_matches: number;
  strong_matches: number;
  apply_matches: number;
  cvs_generated: number;
  cover_letters_generated: number;
  applications_total: number;
  applications_submitted: number;
  applications_awaiting_action: number;
  interviews: number;
  offers: number;
}

export interface Match {
  id: string;
  vacancy_id: string;
  vacancy_title: string | null;
  company_name: string | null;
  score: number;
  band: string;
  decision: string;
  confidence: string;
  hard_ok: boolean;
  status: string;
  created_at: string;
}

export interface MatchDetail extends Match {
  sub_scores: Record<string, number>;
  reasons: string[];
  gaps: string[];
  engine_version: string;
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
  mode: string;
  status: string;
  application_url: string | null;
  action_required_note: string | null;
  submitted_at: string | null;
  created_at: string;
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
  last_http_status: number | null;
  url_looks_like_careers: boolean | null;
  notes: string | null;
}
