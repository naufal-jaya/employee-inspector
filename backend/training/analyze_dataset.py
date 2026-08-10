import os
import yaml
from collections import Counter

# Get the directory where this script is located (backend/training)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')

# 1. Load class names from data.yaml
with open(os.path.join(DATA_DIR, 'data.yaml'), 'r') as f:
    data_yaml = yaml.safe_load(f)
class_names = data_yaml['names']

# 2. Count all labels in train and valid directories
label_dirs = [os.path.join(DATA_DIR, 'train', 'labels'), os.path.join(DATA_DIR, 'valid', 'labels')] 
class_counts = Counter()

for d in label_dirs:
    if os.path.exists(d):
        for filename in os.listdir(d):
            if filename.endswith('.txt'):
                with open(os.path.join(d, filename), 'r') as f:
                    for line in f:
                        parts = line.strip().split()
                        if parts:
                            class_id = int(parts[0])
                            class_counts[class_id] += 1

# 3. Print the results
print("\n" + "="*50)
print(f"{'CLASS NAME':<25} | {'COUNT':<10}")
print("="*50)

total_objects = 0
for class_id in range(len(class_names)):
    count = class_counts.get(class_id, 0)
    total_objects += count
    print(f"{class_names[class_id]:<25} | {count:<10}")

print("="*50)
print(f"{'TOTAL OBJECTS':<25} | {total_objects:<10}")
print("="*50 + "\n")
