import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/uv/:path*',
        destination: 'http://127.0.0.1:8000/api/uv/:path*',
      },
    ];
  },
};

export default nextConfig;
