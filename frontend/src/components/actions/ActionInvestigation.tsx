import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Play, ServerCrash, Shield, Fingerprint, BrainCircuit, Users2, Dna, Network, Zap, CheckCircle2, ShieldAlert } from "lucide-react";
import { api } from "../../services/api";
import type { EvaluationResponse } from "../../types";
import { PageContainer } from "../layout/PageContainer";
import { formatCurrency, formatDate } from "../../utils/format";
import { StatusBadge } from "../common/Badge";
import { SecurityEngineCard } from "../common/SecurityEngineCard";
import { cn } from "../../utils/cn";

export function ActionInvestigation() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<EvaluationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [evaluating, setEvaluating] = useState(false);

  async function loadData() {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      // Try to get latest evaluation if it has one, else just the proposal
      const [proposal, evals] = await Promise.all([
        api.getAction(id),
        api.getActionEvaluations(id).catch(() => [])
      ]);
      
      if (evals && evals.length > 0) {
        setData({ proposal, evaluation: evals[0] });
      } else {
        setData({ proposal, evaluation: null as any }); // not evaluated yet
      }
    } catch (err: any) {
      setError(err.message || "Failed to load action details");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, [id]);

  const handleEvaluate = async () => {
    if (!id) return;
    try {
      setEvaluating(true);
      const result = await api.evaluateAction(id);
      setData(result);
    } catch (err: any) {
      alert("Evaluation failed: " + err.message);
    } finally {
      setEvaluating(false);
    }
  };

  if (loading) {
    return <PageContainer><div className="text-slate-400">Loading investigation data...</div></PageContainer>;
  }

  if (error || !data) {
    return (
      <PageContainer>
        <div className="panel bg-rose-500/10 border-rose-500/20 text-rose-400">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <ServerCrash className="w-5 h-5" /> Error
          </h2>
          <p className="mt-2">{error}</p>
          <Link to="/actions" className="mt-4 inline-block text-sm text-slate-300 hover:text-white underline">
            Return to Actions
          </Link>
        </div>
      </PageContainer>
    );
  }

  const { proposal, evaluation } = data;
  const isEvaluated = !!evaluation;
  const decisionColor = evaluation?.decision === "EXECUTE" 
    ? "text-emerald-400" 
    : evaluation?.decision === "BLOCK" 
      ? "text-rose-400" 
      : "text-amber-400";

  return (
    <PageContainer>
      {/* Header */}
      <div className="flex items-center gap-4 mb-2">
        <Link to="/actions" className="p-2 rounded-md hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-slate-100 font-mono">{proposal.action_id}</h1>
            <StatusBadge status={proposal.status} />
          </div>
          <p className="text-sm text-slate-400 mt-1">Proposed at {formatDate(proposal.created_at)}</p>
        </div>
        
        <div className="ml-auto">
          {!isEvaluated ? (
            <button 
              onClick={handleEvaluate}
              disabled={evaluating}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-md font-medium transition-colors"
            >
              {evaluating ? "Evaluating..." : <><Play className="w-4 h-4 fill-current" /> Run Evaluation</>}
            </button>
          ) : (
            <button 
              onClick={handleEvaluate}
              disabled={evaluating}
              className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-md font-medium transition-colors border border-slate-700"
            >
              {evaluating ? "Re-evaluating..." : <><Play className="w-4 h-4" /> Re-evaluate</>}
            </button>
          )}
        </div>
      </div>

      {/* Primary Details Panel */}
      <div className="panel grid grid-cols-2 md:grid-cols-4 gap-6">
        <div>
          <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Agent</p>
          <Link to={`/agents/${proposal.agent_id}`} className="font-medium text-slate-200 hover:text-emerald-400 hover:underline">
            Agent #{proposal.agent_id}
          </Link>
        </div>
        <div>
          <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Amount</p>
          <p className="font-mono text-lg font-semibold text-slate-200">
            {formatCurrency(proposal.amount, proposal.currency)}
          </p>
        </div>
        <div className="col-span-2">
          <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Recipient</p>
          <div className="flex items-center gap-2">
            <p className="font-medium text-slate-200 truncate">{proposal.recipient}</p>
            {proposal.recipient_known ? (
              <span className="flex items-center gap-1 text-xs text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                <CheckCircle2 className="w-3 h-3" /> Known
              </span>
            ) : (
              <span className="flex items-center gap-1 text-xs text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20">
                <ShieldAlert className="w-3 h-3" /> Unknown
              </span>
            )}
          </div>
          {proposal.recipient_account_number && (
            <p className="text-xs font-mono text-slate-500 mt-1">Acct: {proposal.recipient_account_number}</p>
          )}
        </div>
        <div className="col-span-4 pt-4 border-t border-slate-800">
          <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Purpose / Context</p>
          <p className="text-sm text-slate-300 italic">"{proposal.purpose}"</p>
        </div>
      </div>

      {isEvaluated && (
        <div className="mt-8 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
              <Shield className="w-5 h-5 text-emerald-400" /> Security Pipeline
            </h2>
            
            <div className="flex items-center gap-3">
              <span className="text-sm text-slate-400">Final Decision:</span>
              <span className={cn("text-xl font-bold tracking-widest", decisionColor)}>
                {evaluation.decision}
              </span>
            </div>
          </div>
          
          {/* Timeline Wrapper */}
          <div className="relative border-l border-slate-800 ml-4 pl-8 py-2 space-y-8">
            
            <div className="absolute top-0 -left-1.5 w-3 h-3 rounded-full bg-slate-700" />
            <div className="absolute bottom-0 -left-1.5 w-3 h-3 rounded-full bg-slate-700" />
            
            {/* Identity & Authority */}
            <div className="relative">
              <div className="absolute top-4 -left-[41px] w-4 h-0.5 bg-slate-800" />
              <SecurityEngineCard 
                engineName="Identity & Authority" 
                description="Validates agent capabilities, constraints, and daily limits."
                icon={<Fingerprint className="w-5 h-5" />}
                result={evaluation.engine_results["authority"]}
              >
                {evaluation.engine_results["authority"]?.status === "PASS" && (
                   <p className="text-xs text-slate-400">Limits verified. Daily spend within boundaries.</p>
                )}
              </SecurityEngineCard>
            </div>

            {/* Financial DNA */}
            <div className="relative">
              <div className="absolute top-4 -left-[41px] w-4 h-0.5 bg-slate-800" />
              <SecurityEngineCard 
                engineName="Financial DNA" 
                description="Checks historical deviation of amount, time, and recipient."
                icon={<Dna className="w-5 h-5" />}
                result={evaluation.engine_results["financial_dna"]}
              >
                {evaluation.engine_results["financial_dna"]?.status === "PASS" && (
                   <p className="text-xs text-slate-400">Transaction matches established behavioural baseline.</p>
                )}
              </SecurityEngineCard>
            </div>

            {/* Future Engines - Placeholders */}
            <div className="relative">
              <div className="absolute top-4 -left-[41px] w-4 h-0.5 bg-slate-800" />
              <SecurityEngineCard 
                engineName="Intent Alignment" 
                description="AI-driven analysis of agent prompt manipulation and objective drift."
                icon={<BrainCircuit className="w-5 h-5" />}
                result={evaluation.engine_results["intent"]}
              />
            </div>
            
            <div className="relative">
              <div className="absolute top-4 -left-[41px] w-4 h-0.5 bg-slate-800" />
              <SecurityEngineCard 
                engineName="Counterparty Intelligence" 
                description="External risk enrichment and entity resolution for the recipient."
                icon={<Users2 className="w-5 h-5" />}
                result={evaluation.engine_results["counterparty"]}
              />
            </div>

            <div className="relative">
              <div className="absolute top-4 -left-[41px] w-4 h-0.5 bg-slate-800" />
              <SecurityEngineCard 
                engineName="Cascade Detection" 
                description="Detects multi-agent coordinated attacks and structured movements."
                icon={<Network className="w-5 h-5" />}
                result={evaluation.engine_results["cascade"]}
              />
            </div>
            
            {/* Risk Fusion */}
            <div className="relative">
              <div className="absolute top-4 -left-[41px] w-4 h-0.5 bg-slate-800" />
              <SecurityEngineCard 
                engineName="Risk Fusion & Governance" 
                description="Synthesizes all signals and makes the final execution decision."
                icon={<Zap className="w-5 h-5" />}
                result={evaluation.engine_results["governance"]}
              >
                 <div className="flex items-center gap-4 mt-2">
                    <div>
                      <p className="text-[10px] text-slate-500 uppercase">Provisional</p>
                      <p className="text-sm font-mono text-slate-300">{evaluation.provisional ? "TRUE" : "FALSE"}</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-slate-500 uppercase">Coverage</p>
                      <p className="text-sm font-mono text-slate-300">
                        {evaluation.coverage.implemented.length} / {evaluation.coverage.implemented.length + evaluation.coverage.not_implemented.length}
                      </p>
                    </div>
                 </div>
              </SecurityEngineCard>
            </div>

          </div>
        </div>
      )}
    </PageContainer>
  );
}
