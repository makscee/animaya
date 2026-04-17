/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  poweredByHeader: false,
  experimental: {
    // Nonce-based CSP via middleware (Plan 04). No runtime config here.
  },
};
export default nextConfig;
