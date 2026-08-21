"""
Oversample PPE-context images to fix Person label-assignment starvation.

Problem (per Claude's diagnosis):
  YOLOv8's TaskAlignedAssigner picks anchor points ranked by cls_score × IoU.
  Hardhat/Vest boxes sit *inside* the Person box. In PPE-context images, those
  anchors keep getting claimed by the smaller nested classes, starving Person
  of positive assignments. The model only sees "Person without competing boxes"
  in the majority (~866) of training images, so it learns to fail exactly where
  PPE is present.

Fix:
  Repeat PPE-context images (images containing Hardhat OR Safety Vest) 3x in
  the training list. This directly rebalances the co-occurrence ratio so the
  assigner sees "Person nested with PPE" far more often during training.

Usage:
  cd backend/training
  python oversample.py
  # Then train with the generated data_oversampled.yaml:
  python train.py --data ./data/data_oversampled.yaml --epochs 50

Class indices (from data.yaml):
  0: Hardhat
  1: Person
  2: Safety Vest
  PPE classes = {0, 2}
"""

from pathlib import Path

# ── config ───────────────────────────────────────────────────────────────────
TRAINING_DIR = Path(__file__).parent          # backend/training/
DATA_YAML    = TRAINING_DIR / "data" / "data.yaml"
TRAIN_IMGS   = TRAINING_DIR / "data" / "train" / "images"
TRAIN_LBLS   = TRAINING_DIR / "data" / "train" / "labels"

OUTPUT_TXT   = TRAINING_DIR / "data" / "train_oversampled.txt"
OUTPUT_YAML  = TRAINING_DIR / "data" / "data_oversampled.yaml"

PPE_CLASSES      = {0, 2}   # Hardhat=0, Safety Vest=2  (Person=1 is NOT PPE)
OVERSAMPLE_FACTOR = 3        # repeat PPE-context images this many extra times
# ─────────────────────────────────────────────────────────────────────────────


def has_ppe(label_path: Path) -> bool:
    """Return True if the label file contains at least one PPE annotation."""
    if not label_path.exists():
        return False
    with open(label_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            cls_id = int(line.split()[0])
            if cls_id in PPE_CLASSES:
                return True
    return False


def main():
    img_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

    all_imgs = sorted(
        p for p in TRAIN_IMGS.iterdir()
        if p.suffix.lower() in img_extensions
    )

    if not all_imgs:
        print(f"[ERROR] No images found in {TRAIN_IMGS}")
        return

    all_paths  = []   # absolute path strings for every training image
    ppe_paths  = []   # absolute paths for PPE-context images only

    for img in all_imgs:
        lbl = TRAIN_LBLS / (img.stem + ".txt")
        abs_str = str(img.resolve())
        all_paths.append(abs_str)
        if has_ppe(lbl):
            ppe_paths.append(abs_str)

    # Oversample: original list + (factor) extra copies of PPE-context images
    oversampled = all_paths + ppe_paths * OVERSAMPLE_FACTOR

    # Write the flat image-path list
    with open(OUTPUT_TXT, "w") as f:
        f.write("\n".join(oversampled) + "\n")

    print(f"Total training images   : {len(all_paths)}")
    print(f"PPE-context images      : {len(ppe_paths)}")
    print(f"Oversampled total       : {len(oversampled)}")
    print(f"Written image list to   : {OUTPUT_TXT}")

    # Write a companion data.yaml that points train at the txt file
    original_yaml = DATA_YAML.read_text()
    # Replace only the train: line; keep val/test/nc/names unchanged
    new_yaml_lines = []
    for line in original_yaml.splitlines():
        if line.strip().startswith("train:"):
            new_yaml_lines.append("train: ./train_oversampled.txt")
        else:
            new_yaml_lines.append(line)

    with open(OUTPUT_YAML, "w") as f:
        f.write("\n".join(new_yaml_lines) + "\n")

    print(f"Written oversampled yaml: {OUTPUT_YAML}")
    print()
    print("Next steps:")
    print("  python train.py --data ./data/data_oversampled.yaml --epochs 50")


if __name__ == "__main__":
    main()
