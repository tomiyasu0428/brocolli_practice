import cv2
import os
import sqlite3
import numpy as np
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from werkzeug.utils import secure_filename


class Config:
    SECRET_KEY = "your_random_secret_key"
    DATABASE_URL = os.path.abspath("database.db")  # データベースファイルの絶対パス
    DEBUG = True
    UPLOAD_FOLDER = os.path.join(os.getcwd(), "static", "static_upload")  # アップロード先のフォルダ
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)  # セッションの有効期限


# Flaskアプリケーションの初期化
app = Flask(__name__)
app.config.from_object(Config)

DATABASE = app.config["DATABASE_URL"]  # SQLiteのURL
app.secret_key = app.config["SECRET_KEY"]

# アップロード先ディレクトリが存在しない場合は作成
if not os.path.exists(app.config["UPLOAD_FOLDER"]):
    os.makedirs(app.config["UPLOAD_FOLDER"])


# データベース接続関数
def get_db():
    # ディレクトリが存在するか確認（なければ作成）
    db_dir = os.path.dirname(DATABASE)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)

    conn = sqlite3.connect(DATABASE)  # 絶対パスを使って接続
    conn.row_factory = sqlite3.Row
    return conn


# データベース初期化
def init_db():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS upload_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                result_image TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES user (id)
            )
        """
        )
        conn.commit()


# ユーザー登録
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        with get_db() as conn:
            try:
                conn.execute("INSERT INTO user (username, password) VALUES (?, ?)", (username, password))
                conn.commit()
                flash("登録が完了しました！ログインしてください。", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("そのユーザー名はすでに使用されています。", "danger")

    return render_template("register.html")


# ユーザーログイン
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        with get_db() as conn:
            user = conn.execute(
                "SELECT * FROM user WHERE username = ? AND password = ?", (username, password)
            ).fetchone()
            if user:
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                session.permanent = True
                flash("ログインに成功しました！", "success")
                return redirect(url_for("dashboard"))
            else:
                flash("ユーザー名またはパスワードが違います。", "danger")

    return render_template("login.html")


# 画像処理関数
def detect_broccoli_size(image_path):
    # 画像を読み込む
    image = cv2.imread(image_path)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # 緑色の範囲を指定（ブロッコリーの色）
    lower_green = np.array([35, 50, 50])
    upper_green = np.array([85, 255, 255])

    # 緑色の部分を抽出
    mask = cv2.inRange(hsv, lower_green, upper_green)
    result = cv2.bitwise_and(image, image, mask=mask)

    # グレースケール変換と輪郭検出
    gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        area = cv2.contourArea(contour)

        # 面積が小さすぎるものは無視（ノイズ除去）
        if area < 500:
            continue

        # 外接円を描画
        ((x, y), radius) = cv2.minEnclosingCircle(contour)
        cv2.circle(image, (int(x), int(y)), int(radius), (0, 255, 0), 2)

        # サイズ分類
        size_label = "Small"
        if area > 3000:
            size_label = "Large"
        elif area > 1500:
            size_label = "Medium"

        # サイズを表示
        cv2.putText(
            image, f"{size_label}", (int(x) - 20, int(y) - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2
        )

    # 結果画像の保存
    result_path = os.path.join("static", "processed_" + os.path.basename(image_path))
    cv2.imwrite(result_path, image)
    return result_path


# ダッシュボード
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user_id" not in session:
        flash("ログインしてください。", "danger")
        return redirect(url_for("login"))

    username = session.get("username", "ゲスト")  # KeyErrorを回避しデフォルト値を設定
    processed_image = None  # 一時的な処理結果表示

    if request.method == "POST":
        file = request.files["file"]
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

            # アップロード先ディレクトリが存在しない場合は作成
            if not os.path.exists(app.config["UPLOAD_FOLDER"]):
                os.makedirs(app.config["UPLOAD_FOLDER"])

            file.save(filepath)
            result_image = detect_broccoli_size(filepath)

            # 処理結果をDBに保存
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO upload_history (user_id, filename, result_image) VALUES (?, ?, ?)",
                    (session["user_id"], filename, result_image),
                )
                conn.commit()

            # sessionに一時的なデータを保存
            session["processed_image"] = result_image
            flash("画像が処理されました！", "success")
            return redirect(url_for("dashboard"))

    # 一時的な処理結果を表示
    processed_image = session.pop("processed_image", None)

    with get_db() as conn:
        history = conn.execute(
            "SELECT * FROM upload_history WHERE user_id = ?", (session["user_id"],)
        ).fetchall()

    return render_template(
        "dashboard.html",
        username=username,  # KeyError回避済み
        history=history,
        processed_image=processed_image,
    )


# ファイルダウンロード
@app.route("/download/<path:filename>")
def download(filename):
    return send_file(filename, as_attachment=True)


# ファイル削除のルート
@app.route("/delete/<int:file_id>", methods=["POST"])
def delete_file(file_id):
    if "user_id" not in session:
        flash("ログインしてください。", "danger")
        return redirect(url_for("login"))

    with get_db() as conn:
        # ユーザーが所有するファイルか確認
        file_entry = conn.execute(
            "SELECT * FROM upload_history WHERE id = ? AND user_id = ?", (file_id, session["user_id"])
        ).fetchone()

        if not file_entry:
            flash("ファイルが存在しないか、削除権限がありません。", "danger")
            return redirect(url_for("dashboard"))

        # ファイルのパスを取得して削除
        file_path = file_entry["result_image"]
        if os.path.exists(file_path):
            os.remove(file_path)
            flash("ファイルが削除されました。", "success")
        else:
            flash("ファイルが見つかりませんでした。", "warning")

        # データベースから履歴を削除
        conn.execute("DELETE FROM upload_history WHERE id = ?", (file_id,))
        conn.commit()

    return redirect(url_for("dashboard"))


# ログアウト
@app.route("/logout")
def logout():
    session.clear()
    flash("ログアウトしました。", "info")
    return redirect(url_for("login"))


if __name__ == "__main__":
    init_db()  # データベース初期化
    if not os.path.exists("static"):
        os.makedirs("static")
    app.run(debug=True)
