export type CastingViewport = {
  width: number;
  height: number;
  keyboardOpen: boolean;
};

/** Keep the accepted casting composition still while the mobile keyboard covers it. */
export function castingViewport(
  previous: CastingViewport | null,
  width: number,
  visibleHeight: number,
  editing: boolean,
): CastingViewport {
  const sameWidth = previous !== null && Math.abs(previous.width - width) < 32;
  const keyboardOcclusion = sameWidth && previous.height - visibleHeight > 100;

  // Keep the baseline through the short focusout -> keyboard-close animation.
  if (previous && keyboardOcclusion && (editing || previous.keyboardOpen)) {
    return { width, height: previous.height, keyboardOpen: true };
  }

  return { width, height: visibleHeight, keyboardOpen: false };
}
