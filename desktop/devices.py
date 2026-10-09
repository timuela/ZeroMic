# PortAudio is imported lazily. Importing sounddevice initialises PortAudio,
# which costs ~0.6s and blocks the window if it happens at startup; it may also
# be missing entirely on Linux, which must not take the app down.
_sd = None
_sd_error = ""


def _sounddevice():
    global _sd, _sd_error
    if _sd is None and not _sd_error:
        try:
            import sounddevice as sd
        except Exception as exc:  # pragma: no cover - depends on the host
            _sd_error = str(exc)
        else:
            _sd = sd
    return _sd


def audio_available():
    return _sounddevice() is not None


def unavailable_reason():
    _sounddevice()
    return _sd_error


def list_output_devices():
    """Return a list of (index, name) for every device that can play audio."""
    result = []
    sd = _sounddevice()
    if sd is None:
        return result

    try:
        devices = sd.query_devices()
    except Exception:
        return result

    for index, device in enumerate(devices):
        try:
            if device["max_output_channels"] > 0:
                result.append((index, device["name"]))
        except Exception:
            continue
    return result


def find_output_index(keyword, devices):
    """Return the index of the first output device whose name matches keyword."""
    if not keyword:
        return None
    needle = keyword.lower()
    for index, name in devices:
        if needle in name.lower():
            return index
    return None


def default_output_index():
    sd = _sounddevice()
    if sd is None:
        return None
    try:
        return sd.default.device[1]
    except Exception:
        return None
