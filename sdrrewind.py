#!/usr/bin/env python3
import argparse
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np

try:
    from rtlsdr import RtlSdr  # pyrtlsdr
except Exception as e:
    RtlSdr = None

# ===== Utilities =====

def utcnow_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)
    return p

def write_json(path: Path, obj: dict):
    path.write_text(json.dumps(obj, indent=2))

# ===== Capture Loop =====

def capture_loop(freq_hz: float, samp_rate: float, gain: str, outdir: Path,
                 buffer_sec: int, chunk_sec: int, driver: str):
    """Rolling capture by chunked files; prune to keep <= buffer_sec."""
    if driver != "rtlsdr":
        print(f"[!] Only 'rtlsdr' supported in MVP. Got '{driver}'.", file=sys.stderr)
        sys.exit(2)

    if RtlSdr is None:
        print("[!] pyrtlsdr not available. Install 'pyrtlsdr'.", file=sys.stderr)
        sys.exit(2)

    sdr = RtlSdr()
    sdr.sample_rate = int(samp_rate)
    sdr.center_freq = int(freq_hz)
    if gain == "auto":
        sdr.gain = 'auto'
    else:
        try:
            sdr.gain = float(gain)
        except Exception:
            sdr.gain = 'auto'

    samples_per_chunk = int(samp_rate * chunk_sec)

    print(f"[+] Starting capture @ {freq_hz/1e6:.3f} MHz, {samp_rate/1e6:.2f} MS/s, chunk={chunk_sec}s, buffer={buffer_sec}s")
    running = True

    def handle_sig(signum, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, handle_sig)
    signal.signal(signal.SIGTERM, handle_sig)

    ensure_dir(outdir)

    try:
        while running:
            t0 = time.time()
            iq = sdr.read_samples(samples_per_chunk).astype(np.complex64)

            ts = int(t0 * 1000)
            iq_path = outdir / f"{ts}.iq"
            meta = {
                "center_freq_hz": int(freq_hz),
                "samp_rate_hz": int(samp_rate),
                "timestamp_utc": utcnow_iso(),
                "duration_s": float(chunk_sec),
                "dtype": "complex64"
            }
            iq.tofile(iq_path)
            write_json(iq_path.with_suffix('.json'), meta)

            prune_seconds(outdir, buffer_sec)

            elapsed = time.time() - t0
            sleep_left = chunk_sec - elapsed
            if sleep_left > 0:
                time.sleep(sleep_left)
    finally:
        try:
            sdr.close()
        except Exception:
            pass

def prune_seconds(outdir: Path, buffer_sec: int):
    files = sorted(outdir.glob("*.json"))
    total = 0.0
    kept = []
    for meta_path in reversed(files):
        try:
            meta = json.loads(meta_path.read_text())
            dur = float(meta.get("duration_s", 0))
        except Exception:
            dur = 0
        total += dur
        kept.append(meta_path)
        if total >= buffer_sec:
            break

    keep_set = {p.stem for p in kept}
    for meta_path in files:
        stem = meta_path.stem
        if stem not in keep_set:
            iq_path = meta_path.with_suffix('.iq')
            for p in (meta_path, iq_path):
                try:
                    p.unlink()
                except FileNotFoundError:
                    pass

# ===== Extract =====

def extract_slice(outdir: Path, start_rel_s: float, duration_s: float, outfile: Path):
    now = datetime.now(timezone.utc)
    start_time = now + timedelta(seconds=start_rel_s)
    end_time = start_time + timedelta(seconds=duration_s)

    metas = []
    for meta_path in outdir.glob("*.json"):
        try:
            meta = json.loads(meta_path.read_text())
            t = datetime.fromisoformat(meta["timestamp_utc"].replace('Z', '+00:00'))
            dur = float(meta.get("duration_s", 0))
            t_end = t + timedelta(seconds=dur)
        except Exception:
            continue
        if t <= end_time and t_end >= start_time:
            metas.append((t, dur, meta_path))

    metas.sort(key=lambda x: x[0])
    if not metas:
        print("[!] No chunks found for requested window.")
        sys.exit(1)

    with open(outfile, "wb") as fo:
        for _, _, meta_path in metas:
            iq_path = meta_path.with_suffix('.iq')
            fo.write(iq_path.read_bytes())

    first_meta = json.loads(metas[0][2].read_text())
    combined = {
        "center_freq_hz": first_meta["center_freq_hz"],
        "samp_rate_hz": first_meta["samp_rate_hz"],
        "timestamp_utc": utcnow_iso(),
        "requested_window": {
            "start_rel_s": start_rel_s,
            "duration_s": duration_s
        }
    }
    write_json(Path(str(outfile) + ".json"), combined)
    print(f"[+] Wrote slice -> {outfile}")

# ===== Replay (stub) =====

def replay_stub(infile: Path, driver: str):
    print("[!] Replay is a stub in MVP. For HackRF, consider piping via hackrf_transfer:")
    print(f"    hackrf_transfer -t {infile} -f <freq_hz> -s <samp_rate> -x <tx_gain>")

# ===== CLI =====

def main():
    p = argparse.ArgumentParser(
        description="SDR-Rewind: rolling IQ capture, extraction, and replay (MVP)"
    )
    sub = p.add_subparsers(dest="cmd")

    p_cap = sub.add_parser("capture", help="Start rolling capture")
    p_cap.add_argument("--freq", type=float, required=True)
    p_cap.add_argument("--samp-rate", type=float, default=2.4e6)
    p_cap.add_argument("--gain", type=str, default="auto")
    p_cap.add_argument("--driver", type=str, default="rtlsdr")
    p_cap.add_argument("--buffer", type=int, default=60)
    p_cap.add_argument("--chunk", type=int, default=5)
    p_cap.add_argument("--outdir", type=Path, default=Path("captures"))

    p_ext = sub.add_parser("extract", help="Extract a time slice relative to now")
    p_ext.add_argument("--outdir", type=Path, default=Path("captures"))
    p_ext.add_argument("--start", type=float, required=True)
    p_ext.add_argument("--duration", type=float, required=True)
    p_ext.add_argument("--outfile", type=Path, required=True)

    p_rep = sub.add_parser("replay", help="Replay a stored slice (stub)")
    p_rep.add_argument("--infile", type=Path, required=True)
    p_rep.add_argument("--driver", type=str, default="hackrf")

    args = p.parse_args()

    if args.cmd in (None, "capture"):
        if args.cmd is None:
            args = p.parse_args(["capture", *sys.argv[1:]])
        capture_loop(args.freq, args.samp_rate, args.gain, args.outdir, args.buffer, args.chunk, args.driver)
    elif args.cmd == "extract":
        ensure_dir(args.outdir)
        extract_slice(args.outdir, args.start, args.duration, args.outfile)
    elif args.cmd == "replay":
        replay_stub(args.infile, args.driver)
    else:
        p.print_help()

if __name__ == "__main__":
    main()