import type { NextConfig } from 'next';
// STATIC_EXPORT=1 builds plain files that the FastAPI container serves (see deploy/Dockerfile).
const config: NextConfig = { turbopack: { root: process.cwd() }, ...(process.env.STATIC_EXPORT ? { output: 'export' } : {}) };
export default config;
