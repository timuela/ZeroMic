import ctypes
import subprocess
import os
import urllib.request
import zipfile
import tempfile
from .base import BasePlatform 

class WindowsPlatform(BasePlatform):
    @property
    def use_system_browser(self) -> bool:
        """Windows 下默认使用 pywebview 内嵌窗口"""
        return False

    @property
    def gui_backend(self) -> str:
        return 'edgechromium'

    @property
    def driver_display_name(self) -> str:
        return 'CABLE Output (VB-Audio Virtual Cable)'

    @property
    def driver_match_keyword(self) -> str:
        return 'cable input'

    def get_webview_env(self) -> dict[str, str]:
        return {
            'WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS': (
                '--ignore-certificate-errors '
                '--use-fake-ui-for-media-stream '
                '--autoplay-policy=no-user-gesture-required'
            ),
        }

    def is_admin(self) -> bool:
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    def is_driver_installed(self) -> bool:
        try:
            cmd = 'powershell -Command "Get-CimInstance Win32_SoundDevice | Select-Object -Property Name"'
            output = subprocess.check_output(cmd, shell=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            return 'VB-Audio Virtual' in output or 'CABLE' in output
        except Exception:
            return False

    def _get_default_audio_endpoint(self) -> str:
        ps_code = r"""
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
[Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IMMDevice {
    int a(); int o();
    int GetId([MarshalAs(UnmanagedType.LPWStr)] out string id);
}
[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IMMDeviceEnumerator {
    int f();
    int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice endpoint);
}
[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
public class MMDeviceEnumeratorComObject { }
public class AudioHelper {
    public static string GetDefaultAudioEndpoint() {
        var enumerator = new MMDeviceEnumeratorComObject() as IMMDeviceEnumerator;
        IMMDevice dev = null;
        enumerator.GetDefaultAudioEndpoint(0, 0, out dev);
        string id = null;
        dev.GetId(out id);
        return id;
    }
}
"@
[AudioHelper]::GetDefaultAudioEndpoint()
"""
        try:
            cmd = ['powershell', '-NoProfile', '-Command', ps_code]
            output = subprocess.check_output(cmd, text=True, creationflags=subprocess.CREATE_NO_WINDOW).strip()
            return output
        except Exception as e:
            print("Get Audio Endpoint Error:", e)
            return ""

    def _set_default_audio_endpoint(self, device_id: str):
        if not device_id: return
        ps_code = f"""
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
[ComImport, Guid("870AF99C-171D-4F9E-AF0D-E63DF40C2BC9")]
internal class _CPolicyConfigClient {{ }}
[ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("F8679F50-850A-41CF-9C72-430F290290C8")]
internal interface IPolicyConfig {{
    int a(); int b(); int c(); int d(); int e(); int f(); int g(); int h(); int i(); int j();
    int SetDefaultEndpoint(string wszDeviceId, uint role);
    int SetEndpointVisibility(string wszDeviceId, bool bVisible);
}}
public class PolicyConfigClient {{
    public static void SetDefaultDevice(string deviceID) {{
        IPolicyConfig policyConfig = (IPolicyConfig)new _CPolicyConfigClient();
        policyConfig.SetDefaultEndpoint(deviceID, 0);
        policyConfig.SetDefaultEndpoint(deviceID, 1);
        policyConfig.SetDefaultEndpoint(deviceID, 2);
    }}
}}
"@
[PolicyConfigClient]::SetDefaultDevice('{device_id}')
"""
        try:
            cmd = ['powershell', '-NoProfile', '-Command', ps_code]
            subprocess.run(cmd, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception as e:
            print("Set Audio Endpoint Error:", e)

    def install_driver(self) -> tuple[bool, str]:
        if self.is_driver_installed():
            return True, '虚拟声卡已安装'

        try:
            import sys
            import shutil
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

            # 在安装前记录当前默认音频输出设备
            old_device = self._get_default_audio_endpoint()

            temp_dir = tempfile.mkdtemp()
            zip_path = os.path.join(base_path, 'drivers', 'vbcable.zip')

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            setup_exe = os.path.join(temp_dir, 'VBCABLE_Setup_x64.exe')
            creation_flags = subprocess.CREATE_NO_WINDOW
            if self.is_admin():
                subprocess.run([setup_exe, '-i', '-h'], check=True, creationflags=creation_flags)
            else:
                cmd = ['powershell', '-WindowStyle', 'Hidden', '-Command', f'Start-Process -FilePath "{setup_exe}" -ArgumentList "-i -h" -Verb RunAs -Wait -WindowStyle Hidden']
                subprocess.run(cmd, check=True, creationflags=creation_flags)
            shutil.rmtree(temp_dir, ignore_errors=True)
            # 安装完成后恢复之前的默认音频输出设备
            if old_device:
                self._set_default_audio_endpoint(old_device)

            return True, '安装成功！'
        except Exception as e:
            return False, f'安装异常: {str(e)}'

    def uninstall_driver(self) -> tuple[bool, str]:
        setup_path = r'C:\Program Files\VB\CABLE\VBCABLE_Setup_x64.exe'

        if not os.path.exists(setup_path):
            return False, '未找到卸载程序，可能已被手动卸载。'

        try:
            creation_flags = subprocess.CREATE_NO_WINDOW
            if self.is_admin():
                process = subprocess.run([setup_path, '-u', '-h'], check=False, creationflags=creation_flags)
                return_code = process.returncode
            else:
                cmd = ['powershell', '-WindowStyle', 'Hidden', '-Command', f'$p = Start-Process -FilePath "{setup_path}" -ArgumentList "-u -h" -Verb RunAs -Wait -WindowStyle Hidden -PassThru; exit $p.ExitCode']
                process = subprocess.run(cmd, check=False, creationflags=creation_flags)
                return_code = process.returncode

            if return_code in [0, 1, 2]:
                return True, '卸载成功！'
            else:
                return False, f'卸载程序返回了异常状态码: {return_code}'
        except Exception as e:
            return False, f'卸载时发生异常: {str(e)}'

    def get_post_install_warning(self) -> str:
        return ""
