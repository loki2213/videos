"""Generate per-scene narration WAVs with Kokoro (kokoro-onnx).

Usage: python tts.py MODEL_DIR OUT_DIR
MODEL_DIR must hold kokoro-v1.0.onnx and voices-v1.0.bin from
https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0
Writes OUT_DIR/<scene>.wav and OUT_DIR/timing.json.
"""
import json
import os
import re
import sys

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro
from kokoro_onnx.tokenizer import Tokenizer

from script import SCENES

VOICE = "am_michael"
SPEED = 1.36
LANG = "en-us"
OVERRIDE = re.compile(r"\{([^|}]+)\|([^}]+)\}")


def to_phonemes(tok, text):
    out, pos = [], 0
    for m in OVERRIDE.finditer(text):
        if m.start() > pos:
            out.append(tok.phonemize(text[pos:m.start()], LANG))
        out.append(" " + m.group(2) + " ")
        pos = m.end()
    if pos < len(text):
        out.append(tok.phonemize(text[pos:], LANG))
    return re.sub(r"\s+", " ", "".join(out)).strip()


def squeeze_pauses(x, sr, max_gap=0.22, thresh=0.012):
    """Shorten internal pauses longer than max_gap seconds."""
    win = int(sr * 0.01)
    n = len(x) // win
    loud = np.abs(x[:n * win]).reshape(n, win).max(1) > thresh
    keep, run = [], 0
    for i in range(n):
        run = 0 if loud[i] else run + 1
        if run * win <= max_gap * sr:
            keep.append(x[i * win:(i + 1) * win])
    return np.concatenate(keep + [x[n * win:]])


def main(model_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    k = Kokoro(os.path.join(model_dir, "kokoro-v1.0.onnx"),
               os.path.join(model_dir, "voices-v1.0.bin"))
    tok = Tokenizer()
    timing = {}
    for sc in SCENES:
        ph = to_phonemes(tok, sc["text"])
        samples, sr = k.create(ph, voice=VOICE, speed=SPEED, lang=LANG,
                               is_phonemes=True)
        samples = squeeze_pauses(samples, sr)
        sf.write(os.path.join(out_dir, sc["id"] + ".wav"), samples, sr)
        timing[sc["id"]] = len(samples) / sr
        print(f'{sc["id"]:12s} {timing[sc["id"]]:6.2f}s')
    print("total speech", round(sum(timing.values()), 2))
    with open(os.path.join(out_dir, "timing.json"), "w") as f:
        json.dump(timing, f, indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
