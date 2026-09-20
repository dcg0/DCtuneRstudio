from pathlib import Path
from PIL import Image

root = Path(__file__).resolve().parents[1]
source = root / "assets" / "branding" / "dc-tuner-rojo-icon.png"
target = root / "assets" / "branding" / "dc-tuner-rojo.ico"
image = Image.open(source).convert("RGBA")
image.save(target, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
print(target)
