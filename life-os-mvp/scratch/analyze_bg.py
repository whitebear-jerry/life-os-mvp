import os
from PIL import Image
from collections import Counter

img_path = "/Users/whitebebear/Desktop/life-os-mvp/life-os-mvp/assets/hero_bear_sage.png"
if os.path.exists(img_path):
    img = Image.open(img_path).convert("RGBA")
    width, height = img.size
    print(f"Image dimensions: {width}x{height}")
    
    # Sample the corner pixels (which are typically background)
    corners = [
        img.getpixel((0, 0)),
        img.getpixel((width - 1, 0)),
        img.getpixel((0, height - 1)),
        img.getpixel((width - 1, height - 1)),
        img.getpixel((5, 5)),
        img.getpixel((width - 6, 5))
    ]
    print("Corner pixels:", corners)
    
    # Get all pixels
    pixels = list(img.getdata())
    counter = Counter(pixels)
    print("\nMost common colors (R, G, B, A) and count:")
    for color, count in counter.most_common(15):
        print(f"Color: {color}, Count: {count} ({count/(width*height)*100:.2f}%)")
else:
    print("File not found")
