import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ShieldCheck, Search, Filter } from "lucide-react";
import { api } from "../../services/api";
import type { ActionProposal } from "../../types";
import { PageContainer } from "../layout/PageContainer";
import { formatCurrency, formatDate } from "../../utils/format";
import { StatusBadge } from "../common/Badge";

export function ActionList() {
  const [actions, setActions] = useState<ActionProposal[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    async function loadData() {
      try {
        const data = await api.getActions();
        setActions(data);
      } catch (error) {
        console.error("Failed to load actions", error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const filteredActions = actions.filter((action) => 
    action.action_id.toLowerCase().includes(search.toLowerCase()) ||
    action.recipient.toLowerCase().includes(search.toLowerCase()) ||
    action.purpose.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <PageContainer>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-slate-100">Action History</h1>
          <p className="text-sm text-slate-400 mt-1">Monitor all financial proposals and their evaluation outcomes.</p>
        </div>
      </div>

      <div className="panel p-0 overflow-hidden">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/50">
          <div className="relative w-72">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input 
              type="text" 
              placeholder="Search by ID, recipient, purpose..." 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-md py-1.5 pl-9 pr-3 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-slate-700"
            />
          </div>
          <button className="flex items-center gap-2 px-3 py-1.5 text-sm bg-slate-800 border border-slate-700 rounded-md text-slate-300 hover:bg-slate-700">
            <Filter className="w-4 h-4" />
            Filter
          </button>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-slate-900">
              <tr className="text-slate-400 border-b border-slate-800">
                <th className="px-6 py-4 font-medium">Action ID</th>
                <th className="px-6 py-4 font-medium">Agent</th>
                <th className="px-6 py-4 font-medium">Type</th>
                <th className="px-6 py-4 font-medium">Amount</th>
                <th className="px-6 py-4 font-medium">Recipient</th>
                <th className="px-6 py-4 font-medium">Time</th>
                <th className="px-6 py-4 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-6 py-8 text-center text-slate-500">Loading actions...</td>
                </tr>
              ) : filteredActions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-8 text-center text-slate-500">No actions found</td>
                </tr>
              ) : (
                filteredActions.map((action) => (
                  <tr key={action.action_id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-6 py-4">
                      <Link to={`/actions/${action.action_id}`} className="font-mono text-emerald-400 hover:underline">
                        {action.action_id.slice(0, 16)}...
                      </Link>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-slate-300">Agent #{action.agent_id}</span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-1 bg-slate-800 rounded text-xs text-slate-300">{action.action_type}</span>
                    </td>
                    <td className="px-6 py-4 font-mono">{formatCurrency(action.amount, action.currency)}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <span className="truncate max-w-[150px]">{action.recipient}</span>
                        {action.recipient_known && <span title="Known Counterparty"><ShieldCheck className="w-3 h-3 text-emerald-400" /></span>}
                      </div>
                    </td>
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
