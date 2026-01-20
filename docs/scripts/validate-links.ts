import {
  scanURLs,
  printErrors,
  readFiles,
  validateFiles,
} from "next-validate-link";
import { glob } from "fast-glob";
import path from "path";

async function main() {
  // Find all MDX files and generate slugs from file paths
  const contentDir = path.join(process.cwd(), "content/docs");
  const mdxFiles = await glob("**/*.mdx", { cwd: contentDir });

  const slugs = mdxFiles.map((file) => {
    const slug = file.replace(/\.mdx?$/, "").replace(/\/index$/, "");
    return {
      value: slug === "index" ? [] : slug.split("/"),
    };
  });

  // Scan URLs from Next.js app router
  const scanned = await scanURLs({
    preset: "next",
    populate: {
      "docs/[[...slug]]": slugs,
    },
  });

  // Validate all MDX files in content directory
  const result = await validateFiles(
    await readFiles("content/**/*.{md,mdx}"),
    {
      scanned,
      checkExternal: false, // Set to true to also check external URLs
    }
  );

  // Print errors and exit with code 1 if any found
  printErrors(result, true);

  if (result.length === 0) {
    console.log("✓ All links are valid!");
  }
}

main().catch(console.error);
