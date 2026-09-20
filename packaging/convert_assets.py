from pathlib import Path
from PIL import Image

root = Path(__file__).resolve().parents[1] / "assets"
for source_name, target_name in (("dc-tuner-logo.png", "dc-tuner-logo.gif"), ("dc-tuner-cover.png", "dc-tuner-cover.gif")):
    source = root / source_name
    target = root / target_name
    image = Image.open(source).convert("RGB")
    image.save(target, format="GIF", optimize=True)
    print(f"created {target} ({target.stat().st_size} bytes)")
