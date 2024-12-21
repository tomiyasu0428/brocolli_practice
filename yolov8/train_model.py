from ultralytics import YOLO

# YOLOモデルのロード
model = YOLO("yolov8n.pt")

# トレーニング実行
model.train(data="yolov8/configs/broccoli_dataset.yaml", epochs=10, imgsz=640)
