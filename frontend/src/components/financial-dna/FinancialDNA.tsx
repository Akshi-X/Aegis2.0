import { useEffect, useState } from "react";
import { Dna, BarChart3, Clock, Users, Activity } from "lucide-react";
import { api } from "../../services/api";
import type { FinancialDNAProfile } from "../../types";
import { PageContainer } from "../layout/PageContainer";
import { formatCurrency, formatDate } from "../../utils/format";

export function FinancialDNA() {
  const [dna, setDna] = useState<FinancialDNAProfile | null>(null);
  const [loading, setLoading] = useState(true);

  // In a real app we might select which agent to view, for now we hardcode agent 1 (Treasury Agent)
  const agentId = 1;

  useEffect(() => {
    async function loadData() {
      try {
        const data = await api.getFinancialDNA(agentId);
        setDna(data);
      } catch (error) {
        console.error("Failed to load financial DNA", error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [agentId]);

  if (loading) {
    return <PageContainer><div className="text-slate-400">Loading Financial DNA...</div></PageContainer>;
  }

  if (!dna) {
    return (
      <PageContainer>
        <div className="panel flex flex-col items-center justify-center py-12 text-slate-400">
          <Dna className="w-12 h-12 mb-4 opacity-50" />
          <h2 className="text-xl font-semibold text-slate-300">No DNA Profile Found</h2>
          <p className="mt-2">The selected agent does not have enough historical data to form a Financial DNA profile.</p>
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-slate-100 flex items-center gap-2">
            <Dna className="w-6 h-6 text-blue-400" /> Financial DNA
          </h1>
          <p className="text-sm text-slate-400 mt-1">Behavioral baseline established from historical transactions.</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-slate-500 uppercase tracking-wider">Agent</p>
          <p className="text-sm font-medium text-slate-200">Treasury Agent (ID: {agentId})</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Amount Baseline */}
        <div className="panel">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 rounded-md bg-blue-500/10 text-blue-400">
              <BarChart3 className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-100">Amount Baseline</h2>
              <p className="text-xs text-slate-400">Typical transaction sizes</p>
            </div>
          </div>
          
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-slate-400">Lower Bound</span>
                <span className="font-mono text-slate-200">{formatCurrency(dna.normal_amount_range[0])}</span>
              </div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-slate-400">Upper Bound</span>
                <span className="font-mono text-slate-200">{formatCurrency(dna.normal_amount_range[1])}</span>
              </div>
            </div>
            
            <div className="pt-4 border-t border-slate-800">
              <p className="text-xs text-slate-500 mb-2">Visual Range</p>
              <div className="relative h-4 bg-slate-800 rounded-full overflow-hidden flex">
                <div className="w-[10%] bg-rose-500/20" title="Unusually low"></div>
                <div className="w-[60%] bg-blue-500/50" title="Normal range"></div>
                <div className="w-[30%] bg-rose-500/20" title="Unusually high"></div>
              </div>
              <div className="flex justify-between text-[10px] text-slate-500 mt-1 font-mono">
                <span>0</span>
                <span>{formatCurrency(dna.normal_amount_range[0])}</span>
                <span>{formatCurrency(dna.normal_amount_range[1])}</span>
                <span>Max</span>
              </div>
            </div>
          </div>
        </div>

        {/* Temporal Baseline */}
        <div className="panel">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 rounded-md bg-amber-500/10 text-amber-400">
              <Clock className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-100">Temporal Baseline</h2>
              <p className="text-xs text-slate-400">Typical operating hours</p>
            </div>
          </div>
          
          <div className="flex items-center justify-between mb-8">
            <div className="text-center">
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Start Time</p>
              <p className="font-mono text-2xl text-slate-200">{dna.normal_hours[0].toString().padStart(2, '0')}:00</p>
            </div>
            <div className="flex-1 px-4 flex items-center justify-center">
              <div className="h-0.5 w-full bg-slate-700 relative">
                 <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 px-2 bg-slate-900 text-xs text-slate-500">to</div>
              </div>
            </div>
            <div className="text-center">
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">End Time</p>
              <p className="font-mono text-2xl text-slate-200">{dna.normal_hours[1].toString().padStart(2, '0')}:00</p>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-800">
             <div className="flex gap-1 h-8">
               {Array.from({ length: 24 }).map((_, i) => (
                 <div 
                   key={i} 
                   className={`flex-1 rounded-sm ${i >= dna.normal_hours[0] && i <= dna.normal_hours[1] ? 'bg-amber-500/50' : 'bg-slate-800'}`}
                   title={`${i.toString().padStart(2, '0')}:00`}
                 />
               ))}
             </div>
             <div className="flex justify-between text-[10px] text-slate-500 mt-1 font-mono">
                <span>00:00</span>
                <span>12:00</span>
                <span>23:59</span>
             </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        {/* Frequency */}
        <div className="panel flex flex-col justify-center">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded-md bg-emerald-500/10 text-emerald-400">
              <Activity className="w-5 h-5" />
            </div>
            <h2 className="text-sm font-semibold text-slate-100">Daily Frequency</h2>
          </div>
          <p className="text-3xl font-bold text-slate-200 font-mono mb-1">{dna.typical_daily_transactions.toFixed(1)}</p>
          <p className="text-xs text-slate-500">transactions per day</p>
        </div>

        {/* Exposure */}
        <div className="panel flex flex-col justify-center">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded-md bg-emerald-500/10 text-emerald-400">
              <BarChart3 className="w-5 h-5" />
            </div>
            <h2 className="text-sm font-semibold text-slate-100">Daily Exposure</h2>
          </div>
          <p className="text-2xl font-bold text-slate-200 font-mono mb-1">{formatCurrency(dna.typical_daily_exposure)}</p>
          <p className="text-xs text-slate-500">average daily volume</p>
        </div>

        {/* Recipients */}
        <div className="panel flex flex-col justify-center">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded-md bg-purple-500/10 text-purple-400">
              <Users className="w-5 h-5" />
            </div>
            <h2 className="text-sm font-semibold text-slate-100">Known Network</h2>
          </div>
          <p className="text-3xl font-bold text-slate-200 font-mono mb-1">{dna.known_recipients.length}</p>
          <p className="text-xs text-slate-500">trusted counterparties</p>
        </div>
      </div>

      {/* Recipient List */}
      <div className="panel">
        <h2 className="text-lg font-semibold text-slate-100 mb-4">Trusted Counterparties</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {dna.known_recipients.map(recipient => (
            <div key={recipient} className="p-3 bg-slate-950 border border-slate-800 rounded-md flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center text-slate-400 font-medium">
                {recipient.charAt(0).toUpperCase()}
              </div>
              <span className="text-sm text-slate-300 truncate">{recipient}</span>
            </div>
          ))}
        </div>
      </div>
      
      <div className="mt-6 flex justify-end">
         <p className="text-xs text-slate-500">Profile last updated: {formatDate(dna.last_updated)}</p>
      </div>
    </PageContainer>
  );
}
