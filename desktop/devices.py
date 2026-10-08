import sounddevice as sd


def list_output_devices():
    """Return a list of (index, name) for every device that can play audio."""
    result = []
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
    try:
        return sd.default.device[1]
    except Exception:
        return None
