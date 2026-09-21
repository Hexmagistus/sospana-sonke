import Link from "next/link";
import { Card } from "@/components/ui";

export const metadata = { title: "Terms of Service — Sospana Sonke" };

export default function TermsPage() {
  return (
    <div className="mx-auto mt-8 max-w-3xl">
      <Card>
        <h1 className="mb-1 text-2xl font-bold text-brand">Terms of Service</h1>
        <p className="mb-6 text-sm text-ss-muted">Last updated: 20 September 2026</p>
        <div className="space-y-4 text-sm leading-relaxed text-ss-text">
          <p>
            These terms govern your use of Sospana Sonke (the &quot;Service&quot;). By creating an
            account or using the Service, you agree to them.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-ss-text">What the Service does</h2>
          <p>
            Sospana Sonke helps you discover job vacancies across Southern Africa and apply directly
            to employers. We are a discovery and application tool — we are not an employer, agency,
            or recruiter, and we do not guarantee any job, interview, or outcome.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-ss-text">Your account</h2>
          <p>
            You are responsible for the accuracy of the information you provide and for keeping your
            login secure. You may sign in with email and password or with your Google account. You
            must be legally allowed to work where you apply.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-ss-text">Acceptable use</h2>
          <p>
            Use the Service lawfully and honestly. Do not submit false information, misuse other
            people&apos;s data, attempt to disrupt or gain unauthorised access to the Service, or use
            it to send spam or unlawful content.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-ss-text">Messaging between members</h2>
          <p>
            Messaging is optional and temporary: messages are deleted after 24 hours. You must not use it
            to harass, threaten or deceive anyone, to ask for money or payment for a job, to collect
            personal information, to advertise, or to send spam. Do not share other people&apos;s personal
            information. We may block messages automatically, keep a reported message for review, and
            suspend messaging or accounts that break these rules. Never pay anyone to obtain a job.
            Report anything suspicious using the Report button on the message.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-ss-text">Community tips</h2>
          <p>
            Tips under employer links must be truthful, short and useful to other job-seekers. Do not
            post insults, personal information, links, contact details, adverts, or requests for money.
            Tips are opinions of members, not verified by us. We may hide or remove tips and suspend members
            who break these rules.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-ss-text">Employer links and content</h2>
          <p>
            Vacancy details and links to employer careers pages are provided for convenience. We do
            our best to keep them accurate but cannot guarantee that every listing is current or that
            an external site is available. Your application and any hiring decision are between you and
            the employer.
          </p>
          <p>
            Employer, university, college, hospital and public-body names, logos and trade marks belong
            to their owners and are used only to identify them. Sospana Sonke is independent and is not
            affiliated with, sponsored by or endorsed by any listed organisation, including those grouped
            under &quot;BRICS partners&quot;. We link to vacancy pages rather than copying job adverts, and
            we do not permit bulk copying (scraping) of our curated directory.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-ss-text">Availability and changes</h2>
          <p>
            The Service is provided &quot;as is&quot;, and may change or be interrupted from time to
            time. To the extent permitted by law, we are not liable for indirect or consequential loss
            arising from your use of the Service. We may update these terms; continued use means you
            accept the current version.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-ss-text">Contact</h2>
          <p>
            Questions about these terms? Email{" "}
            <a className="text-brand hover:underline" href="mailto:gastricl@gmail.com">gastricl@gmail.com</a>.
          </p>
        </div>
        <p className="mt-6 text-sm">
          <Link href="/" className="text-brand hover:underline">← Back to home</Link>
        </p>
      </Card>
    </div>
  );
}
