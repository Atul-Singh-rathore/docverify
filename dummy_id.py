import os
from PIL import Image, ImageDraw

# Create a dedicated folder for sample IDs if it doesn't exist
output_folder = "sample_images"
os.makedirs(output_folder, exist_ok=True)

# List of sample applicants for batch generation
applicants = [
    {"name": "Aarav Sharma", "id": "202310101150271", "dept": "Data Science"},
    {"name": "Priya Verma", "id": "A10580", "dept": "Engineering"},
    {"name": "Rahul Gupta", "id": "A10581", "dept": "Analytics"},
    {"name": "Sneha Singh", "id": "A10582", "dept": "AI Research"},
    {"name": "Amit Kumar", "id": "A10583", "dept": "Operations"},
]

for i, app in enumerate(applicants, start=1):
  # Create a blank white image for an ID card
  img = Image.new("RGB", (600, 400), color=(255, 255, 255))
  d = ImageDraw.Draw(img)

  # Draw header background
  d.rectangle([0, 0, 600, 80], fill=(99, 102, 241))

  # Add text details
  d.text((20, 30), "DOCUVERIFY PRO - EMPLOYEE ID", fill=(255, 255, 255))
  d.text((50, 140), f"NAME: {app['name']}", fill=(0, 0, 0))
  d.text((50, 190), f"ID: {app['id']}", fill=(0, 0, 0))
  d.text((50, 240), f"DEPARTMENT: {app['dept']}", fill=(0, 0, 0))

  # Save unique image file inside the sample_images folder
  filename = os.path.join(output_folder, f"sample_id_{i}.jpg")
  img.save(filename)
  print(f"{filename} successfully created!")

print("All sample IDs generated cleanly without any conflicts!")