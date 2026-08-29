import { api } from "./api";

export const agentsService = {
  list: api.getAgents,
  get: api.getAgent,
  financialDNA: api.getFinancialDNA,
};
