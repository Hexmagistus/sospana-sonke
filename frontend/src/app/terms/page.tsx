import Link from "next/link";
import { Card } from "@/components/ui";

export const metadata = { title: "Terms of Service — Sospana Sonke" };

export default function TermsPage() {
  return (
    <div className="mx-auto mt-8 max-w-3xl">
      <Card>
        <h1 className="mb-1 text-2xl font-bold text-brand">Terms of Service</h1>
        <p className="mb-6 text-sm text-gray-500">Last updated: 6 September 2026</p>
        <div className="space-y-4 text-sm leading-relaxed text-gray-700">
          <p>
            These terms govern your use of Sospana Sonke (the &quot;Service&quot;). By creating an
            account or using the Service, you agree to them.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-navy">What the Service does</h2>
          <p>
            Sospana Sonke helps you discover job vacancies across Southern Africa and apply directly
            to employers. We are a discovery and application tool — we are not an employer, agency,
            or recruiter, and we do not guarantee any job, interview, or outcome.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-navy">Your account</h2>
          <p>
            You are responsible for the accuracy of the information you provide and for keeping your
            login secure. You may sign in with email and password or with your Google account. You
            must be legally allowed to work where you apply.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-navy">Acceptable use</h2>
          <p>
            Use the Service lawfully and honestly. Do not submit false information, misuse other
            people&apos;s data, attempt to disrupt or gain unauthorised access to the Service, or use
            it to send spam or unlawful content.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-navy">Employer links and content</h2>
          <p>
            Vacancy details and links to employer careers pages are provided for convenience. We do
            our best to keep them accurate but cannot guarantee that every listing is current or that
            an external site is available. Your application and any hiring decision are between you and
            the employer.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-navy">Availability and changes</h2>
          <p>
            The Service is provided &quot;as is&quot;, and may change or be interrupted from time to
            time. To the extent permitted by law, we are not liable for indirect or consequential loss
            arising from your use of the Service. We may update these terms; continued use means you
            accept the current version.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-navy">Contact</h2>
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
