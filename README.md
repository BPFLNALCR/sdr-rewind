# SDR-Rewind 📼

![Build Status](https://img.shields.io/badge/build-In_Progress-yellow)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi%204%2F5-red)
![SDR](https://img.shields.io/badge/SDR-RTL--SDR-blue)
![Planned SDRs](https://img.shields.io/badge/Planned-HackRF%2C%20Airspy%2C%20LimeSDR-yellow)
![Cluster](https://img.shields.io/badge/Feature-Distributed%20Recording-purple)
![License](https://img.shields.io/badge/license-GNU-lightgrey)

**A distributed spectrum recorder for SDR devices. Capture, rewind, and replay the ether.**

This project is a Python-based tool that continuously records IQ data into rolling buffers on Raspberry Pi nodes.  
Users can "rewind" the RF environment, extract specific slices of spectrum/time, and even replay signals live through supported SDRs.  

At its current stage of development, SDR-Rewind is:  
* ✅ Optimized for **RTL-SDR** devices (HackRF, Airspy, LimeSDR, etc. planned).  
* ✅ Intended to run on **Raspberry Pi 4/5** nodes with local storage.  
* ✅ Usable as both a standalone capture service and a distributed cluster.  

---

## ✨ Features

* **📼 Rolling Capture**: Maintain a circular buffer of IQ samples (configurable size).  
* **🔍 Time-Slicing**: Extract specific windows of spectrum/time for offline analysis.  
* **🔁 Replay Mode**: Pipe stored IQ back into SDR hardware for re-transmission or decoding.  
* **🌐 Distributed Operation**: Coordinate multiple Pis to act as a spectrum archiving cluster.  
* **💾 Data Export**: Save captured segments to files (WAV, IQ, HDF5) for long-term storage.  
* **📊 Integration**: Optional hooks into SDR-Watch for event-triggered captures.  

---

## 🛠️ Installation (Raspberry Pi 5 – Raspbian Lite)

```bash
# Update packages
sudo apt update && sudo apt upgrade -y

# Core dependencies
sudo apt install -y python3 python3-pip python3-numpy python3-scipy \
    python3-soapysdr soapysdr-module-rtlsdr rtl-sdr libatlas-base-dev

# Install Python dependencies
pip3 install -r requirements.txt
```

---

## 🚀 Usage

### Start a capture buffer

```bash
python3 sdrrewind.py --freq 100e6 --samp-rate 2.4e6 --driver rtlsdr \
  --buffer 60 --outdir ./captures
```

This records a 60-second rolling buffer at 100 MHz.  

### Extract a 10-second slice

```bash
python3 sdrrewind.py extract --freq 100e6 --start -30 --duration 10 --outfile fm_slice.iq
```

### Replay a stored slice

```bash
python3 sdrrewind.py replay --infile fm_slice.iq --driver hackrf
```

---

## 🗄️ Data Format

By default, data is stored as raw **complex64 IQ files** with JSON sidecar metadata:  

```json
{
  "center_freq_hz": 100000000,
  "samp_rate_hz": 2400000,
  "timestamp_utc": "2025-08-27T21:57:02.979818Z",
  "duration_s": 10.0
}
```

Optional: HDF5/NumPy storage for efficient slicing and indexing.  

---

## 🛣️ Roadmap

* Add cluster controller for multi-node capture/replay.  
* Implement real-time indexing for fast lookup by time/frequency.  
* Provide web dashboard for visual rewind and playback control.  
* Integrate with SDR-Watch event triggers (auto-capture when new signals detected).  

---

## 📜 License

GPL v3.0 License. See [LICENSE](LICENSE).

---

## 🙏 Acknowledgements

Inspired by existing SDR recording tools (rtl_sdr, sox IQ capture), but built for **rolling storage**, **distributed operation**, and **seamless replay**.
