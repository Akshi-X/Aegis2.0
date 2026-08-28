import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Dna, Fingerprint, Activity } from "lucide-react";
import { api } from "../../services/api";
import type { AgentOverview, FinancialDNAProfile, ActionProposal } from "../../types";
import { PageContainer } from "../layout/PageContainer";
import { formatCurrency, formatDate } from "../../utils/format";
import { StatusBadge } from "../common/Badge";

export function AgentDetails() {
  const { id } = useParams<{ id: string }>();
  const [agent, setAgent] = useState<AgentOverview | null>(null);
  const [dna, setDna] = useState<FinancialDNAProfile | null>(null);
  const [actions, setActions] = useState<ActionProposal[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      if (!id) return;
      try {
        const [agentData, dnaData, actionsData] = await Promise.all([
          api.getAgent(parseInt(id)),
          api.getFinancialDNA(parseInt(id)).catch(() => null),
          api.getActions().then(res => res.filter(a => a.agent_id === parseInt(id)).slice(0, 5))
        ]);
        setAgent(agentData);
        setDna(dnaData);
        setActions(actionsData);
      } catch (error) {
        console.error("Failed to load agent details", error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [id]);

  if (loading) {
    return <PageContainer><div className="text-slate-400">Loading agent...</div></PageContainer>;
  }

  if (!agent) {
    return <PageContainer><div className="text-rose-400">Agent not found.</div></PageContainer>;
  }

  return (
    <PageContainer>
      <div className="flex items-center gap-4 mb-2">
        <Link to="/agents" className="p-2 rounded-md hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-slate-100">{agent.name}</h1>
            <StatusBadge status={agent.status} />
          </div>
          <p className="text-sm text-slate-400 mt-1 font-mono">Agent ID: {agent.id}</p>
        </div>
      </div>

      <div className="panel mb-6">
        <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">Prime Objective</p>
        <p className="text-slate-200 text-lg italic border-l-2 border-emerald-500/50 pl-4 py-1 bg-emerald-500/5 rounded-r">
          "{agent.objective}"
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Authority Details */}
        <div className="panel space-y-4">
          <h2 className="text-lg font-semibold text-slate-100 flex items-center gap-2 mb-4">
            <Fingerprint className="w-5 h-5 text-emerald-400" /> Identity & Authority
          </h2>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Max Transaction</p>
              <p className="font-mono text-slate-200 font-medium">{formatCurrency(agent.max_transaction_limit)}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Daily Limit</p>
              <p className="font-mono text-slate-200 font-medium">{formatCurrency(agent.daily_limit)}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Allowed Actions</p>
              <div className="flex flex-wrap gap-1 mt-1">
                {agent.allowed_actions.map(a => (
                  <span key={a} className="px-2 py-0.5 bg-slate-800 rounded text-xs text-slate-300">{a}</span>
                ))}
              </div>
            </div>
            <div>
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Allowed Currencies</p>
              <div className="flex flex-wrap gap-1 mt-1">
                {agent.allowed_currencies.map(c => (
                  <span key={c} className="px-2 py-0.5 bg-slate-800 rounded text-xs text-slate-300">{c}</span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Financial DNA Summary */}
        <div className="panel space-y-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
              <Dna className="w-5 h-5 text-blue-400" /> Financial DNA
            </h2>
            <Link to="/financial-dna" className="text-xs text-emerald-400 hover:underline">View Full Profile</Link>
          </div>
          
          {dna ? (
            <div className="space-y-4">
              <div>
                <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Normal Amount Range</p>
                <div className="flex items-center gap-3">
                  <span className="font-mono text-slate-300">{formatCurrency(dna.normal_amount_range[0])}</span>
                  <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500/50 mx-[10%] w-[60%] rounded-full"></div>
                  </div>
                  <span className="font-mono text-slate-300">{formatCurrency(dna.normal_amount_range[1])}</span>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4 pt-2 border-t border-slate-800">
                 <div>
                   <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Operating Hours</p>
                   <p className="font-mono text-slate-300">
                     {dna.normal_hours[0].toString().padStart(2, '0')}:00 - {dna.normal_hours[1].toString().padStart(2, '0')}:00
                   </p>
                 </div>
                 <div>
                   <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Known Counterparties</p>
                   <p className="text-slate-300">{dna.known_recipients.length} vendors</p>
                 </div>
              </div>
            </div>
          ) : (
             <div className="text-sm text-slate-500 italic py-4">No Financial DNA profile available.</div>
          )}
        </div>
      </div>

      {/* Recent Actions */}
      <div className="panel p-0 overflow-hidden">
        <div className="p-4 border-b border-slate-800 bg-slate-900/50">
          <h2 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
            <Activity className="w-5 h-5 text-emerald-400" /> Recent Actions
          </h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-slate-900">
              <tr className="text-slate-400 border-b border-slate-800">
                <th className="px-6 py-4 font-medium">Action ID</th>
                <th className="px-6 py-4 font-medium">Amount</th>
                <th className="px-6 py-4 font-medium">Recipient</th>
                <th className="px-6 py-4 font-medium">Time</th>
                <th className="px-6 py-4 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {actions.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-slate-500">No recent actions</td>
                </tr>
              ) : (
                actions.map((action) => (
                  <tr key={action.action_id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-6 py-4">
                      <Link to={`/actions/${action.action_id}`} className="font-mono text-emerald-400 hover:underline">
                        {action.action_id.slice(0, 16)}...
                      </Link>
                    </td>
                    <td className="px-6 py-4 font-mono">{formatCurrency(action.amount, action.currency)}</td>
                    <td className="px-6 py-4 truncate max-w-[200px]">{action.recipient}</td>
                    <td className="px-6 py-4 text-slate-400">{formatDate(action.created_at)}</td>
                    <td className="px-6 py-4">
                      <StatusBadge status={action.status} />
                    </td>
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
