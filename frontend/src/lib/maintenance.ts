/**
 * TEMPORARY maintenance-mode flag (Neon DB outage, Oct 2026).
 * While true, the public South Africa careers directory (/sa-careers) is live and linked from the
 * site-wide "Under maintenance" banner and the jobs page. To remove after maintenance: set this to
 * false (/sa-careers and /offline-guide then 404 and their links disappear; also drop their two links in
 * public/offline.html and their entries in public/sw.js), or delete src/app/sa-careers, src/app/offline-guide,
 * src/data/saCareers.json, scripts/build_sa_careers.py and the references to SA_CAREERS_ENABLED.
 */
export const SA_CAREERS_ENABLED = true;

/**
 * TEMPORARY: thin "visitors" strip under the maintenance banner (src/components/VisitorStrip.tsx),
 * fed by GET /api/visit (real counts from the Upstash visit store, no database). Set to false to hide
 * it everywhere; to remove fully, delete VisitorStrip.tsx, its line in src/app/layout.tsx, and the
 * GET handler in src/app/api/visit/route.ts (+ readPublicSummary in src/lib/visitStore.ts).
 */
export const VISITOR_STRIP_ENABLED = true;
