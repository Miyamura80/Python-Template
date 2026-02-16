import { docs } from "fumadocs-mdx:collections/server";
import { loader } from "fumadocs-core/source";
import { i18n } from "@/lib/i18n";

export const source = loader({
  baseUrl: "/docs",
  source: docs.toFumadocsSource(),
  i18n,
});

export function getPageImage(page: ReturnType<typeof source.getPage> & {}) {
  const allSegments = page.url.split("/").filter(Boolean);
  // Strip locale and "docs" prefix for the slug param (they're separate route params)
  const docSegments = allSegments.filter(
    (s) => s !== page.locale && s !== "docs",
  );
  return {
    url: `/og/${allSegments.join("/")}/og.png`,
    segments: [...docSegments, "og.png"],
  };
}

export async function getLLMText(
  page: ReturnType<typeof source.getPage> & {}
): Promise<string> {
  const processed = page.data.processedMarkdown;
  if (!processed) return "";
  return `# ${page.data.title}\n\n${page.data.description ?? ""}\n\n${processed}`;
}
