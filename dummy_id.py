import os
from PIL import Image, ImageDraw, ImageFont

output_folder = "sample_images"
os.makedirs(output_folder, exist_ok=True)

applicants = [
    {"name": "Aarav Sharma",  "id": "202310101150271", "dept": "Data Science"},
    {"name": "Priya Verma",   "id": "A10580",          "dept": "Engineering"},
    {"name": "Rahul Gupta",   "id": "A10581",          "dept": "Analytics"},
    {"name": "Sneha Singh",   "id": "A10582",          "dept": "AI Research"},
    {"name": "Amit Kumar",    "id": "A10583",          "dept": "Operations"},
]

for i, app in enumerate(applicants, start=1):
    img = Image.new("RGB", (600, 400), color=(255, 255, 255))
    d = ImageDraw.Draw(img)

    # Header background
    d.rectangle([0, 0, 600, 80], fill=(99, 102, 241))
    d.text((20, 25), "DOCUVERIFY PRO — EMPLOYEE ID", fill=(255, 255, 255))

    # Details
    d.text((50, 110), "Name:",       fill=(100, 100, 100))
    d.text((200, 110), app["name"],  fill=(0, 0, 0))
    d.text((50, 155), "ID No:",      fill=(100, 100, 100))
    d.text((200, 155), app["id"],    fill=(0, 0, 0))
    d.text((50, 200), "Department:", fill=(100, 100, 100))
    d.text((200, 200), app["dept"],  fill=(0, 0, 0))

    # Footer bar
    d.rectangle([0, 350, 600, 400], fill=(229, 231, 235))
    d.text((20, 360), "CONFIDENTIAL — FOR INTERNAL USE ONLY", fill=(107, 114, 128))

    filename = os.path.join(output_folder, f"sample_id_{i}.jpg")
    img.save(filename)
    print(f"✅ {filename} created")

print("All sample IDs generated successfully!")
