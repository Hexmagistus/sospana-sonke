import { ImageResponse } from "next/og";
import { CLOSED_OPPORTUNITY_HEADING, loadPublicJob } from "@/lib/loadPublicJob";

export const runtime = "nodejs";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const job = await loadPublicJob(id);
  const closed = job === "closed";
  const title = closed ? CLOSED_OPPORTUNITY_HEADING : job && job !== "down" ? job.title : "Stored roles";
  const subtitle = closed ? "Sospana Sonke" : job && job !== "down" ? job.company_name : "Sospana Sonke";
  const note = closed
    ? "This opportunity has closed. It is not a live listing."
    : "Apply on the source page. Sospana Sonke does not send the application.";
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          background: "#0c1b33",
          color: "#ffffff",
          padding: 72,
        }}
      >
        <div style={{ fontSize: 28, color: "#5eead4", fontWeight: 700 }}>{subtitle}</div>
        <div style={{ fontSize: 64, fontWeight: 800, marginTop: 16, lineHeight: 1.1 }}>{title}</div>
        <div style={{ fontSize: 24, color: "#d5dde8", marginTop: 28 }}>
          {note}
        </div>
      </div>
    ),
    size,
  );
}
