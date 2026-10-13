import { liteDocument, liteEmployerPage } from "@/lib/litePage";
import { liteResponse } from "../../html";
import { loadLiteEmployer } from "../../load";

export const revalidate = 300;

type Props = { params: Promise<{ id: string }> };

export async function GET(_request: Request, { params }: Props): Promise<Response> {
  const { id } = await params;
  const loaded = await loadLiteEmployer(id);
  if (loaded === "down") {
    return liteResponse(liteDocument("Employer", "<h1>Employer</h1><p>The directory did not answer. No name was invented.</p>"));
  }
  if (!loaded) return liteResponse(liteEmployerPage(null));
  return liteResponse(liteEmployerPage({ id, ...loaded }));
}
