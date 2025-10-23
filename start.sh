#!/usr/bin/env bash
set -e

# Update and install system packages
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
    x11vnc xvfb xfce4 xfce4-goodies pulseaudio pulseaudio-utils \
    websockify novnc python3-pip git

# Make sure noVNC is available
if [ ! -d "/usr/share/novnc" ]; then
  echo "Downloading noVNC..."
  sudo git clone https://github.com/novnc/noVNC.git /usr/share/novnc
  sudo git clone https://github.com/novnc/websockify.git /usr/share/novnc/utils/websockify || true
fi

# Install Python packages
python3 -m pip install --upgrade pip
pip3 install -r requirements.txt

# Start PulseAudio
pulseaudio --check || pulseaudio --start || true

# Create VNC password if defined
if [ -n "$VNC_PASSWORD" ]; then
  echo "Setting VNC password"
  mkdir -p /tmp
  /usr/bin/printf "%s\n%s\n" "$VNC_PASSWORD" "$VNC_PASSWORD" | /usr/bin/x11vnc -storepasswd "$VNC_PASSWORD" /tmp/.vncpasswd || true
fi

# Start the Flask app (main.py)
echo "Starting Cloud Desktop..."
python3 main.py
