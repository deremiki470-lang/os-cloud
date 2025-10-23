# main.py
import os
import time
import subprocess
import signal
from flask import Flask, request, redirect, render_template_string
from dotenv import load_dotenv

# Load .env
load_dotenv()

CLOUD_USER = os.getenv("CLOUD_USER", "user")
CLOUD_PASS = os.getenv("CLOUD_PASS", "pass")
VNC_PASSWORD = os.getenv("VNC_PASSWORD", "vncpass")
PORT = int(os.getenv("PORT", "8080"))
DISPLAY_NUM = os.getenv("DISPLAY_NUM", ":1")
VNC_PORT = os.getenv("VNC_PORT", "5901")
WEBSOCKIFY_PORT = os.getenv("WEBSOCKIFY_PORT", "6080")
NOVNC_WEBROOT = os.getenv("NOVNC_WEBROOT", "/usr/share/novnc")

# Process handles so we can terminate when needed
processes = []

def start_process(cmd, env=None):
    print("Starting:", " ".join(cmd))
    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    processes.append(p)
    time.sleep(0.7)  # brief pause to let things start
    return p

def start_desktop_pipeline():
    # Start Xvfb
    start_process(["Xvfb", DISPLAY_NUM, "-screen", "0", "1280x720x24"])

    # Start PulseAudio (optional, but helpful for audio)
    start_process(["pulseaudio", "--start"])

    # Start xfce4 session bound to the virtual display
    env = os.environ.copy()
    env["DISPLAY"] = DISPLAY_NUM
    # startxfce4 may spawn multiple processes; use --replace to avoid conflicts
    start_process(["/bin/sh", "-c", "startxfce4 &"], env=env)

    # Give xfce time to spin up windows manager, panels etc
    time.sleep(2)

    # Start x11vnc attached to DISPLAY_NUM and set password
    # Create a vncpasswd file
    vnc_passwd_file = "/tmp/.vncpasswd"
    p = subprocess.Popen(["/usr/bin/printf", VNC_PASSWORD+"\n"+VNC_PASSWORD+"\n"], stdout=subprocess.PIPE)
    # Write password via vncpasswd with -f to file (if available) else use x11vnc -passwd
    try:
        # try using x11vnc's -storepasswd if available
        subprocess.run(["x11vnc", "-storepasswd", VNC_PASSWORD, vnc_passwd_file], check=True)
        start_process(["x11vnc", "-display", DISPLAY_NUM, "-rfbport", VNC_PORT, "-rfbauth", vnc_passwd_file, "-forever", "-shared", "-noxdamage"])
    except Exception:
        # fallback to x11vnc without stored passwd (not recommended)
        start_process(["x11vnc", "-display", DISPLAY_NUM, "-rfbport", VNC_PORT, "-forever", "-shared", "-noxdamage"])

    # Start websockify (noVNC) to serve the noVNC web client and bridge websocket to VNC
    # If /usr/share/novnc is different on your system, edit NOVNC_WEBROOT env var.
    start_process(["websockify", "--web", NOVNC_WEBROOT, WEBSOCKIFY_PORT, "localhost:"+VNC_PORT])

def terminate_processes():
    print("Terminating child processes...")
    for p in processes:
        try:
            p.terminate()
        except Exception:
            pass
    # give some time then kill
    time.sleep(1)
    for p in processes:
        if p.poll() is None:
            try:
                p.kill()
            except Exception:
                pass

# Flask application
app = Flask(__name__)

login_html = """
<!doctype html>
<html>
<head>
  <title>Cloud Desktop Login</title>
  <style>
    body { font-family: system-ui, Arial; background:#0b0b0b; color:#fff; display:flex; align-items:center; justify-content:center; height:100vh;}
    form { background:#111; padding:24px; border-radius:8px; width:320px; }
    input { display:block; width:100%; padding:10px; margin:8px 0; border-radius:6px; border:1px solid #333; }
    button { width:100%; padding:10px; background:#0a84ff; border:none; color:#fff; border-radius:6px; cursor:pointer; }
    .small { font-size:12px; color:#999; margin-top:8px; }
  </style>
</head>
<body>
  {% if not ok %}
  <form method="post">
    <h3 style="margin:0 0 8px 0">Cloud Desktop</h3>
    <input name="user" placeholder="Username" required />
    <input name="pass" placeholder="Password" type="password" required />
    <button type="submit">Login</button>
    <div class="small">Connects you to the desktop stream (noVNC)</div>
  </form>
  {% else %}
  <div style="width:100vw;height:100vh;">
    <iframe src="/desktop" style="width:100%;height:100%;border:none;"></iframe>
  </div>
  {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET","POST"])
def index():
    if request.method == "POST":
        if request.form.get("user") == CLOUD_USER and request.form.get("pass") == CLOUD_PASS:
            resp = redirect("/desktop")
            resp.set_cookie("auth","1", max_age=60*60*24)
            return resp
    ok = request.cookies.get("auth") == "1"
    return render_template_string(login_html, ok=ok)

@app.route("/desktop")
def desktop():
    if request.cookies.get("auth") != "1":
        return redirect("/")
    # The noVNC client page (vnc.html) will be served by websockify at /vnc.html
    # We point it to ws://<host>:WEBSOCKIFY_PORT/?token=... but websockify serves it directly
    host = request.host.split(":")[0]
    scheme = "https" if request.scheme == "https" else "http"
    noVNC_url = f"{scheme}://{host}:{WEBSOCKIFY_PORT}/vnc.html?host={host}&port={WEBSOCKIFY_PORT}"
    # To ease browser-origin restrictions we'll load the noVNC page locally via websockify's webroot
    # Simply embed the relative path: the browser will request /vnc.html from the same origin if proxied.
    # But since websockify may be on a different port, we embed its absolute URL.
    return f'<iframe src="{noVNC_url}" style="width:100%;height:100%;border:none;"></iframe>'

if __name__ == "__main__":
    try:
        # Start the desktop pipeline in background
        start_desktop_pipeline()
        print(f"Starting Flask on 0.0.0.0:{PORT}")
        app.run(host="0.0.0.0", port=PORT)
    except KeyboardInterrupt:
        pass
    finally:
        terminate_processes()
