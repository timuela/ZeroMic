# Taste

## Engineering approach
- Prefers native platform solutions over workarounds that fight the browser/OS — e.g. chose a native Android client (foreground service + wake lock) rather than hacking the web client to survive Android's screen-off suspension. Confidence: 0.55
- Prefers additive changes that leave existing, working code untouched — chose options specifically because they required "no server changes at all" and kept the PC-side protocol/`main.py`/`webui` unchanged. Confidence: 0.5

## Tooling
- For Android UI, prefers Jetpack Compose over XML Views. Confidence: 0.5
- Prefers build/CI paths that produce artifacts (e.g. a GitHub Actions workflow that builds a debug APK) over requiring a local toolchain install. Confidence: 0.4

## Workflow / communication
- Prefers to review plan files himself rather than have plans repeatedly re-presented or re-explained, and dislikes being asked repeated clarifying questions. Confidence: 0.4
