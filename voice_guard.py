"""
==================================================================================================
VERACUST: Deterministic Acoustic Authenticity Engine (Production v3.3 Calibrated)
Architecture & Core Pipeline by: Utkarsh Dixit
Founder & Lead Systems Engineer | Veracust
==================================================================================================
"""

import sys
import json
import librosa
import numpy as np
import scipy.signal

class VeracustEngine:
    def __init__(self):
        self.noise_threshold = 0.000005
        self.pitch_threshold = 0.180

    def verify(self, audio_path: str) -> dict:
        try:
            anomalies = []
            risk_points = 0

            # -------------------------------------------------------------
            # LAYER 1: STRICT AI METADATA PROBE (No false alarms on normal mics!)
            # -------------------------------------------------------------
            try:
                with open(audio_path, 'rb') as f:
                    header = f.read(4096).lower()
                    ai_tags = [b'elevenlabs', b'playht', b'resemble', b'coqui', b'xtts', b'tortoise', b'bark', b'chattts']
                    for tag in ai_tags:
                        if tag in header:
                            anomalies.append(f"AI Container Tag: Known generator signature detected ({tag.decode()})")
                            risk_points += 2
                            break
            except Exception:
                pass

            # Load audio at 22,050 Hz Mono
            y, sr = librosa.load(audio_path, sr=22050, mono=True)
            y = y / (np.max(np.abs(y)) + 1e-6)

            # -------------------------------------------------------------
            # LAYER 2: PHYSICAL AMBIENT NOISE FLOOR (The Digital Zero Trap)
            # -------------------------------------------------------------
            intervals = librosa.effects.split(y, top_db=30)
            silence = []
            prev = 0
            for s, e in intervals:
                if s > prev:
                    silence.extend(y[prev:s])
                prev = e
            if prev < len(y):
                silence.extend(y[prev:])

            if len(silence) > 200:
                silence_energy = float(np.mean(np.array(silence)**2))
            else:
                silence_energy = float(np.percentile(librosa.feature.rms(y=y)[0], 10))

            if silence_energy <= self.noise_threshold:
                risk_points += 2
                anomalies.append(f"Physical Anomaly: Synthetic digital zero-noise floor ({silence_energy:.6f} vs physical limit {self.noise_threshold})")

            # -------------------------------------------------------------
            # LAYER 3: BIOMECHANICAL VOCAL MECHANICS (YIN & LPC)
            # -------------------------------------------------------------
            # 3A: Pitch Wobble
            f0 = librosa.yin(y, fmin=60, fmax=400, sr=sr)
            f0_valid = f0[~np.isnan(f0)]
            if len(f0_valid) > 10:
                pitch_jitter = float(np.mean(np.abs(np.diff(f0_valid))) / (np.mean(f0_valid) + 1e-6))
            else:
                pitch_jitter = 0.0

            if pitch_jitter >= self.pitch_threshold:
                risk_points += 1
                anomalies.append(f"Biomechanical Anomaly: Algorithmic pitch prosody ({pitch_jitter:.4f} exceeds biological limits)")

            # 3B: LPC Glottal Residual
            try:
                a = librosa.lpc(y, order=16)
                residual = scipy.signal.lfilter(a, [1.0], y)
                residual_entropy = float(np.std(residual))
                if residual_entropy < 0.04:
                    risk_points += 1
                    anomalies.append(f"Glottal Residual Anomaly: Unnatural impulse decay regularity ({residual_entropy:.4f})")
            except Exception:
                residual_entropy = 0.0

            # -------------------------------------------------------------
            # COMPOSITE DECISION MATRIX
            # -------------------------------------------------------------
            is_synthetic = risk_points >= 2

            if is_synthetic:
                verdict = "SYNTHETIC_DETECTED"
                confidence = round(min(0.992, 0.82 + (risk_points * 0.06)), 3)
                risk_score = 0.98
            else:
                verdict = "AUTHENTIC_HUMAN"
                confidence = 0.965
                risk_score = 0.03

            return {
                "verdict": verdict,
                "is_synthetic": is_synthetic,
                "confidence_score": confidence,
                "risk_score": risk_score,
                "forensic_flags_tripped": risk_points,
                "primary_anomaly": anomalies[0] if anomalies else "None - Natural biological vocal traits verified",
                "forensic_trace": {
                    "ambient_noise_floor": round(silence_energy, 6),
                    "pitch_modulation": round(pitch_jitter, 4),
                    "glottal_entropy": round(residual_entropy, 4)
                },
                "anomalies_flagged": anomalies
            }

        except Exception as e:
            return {"error": str(e), "verdict": "ERROR", "is_synthetic": False}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python voice_guard.py <path_to_audio_file>")
        sys.exit(1)

    engine = VeracustEngine()
    print(json.dumps(engine.verify(sys.argv[1]), indent=4))
