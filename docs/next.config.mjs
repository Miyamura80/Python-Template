import { createMDX } from 'fumadocs-mdx/next';

const withMDX = createMDX();

/** @type {import('next').NextConfig} */
const config = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/:lang/docs/:path*.mdx',
        destination: '/llms.mdx/:lang/docs/:path*',
      },
      {
        source: '/docs/:path*.mdx',
        destination: '/llms.mdx/en/docs/:path*',
      },
    ];
  },
};

export default withMDX(config);
