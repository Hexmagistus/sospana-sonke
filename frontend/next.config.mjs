/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Lint is run separately; don't fail production builds on lint.
  eslint: { ignoreDuringBuilds: true },
};

export default nextConfig;
