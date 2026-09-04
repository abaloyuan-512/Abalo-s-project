from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "sites" / "hosted-app" / "public"
OUT = ROOT / "artifacts" / "p1-motion-concepts-v1"

WIDTH = 390
HEIGHT = 844
FPS = 16
DURATION = 4.5
FRAME_COUNT = round(FPS * DURATION)

FINAL_PATH = PUBLIC / "p1-motion-ink-realm-v1.png"
BASE_PATH = PUBLIC / "p1-motion-pre-reveal-base-v2.png"
RIPPLE_PATH = PUBLIC / "p1-motion-ripple-source-v3.png"
DROP_PATH = PUBLIC / "p1-motion-falling-drop-source-v4.png"


def fit(im: Image.Image) -> Image.Image:
    return im.convert("RGB").resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)


def rgba_fit(im: Image.Image, scale: float) -> Image.Image:
    w = max(1, round(im.width * scale))
    h = max(1, round(im.height * scale))
    return im.convert("RGBA").resize((w, h), Image.Resampling.LANCZOS)


def clamp01(value: np.ndarray | float) -> np.ndarray | float:
    return np.clip(value, 0.0, 1.0)


def smoothstep(edge0: float, edge1: float, value: np.ndarray | float):
    x = clamp01((value - edge0) / (edge1 - edge0))
    return x * x * (3.0 - 2.0 * x)


def ease_out(value: float) -> float:
    value = min(1.0, max(0.0, value))
    return 1.0 - (1.0 - value) ** 3


def ease_in_out(value: float) -> float:
    value = min(1.0, max(0.0, value))
    return value * value * (3.0 - 2.0 * value)


def segment(t: float, start: float, end: float, easing=ease_in_out) -> float:
    if t <= start:
        return 0.0
    if t >= end:
        return 1.0
    return easing((t - start) / (end - start))


def composite(base: np.ndarray, final: np.ndarray, alpha: np.ndarray) -> Image.Image:
    alpha = np.asarray(alpha, dtype=np.float32)
    if alpha.ndim == 2:
        alpha = alpha[..., None]
    rgb = base * (1.0 - alpha) + final * alpha
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")


def alpha_paste(canvas: Image.Image, overlay: Image.Image, xy: tuple[int, int], opacity: float = 1.0) -> None:
    if opacity <= 0:
        return
    overlay = overlay.copy()
    if opacity < 1.0:
        a = overlay.getchannel("A").point(lambda p: round(p * opacity))
        overlay.putalpha(a)
    canvas.alpha_composite(overlay, xy)


def low_frequency_noise(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    small = (rng.random((28, 13)) * 255).astype(np.uint8)
    noise = Image.fromarray(small, "L").resize((WIDTH, HEIGHT), Image.Resampling.BICUBIC)
    noise = noise.filter(ImageFilter.GaussianBlur(10))
    arr = np.asarray(noise, dtype=np.float32) / 255.0
    return (arr - arr.min()) / max(1e-6, arr.max() - arr.min())


def blurred(arr: np.ndarray, radius: float) -> np.ndarray:
    im = Image.fromarray(np.clip(arr * 255, 0, 255).astype(np.uint8), "L")
    im = im.filter(ImageFilter.GaussianBlur(radius))
    return np.asarray(im, dtype=np.float32) / 255.0


def save_animation(name: str, frames: list[Image.Image], key_indices: list[int]) -> dict[str, object]:
    OUT.mkdir(parents=True, exist_ok=True)
    deps = ROOT / "artifacts" / "p1-motion-concepts-v1" / ".deps"
    if str(deps) not in sys.path:
        sys.path.insert(0, str(deps))
    import imageio_ffmpeg

    mp4 = OUT / f"{name}.mp4"
    writer = imageio_ffmpeg.write_frames(
        str(mp4),
        (WIDTH, HEIGHT),
        fps=FPS,
        codec="libx264",
        pix_fmt_in="rgb24",
        pix_fmt_out="yuv420p",
        macro_block_size=2,
        quality=7,
        output_params=["-movflags", "+faststart"],
    )
    writer.send(None)
    try:
        for frame in frames:
            writer.send(np.asarray(frame.convert("RGB"), dtype=np.uint8).tobytes())
    finally:
        writer.close()

    strip_w = WIDTH * len(key_indices)
    strip = Image.new("RGB", (strip_w, HEIGHT), (240, 235, 225))
    for column, frame_index in enumerate(key_indices):
        strip.paste(frames[frame_index], (column * WIDTH, 0))
    strip_path = OUT / f"{name}-keyframes.png"
    strip.save(strip_path, optimize=True)

    return {
        "file": mp4.name,
        "frames": len(frames),
        "fps": FPS,
        "duration_seconds": len(frames) / FPS,
        "sha256": hashlib.sha256(mp4.read_bytes()).hexdigest().upper(),
        "keyframes": strip_path.name,
        "keyframes_sha256": hashlib.sha256(strip_path.read_bytes()).hexdigest().upper(),
    }


def concept_01_drop_and_ink(
    base: np.ndarray,
    final: np.ndarray,
    density: np.ndarray,
    ripple: Image.Image,
    drop: Image.Image,
) -> list[Image.Image]:
    yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH].astype(np.float32)
    impact_x = WIDTH * 0.49
    impact_y = HEIGHT * 0.283
    dx = (xx - impact_x) / (WIDTH * 0.58)
    dy = (yy - impact_y) / (HEIGHT * 0.82)
    radial = np.sqrt(dx * dx + dy * dy)
    organic = (low_frequency_noise(11) - 0.5) * 0.13

    frames: list[Image.Image] = []
    for index in range(FRAME_COUNT):
        t = index / FPS
        reveal = segment(t, 0.98, 3.48, ease_out)
        wave_front = reveal * 1.34
        alpha = smoothstep(-0.12, 0.08, wave_front - radial + organic)
        alpha *= 0.62 + 0.38 * smoothstep(0.04, 0.45, density)
        alpha = blurred(alpha, 2.0)
        if t >= 3.48:
            alpha = np.ones_like(alpha)

        frame = composite(base, final, alpha).convert("RGBA")

        fall = segment(t, 0.22, 0.94, ease_in_out)
        if 0 < fall < 1:
            x = round(impact_x - drop.width / 2)
            y = round(HEIGHT * 0.075 + (impact_y - HEIGHT * 0.075) * fall - drop.height / 2)
            alpha_paste(frame, drop, (x, y), 0.25 + 0.75 * smoothstep(0.0, 0.18, fall))

        impact = segment(t, 0.88, 1.36, ease_out) * (1.0 - segment(t, 1.36, 2.20, ease_in_out))
        if impact > 0:
            scale = 0.70 + 0.36 * segment(t, 0.88, 1.75, ease_out)
            ring = rgba_fit(ripple, scale * 0.46)
            x = round(impact_x - ring.width / 2)
            y = round(impact_y - ring.height * 0.47)
            alpha_paste(frame, ring, (x, y), 0.78 * impact)

        frames.append(frame.convert("RGB"))
    return frames


