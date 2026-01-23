import { printErrors, scanURLs, validateFiles, readFiles } from 'next-validate-link';
import { getTableOfContents } from 'fumadocs-core/content/toc';
import path from 'path';

async function checkLinks() {
  const files = await readFiles('content/docs/**/*.{md,mdx}');
  
  const populate: Record<string, any[]> = {};
  const populateKey = 'docs/[[...slug]]';
  populate[populateKey] = [];
  
  for (const file of files) {
    // Generate slug from file path
    // Assuming content/docs is the root for docs
    // file.path is absolute
    const relativePath = path.relative(path.join(process.cwd(), 'content/docs'), file.path);
    
    // Remove extension
    let slugPath = relativePath.replace(/\.(mdx?|md)$/, '');
    
    // Handle index
    if (slugPath === 'index') {
      slugPath = '';
    } else if (slugPath.endsWith('/index')) {
      slugPath = slugPath.slice(0, -6);
    }
    
    const slug = slugPath ? slugPath.split('/') : [];
    
    const toc = await getTableOfContents(file.content);
    const hashes = toc.map(item => item.url.slice(1));
    
    populate[populateKey].push({
      value: {
        slug: slug
      },
      hashes
    });
  }

  const scanned = await scanURLs({
    preset: 'next',
    populate
  });

  printErrors(
    await validateFiles(files, {
      scanned,
      markdown: {
        components: {
          Card: { attributes: ['href'] },
        },
      },
      checkRelativePaths: 'as-url',
    }),
    true,
  );
}

checkLinks().catch(console.error);
