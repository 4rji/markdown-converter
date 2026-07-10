# Run Markdown Converter as a systemd Service

This guide shows how to run the Markdown Converter Flask app as a Linux
`systemd` service that starts automatically when the server boots and restarts
if the app exits or crashes.

The examples below install the app in:

```bash
/opt/markdown-converter
```

If your project lives somewhere else, replace `/opt/markdown-converter` with
your actual project path.

## 1. Install System Dependencies

On Debian or Ubuntu:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip tesseract-ocr
```

`tesseract-ocr` is optional, but it enables OCR support for image uploads.

## 2. Create a Dedicated Service User

Create a Linux user that will run the app:

```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin markdown-converter
```

## 3. Install the App

Copy or clone the project into `/opt/markdown-converter`.

Example using `git`:

```bash
sudo git clone <repository-url> /opt/markdown-converter
sudo chown -R markdown-converter:markdown-converter /opt/markdown-converter
```

If the project is already on the server, copy it into `/opt/markdown-converter`
and then run:

```bash
sudo chown -R markdown-converter:markdown-converter /opt/markdown-converter
```

## 4. Create the Python Virtual Environment

```bash
sudo -u markdown-converter python3 -m venv /opt/markdown-converter/.venv
sudo -u markdown-converter /opt/markdown-converter/.venv/bin/pip install --upgrade pip
sudo -u markdown-converter /opt/markdown-converter/.venv/bin/pip install -r /opt/markdown-converter/requirements.txt
```

## 5. Test the App Manually

Before creating the service, confirm that the app starts:

```bash
sudo -u markdown-converter /opt/markdown-converter/.venv/bin/python /opt/markdown-converter/app.py
```

Open another terminal and test:

```bash
curl http://SERVER_IP:8082
```

Stop the manual app process with `Ctrl+C` after testing.

## 6. Create the systemd Service File

Create this file:

```bash
sudo nano /etc/systemd/system/markdown-converter.service
```

Paste this service definition:

```ini
[Unit]
Description=Markdown Converter Flask App
After=network.target

[Service]
Type=simple
User=markdown-converter
Group=markdown-converter
WorkingDirectory=/opt/markdown-converter
Environment=PYTHONUNBUFFERED=1
Environment=MAX_UPLOAD_SIZE_MB=500
ExecStart=/opt/markdown-converter/.venv/bin/python /opt/markdown-converter/app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Important settings:

- `ExecStart` starts the Flask app.
- `MAX_UPLOAD_SIZE_MB` controls the maximum size of each uploaded file.
- `Restart=always` restarts the app if it exits or crashes.
- `RestartSec=5` waits 5 seconds before restarting.
- `WantedBy=multi-user.target` allows the service to start during normal boot.

## 7. Enable and Start the Service

Reload systemd so it sees the new service:

```bash
sudo systemctl daemon-reload
```

Enable the service at boot:

```bash
sudo systemctl enable markdown-converter
```

Start it now:

```bash
sudo systemctl start markdown-converter
```

## 8. Check Service Status and Logs

Check whether the service is running:

```bash
sudo systemctl status markdown-converter
```

View live logs:

```bash
sudo journalctl -u markdown-converter -f
```

View recent logs:

```bash
sudo journalctl -u markdown-converter -n 100 --no-pager
```

## 9. Restart, Stop, or Disable the Service

Restart the app:

```bash
sudo systemctl restart markdown-converter
```

Stop the app:

```bash
sudo systemctl stop markdown-converter
```

Disable automatic startup:

```bash
sudo systemctl disable markdown-converter
```

## 10. Network Access Note

By default, this app listens on:

```text
0.0.0.0:8082
```

That means it listens on all IPv4 network interfaces. You can access it from
another machine with:

```text
http://SERVER_IP:8082
```

Make sure your firewall allows inbound traffic on port `8082`. For production,
a common setup is to put Nginx, Caddy, or another reverse proxy in front of the
Flask app.

## 11. Updating the App

When you deploy application code or Python dependency changes:

```bash
cd /opt/markdown-converter
sudo -u markdown-converter git pull
sudo -u markdown-converter /opt/markdown-converter/.venv/bin/pip install -r requirements.txt
sudo systemctl restart markdown-converter
sudo systemctl status markdown-converter --no-pager
```

You do not need `daemon-reload` for application code changes. Run it only after
editing `/etc/systemd/system/markdown-converter.service`, then restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart markdown-converter
sudo systemctl status markdown-converter --no-pager
```

The current service needs only `PYTHONUNBUFFERED` and the optional
`MAX_UPLOAD_SIZE_MB` setting. Audio and video transcription are disabled, so no
speech model or transcription-service environment variables are required.
