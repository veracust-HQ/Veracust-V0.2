<div align="center">

# VERACUST
### Deterministic Acoustic Authenticity Engine for Enterprise Infrastructure

[![API Status](https://img.shields.io/badge/API-Online_200_OK-00E5FF?style=flat-square)](https://voiceguard-core.onrender.com/docs)
[![Latency SLA](https://img.shields.io/badge/Inference_SLA-%3C150ms_CPU-brightgreen?style=flat-square)]()
[![Compliance](https://img.shields.io/badge/Data_Privacy-GDPR_%7C_PCI--DSS_Ephemeral-blueviolet?style=flat-square)]()
[![License](https://img.shields.io/badge/Architecture-Proprietary_Core_v3.4-black?style=flat-square)]()

**Engineered by: Utkarsh Dixit**  
*Founder & Lead Systems Engineer | Veracust*

</div>

---

## 1. Executive Summary

**Veracust** is an on-premises acoustic forensics engine engineered to protect banking telephony, wealth management verification lines, and customer service infrastructure against real-time generative voice cloning (e.g., ElevenLabs, Speech-to-Speech runtimes, and diffusion vocoders).

Traditional deepfake detection systems fail in live production because they rely on fragile, black-box deep learning classifiers trained on studio datasets—yielding unacceptable False Positive Rates (FPR) on standard phone lines. 

Veracust replaces probabilistic guesswork with **deterministic physical acoustics and digital signal processing (DSP)**. By evaluating ambient room-air entropy, inverse-filtered glottal pulses, and container-level provenance signatures, Veracust executes in **under 150 milliseconds on standard CPU hardware**, ensuring zero customer voice data ever leaves the enterprise perimeter.

---

## 2. Multi-Stage Forensic Architecture

[ Inbound Audio Stream / Telephony Payload ]
                                  │
                                  ▼
        ┌───────────────────────────────────────────────────┐
        │ STAGE 1: PRE-INGESTION BYTE PROVENANCE SNIFFER    │
        │ Scans raw file bytes before decoding/resampling   │
        │ Catches container signatures, C2PA, and S2S tags  │
        └─────────────────────────┬─────────────────────────┘
                                  │
                                  ▼
        ┌───────────────────────────────────────────────────┐
        │ STAGE 2: PHYSICAL & BIOMECHANICAL ANALYSIS (DSP)  │
        │ • 16th-Order LPC Glottal Residual Inversion       │
        │ • YIN Fundamental Frequency (F0) Jitter Tracking  │
        │ • Ambient Noise Floor Zero-Entropy Extraction     │
        │ • Nyquist Carrier Roll-Off Spectral Analysis      │
        └─────────────────────────┬─────────────────────────┘
                                  │
                                  ▼
        ┌───────────────────────────────────────────────────┐
        │ STAGE 3: CODEC-AWARE DYNAMIC WEIGHT SHIFTING      │
        │ Damps high-frequency metrics on G.711/AMR lines   │
        │ Anchors decisioning to 60–400Hz baseband acoustics│
        └─────────────────────────┬─────────────────────────┘
                                  │
                                  ▼
        ┌───────────────────────────────────────────────────┐
        │ STAGE 4: THREE-TIERED TELEMETRY & DECISION GATE   │
        │ • AUTHENTIC_HUMAN        (Proceed standard auth)  │
        │ • SYNTHETIC_DETECTED     (Block transaction)      │
        │ • INCONCLUSIVE_ESCALATE  (Trigger secondary MFA)  │
        └───────────────────────────────────────────────────┘

        ---

## 3. Core Forensic Vectors

### 1. Ambient Thermal Room-Air Entropy
Physical microphones (condenser and dynamic) continuously capture analog ambient air resistance and preamp noise ($-45\text{dB}$ to $-60\text{dB}$ RMS). Synthetic neural vocoders render audio mathematically on cloud chips, generating unnatural **digital zero-noise floors ($\le 10^{-6}\text{ RMS}$)** during speech pauses. Veracust isolates unvoiced intervals to catch digital audio injections.

### 2. Linear Predictive Coding (LPC) Glottal Inverse Filtering
Human speech is produced via vocal cord excitation filtered by the vocal tract. Veracust computes a 16th-order LPC inverse filter to subtract vocal tract resonance and evaluate the raw **glottal residual pulse**. While human vocal fold decay exhibits biological variance, synthetic speech algorithms produce unnaturally rigid pulse decay entropy ($<0.04$).

### 3. Codec-Aware Channel Normalization
Telephony codecs (G.711, AMR-WB, Opus) and modern neural codecs heavily truncate high-frequency acoustic data. Veracust dynamically analyzes carrier energy ratios: if transmission bandwidth is constrained, the engine automatically down-weights high-frequency metrics and anchors verification inside the protected 60Hz–400Hz human baseband.

---

## 4. Live Telemetry & API Payload

### Endpoint: `POST /v1/verify`
```bash
curl -X 'POST' \
  'https://voiceguard-core.onrender.com/v1/verify' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@telephony_sample.wav'
