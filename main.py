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
VERSION = "v0.0.4"
DEFAULT_PORT = 5000

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

# WebView2 环境变量（仅 Windows 需要）
for k, v in platform.get_webview_env().items():
    os.environ[k] = v

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
@socketio.on('join')
def on_join(data):
    role = data.get('role', 'unknown')
    print(f"[{role}] 已连接到信令服务器")
    emit('ready', {'role': role}, broadcast=True, include_self=False)


@socketio.on('offer')
def on_offer(data):
    emit('offer', data, broadcast=True, include_self=False)


@socketio.on('answer')
def on_answer(data):
    emit('answer', data, broadcast=True, include_self=False)


@socketio.on('ice_candidate')
def on_ice_candidate(data):
    emit('ice_candidate', data, broadcast=True, include_self=False)


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
    # 启动 Flask 线程
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()

    # 给 Flask 一点时间启动
    time.sleep(1.5)

    desktop_url = f'https://127.0.0.1:{SERVER_PORT}/desktop'

    if platform.use_system_browser:
        import webbrowser
        print(f"[ZeroMic] 桌面页面已用系统浏览器打开: {desktop_url}")
        webbrowser.open(desktop_url)
        # 主线程保持存活
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    else:
        import webview
        icon_ext = 'ico' if sys.platform == 'win32' else 'png'
        icon_path = os.path.join(base_path, f'icon.{icon_ext}')
        if not os.path.exists(icon_path):
            icon_path = ''

        window = webview.create_window(
            title='ZeroMic Desktop',
            url=desktop_url,
            width=380,
            height=740,
            resizable=False,
            frameless=False,
            easy_drag=False,
            background_color='#121212'
        )

        if sys.platform == 'win32':
            import pystray
            from PIL import Image

            tray_strings = {"show": "Show Window", "exit": "Exit ZeroMic", "mute": "Mute", "unmute": "Unmute"}

            def force_update_tray():
                if 'tray_icon' in globals() or 'tray_icon' in locals() or 'tray_icon' in sys.modules[__name__].__dict__:
                    try:
                        tray_icon.update_menu()
                    except Exception:
                        pass
                        
            tray_force_update_callback = force_update_tray

            def update_tray_strings(lang_code):
                try:
                    import json
                    lang_file = os.path.join(WEBUI_DIR, 'lang', f'{lang_code}.json')
                    if not os.path.exists(lang_file):
                        lang_prefix = lang_code.split('_')[0]
                        for f in os.listdir(os.path.join(WEBUI_DIR, 'lang')):
                            if f.startswith(lang_prefix):
                                lang_file = os.path.join(WEBUI_DIR, 'lang', f)
                                break
                    if os.path.exists(lang_file):
                        with open(lang_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            tray_strings["show"] = data.get('tray_show', tray_strings["show"])
                            tray_strings["exit"] = data.get('tray_exit', tray_strings["exit"])
                            tray_strings["mute"] = data.get('tray_mute', tray_strings["mute"])
                            tray_strings["unmute"] = data.get('tray_unmute', tray_strings["unmute"])
                    force_update_tray()
                except Exception:
                    pass

            tray_update_callback = update_tray_strings

            # 初始化读取当前系统语言
            try:
                import ctypes
                import locale
                windll = ctypes.windll.kernel32
                default_lang_code = locale.windows_locale.get(windll.GetUserDefaultUILanguage())
                default_lang_code = default_lang_code.lower() if default_lang_code else 'en_us'
                update_tray_strings(default_lang_code)
            except Exception:
                pass

            def create_tray():
                image = Image.open(icon_path) if icon_path else Image.new('RGB', (64, 64), color='black')
                
                def on_show(icon, item):
                    window.show()
                    window.restore()
                
                def on_exit(icon, item):
                    icon.stop()
                    window.destroy()
                    
                def on_mute_toggle(icon, item):
                    socketio.emit('toggle_mute')

                menu = pystray.Menu(
                    pystray.MenuItem(lambda item: tray_strings["show"], on_show, default=True),
                    pystray.MenuItem(lambda item: tray_strings["unmute"] if is_muted else tray_strings["mute"], on_mute_toggle),
                    pystray.MenuItem(lambda item: tray_strings["exit"], on_exit)
                )
                
                icon = pystray.Icon('ZeroMic', image, 'ZeroMic', menu)
                return icon

            tray_icon = create_tray()

            def on_minimized():
                window.hide()

            def on_closed():
                tray_icon.stop()

            window.events.minimized += on_minimized
            window.events.closed += on_closed
            
            tray_icon.run_detached()

        webview.start(
            gui=platform.gui_backend,
            debug=False,
            icon=icon_path
        )

