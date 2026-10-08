import os
import sys
import socket
import threading
import time
import OpenSSL       # 确保 PyInstaller 能检测到 adhoc SSL 的依赖
import cryptography

from flask import Flask, send_from_directory, jsonify, request
from flask_socketio import SocketIO, emit

from platforms import get_platform

# 兼容 PyInstaller 的资源路径定位机制
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

# 常量
VERSION = "v0.0.10"
DEFAULT_PORT = 5000

# 单实例检测
MUTEX_NAME = r'Local\ZeroMicSingleInstance'
LOCK_FILENAME = 'zeromic.lock'
ERROR_ALREADY_EXISTS = 183
_instance_lock = None


def acquire_instance_lock():
    """尝试成为唯一运行实例。

    返回 True 表示可以继续启动，False 表示已经有一个实例在运行。
    检测本身出错时不会阻止启动。
    """
    global _instance_lock
    try:
        if sys.platform == 'win32':
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel32.CreateMutexW.restype = wintypes.HANDLE
            handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
            if not handle:
                return True
            if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
                kernel32.CloseHandle(handle)
                return False
            _instance_lock = handle
            return True

        import fcntl
        import tempfile

        path = os.path.join(tempfile.gettempdir(), LOCK_FILENAME)
        handle = open(path, 'w')
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close()
            return False
        _instance_lock = handle
        return True
    except Exception:
        return True


def notify_already_running():
    message = 'ZeroMic 已在运行中，请勿重复启动。\n\nZeroMic is already running.'
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, message, 'ZeroMic', 0x00000040)
            return
        except Exception:
            pass
    print(f'[ZeroMic] {message}')


def get_available_port(start_port, max_port=5100):
    for port in range(start_port, max_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', port))
                return port
            except OSError:
                continue
    return start_port

SERVER_PORT = get_available_port(DEFAULT_PORT)

# 平台检测
platform = get_platform()

# ==========================================
# 1. Flask & SocketIO 初始化
# ==========================================
WEBUI_DIR = os.path.join(base_path, 'webui')
app = Flask(__name__, static_folder=WEBUI_DIR, static_url_path='')
app.config['SECRET_KEY'] = 'webmic-super-secret-key'

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')


def get_lan_ip():
    """获取本机在局域网内的 IPv4 地址"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


# ==========================================
# 2. 路由配置
# ==========================================
@app.route('/')
def index():
    return send_from_directory(WEBUI_DIR, 'index.html')


@app.route('/desktop')
def desktop():
    return send_from_directory(WEBUI_DIR, 'desktop.html')


@app.route('/api/info')
def api_info():
    return jsonify({
        "ip": get_lan_ip(),
        "port": SERVER_PORT,
        "version": VERSION
    })


@app.route('/api/platform_info')
def api_platform_info():
    return jsonify({
        "os": sys.platform,
        "driver_display_name": platform.driver_display_name,
        "driver_match_keyword": platform.driver_match_keyword,
        "post_install_warning": platform.get_post_install_warning(),
    })


@app.route('/api/check_driver', methods=['GET'])
def api_check_driver():
    return jsonify({"installed": platform.is_driver_installed()})


@app.route('/api/install_driver', methods=['POST'])
def api_install_driver():
    success, msg = platform.install_driver()
    return jsonify({"success": success, "msg": msg})


@app.route('/api/uninstall_driver', methods=['POST'])
def api_uninstall_driver():
    success, msg = platform.uninstall_driver()
    return jsonify({"success": success, "msg": msg})


@app.route('/api/exit', methods=['POST'])
def api_exit():
    def kill_me():
        time.sleep(1)
        os._exit(0)
    threading.Thread(target=kill_me).start()
    return jsonify({"success": True})


tray_update_callback = None
is_muted = False
tray_force_update_callback = None

@app.route('/api/set_lang', methods=['POST'])
def api_set_lang():
    data = request.json or {}
    lang = data.get('lang', 'en_us')
    if tray_update_callback:
        tray_update_callback(lang)
    return jsonify({"success": True})

@app.route('/api/sync_mute', methods=['POST'])
def api_sync_mute():
    global is_muted
    data = request.json or {}
    is_muted = data.get('muted', False)
    if tray_force_update_callback:
        tray_force_update_callback()
    return jsonify({"success": True})


# ==========================================
# 3. WebRTC 信令服务器 (Socket.IO)
# ==========================================
clients = {}  # sid -> role


def _presence_payload():
    roles = set(clients.values())
    return {
        'mobile': 'mobile' in roles,
        'desktop': 'desktop' in roles,
    }


def _broadcast_presence():
    socketio.emit('presence', _presence_payload())


@socketio.on('join')
def on_join(data):
    role = data.get('role', 'unknown') if isinstance(data, dict) else 'unknown'
    clients[request.sid] = role
    print(f"[{role}] 已连接到信令服务器 (sid={request.sid})")
    emit('ready', {'role': role}, broadcast=True, include_self=False)
    _broadcast_presence()


@socketio.on('disconnect')
def on_disconnect():
    role = clients.pop(request.sid, None)
    if role is not None:
        print(f"[{role}] 已断开连接 (sid={request.sid})")
        _broadcast_presence()


@socketio.on('offer')
def on_offer(data):
    emit('offer', data, broadcast=True, include_self=False)


@socketio.on('answer')
def on_answer(data):
    emit('answer', data, broadcast=True, include_self=False)


@socketio.on('ice_candidate')
def on_ice_candidate(data):
    emit('ice_candidate', data, broadcast=True, include_self=False)


@socketio.on('toggle_mute')
def on_toggle_mute():
    emit('toggle_mute', broadcast=True, include_self=False)


# ==========================================
# 4. 启动入口
# ==========================================
def start_flask():
    lan_ip = get_lan_ip()
    print(f"\n=========================================")
    print(f"ZeroMic 服务端已启动！")
    print(f"手机请访问: https://{lan_ip}:{SERVER_PORT}")
    print(f"=========================================\n")

    socketio.run(app, host='0.0.0.0', port=SERVER_PORT, ssl_context='adhoc', debug=False, use_reloader=False, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    if not acquire_instance_lock():
        notify_already_running()
        sys.exit(0)

    # 启动 Flask 线程
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()

    # 给 Flask 一点时间启动
    time.sleep(1.5)

    icon_path = None
    for icon_name in ('icon.ico', 'icon.png', 'icon.icns'):
        candidate = os.path.join(base_path, icon_name)
        if os.path.exists(candidate):
            icon_path = candidate
            break

    from desktop.app import run_desktop

    run_desktop(
        platform=platform,
        port=SERVER_PORT,
        url=f'https://{get_lan_ip()}:{SERVER_PORT}',
        version=VERSION,
        webui_dir=WEBUI_DIR,
        icon_path=icon_path,
    )

