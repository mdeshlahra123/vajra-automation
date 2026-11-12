"""Beat grid of a music file: (bpm, first_beat_offset_seconds). Pure numpy: onset envelope -> autocorrelation -> phase."""
import subprocess, sys
import numpy as np


def beat_grid(path, lo=75, hi=165):
    sr = 11025
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-t", "40", "-f", "s16le", "-ac", "1", "-ar", str(sr), "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0
    hop = 110   # 10 ms
    n = len(x) // hop
    e = np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1))
    on = np.maximum(0, np.diff(e)); on = on / (on.max() + 1e-9)
    best, bl = -1.0, 50
    for lag in range(int(6000 / hi), int(6000 / lo) + 1):   # lag in 10 ms units
        a = np.dot(on[:-lag], on[lag:]) / (len(on) - lag)
        a += 0.5 * (np.dot(on[:-2 * lag], on[2 * lag:]) / max(1, len(on) - 2 * lag))   # reward the 2-beat repeat too
        if a > best:
            best, bl = a, lag
    ph = max(range(bl), key=lambda p: on[p::bl].sum())
    return round(6000.0 / bl, 1), round(ph / 100.0, 2)


if __name__ == "__main__":
    print(beat_grid(sys.argv[1]))
