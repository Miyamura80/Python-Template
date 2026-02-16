import { docs } from "fumadocs-mdx:collections/server";
import { loader } from "fumadocs-core/source";
import { i18n } from "@/lib/i18n";

export const source = loader({
  baseUrl: "/docs",
  source: docs.toFumadocsSource(),
  i18n,
});

export function getPageImage(page: ReturnType<typeof source.getPage> & {}) {
  const segments = page.url.split("/").filter(Boolean);
  return {
    url: `/og/${segments.join("/")}/og.png`,
    segments: [...segments, "og.png"],
  };
}

export async function getLLMText(
  page: ReturnType<typeof source.getPage> & {}
): Promise<string> {
  const processed = page.data.processedMarkdown;
  if (!processed) return "";
  return `# ${page.data.title}\n\n${page.data.description ?? ""}\n\n${processed}`;
}
