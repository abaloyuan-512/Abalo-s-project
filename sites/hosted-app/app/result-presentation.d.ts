export type ResultSectionVisibility = {
  showGenericSignals: boolean;
  showGenericWhy: boolean;
  showGenericGuidance: boolean;
};

export function resultSectionVisibility(
  hasPersonalizedReading: boolean,
): ResultSectionVisibility;
