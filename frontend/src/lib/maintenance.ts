/**
 * TEMPORARY maintenance-mode flag (Neon DB outage, Oct 2026).
 * While true, the public South Africa careers directory (/sa-careers) is live and linked from the
 * site-wide "Under maintenance" banner and the jobs page. To remove after maintenance: set this to
 * false (the page then 404s and the links disappear), or delete src/app/sa-careers,
 * src/data/saCareers.json, scripts/build_sa_careers.py and the references to SA_CAREERS_ENABLED.
 */
export const SA_CAREERS_ENABLED = true;
