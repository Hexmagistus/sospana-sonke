import Link from "next/link";
import { Card } from "@/components/ui";

export const metadata = { title: "Privacy Policy — Sospana Sonke" };

export default function PrivacyPage() {
  return (
    <div className="mx-auto mt-8 max-w-3xl">
      <Card>
        <h1 className="mb-1 text-2xl font-bold text-brand">Privacy Policy</h1>
        <p className="mb-6 text-sm text-gray-500">Last updated: 6 September 2026</p>
        <div className="space-y-4 text-sm leading-relaxed text-gray-700">
          <p>
            Sospana Sonke (&quot;we&quot;, &quot;us&quot;) helps job seekers across Southern Africa
            discover vacancies and apply directly to employers. This policy explains what
            personal information we collect, why we collect it, and the choices you have.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-navy">Information we collect</h2>
          <ul className="list-disc space-y-1 pl-5">
            <li>Account details you give us: your name, email address, and (optionally) mobile number.</li>
            <li>
              If you choose <strong>Continue with Google</strong>: your Google-verified email
              address and basic profile name. We never receive your Google password, and we do
              not store Google access tokens.
            </li>
            <li>
              Profile and job-matching information you add — your skills, experience, preferences,
              and any CV or documents you upload.
            </li>
            <li>Records of the jobs you view and the applications you submit through the platform.</li>
          </ul>

          <h2 className="pt-2 text-lg font-semibold text-navy">How we use your information</h2>
          <p>
            We use it to match you to relevant vacancies, let you apply to employers, maintain
            and secure your account, and send you service messages such as email verification and
            job notifications. We do not use it for unrelated advertising.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-navy">When we share it</h2>
          <p>
            When you apply to an employer, the information needed for that application is shared
            with that employer. We use Google only to verify your identity when you sign in. We do
            not sell your personal information.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-navy">Storage and security</h2>
          <p>
            Your data is stored in a secured database, passwords are hashed, and we apply
            reasonable technical measures to protect it. No online service can be completely
            secure, but we work to keep your information safe.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-navy">Your choices</h2>
          <p>
            You can view and update your profile at any time, and you can ask us to delete your
            account and associated personal data by contacting us at the address below.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-navy">Contact</h2>
          <p>
            For any privacy question or request, email{" "}
            <a className="text-brand hover:underline" href="mailto:gastricl@gmail.com">gastricl@gmail.com</a>.
          </p>

          <p className="pt-2 text-xs text-gray-400">
            We may update this policy from time to time; the current version is always available on
            this page.
          </p>
        </div>
        <p className="mt-6 text-sm">
          <Link href="/" className="text-brand hover:underline">← Back to home</Link>
        </p>
      </Card>
    </div>
  );
}
