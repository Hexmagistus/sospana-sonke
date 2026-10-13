const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

type Brand = {
  branded?: boolean;
  headline?: string | null;
  blurb?: string | null;
  contact_email?: string | null;
};

/** Shown only when Employer Pro is active. A free claim does not add a brand panel. */
export async function OrganisationBrand({ companyId }: { companyId: string }) {
  let profile: Brand | null = null;
  try {
    const res = await fetch(`${API}/organisations/brand/${encodeURIComponent(companyId)}`, {
      next: { revalidate: 60 },
    });
    if (res.ok) profile = (await res.json()) as Brand;
  } catch {
    profile = null;
  }
  if (!profile?.branded) return null;
  return (
    <section className="ss-card space-y-2">
      <h2 className="text-lg font-bold text-ss-text">From the organisation</h2>
      {profile.headline ? <p className="text-base font-semibold text-ss-text">{profile.headline}</p> : null}
      {profile.blurb ? <p className="text-sm leading-relaxed text-ss-text">{profile.blurb}</p> : null}
      {profile.contact_email ? (
        <p className="text-sm text-ss-muted">
          Contact:{" "}
          <a className="font-semibold text-navy underline" href={`mailto:${profile.contact_email}`}>
            {profile.contact_email}
          </a>
        </p>
      ) : null}
    </section>
  );
}
