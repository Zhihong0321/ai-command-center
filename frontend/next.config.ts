import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export',
  // Disable image optimization because it requires a Node server
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
