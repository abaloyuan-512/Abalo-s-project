export function resultSectionVisibility(hasPersonalizedReading) {
  return {
    showGenericSignals: !hasPersonalizedReading,
    showGenericWhy: !hasPersonalizedReading,
    showGenericGuidance: !hasPersonalizedReading,
  };
}
