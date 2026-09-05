export type CastingViewport = { width: number; height: number; keyboardOpen: boolean };

/** Keep the layout canvas still while the IME occludes it. Never infer a cast from UI state. */
export function castingViewport(
  previous: CastingViewport | null,
  width: number,
  visibleHeight: number,
  editing: boolean,
): CastingViewport {
  const sameWidth = previous !== null && Math.abs(previous.width - width) < 32;
  const occluded = sameWidth && previous.height - visibleHeight > 100;
  // Preserve the baseline during the focusout -> keyboard-close animation too.
  if (previous && occluded && (editing || previous.keyboardOpen)) {
    return { width, height: previous.height, keyboardOpen: true };
  }
  return { width, height: visibleHeight, keyboardOpen: false };
}
