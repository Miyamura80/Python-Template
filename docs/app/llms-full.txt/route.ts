import { getLLMText, source } from "@/lib/source";
import { i18n } from "@/lib/i18n";
import { type NextRequest } from "next/server";

export const revalidate = false;

export async function GET(req: NextRequest) {
  const lang = req.nextUrl.searchParams.get("lang") ?? i18n.defaultLanguage;
  const pages = source.getPages(lang);
  const scanned = await Promise.all(pages.map(getLLMText));

  return new Response(scanned.join("\n\n"));
}
