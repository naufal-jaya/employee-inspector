"""
Fine-tuning script — run this OUTSIDE the docker-compose demo stack,
during development, to produce backend/model/weights/best.pt.

Usage:
    1. Download a PPE dataset in YOLO format, e.g.:
       "Construction Site Safety Image Dataset" (Roboflow Universe)
       -> https://universe.roboflow.com/  (search "construction site safety")
       Export as "YOLOv8" format -> gives you a folder with data.yaml,
       train/, valid/, test/.

    2. Place it at: backend/training/data/data.yaml (or point --data to it)

    3. Run:
       pip install ultralytics
       python train.py --data ./data/data.yaml --epochs 50

    4. Copy the resulting best.pt:
       cp runs/detect/train/weights/best.pt ../model/weights/best.pt

Note: this script is intentionally run manually / offline. It is NOT
called by the API at request time — inference in main.py only loads an
already fine-tuned .pt file, keeping the MVP's inference path static and
synchronous as required by the competition rules.
"""

import argparse
from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser(description="Fine-tune YOLOv8 for PPE detection")
    parser.add_argument("--data", type=str, default="./data/data.yaml",
                         help="Path to dataset's data.yaml (YOLO format)")
    parser.add_argument("--base-model", type=str, default="yolov8n.pt",
                         help="Pretrained base checkpoint to fine-tune from")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    args = parser.parse_args()

    # Start from a COCO-pretrained checkpoint (transfer learning),
    # then fine-tune head + backbone on the PPE-specific classes.
    model = YOLO(args.base_model)

    model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        freeze=0,             # Fully unfreeze — enough data to fine-tune end-to-end
        hsv_s=0.5,            # Mild saturation randomize, not aggressive
        lr0=0.001,            # Smoother LR for full fine-tune
        cos_lr=True,          # Cosine LR decay — better convergence
        close_mosaic=10,      # Disable mosaic for last 10 epochs — helps precise localization
        patience=10,          # early stop if val metrics plateau
        project="runs/detect",
        name="ppe_finetune",
    )

    metrics = model.val()
    print("Validation metrics:", metrics.results_dict)
    print(
        "\nDone. Copy the best checkpoint into the backend, e.g.:\n"
        "  cp runs/detect/ppe_finetune/weights/best.pt ../model/weights/best.pt"
    )


if __name__ == "__main__":
    main()
