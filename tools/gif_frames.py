import sys

from PIL import Image, ImageDraw, ImageFont, ImageSequence


MAX_FRAMES = 20
MIN_CELL = 96
MAX_CELL = 640
SHEET_LIMIT = 4096


def main():
    src, dst = sys.argv[1], sys.argv[2]
    try:
        img = Image.open(src)
    except Exception as e:
        print("open failed:", e)
        return 1

    frames = [frame.convert("RGBA").copy() for frame in ImageSequence.Iterator(img)]
    if not frames:
        return 1

    n0 = len(frames)
    if n0 > MAX_FRAMES:
        idx = [round(i * (n0 - 1) / (MAX_FRAMES - 1)) for i in range(MAX_FRAMES)]
        seen = []
        for i in idx:
            if not seen or seen[-1] != i:
                seen.append(i)
        frames = [frames[i] for i in seen]

    n = len(frames)
    cols = 5 if n > 8 else max(1, min(n, 4))
    rows = (n + cols - 1) // cols
    cell = min(MAX_CELL, SHEET_LIMIT // max(cols, rows))
    cell = max(MIN_CELL, cell)

    sheet = Image.new("RGBA", (cols * cell, rows * cell), (255, 255, 255, 255))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.load_default(size=max(12, cell // 14))
    except Exception:
        font = ImageFont.load_default()

    for i, f in enumerate(frames):
        f.thumbnail((cell, cell), Image.LANCZOS)
        x = (i % cols) * cell + (cell - f.width) // 2
        y = (i // cols) * cell + (cell - f.height) // 2
        sheet.paste(f, (x, y), f)
        tx = (i % cols) * cell + 3
        ty = (i // cols) * cell + 2
        label = str(i + 1)
        draw.text((tx, ty), label, fill=(255, 50, 50, 230), font=font,
                  stroke_width=1, stroke_fill=(255, 255, 255, 200))

    sheet.convert("RGB").save(dst, "PNG", optimize=True)
    print("ok", n0, "->", n, "frames", cols, "x", rows, "cell", cell)
    return 0


if __name__ == "__main__":
    sys.exit(main())
