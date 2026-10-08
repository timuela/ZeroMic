import os
import subprocess
import re
from .base import BasePlatform

class LinuxPlatform(BasePlatform):
    SINK_NAME = 'zeromic_sink'
    SINK_DESCRIPTION = 'ZeroMic Virtual Output'

    @property
    def driver_display_name(self) -> str:
        return f'{self.SINK_DESCRIPTION} Monitor'

    @property
    def driver_match_keyword(self) -> str:
        return self.SINK_NAME

    def list_lan_ips(self) -> list[str]:
        """列出所有 IPv4 地址，包含 VPN / Tailscale 等虚拟网卡。"""
        ips: list[str] = []
        try:
            output = subprocess.check_output(
                ['ip', '-o', '-4', 'addr', 'show'], text=True, timeout=5
            )
            for line in output.splitlines():
                parts = line.split()
                if len(parts) >= 4:
                    address = parts[3].split('/')[0]
                    if not address.startswith(('127.', '169.254.')):
                        ips.append(address)
            return ips
        except Exception:
            pass

        try:
            output = subprocess.check_output(
                ['hostname', '-I'], text=True, timeout=5
            )
            return [
                a for a in output.split()
                if not a.startswith(('127.', '169.254.'))
            ]
        except Exception as e:
            print("List LAN IPs Error:", e)
            return []

    def is_admin(self) -> bool:
        try:
            return True
        except AttributeError:
            return False

    def _run_pactl(self, *args) -> tuple[int, str, str]:
        """运行 pactl 命令，返回 (returncode, stdout, stderr)"""
        try:
            proc = subprocess.run(
                ['pactl', *args],
                capture_output=True, text=True, timeout=10
            )
            return proc.returncode, proc.stdout, proc.stderr
        except FileNotFoundError:
            return -1, '', 'pactl 命令不可用，请确认 PulseAudio/PipeWire 已安装'
        except subprocess.TimeoutExpired:
            return -1, '', 'pactl 命令超时'

    def _get_module_id(self) -> int | None:
        """获取已加载的 zeromic null-sink 模块 ID。"""
        code, stdout, _ = self._run_pactl('list', 'modules', 'short')
        if code != 0:
            return None
        for line in stdout.splitlines():
            if f'sink_name={self.SINK_NAME}' in line:
                m = re.match(r'(\d+)', line)
                if m:
                    return int(m.group(1))
        return None

    def is_driver_installed(self) -> bool:
        return self._get_module_id() is not None

    def install_driver(self) -> tuple[bool, str]:
        if self.is_driver_installed():
            return True, '虚拟音频设备已存在'

        code, stdout, stderr = self._run_pactl(
            'load-module', 'module-null-sink',
            f'sink_name={self.SINK_NAME}',
            f'sink_properties=device.description={self.SINK_DESCRIPTION}'
        )
        if code == 0:
            return True, '虚拟音频设备创建成功！'
        return False, f'创建虚拟音频设备失败:\n{stderr}'

    def uninstall_driver(self) -> tuple[bool, str]:
        module_id = self._get_module_id()
        if module_id is None:
            return False, '未找到 ZeroMic 虚拟音频设备'

        code, stdout, stderr = self._run_pactl('unload-module', str(module_id))
        if code == 0:
            return True, '虚拟音频设备已移除。'
        return False, f'移除失败:\n{stderr}'

    def get_post_install_warning(self) -> str:
        return (
            '虚拟音频设备已创建。\n\n'
            '在游戏或会议软件中，请将麦克风设备设置为：\n'
            f'"{self.SINK_DESCRIPTION} Monitor"\n\n'
            '如果设备未出现，请尝试重新打开目标软件。'
        )
