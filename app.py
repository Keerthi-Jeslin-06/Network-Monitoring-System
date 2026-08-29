from flask import (
    Flask,
    render_template,
    jsonify,
    send_file,
    request,
    redirect,
    url_for,
    session
)

import psutil
import socket
import subprocess
import re
import sqlite3
from datetime import datetime
import csv
import os


app = Flask(__name__)

# ==========================================
# SECRET KEY
# ==========================================

app.secret_key = "network-monitoring-secret-key"

DATABASE = "network_history.db"


# ==========================================
# LOGIN CREDENTIALS
# ==========================================

USERNAME = "admin"
PASSWORD = "Keerthi@NMS2026#"


# ==========================================
# DATABASE
# ==========================================

def init_database():

    connection = sqlite3.connect(DATABASE)

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS traffic_history (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            timestamp TEXT,

            bytes_sent INTEGER,

            bytes_recv INTEGER
        )
    """)

    connection.commit()

    connection.close()


# ==========================================
# LOGIN REQUIRED
# ==========================================

def login_required():

    return "username" in session


# ==========================================
# LOGIN PAGE
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")

        password = request.form.get("password")

        if username == USERNAME and password == PASSWORD:

            session["username"] = username

            return redirect(url_for("home"))

        return render_template(
            "login.html",
            error="Invalid username or password"
        )

    return render_template("login.html")


# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
def logout():

    session.pop("username", None)

    return redirect(url_for("login"))


# ==========================================
# HOME / DASHBOARD
# ==========================================

@app.route("/")
def home():

    if not login_required():

        return redirect(url_for("login"))

    return render_template(
        "index.html",
        username=session["username"]
    )


# ==========================================
# FEATURE 1: NETWORK TRAFFIC
# ==========================================

@app.route("/api/network")
def network_stats():

    if not login_required():

        return jsonify({
            "error": "Unauthorized"
        }), 401

    stats = psutil.net_io_counters()

    return jsonify({

        "bytes_sent": stats.bytes_sent,

        "bytes_recv": stats.bytes_recv,

        "packets_sent": stats.packets_sent,

        "packets_recv": stats.packets_recv
    })


# ==========================================
# FEATURE 2: SYSTEM MONITORING
# ==========================================

@app.route("/api/system")
def system_stats():

    if not login_required():

        return jsonify({
            "error": "Unauthorized"
        }), 401

    cpu = psutil.cpu_percent(interval=0.5)

    memory = psutil.virtual_memory().percent

    disk = psutil.disk_usage("/").percent

    return jsonify({

        "cpu": cpu,

        "memory": memory,

        "disk": disk,

        "hostname": socket.gethostname()
    })


# ==========================================
# FEATURE 3: NETWORK INFORMATION
# ==========================================

@app.route("/api/network-info")
def network_info():

    if not login_required():

        return jsonify({
            "error": "Unauthorized"
        }), 401

    interfaces = psutil.net_if_addrs()

    stats = psutil.net_if_stats()

    result = []

    for interface, addresses in interfaces.items():

        ip = "N/A"

        mac = "N/A"

        for address in addresses:

            if address.family == psutil.AF_LINK:

                mac = address.address

            elif address.family == socket.AF_INET:

                ip = address.address

        status = "Offline"

        if (
            interface in stats
            and stats[interface].isup
        ):

            status = "Online"

        result.append({

            "interface": interface,

            "ip": ip,

            "mac": mac,

            "status": status
        })

    return jsonify(result)


# ==========================================
# FEATURE 4: NETWORK STATUS
# ==========================================

@app.route("/api/network-status")
def network_status():

    if not login_required():

        return jsonify({
            "error": "Unauthorized"
        }), 401

    interfaces = psutil.net_if_stats()

    active_interface = "None"

    connection_status = "Offline"

    for interface, information in interfaces.items():

        if information.isup:

            active_interface = interface

            connection_status = "Online"

            break

    # Check Internet connection

    internet_status = "Offline"

    try:

        socket.create_connection(
            ("8.8.8.8", 53),
            timeout=2
        )

        internet_status = "Online"

    except OSError:

        internet_status = "Offline"

    return jsonify({

        "connection": connection_status,

        "interface": active_interface,

        "internet": internet_status
    })


# ==========================================
# FEATURE 5: NETWORK ALERTS
# ==========================================

@app.route("/api/alerts")
def alerts():

    if not login_required():

        return jsonify({
            "error": "Unauthorized"
        }), 401

    alerts_list = []

    # ======================================
    # CPU CHECK
    # CPU > 80%
    # ======================================

    cpu = psutil.cpu_percent(interval=0.5)

    if cpu > 80:

        alerts_list.append({

            "type": "warning",

            "icon": "⚠️",

            "title": "High CPU Alert",

            "message":
                f"High CPU usage detected: {cpu}%",

            "value": cpu
        })


    # ======================================
    # MEMORY CHECK
    # MEMORY > 80%
    # ======================================

    memory = psutil.virtual_memory().percent

    if memory > 80:

        alerts_list.append({

            "type": "warning",

            "icon": "⚠️",

            "title": "High Memory Alert",

            "message":
                f"High memory usage detected: {memory}%",

            "value": memory
        })


    # ======================================
    # DISK CHECK
    # DISK > 90%
    # ======================================

    disk = psutil.disk_usage("/").percent

    if disk > 90:

        alerts_list.append({

            "type": "warning",

            "icon": "⚠️",

            "title": "Low Storage Alert",

            "message":
                f"Storage usage is critically high: {disk}%",

            "value": disk
        })


    # ======================================
    # INTERNET CHECK
    # INTERNET DOWN
    # ======================================

    internet_available = True

    try:

        socket.create_connection(
            ("8.8.8.8", 53),
            timeout=2
        )

    except OSError:

        internet_available = False


    if not internet_available:

        alerts_list.append({

            "type": "danger",

            "icon": "🔴",

            "title": "Network Alert",

            "message":
                "Internet connection is unavailable",

            "value": "Offline"
        })


    # ======================================
    # NO ALERTS
    # ======================================

    if not alerts_list:

        alerts_list.append({

            "type": "success",

            "icon": "✅",

            "title": "System Normal",

            "message":
                "Network and system status are normal",

            "value": "Normal"
        })


    return jsonify(alerts_list)


# ==========================================
# FEATURE 6: CONNECTED DEVICES
# ==========================================

@app.route("/api/devices")
def connected_devices():

    if not login_required():

        return jsonify({
            "error": "Unauthorized"
        }), 401

    devices = []

    try:

        output = subprocess.check_output(
            ["arp", "-a"],
            text=True,
            encoding="utf-8",
            errors="ignore"
        )

        lines = output.splitlines()

        for line in lines:

            match = re.search(
                r"(\d+\.\d+\.\d+\.\d+)\s+"
                r"([0-9a-fA-F-]{17})\s+"
                r"(\w+)",
                line
            )

            if match:

                ip = match.group(1)

                mac = match.group(2)

                device_type = match.group(3)

                first_octet = int(
                    ip.split(".")[0]
                )

                # Ignore broadcast addresses

                if ip.endswith(".255"):

                    continue

                # Ignore multicast addresses

                if 224 <= first_octet <= 239:

                    continue

                # Ignore global broadcast

                if ip == "255.255.255.255":

                    continue

                devices.append({

                    "ip": ip,

                    "mac": mac,

                    "status": "Online",

                    "type": device_type
                })

    except Exception as error:

        print(
            "Device scanning error:",
            error
        )

    return jsonify(devices)


# ==========================================
# FEATURE 7: SAVE HISTORY
# ==========================================

@app.route("/api/save-history")
def save_history():

    if not login_required():

        return jsonify({
            "error": "Unauthorized"
        }), 401

    stats = psutil.net_io_counters()

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    connection = sqlite3.connect(DATABASE)

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO traffic_history
        (timestamp, bytes_sent, bytes_recv)

        VALUES (?, ?, ?)
    """, (

        timestamp,

        stats.bytes_sent,

        stats.bytes_recv
    ))

    connection.commit()

    connection.close()

    return jsonify({

        "message":
            "Traffic history saved"
    })


