import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../services/api";
import type { AgentOverview } from "../../types";
import { PageContainer } from "../layout/PageContainer";
import { formatCurrency } from "../../utils/format";
import { StatusBadge } from "../common/Badge";
import { Shield } from "lucide-react";

export function AgentList() {
  const [agents, setAgents] = useState<AgentOverview[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const data = await api.getAgents();
        setAgents(data);
      } catch (error) {
        console.error("Failed to load agents", error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <PageContainer>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-slate-100">Autonomous Agents</h1>
          <p className="text-sm text-slate-400 mt-1">Manage and monitor active financial agents.</p>
        </div>
      </div>

      <div className="panel p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-slate-900">
              <tr className="text-slate-400 border-b border-slate-800">
                <th className="px-6 py-4 font-medium">Agent</th>
                <th className="px-6 py-4 font-medium">Objective</th>
                <th className="px-6 py-4 font-medium">Status</th>
                <th className="px-6 py-4 font-medium">Trust Score</th>
                <th className="px-6 py-4 font-medium">Daily Limit</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-slate-500">Loading agents...</td>
                </tr>
              ) : (
                agents.map((agent) => (
                  <tr key={agent.id} className="hover:bg-slate-800/30 transition-colors cursor-pointer relative group">
                    <td className="px-6 py-4">
                      <Link to={`/agents/${agent.id}`} className="absolute inset-0 z-10" />
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                          <Shield className="w-4 h-4" />
                        </div>
                        <div>
                          <p className="font-medium text-slate-200 group-hover:text-emerald-400 transition-colors">{agent.name}</p>
                          <p className="text-xs text-slate-500 font-mono mt-0.5">ID: {agent.id}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-slate-300 truncate max-w-sm">{agent.objective}</p>
                    </td>
                    <td className="px-6 py-4 relative z-20">
                      <StatusBadge status={agent.status} />
                    </td>
                    <td className="px-6 py-4 font-mono text-emerald-400">{agent.trust_score.toFixed(1)}</td>
                    <td className="px-6 py-4 font-mono text-slate-300">{formatCurrency(agent.daily_limit)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </PageContainer>
  );
}
