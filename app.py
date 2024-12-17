from flask import Flask
from config import Config
from database import init_db
from routes import routes_bp

app = Flask(__name__)
app.config.from_object(Config)

# Blueprint登録
app.register_blueprint(routes_bp)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
