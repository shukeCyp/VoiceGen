# Bundled FFmpeg (Windows)

CI downloads official essentials build into `windows/`:

- `ffmpeg.exe`
- `ffprobe.exe`

Local prepare:

```bash
python scripts/download_ffmpeg_windows.py
```

These binaries are packaged into the one-file Windows EXE via `voicegen.spec`.
