from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file
from werkzeug.utils import secure_filename
from database import get_db
from image_proces import detect_broccoli_size
import os
from config import Config
from werkzeug.security import generate_password_hash, check_password_hash  # ハッシュ化用

routes_bp = Blueprint("routes", __name__)


# ユーザー登録機能
@routes_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)  # パスワードをハッシュ化

        with get_db() as conn:
            try:
                conn.execute(
                    "INSERT INTO user (username, password) VALUES (?, ?)", (username, hashed_password)
                )
                conn.commit()
                flash("登録が完了しました！ログインしてください。", "success")
                return redirect(url_for("routes.login"))
            except Exception as e:
                flash("そのユーザー名はすでに使用されています。", "danger")
                print(f"Error: {e}")
    return render_template("register.html")


# ログイン機能
@routes_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        with get_db() as conn:
            user = conn.execute("SELECT * FROM user WHERE username = ?", (username,)).fetchone()

            # ハッシュ化されたパスワードを検証
            if user and check_password_hash(user["password"], password):
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                session.permanent = True
                flash("ログインに成功しました！", "success")
                return redirect(url_for("routes.dashboard"))
            else:
                flash("ユーザー名またはパスワードが違います。", "danger")
    return render_template("login.html")


# ログアウト機能
@routes_bp.route("/logout")
def logout():
    session.clear()
    flash("ログアウトしました。", "info")
    return redirect(url_for("routes.login"))


# ダッシュボード機能
@routes_bp.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user_id" not in session:
        flash("ログインしてください。", "danger")
        return redirect(url_for("routes.login"))

    username = session.get("username", "ゲスト")
    processed_image = None

    if request.method == "POST":
        file = request.files["file"]
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
            os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

            file.save(filepath)
            result_image = detect_broccoli_size(filepath)

            with get_db() as conn:
                conn.execute(
                    "INSERT INTO upload_history (user_id, filename, result_image) VALUES (?, ?, ?)",
                    (session["user_id"], filename, result_image),
                )
                conn.commit()

            session["processed_image"] = result_image
            flash("画像が処理されました！", "success")
            return redirect(url_for("routes.dashboard"))

    processed_image = session.pop("processed_image", None)
    with get_db() as conn:
        history = conn.execute(
            "SELECT * FROM upload_history WHERE user_id = ?", (session["user_id"],)
        ).fetchall()

    return render_template(
        "dashboard.html", username=username, history=history, processed_image=processed_image
    )


# ファイル削除機能
@routes_bp.route("/delete/<int:file_id>", methods=["POST"])
def delete_file(file_id):
    if "user_id" not in session:
        flash("ログインしてください。", "danger")
        return redirect(url_for("routes.login"))

    with get_db() as conn:
        # 該当のファイルがユーザーのものであるか確認
        file_entry = conn.execute(
            "SELECT * FROM upload_history WHERE id = ? AND user_id = ?", (file_id, session["user_id"])
        ).fetchone()

        if file_entry:
            file_path = file_entry["result_image"]
            # ファイルが存在すれば削除
            if os.path.exists(os.path.join(Config.UPLOAD_FOLDER, file_path)):
                os.remove(os.path.join(Config.UPLOAD_FOLDER, file_path))

            # データベースからレコードを削除
            conn.execute("DELETE FROM upload_history WHERE id = ?", (file_id,))
            conn.commit()
            flash("ファイルが削除されました。", "success")
        else:
            flash("ファイルが見つかりません。", "danger")

    return redirect(url_for("routes.dashboard"))


# ファイルダウンロード機能
@routes_bp.route("/download/<path:filename>")
def download(filename):
    # パスを安全に構築
    file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
    file_path = os.path.abspath(file_path)

    # セキュリティ対策: UPLOAD_FOLDERの外へのアクセスを防止
    if not file_path.startswith(os.path.abspath(Config.UPLOAD_FOLDER)):
        flash("不正なファイルパスです。", "danger")
        return redirect(url_for("routes.dashboard"))

    # ファイルの存在確認
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        flash("ファイルが見つかりません。", "danger")
        return redirect(url_for("routes.dashboard"))
