import os
import subprocess
from .base import BasePlatform


class MacOSPlatform(BasePlatform):
    @property
    def driver_display_name(self) -> str:
        return 'BlackHole 2ch'

    @property
    def driver_match_keyword(self) -> str:
        return 'blackhole'

    def list_lan_ips(self) -> list[str]:
        """列出所有 IPv4 地址，包含 VPN / Tailscale 等虚拟网卡。"""
        ips: list[str] = []
        try:
            output = subprocess.check_output(['ifconfig'], text=True, timeout=5)
        except Exception as e:
            print("List LAN IPs Error:", e)
            return ips

        for line in output.splitlines():
            line = line.strip()
            if not line.startswith('inet '):
                continue
            address = line.split()[1]
            if not address.startswith(('127.', '169.254.')):
                ips.append(address)
        return ips

    def is_admin(self) -> bool:
        try:
            return True
        except AttributeError:
            return False

    def is_driver_installed(self) -> bool:
        try:
            result = subprocess.run(
                ['system_profiler', 'SPAudioDataType'],
                capture_output=True, text=True, timeout=10
            )
            return 'BlackHole' in result.stdout
        except Exception:
            return False

    def install_driver(self) -> tuple[bool, str]:
        if self.is_driver_installed():
            return True, 'BlackHole 已安装'

        return False, (
            '请手动安装 BlackHole:\n'
            'brew install blackhole-2ch\n'
            '或访问 https://github.com/ExistentialAudio/BlackHole 下载安装包。'
        )

    def uninstall_driver(self) -> tuple[bool, str]:
        return False, '请手动卸载 BlackHole:\nbrew uninstall blackhole-2ch'

    def get_post_install_warning(self) -> str:
        return (
            '请将游戏/会议软件的麦克风设备设置为 "BlackHole 2ch"。\n'
            '如果设备未出现，请尝试重启应用或电脑。'
        )
