import Link from "next/link";

export default function JobAlertsLink({ className = "" }: { className?: string }) {
  return (
    <Link href="/job-alerts" className={`block rounded-lg border border-[#07284C]/10 border-l-[6px] border-l-[#0B6575] bg-[#EEF6F7] p-4 text-[#07284C] shadow-sm transition-colors hover:bg-[#E2F0F2] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#07284C] motion-reduce:transition-none ${className}`}>
      <span className="block text-base font-bold tracking-tight sm:text-lg">🔔 Job alerts helper →</span>
      <span className="mt-1 block text-sm text-slate-700">Pick employers, register on their official portals and track your job alerts. Free, no login.</span>
    </Link>
  );
}
