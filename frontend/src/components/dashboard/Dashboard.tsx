import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Activity, ShieldCheck, ShieldAlert, Users } from "lucide-react";
import { api } from "../../services/api";
import type { ActionProposal, AgentOverview } from "../../types";
import { PageContainer } from "../layout/PageContainer";
import { formatCurrency, formatDate } from "../../utils/format";
import { StatusBadge } from "../common/Badge";

export function Dashboard() {
  const [metrics, setMetrics] = useState<any>(null);
  const [recentActions, setRecentActions] = useState<ActionProposal[]>([]);
  const [agents, setAgents] = useState<AgentOverview[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [metricsData, actionsData, agentsData] = await Promise.all([
          api.getDashboardMetrics(),
          api.getActions(),
          api.getAgents(),
        ]);
        setMetrics(metricsData);
        setRecentActions(actionsData.slice(0, 5));
        setAgents(agentsData);
      } catch (error) {
        console.error("Failed to load dashboard data", error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return <PageContainer><div className="text-slate-400">Loading dashboard...</div></PageContainer>;
  }

  return (
    <PageContainer>
      {/* Top Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="panel flex items-center gap-4">
          <div className="p-3 bg-blue-500/10 rounded-lg text-blue-400">
            <Users className="w-6 h-6" />
          </div>
          <div>
            <p className="text-sm text-slate-400">Active Agents</p>
            <p className="text-2xl font-semibold text-slate-100">{metrics?.active_agents}</p>
          </div>
        </div>
        
        <div className="panel flex items-center gap-4">
          <div className="p-3 bg-slate-500/10 rounded-lg text-slate-400">
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <p className="text-sm text-slate-400">Actions Today</p>
            <p className="text-2xl font-semibold text-slate-100">{metrics?.actions_today}</p>
          </div>
        </div>
        
        <div className="panel flex items-center gap-4">
          <div className="p-3 bg-emerald-500/10 rounded-lg text-emerald-400">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <p className="text-sm text-slate-400">Executed Actions</p>
            <p className="text-2xl font-semibold text-slate-100">{metrics?.executed_actions}</p>
          </div>
        </div>
        
        <div className="panel flex items-center gap-4">
          <div className="p-3 bg-rose-500/10 rounded-lg text-rose-400">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <p className="text-sm text-slate-400">Blocked Actions</p>
            <p className="text-2xl font-semibold text-slate-100">{metrics?.blocked_actions}</p>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Recent Actions Table */}
        <div className="panel lg:col-span-2">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-slate-100">Recent Action Proposals</h2>
            <Link to="/actions" className="text-sm text-emerald-400 hover:text-emerald-300">View all</Link>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead>
                <tr className="text-slate-400 border-b border-slate-800">
                  <th className="pb-3 font-medium">Action ID</th>
                  <th className="pb-3 font-medium">Amount</th>
                  <th className="pb-3 font-medium">Recipient</th>
                  <th className="pb-3 font-medium">Status</th>
                  <th className="pb-3 font-medium">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {recentActions.map((action) => (
                  <tr key={action.action_id} className="hover:bg-slate-800/20 transition-colors">
                    <td className="py-3">
                      <Link to={`/actions/${action.action_id}`} className="font-mono text-emerald-400 hover:underline">
                        {action.action_id.slice(0, 12)}...
                      </Link>
                    </td>
                    <td className="py-3 font-mono">{formatCurrency(action.amount, action.currency)}</td>
                    <td className="py-3">
                      <div className="flex items-center gap-2">
                        <span>{action.recipient}</span>
                        {action.recipient_known && <ShieldCheck className="w-3 h-3 text-emerald-400" />}
                      </div>
                    </td>
                    <td className="py-3">
                      <StatusBadge status={action.status} />
                    </td>
                    <td className="py-3 text-slate-400">{formatDate(action.created_at)}</td>
                  </tr>
                ))}
                {recentActions.length === 0 && (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-slate-500">No actions found</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
        
        {/* Agent Overview */}
        <div className="panel flex flex-col">
          <h2 className="text-lg font-semibold text-slate-100 mb-6 flex justify-between items-center">
            Agent Security Overview
            <span className="text-sm font-normal text-emerald-400">Avg Trust: {metrics?.average_trust}</span>
          </h2>
          
          <div className="space-y-6 overflow-y-auto flex-1 max-h-[400px] pr-2 custom-scrollbar">
            {agents.map((agent) => (
              <div key={agent.id} className="p-4 bg-slate-800/30 rounded-lg border border-slate-700/50">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-sm font-medium text-slate-200">{agent.name}</p>
                  <StatusBadge status={agent.status} />
                </div>
                
                <div className="pt-2 border-t border-slate-800/50">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-slate-400">Trust Score</span>
                    <span className={`text-xs font-mono ${agent.trust_score >= 80 ? 'text-emerald-400' : agent.trust_score >= 60 ? 'text-yellow-400' : 'text-rose-400'}`}>
                      {agent.trust_score.toFixed(1)}
                    </span>
                  </div>
                  <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                    <div 
                      className={`h-full rounded-full ${agent.trust_score >= 80 ? 'bg-emerald-500' : agent.trust_score >= 60 ? 'bg-yellow-500' : 'bg-rose-500'}`} 
                      style={{ width: `${agent.trust_score}%` }}
                    ></div>
                  </div>
                </div>
                
                <div className="pt-3 mt-3 border-t border-slate-800/50 flex items-center justify-between">
                   <span className="text-xs text-slate-500">Daily Limit</span>
                   <span className="text-xs font-mono text-slate-300">{formatCurrency(agent.daily_limit, agent.allowed_currencies[0] || 'INR')}</span>
                </div>
              </div>
            ))}
            
            {agents.length === 0 && (
              <div className="text-center text-slate-500 py-4 text-sm">No agents registered</div>
            )}
          </div>
          
          <div className="pt-4 mt-auto">
            <Link to="/agents" className="block w-full py-2 text-center text-sm bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-md transition-colors">
              Manage All Agents
            </Link>
          </div>
        </div>
        
      </div>
    </PageContainer>
  );
}
