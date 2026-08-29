import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AppLayout } from "./components/layout/AppLayout";
import { Dashboard } from "./components/dashboard/Dashboard";
import { AgentList } from "./components/agents/AgentList";
import { AgentDetails } from "./components/agents/AgentDetails";
import { ActionList } from "./components/actions/ActionList";
import { ActionInvestigation } from "./components/actions/ActionInvestigation";
import { FinancialDNA } from "./components/financial-dna/FinancialDNA";
import { SecurityOverview } from "./components/security/SecurityOverview";
import { Reviews } from "./components/reviews/Reviews";
import { AuditLog } from "./components/audit/AuditLog";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/agents" element={<AgentList />} />
          <Route path="/agents/:id" element={<AgentDetails />} />
          <Route path="/actions" element={<ActionList />} />
          <Route path="/actions/:id" element={<ActionInvestigation />} />
          <Route path="/financial-dna" element={<FinancialDNA />} />
          <Route path="/security" element={<SecurityOverview />} />
          <Route path="/reviews" element={<Reviews />} />
          <Route path="/audit" element={<AuditLog />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
