/**
 * Loading skeleton for Agent Performance page
 * Following 2025 Next.js patterns for loading states
 */

export default function Loading() {
  return (
    <div className="container mx-auto p-6">
      <div className="h-10 w-96 bg-gray-200 animate-pulse rounded mb-6" />
      <div className="h-6 w-64 bg-gray-200 animate-pulse rounded mb-8" />

      <div className="flex gap-4 mb-6">
        <div className="h-10 w-64 bg-gray-200 animate-pulse rounded" />
        <div className="h-10 w-64 bg-gray-200 animate-pulse rounded" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="h-32 bg-gray-200 animate-pulse rounded" />
        ))}
      </div>
    </div>
  );
}
