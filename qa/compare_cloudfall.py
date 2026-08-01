from pathlib import Path

from PIL import Image, ImageChops, ImageEnhance, ImageOps, ImageStat


ROOT = Path(__file__).resolve().parent
SOURCE = Path(
    r"C:\Users\27622\.codex\generated_images\019fa5e9-2a61-7f92-813b-b9d609ccb12c\exec-04c25898-61ae-4837-92eb-6bbe9106ac01.png"
)
FRAME_A = ROOT / "inquiry-cloudfall-v6-browser-t1.png"
FRAME_B = ROOT / "inquiry-cloudfall-v6-browser-t2.png"


first = Image.open(FRAME_A).convert("RGB")
second = Image.open(FRAME_B).convert("RGB")
difference = ImageChops.difference(first, second)
greyscale = difference.convert("L")
changed_pixels = sum(1 for value in greyscale.getdata() if value > 2)
pixel_count = first.width * first.height
mean_difference = sum(ImageStat.Stat(difference).mean) / 3

amplified = ImageEnhance.Brightness(difference).enhance(10)
amplified.save(ROOT / "inquiry-cloudfall-v6-motion-diff.png")

scene_height = first.height - 68
target = ImageOps.fit(
    Image.open(SOURCE).convert("RGB"),
    (first.width, scene_height),
    method=Image.Resampling.LANCZOS,
    centering=(0.5, 0.5),
)
implementation = first.crop((0, 68, first.width, first.height))
half_width = 953
target = target.resize((half_width, 473), Image.Resampling.LANCZOS)
implementation = implementation.resize((half_width, 473), Image.Resampling.LANCZOS)
comparison = Image.new("RGB", (1914, 473), (232, 223, 204))
comparison.paste(target, (0, 0))
comparison.paste(implementation, (961, 0))
comparison.save(ROOT / "inquiry-cloudfall-v6-comparison.png")

print(
    {
        "mean_rgb_difference": round(mean_difference, 3),
        "changed_pixels_over_2": changed_pixels,
        "changed_percent": round(changed_pixels / pixel_count * 100, 2),
    }
)
