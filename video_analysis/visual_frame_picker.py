import os
import sys
import argparse
import subprocess
import threading
import webbrowser
from flask import Flask, render_template_string, request, redirect, url_for
from werkzeug.middleware.shared_data import SharedDataMiddleware

app = Flask(__name__)
images = []
IMAGE_DIR = ""
LOG_FILE = ""

@app.route("/")
def index():
    if not images:
        return "<h2>No images found in the directory.</h2>"

    idx = int(request.args.get("idx", 0)) % len(images)
    image = images[idx]
    user_home = os.path.expanduser("~")
    if IMAGE_DIR.startswith(user_home):
        display_dir = IMAGE_DIR.replace(user_home, "~")
    else:
        display_dir = IMAGE_DIR
    return render_template_string(
        TEMPLATE,
        image=image,
        idx=idx,
        total=len(images),
        IMAGE_DIR=IMAGE_DIR,
        display_dir=display_dir
    )

@app.route("/action", methods=["POST"])
def action():
    image = request.form["image"]
    command = request.form["command"]
    idx = int(request.form["idx"])
    path = os.path.join(IMAGE_DIR, image)
    image_stem = os.path.splitext(image)[0]

    if command == "open":
        try:
            if sys.platform.startswith("darwin"):
                subprocess.run(["open", path])
            elif sys.platform.startswith("linux"):
                subprocess.run(["xdg-open", path])
            elif sys.platform.startswith("win"):
                os.startfile(path)
        except Exception as e:
            print(f"[ERROR] {e}")

    elif command in ("fadein", "fadeout"):
        # --- Read entries from file ---
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                lines = [line.strip() for line in f if line.strip()]
                line = lines[1] if len(lines) > 1 else ""
                cols = line.strip().split(",")
                fadein_val = cols[0].strip() if len(cols) > 0 else ""
                fadeout_val = cols[1].strip() if len(cols) > 1 else ""
                print(f"[INFO] Read entries from {LOG_FILE}: {fadein_val}, {fadeout_val}")
        else:
            print(f"[INFO] Creating new log file: {LOG_FILE}")
            fadein_val = ""
            fadeout_val = ""


        if command == "fadein":
            fadein_val = image_stem.strip()
        elif command == "fadeout":
            fadeout_val = image_stem.strip()

        print(f"[INFO] Setting fadein: {fadein_val}, fadeout: {fadeout_val}")

        # --- Reconstruct file ---
        new_lines = ["fadein,fadeout", f'{fadein_val},{fadeout_val}']

        with open(LOG_FILE, "w") as f:
            f.write("\n".join(new_lines) + "\n")

    elif command == "delete":
        os.remove(path)
        images.remove(image)
        idx = idx % max(len(images), 1)

    return redirect(url_for("index", idx=idx))


TEMPLATE = """
<!doctype html>
<html>
<head>
  <title>Flask Image Picker</title>
  <script>
    document.addEventListener("keydown", function(event) {
      if (event.key === "ArrowRight") {
        window.location.href = "/?idx={{ (idx + 1) % total }}";
      } else if (event.key === "ArrowLeft") {
        window.location.href = "/?idx={{ (idx - 1) % total }}";
      } else if (event.key === "1") {
        document.getElementById("fadein-form").submit();
      } else if (event.key === "2") {
        document.getElementById("fadeout-form").submit();
      }
    });
  </script>
</head>
<body>
  <h2 style="font-size: 1.2em;">Path: {{ display_dir }}<br>Image: {{ image }}</h2>
  <img src="/static/{{ image }}" width="600" /><br><br>

  <div style="display: flex; gap: 10px; justify-content: center;">
    <form method="post" action="/action" id="fadein-form">
      <input type="hidden" name="image" value="{{ image }}">
      <input type="hidden" name="idx" value="{{ idx }}">
      <input type="hidden" name="command" value="fadein">
      <button type="submit">Verify Fade In</button>
    </form>
    <form method="post" action="/action" id="fadeout-form">
      <input type="hidden" name="image" value="{{ image }}">
      <input type="hidden" name="idx" value="{{ idx }}">
      <input type="hidden" name="command" value="fadeout">
      <button type="submit">Verify Fade Out</button>
    </form>
  </div>

  <p>
    <a href="/?idx={{ (idx - 1) % total }}">Previous</a> |
    <a href="/?idx={{ (idx + 1) % total }}">Next</a>
  </p>

  <p><strong>Keyboard Shortcuts:</strong><br>
    ← = Previous<br>
    → = Next<br>
    1 = Fade In<br>
    2 = Fade Out<br>
  </p>
</body>
</html>
"""

def main():
    global IMAGE_DIR, images, LOG_FILE

    parser = argparse.ArgumentParser(description="Flask Image Picker")
    parser.add_argument("directory", help="Path to folder containing images")
    args = parser.parse_args()

    IMAGE_DIR = os.path.abspath(args.directory)
    LOG_FILE = os.path.join(os.path.dirname(IMAGE_DIR), "env_visible_timebounds.txt")

    if not os.path.isdir(IMAGE_DIR):
        print(f"[ERROR] Directory not found: {IMAGE_DIR}")
        sys.exit(1)

    images = [f for f in sorted(os.listdir(IMAGE_DIR))
              if f.lower().endswith((".jpg", ".png", ".jpeg", ".bmp", ".gif"))]

    app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
        '/static': IMAGE_DIR
    })

    def open_browser():
        webbrowser.open_new(f"http://127.0.0.1:5000/")

    threading.Timer(1.0, open_browser).start()
    app.run(debug=True)

if __name__ == "__main__":
    main()