# ==========================================
# FEATURE 8: GET HISTORY
# ==========================================

@app.route("/api/history")
def get_history():

    if not login_required():

        return jsonify({
            "error": "Unauthorized"
        }), 401

    connection = sqlite3.connect(DATABASE)

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            timestamp,
            bytes_sent,
            bytes_recv

        FROM traffic_history

        ORDER BY id DESC

        LIMIT 50
    """)

    rows = cursor.fetchall()

    connection.close()

    rows.reverse()

    history = []

    for row in rows:

        history.append({

            "timestamp": row[0],

            "bytes_sent": row[1],

            "bytes_recv": row[2]
        })

    return jsonify(history)


# ==========================================
# FEATURE 9: REPORT
# ==========================================

@app.route("/api/report")
def report_data():

    if not login_required():

        return jsonify({
            "error": "Unauthorized"
        }), 401

    connection = sqlite3.connect(DATABASE)

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            COUNT(*),
            MAX(bytes_sent),
            MIN(bytes_sent),
            MAX(bytes_recv),
            MIN(bytes_recv)

        FROM traffic_history
    """)

    row = cursor.fetchone()

    connection.close()

    total_records = row[0] or 0

    max_sent = row[1] or 0

    min_sent = row[2] or 0

    max_recv = row[3] or 0

    min_recv = row[4] or 0

    return jsonify({

        "generated_at":
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

        "hostname":
            socket.gethostname(),

        "cpu":
            psutil.cpu_percent(
                interval=0.5
            ),

        "memory":
            psutil.virtual_memory().percent,

        "disk":
            psutil.disk_usage("/").percent,

        "records":
            total_records,

        "total_sent_mb":
            round(
                max_sent /
                1024 /
                1024,
                2
            ),

        "total_received_mb":
            round(
                max_recv /
                1024 /
                1024,
                2
            ),

        "traffic_sent_mb":
            round(
                (
                    max_sent -
                    min_sent
                )
                / 1024
                / 1024,
                2
            ),

        "traffic_received_mb":
            round(
                (
                    max_recv -
                    min_recv
                )
                / 1024
                / 1024,
                2
            )
    })


# ==========================================
# FEATURE 10: DOWNLOAD REPORT
# ==========================================

@app.route("/download-report")
def download_report():

    if not login_required():

        return redirect(
            url_for("login")
        )

    filename = (
        "network_monitoring_report.csv"
    )

    filepath = os.path.join(
        os.getcwd(),
        filename
    )

    connection = sqlite3.connect(DATABASE)

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            timestamp,
            bytes_sent,
            bytes_recv

        FROM traffic_history

        ORDER BY id
    """)

    rows = cursor.fetchall()

    connection.close()

    with open(
        filepath,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow([

            "Timestamp",

            "Bytes Sent",

            "Bytes Received"
        ])

        writer.writerows(rows)

    return send_file(

        filepath,

        as_attachment=True,

        download_name=filename
    )


# ==========================================
# START APPLICATION
# ==========================================

if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )