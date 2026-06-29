from flask import Flask, render_template
from datetime import datetime

app = Flask(__name__)

@app.route("/")
def index():
    return render_template(
        "index.html",
        time=datetime.now().strftime("%H:%M"),
        title="MusicStreamer",
        status="Development mode"
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
