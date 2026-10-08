class BasePlatform:
    """平台抽象基类，定义各平台必须实现的接口。"""

    @property
    def driver_display_name(self) -> str:
        """前端 UI 中显示的虚拟设备名称。"""
        raise NotImplementedError

    @property
    def driver_match_keyword(self) -> str:
        """在前端 enumerateDevices 中匹配设备的关键词（小写）。"""
        raise NotImplementedError

    def list_lan_ips(self) -> list[str]:
        """返回本机所有可用的局域网 IPv4 地址（用于生成多个访问地址）。"""
        return []

    def is_admin(self) -> bool:
        raise NotImplementedError

    def is_driver_installed(self) -> bool:
        raise NotImplementedError

    def install_driver(self) -> tuple[bool, str]:
        """返回 (成功, 消息)"""
        raise NotImplementedError

    def uninstall_driver(self) -> tuple[bool, str]:
        """返回 (成功, 消息)"""
        raise NotImplementedError

    def get_post_install_warning(self) -> str:
        """驱动安装后的提醒文案。"""
        return ""
