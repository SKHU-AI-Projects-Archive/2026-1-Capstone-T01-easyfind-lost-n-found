from ultralytics import YOLO
import time

model = YOLO("yolo26x.pt")  # Load a model

model.export(format="engine", 
             imgsz = 640 ,
            #  int8=True, 
             half=True,
             dynamic = True,
             data = 'coco8.yaml',
            #  workspace = 4
             )