import { source } from "@/lib/source";
import { createFromSource } from "fumadocs-core/search/server";

export const { GET } = createFromSource(source, {
  localeMap: {
    zh: {
      search: {
        threshold: 0,
        tolerance: 0,
      },
    },
    ja: {
      search: {
        threshold: 0,
        tolerance: 0,
      },
    },
  },
});
