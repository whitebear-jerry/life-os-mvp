import os
from PIL import Image

def clean_sprite_background(img_path):
    if not os.path.exists(img_path):
        print(f"File not found: {img_path}")
        return
        
    print(f"🧹 Processing background cleaning for: {img_path}")
    img = Image.open(img_path).convert("RGBA")
    datas = img.getdata()
    
    new_data = []
    removed_count = 0
    
    for item in datas:
        # item is (R, G, B, A)
        r, g, b, a = item[:4]
        
        # 1. 檢測純白或非常接近純白的像素
        is_white = (r > 235 and g > 235 and b > 235)
        
        # 2. 檢測偽透明棋盤格的淺灰色 (R == G == B 且大於 180 的灰色)
        is_gray = (abs(r - g) < 8 and abs(g - b) < 8 and r > 180)
        
        # 3. 如果原圖就已經是透明的，保留透明度
        if a < 10:
            new_data.append((0, 0, 0, 0))
        elif is_white or is_gray:
            # 將這些背景像素全部變為 100% 透明
            new_data.append((255, 255, 255, 0))
            removed_count += 1
        else:
            new_data.append(item)
            
    img.putdata(new_data)
    img.save(img_path, "PNG")
    print(f"✅ Successfully cleaned sprite! Cleared {removed_count} background pixels.")

# 執行路徑
assets_dir = "/Users/whitebebear/Desktop/life-os-mvp/life-os-mvp/assets"

heroes = [
    "hero_bear_sage.png",
    "hero_cat_warrior.png",
    "hero_monkey_ninja.png",
    "hero_rabbit_mage.png"
]

for hero in heroes:
    path = os.path.join(assets_dir, hero)
    clean_sprite_background(path)

# 同時也清理 root 目錄的 assets 副本
root_assets_dir = "/Users/whitebebear/Desktop/life-os-mvp/assets"
for hero in heroes:
    path = os.path.join(root_assets_dir, hero)
    clean_sprite_background(path)
