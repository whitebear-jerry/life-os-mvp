import os
from PIL import Image

def clean_sprite_pro(img_path, sprite_type):
    if not os.path.exists(img_path):
        print(f"File not found: {img_path}")
        return
        
    print(f"🧹 Pro cleaning background for {sprite_type}: {img_path}")
    img = Image.open(img_path).convert("RGBA")
    datas = img.getdata()
    
    new_data = []
    removed_count = 0
    
    for item in datas:
        r, g, b, a = item[:4]
        
        # Keep existing transparency
        if a < 10:
            new_data.append((0, 0, 0, 0))
            continue
            
        should_remove = False
        
        # 1. Bear Sage background grays: around 170-178
        if sprite_type == 'bear':
            is_bear_gray = (r >= 165 and r <= 182 and g >= 165 and g <= 182 and b >= 165 and b <= 182)
            is_white = (r > 240 and g > 240 and b > 240)
            if is_bear_gray or is_white:
                should_remove = True
                
        # 2. Rabbit Mage background bluish-grays: around 196-218 (R <= G <= B style)
        elif sprite_type == 'rabbit':
            is_rabbit_gray = (r >= 190 and r <= 222 and g >= 195 and g <= 225 and b >= 200 and b <= 230 and abs(r - g) <= 12 and abs(g - b) <= 12)
            is_white = (r > 240 and g > 240 and b > 240)
            if is_rabbit_gray or is_white:
                should_remove = True
                
        # 3. Other sprites: standard grays and whites
        else:
            is_gray = (abs(r - g) < 12 and abs(g - b) < 12 and r > 160 and r < 230)
            is_white = (r > 235 and g > 235 and b > 235)
            if is_gray or is_white:
                should_remove = True
                
        if should_remove:
            new_data.append((255, 255, 255, 0))
            removed_count += 1
        else:
            new_data.append(item)
            
    img.putdata(new_data)
    img.save(img_path, "PNG")
    print(f"✅ Cleaned {removed_count} pixels successfully.")

# Paths to clean
sub_assets = "/Users/whitebebear/Desktop/life-os-mvp/life-os-mvp/assets"
root_assets = "/Users/whitebebear/Desktop/life-os-mvp/assets"

# Clean subfolder sprites
clean_sprite_pro(os.path.join(sub_assets, "hero_bear_sage.png"), 'bear')
clean_sprite_pro(os.path.join(sub_assets, "hero_rabbit_mage.png"), 'rabbit')
clean_sprite_pro(os.path.join(sub_assets, "hero_cat_warrior.png"), 'cat')
clean_sprite_pro(os.path.join(sub_assets, "hero_monkey_ninja.png"), 'monkey')

# Clean root folder sprites
clean_sprite_pro(os.path.join(root_assets, "hero_bear_sage.png"), 'bear')
clean_sprite_pro(os.path.join(root_assets, "hero_rabbit_mage.png"), 'rabbit')
clean_sprite_pro(os.path.join(root_assets, "hero_cat_warrior.png"), 'cat')
clean_sprite_pro(os.path.join(root_assets, "hero_monkey_ninja.png"), 'monkey')
