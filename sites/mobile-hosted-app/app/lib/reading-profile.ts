/** Server configuration only; never accept generation settings from browser input. */
export const CONCISE_READING_PROFILE = "concise-medium-v1";

export function selectReadingProfile(configured: string | undefined, supported: readonly unknown[]): string | undefined {
  return configured === CONCISE_READING_PROFILE && supported.includes(CONCISE_READING_PROFILE)
    ? CONCISE_READING_PROFILE : undefined;
}
