from flask import Flask, render_template_string, request, redirect
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

USERNAME = os.getenv("CLOUD_USER", "user")
PASSWORD = os.getenv("CLOUD_PASS", "pass")

html = """
<!doctype html>
<html>
<head>
  <title>MIKI Cloud OS</title>
  <style>
    body {font-family:sans-serif;background:#0b0b0b;color:#fff;margin:0;padding:0;}
    .center {display:flex;align-items:center;justify-content:center;height:100vh;}
    form {background:#111;padding:30px;border-radius:10px;box-shadow:0 0 10px #000;width:300px;}
    input{width:100%;margin:5px 0;padding:10px;border:none;border-radius:5px;}
    button{width:100%;padding:10px;background:#0099ff;border:none;border-radius:5px;color:white;cursor:pointer;}
    iframe{width:100%;height:100vh;border:none;}
  </style>
</head>
<body>
{% if not ok %}
<div class="center">
  <form method="post">
    <h2>Cloud OS Login</h2>
    <input name="user" placeholder="Username" required>
    <input type="password" name="pass" placeholder="Password" required>
    <button>Login</button>
  </form>
</div>
{% else %}
<iframe src="https://duckduckgo.com" title="Cloud Desktop"></iframe>
{% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET","POST"])
def index():
    if request.method == "POST":
        if request.form["user"] == USERNAME and request.form["pass"] == PASSWORD:
            resp = redirect("/")
            resp.set_cookie("auth", "1")
            return resp
    ok = request.cookies.get("auth") == "1"
    return render_template_string(html, ok=ok)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
