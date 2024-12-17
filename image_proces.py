import cv2
import os
import numpy as np


def detect_broccoli_size(image_path):
    image = cv2.imread(image_path)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    lower_green = np.array([35, 50, 50])
    upper_green = np.array([85, 255, 255])

    mask = cv2.inRange(hsv, lower_green, upper_green)
    result = cv2.bitwise_and(image, image, mask=mask)

    gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < 500:
            continue

        ((x, y), radius) = cv2.minEnclosingCircle(contour)
        cv2.circle(image, (int(x), int(y)), int(radius), (0, 255, 0), 2)

        size_label = "Small"
        if area > 3000:
            size_label = "Large"
        elif area > 1500:
            size_label = "Medium"

        cv2.putText(
            image, f"{size_label}", (int(x) - 20, int(y) - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2
        )

    result_path = os.path.join("static", "processed_" + os.path.basename(image_path))
    cv2.imwrite(result_path, image)
    return result_path
