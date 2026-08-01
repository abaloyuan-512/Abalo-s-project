from pathlib import Path

from PIL import Image, ImageChops, ImageEnhance, ImageOps, ImageStat


ROOT = Path(__file__).resolve().parent
SOURCE = Path(r"C:\Users\27622\AppData\Local\Temp\codex-clipboard-9d06dc28-1b60-48dd-88e6-d5a72a32d191.png")
CONCEPT = Path(r"C:\Users\27622\.codex\generated_images\019fa5e9-2a61-7f92-813b-b9d609ccb12c\exec-04c25898-61ae-4837-92eb-6bbe9106ac01.png")
FRAME_A = ROOT / "inquiry-cloudfall-v7-motion-iab-t1.png"
FRAME_B = ROOT / "inquiry-cloudfall-v7-motion-iab-t2.png"


first = Image.open(FRAME_A).convert("RGB")
second = Image.open(FRAME_B).convert("RGB")
difference = ImageChops.difference(first, second)
ImageEnhance.Brightness(difference).enhance(7).save(ROOT / "inquiry-cloudfall-v7-motion-diff.png")

source = Image.open(SOURCE).convert("RGB")
focus_height = round(first.width / (source.width / source.height))
implementation = first.crop((0, 65, first.width, 65 + focus_height))
source = ImageOps.fit(source, implementation.size, method=Image.Resampling.LANCZOS)
comparison = Image.new("RGB", (implementation.width * 2 + 8, implementation.height), (232, 223, 204))
comparison.paste(source, (0, 0))
comparison.paste(implementation, (implementation.width + 8, 0))
comparison.save(ROOT / "inquiry-cloudfall-v7-focused-comparison.png")

concept = ImageOps.fit(
    Image.open(CONCEPT).convert("RGB"),
    first.size,
    method=Image.Resampling.LANCZOS,
    centering=(0.5, 0.5),
)
concept = concept.resize((632, 356), Image.Resampling.LANCZOS)
implementation_full = first.resize((632, 356), Image.Resampling.LANCZOS)
full_comparison = Image.new("RGB", (1272, 356), (232, 223, 204))
full_comparison.paste(concept, (0, 0))
full_comparison.paste(implementation_full, (640, 0))
full_comparison.save(ROOT / "inquiry-cloudfall-v7-full-comparison.png")

top_cloud = difference.crop((0, 65, min(1000, first.width), 320))
falls = difference.crop((720, 180, first.width, 680))


def metrics(image: Image.Image) -> dict[str, float]:
    grey = image.convert("L")
    values = list(grey.getdata())
    return {
        "mean_rgb": round(sum(ImageStat.Stat(image).mean) / 3, 3),
        "changed_over_5_percent": round(sum(value > 5 for value in values) / len(values) * 100, 2),
        "changed_over_10_percent": round(sum(value > 10 for value in values) / len(values) * 100, 2),
    }


print({"top_cloud": metrics(top_cloud), "falls": metrics(falls)})
