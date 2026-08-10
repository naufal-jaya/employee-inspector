import os
import shutil
from pathlib import Path
from ultralytics import YOLO

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')
MODEL_PATH = os.path.join(SCRIPT_DIR, 'yolov8n.pt')

# In COCO, Person is 0. In our dataset, Person is 11.
TARGET_CLASS_ID = 11

def backup_labels():
    print("Creating backups of existing labels...")
    for split in ['train', 'valid']:
        labels_dir = os.path.join(DATA_DIR, split, 'labels')
        backup_dir = os.path.join(DATA_DIR, split, 'labels_backup')
        
        if not os.path.exists(labels_dir):
            continue
            
        if not os.path.exists(backup_dir):
            print(f"Backing up {labels_dir} to {backup_dir}")
            shutil.copytree(labels_dir, backup_dir)
        else:
            print(f"Backup already exists at {backup_dir}, skipping backup.")

def auto_annotate():
    print(f"Loading pretrained model: {MODEL_PATH}")
    model = YOLO(MODEL_PATH)
    
    for split in ['train', 'valid']:
        images_dir = os.path.join(DATA_DIR, split, 'images')
        labels_dir = os.path.join(DATA_DIR, split, 'labels')
        
        if not os.path.exists(images_dir):
            print(f"Skipping {split} - images directory not found.")
            continue
            
        print(f"\nProcessing {split} dataset...")
        
        # Get all image files
        image_files = [f for f in os.listdir(images_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        total = len(image_files)
        persons_added = 0
        
        for idx, img_file in enumerate(image_files):
            img_path = os.path.join(images_dir, img_file)
            txt_filename = os.path.splitext(img_file)[0] + '.txt'
            txt_path = os.path.join(labels_dir, txt_filename)
            
            # Predict only class 0 (Person), confidence 0.5
            results = model.predict(img_path, classes=[0], conf=0.5, verbose=False)
            
            new_lines = []
            for r in results:
                for box in r.boxes:
                    # YOLO format: class_id x_center y_center width height (normalized)
                    x, y, w, h = box.xywhn[0].tolist()
                    new_lines.append(f"{TARGET_CLASS_ID} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n")
            
            if new_lines:
                # Ensure the labels directory exists
                os.makedirs(labels_dir, exist_ok=True)
                # Append the new Person boxes to the file
                with open(txt_path, 'a') as f:
                    f.writelines(new_lines)
                persons_added += len(new_lines)
            
            if (idx + 1) % 500 == 0:
                print(f"Processed {idx + 1}/{total} images. Added {persons_added} missing person boxes so far...")
                
        print(f"Done with {split}. Total new Person boxes added: {persons_added}")

if __name__ == "__main__":
    print("Starting Auto-Annotation process...\n")
    backup_labels()
    print("\n-----------------------------------")
    auto_annotate()
    print("\nAnnotation complete! Run analyze_dataset.py again to verify the new counts.")
