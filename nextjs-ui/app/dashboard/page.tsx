import { DashboardLayout } from "@/components/dashboard/DashboardLayout";

/**
 * Dashboard Home Page
 *
 * Displays overview metrics and stats cards with Liquid Glass design
 *
 * Reference: tech-spec Section 2.3.1
 */
export default function DashboardPage() {
  return (
    <DashboardLayout>
      <div className="space-y-6">
        <h2 className="text-h2 font-bold text-text-primary">Dashboard</h2>

        {/* Stats Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="glass-card p-6">
            <div className="text-caption text-text-secondary mb-2">
              Active Agents
            </div>
            <div className="text-h2 font-bold text-text-primary">12</div>
            <div className="text-small text-accent-green mt-2">+2 from last week</div>
          </div>

          <div className="glass-card p-6">
            <div className="text-caption text-text-secondary mb-2">
              Executions Today
            </div>
            <div className="text-h2 font-bold text-text-primary">48</div>
            <div className="text-small text-accent-blue mt-2">32 successful</div>
          </div>

          <div className="glass-card p-6">
            <div className="text-caption text-text-secondary mb-2">
              Avg Response Time
            </div>
            <div className="text-h2 font-bold text-text-primary">1.2s</div>
            <div className="text-small text-accent-green mt-2">-0.3s from avg</div>
          </div>

          <div className="glass-card p-6">
            <div className="text-caption text-text-secondary mb-2">
              Error Rate
            </div>
            <div className="text-h2 font-bold text-text-primary">2.1%</div>
            <div className="text-small text-accent-orange mt-2">Monitor closely</div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="glass-card p-6">
          <h3 className="text-h3 font-semibold text-text-primary mb-4">
            Recent Activity
          </h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 rounded-lg hover:bg-white/30 transition-colors">
              <div>
                <div className="text-sm font-medium text-text-primary">
                  Agent &quot;Customer Support Bot&quot; executed successfully
                </div>
                <div className="text-small text-text-secondary">2 minutes ago</div>
              </div>
              <span className="px-2 py-1 rounded-md bg-accent-green/20 text-accent-green text-small font-medium">
                Success
              </span>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg hover:bg-white/30 transition-colors">
              <div>
                <div className="text-sm font-medium text-text-primary">
                  New prompt template created
                </div>
                <div className="text-small text-text-secondary">15 minutes ago</div>
              </div>
              <span className="px-2 py-1 rounded-md bg-accent-blue/20 text-accent-blue text-small font-medium">
                Info
              </span>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
