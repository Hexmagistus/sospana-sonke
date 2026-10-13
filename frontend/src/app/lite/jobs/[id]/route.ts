import { liteDocument, liteJobPage } from "@/lib/litePage";
import { liteResponse } from "../../html";
import { loadLiteJob } from "../../load";

export const revalidate = 60;

type Props = { params: Promise<{ id: string }> };

export async function GET(_request: Request, { params }: Props): Promise<Response> {
  const { id } = await params;
  const loaded = await loadLiteJob(id);
  if (loaded === "down") {
    return liteResponse(liteDocument("Role", "<h1>Role</h1><p>The stored role could not be reached. No substitute advert is shown.</p>"));
  }
  return liteResponse(liteJobPage(loaded));
}
