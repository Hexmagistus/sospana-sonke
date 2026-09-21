import Link from "next/link";
import { Card } from "@/components/ui";

export const metadata = { title: "Privacy Policy — Sospana Sonke" };

export default function PrivacyPage() {
  return (
    <div className="mx-auto mt-8 max-w-3xl">
      <Card>
        <h1 className="mb-1 text-2xl font-bold text-ss-text">Privacy Policy</h1>
        <p className="mb-6 text-sm text-ss-muted">Last updated: 20 September 2026</p>
        <div className="space-y-4 text-sm leading-relaxed text-ss-text">
          <p>
            Sospana Sonke (&quot;we&quot;, &quot;us&quot;) helps job seekers across Southern Africa
            discover vacancies and apply directly to employers. This policy explains what
            personal information we collect, why we collect it, and the choices you have.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-ss-text">Information we collect</h2>
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

          <h2 className="pt-2 text-lg font-semibold text-ss-text">How we use your information</h2>
          <p>
            We use it to match you to relevant vacancies, let you apply to employers, maintain
            and secure your account, and send you service messages such as email verification and
            job notifications. We do not use it for unrelated advertising.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-ss-text">When we share it</h2>
          <p>
            When you apply to an employer, the information needed for that application is shared
            with that employer. We use Google only to verify your identity when you sign in. We do
            not sell your personal information.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-ss-text">Storage and security</h2>
          <p>
            Your data is stored in a secured database, passwords are hashed, and we apply
            reasonable technical measures to protect it. No online service can be completely
            secure, but we work to keep your information safe.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-ss-text">Your choices</h2>
          <p>
            You can view and update your profile at any time, and you can ask us to delete your
            account and associated personal data by contacting us at the address below.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-ss-text">Who is responsible (POPIA)</h2>
          <p>
            Sospana Sonke is the &quot;responsible party&quot; under South Africa&apos;s Protection of
            Personal Information Act 4 of 2013 (POPIA). Our Information Officer is Lungani Tshabalala,
            reachable at <a className="text-brand hover:underline" href="mailto:gastricl@gmail.com">gastricl@gmail.com</a>.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-ss-text">Why we process your information</h2>
          <p>
            We collect only what we need for a specific purpose: creating and securing your account,
            matching you to vacancies, tailoring your CV, tracking the applications you choose to make,
            and sending service messages. We process it because you gave consent when you registered
            and because it is needed to provide the service you asked for. You may withdraw consent at
            any time by deleting your account, which does not affect processing done before then.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-ss-text">Service providers and transfers abroad</h2>
          <p>
            We use hosting and database providers (currently Vercel, Render and Neon) and Google sign-in
            to run the service. These operators may store or process data on servers outside South
            Africa. We only use providers that apply safeguards comparable to POPIA, and we do not sell
            or rent your information.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-ss-text">Community tips on employer links</h2>
          <p>
            Signed-in members can add a short tag or tip (up to 300 characters) under an employer&apos;s
            careers link, for example whether the link works. Tips are visible to every visitor of the site, including people who are not signed in, and show your first name and last initial
            only, are checked automatically (no links, contact details or requests for money), disappear
            automatically 5 days after they are posted, and are deleted when you delete your account. Other members can report a tip; tips with
            several reports are hidden until an administrator reviews them. Do not post other people&apos;s
            personal information. You can delete your own tips at any time, and they are included in your
            data download.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-ss-text">Temporary messages between members</h2>
          <p>
            Members can switch on messaging and send short text messages to one another. Messaging is off
            by default. When it is on, other members can find you by first name and last initial only; your
            email address and phone number are never shown. Every message is deleted automatically 24 hours
            after it is sent. Links, contact details and requests for money are blocked to protect members
            from scams, and messages are checked automatically for abuse. If a recipient reports a message,
            we keep a copy of it, together with the report, only so an administrator can review it, and
            delete it within 30 days. You can block any member, switch messaging off at any time, and
            download or delete your data from the Security page. We process these messages to provide the
            feature you chose to use, and to protect members from harm (POPIA conditions of lawful
            processing, including minimality and storage limitation).
          </p>

          <h2 className="pt-2 text-lg font-semibold text-ss-text">How long we keep it</h2>
          <p>
            We keep your information while your account is active. When you delete your account we delete
            or anonymise your profile, CVs and application records, except where the law requires us to
            keep something for longer.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-ss-text">Your rights</h2>
          <p>
            You may ask us to confirm what we hold about you, to correct or delete it, to stop or
            restrict processing, and to object to processing. You can download your data and delete your
            account yourself from the Security page. For anything else, email the Information Officer above and we
            will respond within a reasonable time. If you are unhappy with our response you may complain
            to the Information Regulator (South Africa) at{" "}
            <a className="text-brand hover:underline" href="https://inforegulator.org.za" target="_blank" rel="noopener noreferrer">inforegulator.org.za</a>.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-ss-text">If something goes wrong</h2>
          <p>
            If we believe your personal information has been accessed by an unauthorised person, we
            will notify you and the Information Regulator as soon as reasonably possible, as POPIA requires.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-ss-text">Employer and institution information</h2>
          <p>
            The company, university, college, hospital and public-body names and careers links on the
            platform come from publicly available sources. They are business information, not information
            about candidates. Names, logos and marks belong to their owners; their appearance here does not
            mean the organisation partners with, sponsors or endorses Sospana Sonke. Labels such as
            &quot;BRICS partner&quot; describe the country&apos;s relationship to South Africa only. If you
            represent an organisation and want a listing corrected or removed, email us.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-ss-text">Children</h2>
          <p>
            The service is for people aged 18 and over. We do not knowingly collect information from children.
          </p>

          <h2 className="pt-2 text-lg font-semibold text-ss-text">Contact</h2>
          <p>
            For any privacy question or request, email{" "}
            <a className="text-brand hover:underline" href="mailto:gastricl@gmail.com">gastricl@gmail.com</a>.
          </p>

          <p className="pt-2 text-xs text-ss-muted">
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
