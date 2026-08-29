import { api } from "./api";

export const actionsService = {
  list: api.getActions,
  get: api.getAction,
  evaluate: api.evaluateAction,
  evaluations: api.getActionEvaluations,
};
