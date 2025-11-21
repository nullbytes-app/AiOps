/**
 * Loading Boundary for LLM Cost Dashboard
 *
 * Next.js 14 App Router loading.tsx boundary
 * Displays skeleton UI while page is loading
 */

import React from 'react';

export default function Loading() {
  return (
    <div className="container mx-auto py-8 space-y-6">
      {/* Header Skeleton */}
      <div className="animate-pulse">
        <div className="h-8 bg-muted/50 rounded w-64 mb-2" />
        <div className="h-4 bg-muted/50 rounded w-96" />
      </div>

      {/* Metrics Cards Skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[1, 2, 3, 4, 5].map((i) => (
          <div
            key={i}
            className="glass-card p-6 rounded-xl h-32 animate-pulse"
          >
            <div className="h-4 bg-muted/50 rounded w-24 mb-4" />
            <div className="h-8 bg-muted/50 rounded w-32" />
          </div>
        ))}
      </div>
    </div>
  );
}
