import os
import yaml
from collections import Counter, defaultdict

# Get the directory where this script is located (backend/training)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')

# 1. Load class names from data.yaml
with open(os.path.join(DATA_DIR, 'data.yaml'), 'r') as f:
    data_yaml = yaml.safe_load(f)
class_names = data_yaml['names']

# 2. Count instances and unique image occurrences
label_dirs = [
    ('train', os.path.join(DATA_DIR, 'train', 'labels')),
    ('valid', os.path.join(DATA_DIR, 'valid', 'labels'))
]

class_instance_counts = Counter()
class_image_counts = Counter()
total_images = 0

# Co-occurrence tracking
person_only_images = 0
person_and_ppe_images = 0
ppe_only_images = 0
background_images = 0

# Determine class IDs for Person vs PPE
person_id = None
ppe_ids = set()
for idx, name in enumerate(class_names):
    if name.lower() == 'person':
        person_id = idx
    else:
        ppe_ids.add(idx)

for split_name, d in label_dirs:
    if os.path.exists(d):
        for filename in os.listdir(d):
            if filename.endswith('.txt'):
                total_images += 1
                file_path = os.path.join(d, filename)
                classes_in_file = set()
                
                with open(file_path, 'r') as f:
                    for line in f:
                        parts = line.strip().split()
                        if parts:
                            class_id = int(parts[0])
                            class_instance_counts[class_id] += 1
                            classes_in_file.add(class_id)
                
                # Track unique image counts
                for cid in classes_in_file:
                    class_image_counts[cid] += 1
                
                # Co-occurrence breakdown
                has_person = (person_id in classes_in_file) if person_id is not None else False
                has_ppe = bool(classes_in_file.intersection(ppe_ids))
                
                if has_person and has_ppe:
                    person_and_ppe_images += 1
                elif has_person and not has_ppe:
                    person_only_images += 1
                elif has_ppe and not has_person:
                    ppe_only_images += 1
                else:
                    background_images += 1

# 3. Print the results
print("\n" + "="*65)
print(f" DATASET ANALYSIS (Total Images: {total_images})")
print("="*65)
print(f"{'CLASS NAME':<22} | {'BOXES (INSTANCES)':<18} | {'IMAGES CONTAINING':<18}")
print("-" * 65)

total_boxes = 0
for class_id in range(len(class_names)):
    name = class_names[class_id]
    boxes = class_instance_counts.get(class_id, 0)
    imgs = class_image_counts.get(class_id, 0)
    total_boxes += boxes
    img_pct = (imgs / total_images * 100) if total_images > 0 else 0.0
    print(f"{name:<22} | {boxes:<18} | {imgs:<5} ({img_pct:.1f}%)")

print("="*65)
print(f"{'TOTAL BOUNDING BOXES':<22} | {total_boxes:<18} |")
print("="*65)

print("\n" + "="*65)
print(" IMAGE CO-OCCURRENCE BREAKDOWN")
print("="*65)
print(f"Person + PPE (Hardhat/Vest): {person_and_ppe_images:<6} ({person_and_ppe_images/total_images*100:.1f}%)")
print(f"Person ONLY (No PPE)       : {person_only_images:<6} ({person_only_images/total_images*100:.1f}%)")
print(f"PPE ONLY (No Person Box)   : {ppe_only_images:<6} ({ppe_only_images/total_images*100:.1f}%)")
if background_images > 0:
    print(f"Background (Empty/No Boxes): {background_images:<6} ({background_images/total_images*100:.1f}%)")
print("="*65 + "\n")

