try:
    import sounddevice as sd
except Exception as exc:  # pragma: no cover - depends on the host
    # PortAudio is a system library on Linux and sounddevice raises on import
    # when it is missing. That must not take the whole app down, so remember
    # why and degrade to "no audio devices" instead.
    sd = None
    IMPORT_ERROR = str(exc)
else:
    IMPORT_ERROR = ""


def audio_available():
    return sd is not None


def unavailable_reason():
    return IMPORT_ERROR


def list_output_devices():
    """Return a list of (index, name) for every device that can play audio."""
    result = []
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
    if sd is None:
        return None
    try:
        return sd.default.device[1]
    except Exception:
        return None
