/**
 * RecentActivity Component
 *
 * Displays the last 20 processed tickets with status badges.
 * Provides click-through navigation to ticket details.
 */

'use client';

import React from 'react';
import { RecentTicket } from '@/lib/api/metrics';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { formatDistanceToNow } from 'date-fns';

export interface RecentActivityProps {
  tickets: RecentTicket[];
  className?: string;
  onTicketClick?: (ticketId: string) => void;
}

/**
 * Format processing time for display
 */
function formatProcessingTime(ms: number): string {
  if (ms < 1000) {
    return `${ms}ms`;
  }
  if (ms < 60000) {
    return `${(ms / 1000).toFixed(1)}s`;
  }
  return `${(ms / 60000).toFixed(1)}m`;
}

/**
 * Get badge variant for ticket status
 */
function getStatusVariant(status: RecentTicket['status']): 'success' | 'error' | 'warning' {
  switch (status) {
    case 'success':
      return 'success';
    case 'failed':
      return 'error';
    case 'pending':
      return 'warning';
    default:
      return 'warning';
  }
}

/**
 * RecentActivity Component
 *
 * @example
 * ```tsx
 * const { data } = useTicketMetrics();
 *
 * <RecentActivity
 *   tickets={data.recent_tickets}
 *   onTicketClick={(id) => router.push(`/tickets/${id}`)}
 * />
 * ```
 */
export function RecentActivity({
  tickets,
  className = '',
  onTicketClick,
}: RecentActivityProps) {
  if (tickets.length === 0) {
    return (
      <Card className={`glass-card p-6 ${className}`}>
        <h3 className="text-lg font-semibold text-foreground mb-4">
          Recent Ticket Activity
        </h3>
        <div className="flex flex-col items-center justify-center py-12">
          <div className="text-6xl mb-4" role="img" aria-label="Ticket">
            🎫
          </div>
          <p className="text-muted-foreground text-center">
            No ticket activity yet. Recent processed tickets will appear here.
          </p>
        </div>
      </Card>
    );
  }

  return (
    <Card className={`glass-card p-6 ${className}`}>
      <h3 className="text-lg font-semibold text-foreground mb-4">
        Recent Ticket Activity
      </h3>

      <div className="overflow-x-auto">
        <table className="w-full" role="table">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-3 px-4 font-semibold text-sm text-muted-foreground">
                Ticket ID
              </th>
              <th className="text-left py-3 px-4 font-semibold text-sm text-muted-foreground">
                Status
              </th>
              <th className="text-right py-3 px-4 font-semibold text-sm text-muted-foreground">
                Processing Time
              </th>
              <th className="text-right py-3 px-4 font-semibold text-sm text-muted-foreground">
                Timestamp
              </th>
            </tr>
          </thead>
          <tbody>
            {tickets.map((ticket, index) => (
              <tr
                key={`${ticket.ticket_id}-${index}`}
                className={`border-b border-border last:border-b-0 ${
                  onTicketClick
                    ? 'hover:bg-muted/50 cursor-pointer'
                    : ''
                } transition-colors`}
                onClick={() => onTicketClick?.(ticket.ticket_id)}
                role={onTicketClick ? 'button' : undefined}
                tabIndex={onTicketClick ? 0 : undefined}
                onKeyDown={(e) => {
                  if (onTicketClick && (e.key === 'Enter' || e.key === ' ')) {
                    e.preventDefault();
                    onTicketClick(ticket.ticket_id);
                  }
                }}
                aria-label={onTicketClick ? `View details for ${ticket.ticket_id}` : undefined}
              >
                <td className="py-3 px-4 font-medium text-foreground">
                  {ticket.ticket_id}
                </td>
                <td className="py-3 px-4">
                  <Badge variant={getStatusVariant(ticket.status)}>
                    {ticket.status}
                  </Badge>
                </td>
                <td className="py-3 px-4 text-right text-foreground">
                  {formatProcessingTime(ticket.processing_time_ms)}
                </td>
                <td className="py-3 px-4 text-right text-muted-foreground text-sm">
                  {formatDistanceToNow(new Date(ticket.timestamp), {
                    addSuffix: true,
                  })}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