def concept_02_living_ink(base: np.ndarray, final: np.ndarray, density: np.ndarray) -> list[Image.Image]:
    yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH].astype(np.float32)
    y_norm = yy / max(1, HEIGHT - 1)
    x_norm = xx / max(1, WIDTH - 1)
    noise = low_frequency_noise(27)
    ink_body = blurred(density, 8.0)
    ink_body = (ink_body - ink_body.min()) / max(1e-6, ink_body.max() - ink_body.min())

    # Strong existing brushwork wakes first. The pale washes arrive later and the seal settles last.
    time_map = 0.74 - 0.48 * ink_body + 0.12 * noise
    time_map += 0.05 * np.abs(x_norm - 0.5)
    time_map += np.where(y_norm > 0.72, 0.13, 0.0)
    time_map = clamp01(time_map)

    frames: list[Image.Image] = []
    for index in range(FRAME_COUNT):
        t = index / FPS
        progress = segment(t, 0.30, 3.72, ease_in_out)
        alpha = smoothstep(time_map - 0.12, time_map + 0.10, progress)
        alpha = blurred(alpha, 1.6)

        frame_arr = base * (1.0 - alpha[..., None]) + final * alpha[..., None]
        frontier = np.exp(-((progress - time_map) / 0.050) ** 2) * density
        frame_arr *= (1.0 - 0.11 * frontier[..., None])
        if t >= 3.72:
            frame_arr = final.copy()
        frames.append(Image.fromarray(np.clip(frame_arr, 0, 255).astype(np.uint8), "RGB"))
    return frames


