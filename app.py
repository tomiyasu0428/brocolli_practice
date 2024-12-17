import cv2
import numpy as np
from flask import Flask, request, render_template, redirect, url_for
import os

app = Flask(__name__)


# 画像処理関数
def detect_broccoli_size(image_path):
    # 画像読み込み
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # 輪郭抽出のための二値化
    _, thresh = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY_INV)

    # 輪郭検出
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    sizes = []
    for contour in contours:
        # 最小外接円を取得して直径を計測
        ((x, y), radius) = cv2.minEnclosingCircle(contour)
        diameter = radius * 2  # 直径

        # 高度が一定ならスケール変換係数を利用 (例: 1px = 0.5cm)
        cm_diameter = diameter * 0.33  # 仮のスケール係数

        # サイズ分類
        if cm_diameter < 20:
            size_category = "Other"
        elif cm_diameter < 28:
            size_category = "M"
        elif cm_diameter < 33:
            size_category = "L"
        else:
            size_category = "2L"

        sizes.append((int(x), int(y), cm_diameter, size_category))
        cv2.circle(image, (int(x), int(y)), int(radius), (0, 255, 0), 2)  # 可視化用

    output_path = "static/output.jpg"
    cv2.imwrite(output_path, image)
    return sizes, output_path


# Flaskルート
@app.route("/", methods=["GET", "POST"])
def upload_image():
    if request.method == "POST":
        file = request.files["file"]
        if file:
            file_path = os.path.join("static", file.filename)
            file.save(file_path)
            sizes, output_path = detect_broccoli_size(file_path)
            return render_template("result.html", sizes=sizes, output_image=output_path)
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
