import PIL.Image
import PIL.ImageDraw
import os

assets_dir = "assets"

def process_image(filepath):
    try:
        # Open the image and ensure it's in RGBA format
        img = PIL.Image.open(filepath).convert("RGBA")
        
        # Get the background color at (0, 0)
        bg_color = img.getpixel((0, 0))
        
        # Determine if it's a light or dark background
        is_light = bg_color[0] > 240 and bg_color[1] > 240 and bg_color[2] > 240
        
        # Define the target color to flood-fill with (transparent)
        fill_color = (0, 0, 0, 0)
        
        # Define the threshold / tolerance for color difference
        # thresh is the color distance (or distance squared in some PIL versions)
        # We will use a safe threshold value of 45 for light, 30 for dark
        thresh = 45 if is_light else 30
        
        # Use Pillow's native C-optimized floodfill!
        PIL.ImageDraw.floodfill(img, (0, 0), fill_color, thresh=thresh)
        
        # Save the image
        img.save(filepath, "PNG")
        print(f"Processed {os.path.basename(filepath)} successfully!")
    except Exception as e:
        print(f"Error processing {os.path.basename(filepath)}: {e}")

# Run for all monster PNGs in assets
for filename in os.listdir(assets_dir):
    if filename.startswith("monster_") and filename.endswith(".png"):
        process_image(os.path.join(assets_dir, filename))