def concept_03_water_mirror(base: np.ndarray, final: np.ndarray, density: np.ndarray) -> list[Image.Image]:
    yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH].astype(np.float32)
    waterline = round(HEIGHT * 0.53)
    reflection = base.copy()
    reflected_alpha = np.zeros((HEIGHT, WIDTH), dtype=np.float32)

    for y in range(waterline, HEIGHT):
        source_y = waterline - (y - waterline)
        if source_y < 0:
            break
        distance = (y - waterline) / max(1, HEIGHT - waterline)
        shimmer = 3.0 * math.sin(y * 0.09)
        x_shift = round(shimmer * (0.2 + 0.8 * distance))
        reflection[y] = np.roll(final[source_y], x_shift, axis=0)
        reflected_alpha[y] = density[source_y] * (0.44 * (1.0 - distance) ** 1.35)

    reflection_alpha = blurred(reflected_alpha, 2.2)
    reflection_frame = base * (1.0 - reflection_alpha[..., None]) + reflection * reflection_alpha[..., None]

    vertical_distance = np.abs(yy - waterline) / (HEIGHT * 0.58)
    organic = (low_frequency_noise(73) - 0.5) * 0.10
    frames: list[Image.Image] = []
    for index in range(FRAME_COUNT):
        t = index / FPS
        settle = segment(t, 0.35, 1.35, ease_out)
        reveal = segment(t, 1.00, 3.70, ease_out)
        reflection_mix = (1.0 - segment(t, 1.30, 3.20, ease_in_out)) * (0.68 + 0.32 * settle)
        stage = base * (1.0 - reflection_mix) + reflection_frame * reflection_mix

        alpha = smoothstep(-0.09, 0.08, reveal * 1.16 - vertical_distance + organic)
        alpha *= 0.68 + 0.32 * smoothstep(0.03, 0.40, density)
        alpha = blurred(alpha, 2.0)
        frame_arr = stage * (1.0 - alpha[..., None]) + final * alpha[..., None]

        if t < 2.30:
            ripple_strength = math.sin(min(1.0, t / 2.30) * math.pi)
            band = np.exp(-((yy - waterline) / 9.0) ** 2)
            line = 0.040 * ripple_strength * band[..., None]
            frame_arr = frame_arr * (1.0 - line)
        if t >= 3.70:
            frame_arr = final.copy()
        frames.append(Image.fromarray(np.clip(frame_arr, 0, 255).astype(np.uint8), "RGB"))
    return frames


def main() -> None:
    final_im = fit(Image.open(FINAL_PATH))
    base_im = fit(Image.open(BASE_PATH))
    final = np.asarray(final_im, dtype=np.float32)
    base = np.asarray(base_im, dtype=np.float32)
    density = np.mean(np.abs(final - base), axis=2) / 255.0
    density = clamp01(density * 2.2)

    ripple = Image.open(RIPPLE_PATH).convert("RGBA")
    drop = rgba_fit(Image.open(DROP_PATH), 0.46)

    specs = [
        (
            "01-one-drop-opens-the-realm",
            concept_01_drop_and_ink(base, final, density, ripple, drop),
            [0, 12, 25, 42, 60, FRAME_COUNT - 1],
        ),
        (
            "02-landscape-breathes-into-ink",
            concept_02_living_ink(base, final, density),
            [0, 12, 25, 42, 60, FRAME_COUNT - 1],
        ),
        (
            "03-water-mirror-settles",
            concept_03_water_mirror(base, final, density),
            [0, 12, 25, 42, 60, FRAME_COUNT - 1],
        ),
    ]

    manifest = {
        "status": "LOCAL_CONCEPT_ONLY",
        "website_code_changed": False,
        "commit_or_deploy": False,
        "source_final": str(FINAL_PATH.relative_to(ROOT)),
        "source_final_sha256": hashlib.sha256(FINAL_PATH.read_bytes()).hexdigest().upper(),
        "viewport": f"{WIDTH}x{HEIGHT}",
        "outputs": [],
    }
    for name, frames, key_indices in specs:
        manifest["outputs"].append(save_animation(name, frames, key_indices))

    manifest_path = OUT / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    hash_lines = []
    for path in sorted(OUT.glob("*")):
        if path.name == "MANIFEST.sha256" or not path.is_file():
            continue
        if path.suffix.lower() not in {".mp4", ".png", ".json"}:
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest().upper()
        hash_lines.append(f"{digest}  {path.name}")
    (OUT / "MANIFEST.sha256").write_text("\n".join(hash_lines) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


def build_selected_highres() -> None:
    global WIDTH, HEIGHT, FRAME_COUNT, OUT
    WIDTH = 852
    HEIGHT = 1844
    FRAME_COUNT = round(FPS * DURATION)
    OUT = ROOT / "artifacts" / "p1-motion-selected-v1"

    final_im = fit(Image.open(FINAL_PATH))
    base_im = fit(Image.open(BASE_PATH))
    final = np.asarray(final_im, dtype=np.float32)
    base = np.asarray(base_im, dtype=np.float32)
    density = clamp01(np.mean(np.abs(final - base), axis=2) / 255.0 * 2.2)
    ripple = Image.open(RIPPLE_PATH).convert("RGBA")
    drop = rgba_fit(Image.open(DROP_PATH), WIDTH / 853.0)

    frames = concept_01_drop_and_ink(base, final, density, ripple, drop)
    output = save_animation(
        "p1-mobile-motion-selected-v1",
        frames,
        [0, 12, 25, 42, 60, FRAME_COUNT - 1],
    )
    manifest = {
        "status": "LOCAL_SELECTED_IMPLEMENTATION_ASSET",
        "website_code_changed": False,
        "commit_or_deploy": False,
        "source_final": str(FINAL_PATH.relative_to(ROOT)),
        "source_final_sha256": hashlib.sha256(FINAL_PATH.read_bytes()).hexdigest().upper(),
        "viewport": f"{WIDTH}x{HEIGHT}",
        "output": output,
    }
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--selected-highres", action="store_true")
    args = parser.parse_args()
    if args.selected_highres:
        build_selected_highres()
    else:
        main()
