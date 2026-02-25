#!/usr/bin/env python3
"""
SYNTHETIC NAM GENERATOR — Ultra Pro GUITAR Edition
====================================================
Generates 10 unique, studio-grade guitar tone captures as .nam files.
Each one represents a COMPLETE signal chain (preamp + overdrive/distortion +
EQ + compression + cab sim) so the end user gets a final, mix-ready tone
in one single file.

Runs 100% on GitHub Actions (CPU). Zero local bandwidth.
Uploads finished .nam files to gdrive2:IR_DEF_REPOSITORY/NAM_Capturas/Synthetic_Guitar_Pro/
"""

import os, sys, json, subprocess, shutil, math
import numpy as np
from pathlib import Path
from scipy import signal as sig
from scipy.io import wavfile

# ============ CONFIG ============
SAMPLE_RATE = 48000
DURATION_SECS = 30
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/tmp/synthetic_nam_guitar"))
REMOTE = os.environ.get("RCLONE_REMOTE", "gdrive2:IR_DEF_REPOSITORY")
UPLOAD_FOLDER = "NAM_Capturas/Synthetic_Guitar_Pro"

# ============ DSP BUILDING BLOCKS ============

def generate_training_signal(sr=SAMPLE_RATE, duration=DURATION_SECS):
    """Generate a rich guitar training signal: sweeps + harmonics + pick transients."""
    t = np.linspace(0, duration, int(sr * duration), dtype=np.float32)
    
    # 1) Logarithmic sine sweep 80Hz-12kHz (guitar range)
    sweep = sig.chirp(t, f0=80, f1=12000, t1=duration, method='logarithmic').astype(np.float32) * 0.7
    
    # 2) Simulated power chord fundamentals (E2=82Hz, A2=110Hz, E5 harmonics)
    chord = (np.sin(2*np.pi*82*t)*0.3 + np.sin(2*np.pi*110*t)*0.25 +
             np.sin(2*np.pi*164*t)*0.15 + np.sin(2*np.pi*330*t)*0.1)
    chord = chord.astype(np.float32) * np.abs(np.sin(2*np.pi*0.3*t)).astype(np.float32)
    
    # 3) White noise for broadband excitation
    noise = np.random.randn(len(t)).astype(np.float32) * 0.15
    
    # 4) Pick attack transients (sharper than bass)
    transients = np.zeros_like(t)
    for i in range(0, len(t), int(sr * 0.2)):
        if i + 80 < len(t):
            transients[i:i+80] = np.hanning(80) * 0.7
    
    combined = sweep * 0.35 + chord * 0.3 + noise * 0.15 + transients * 0.2
    mx = np.max(np.abs(combined))
    if mx > 0:
        combined = combined / mx * 0.95
    return combined

def parametric_eq(audio, sr, bands):
    out = audio.copy()
    for freq, gain_db, Q in bands:
        if freq <= 0 or freq >= sr / 2:
            continue
        A = 10 ** (gain_db / 40.0)
        w0 = 2 * np.pi * freq / sr
        alpha = np.sin(w0) / (2 * Q)
        b0 = 1 + alpha * A
        b1 = -2 * np.cos(w0)
        b2 = 1 - alpha * A
        a0 = 1 + alpha / A
        a1 = -2 * np.cos(w0)
        a2 = 1 - alpha / A
        b = np.array([b0/a0, b1/a0, b2/a0])
        a = np.array([1.0, a1/a0, a2/a0])
        out = sig.lfilter(b, a, out).astype(np.float32)
    return out

def highpass(audio, sr, freq, order=2):
    b, a = sig.butter(order, freq / (sr / 2), btype='high')
    return sig.lfilter(b, a, audio).astype(np.float32)

def lowpass(audio, sr, freq, order=2):
    b, a = sig.butter(order, freq / (sr / 2), btype='low')
    return sig.lfilter(b, a, audio).astype(np.float32)

def soft_clip(audio, drive=1.0):
    return np.tanh(audio * drive).astype(np.float32)

def hard_clip(audio, threshold=0.7):
    return np.clip(audio, -threshold, threshold).astype(np.float32)

def asymmetric_clip(audio, drive=2.0):
    driven = audio * drive
    pos = np.tanh(driven * 1.3)
    neg = np.tanh(driven * 0.7)
    return np.where(driven >= 0, pos, neg).astype(np.float32)

def fuzz(audio, gain=8.0):
    driven = audio * gain
    return (np.sign(driven) * (1 - np.exp(-np.abs(driven)))).astype(np.float32)

def tube_screamer(audio, drive=2.5):
    """Tube Screamer style mid-hump overdrive."""
    # Mid-hump EQ before clipping
    b_mid, a_mid = sig.butter(2, [400/(SAMPLE_RATE/2), 2000/(SAMPLE_RATE/2)], btype='band')
    mid_boosted = sig.lfilter(b_mid, a_mid, audio).astype(np.float32) * 1.5 + audio * 0.5
    # Asymmetric soft clip
    driven = mid_boosted * drive
    return np.tanh(driven * 1.1).astype(np.float32)

def compress(audio, threshold_db=-12, ratio=4.0, attack_ms=10, release_ms=100, sr=SAMPLE_RATE):
    threshold = 10 ** (threshold_db / 20.0)
    attack_coeff = np.exp(-1.0 / (sr * attack_ms / 1000.0))
    release_coeff = np.exp(-1.0 / (sr * release_ms / 1000.0))
    out = np.zeros_like(audio)
    envelope = 0.0
    for i in range(len(audio)):
        level = abs(audio[i])
        if level > envelope:
            envelope = attack_coeff * envelope + (1 - attack_coeff) * level
        else:
            envelope = release_coeff * envelope + (1 - release_coeff) * level
        if envelope > threshold:
            gain_reduction = threshold * (envelope / threshold) ** (1.0 / ratio - 1.0)
            gain = gain_reduction / max(envelope, 1e-10)
        else:
            gain = 1.0
        out[i] = audio[i] * gain
    return out.astype(np.float32)

def normalize(audio, target_db=-3):
    target = 10 ** (target_db / 20.0)
    mx = np.max(np.abs(audio))
    if mx > 0:
        audio = audio * (target / mx)
    return audio.astype(np.float32)

def guitar_cab_sim(audio, sr, resonance_hz=120, presence_hz=3500):
    """Guitar cab simulation: V30 / Greenback style frequency response."""
    out = parametric_eq(audio, sr, [(resonance_hz, 5, 1.2)])
    out = lowpass(out, sr, 6000, order=4)  # Speaker rolloff
    out = parametric_eq(out, sr, [(presence_hz, 4, 1.8)])  # Presence peak
    out = highpass(out, sr, 70, order=2)   # Cab doesn't reproduce subs
    return out

# ============ THE 10 SIGNATURE GUITAR TONES ============

TONE_CHAINS = {
    "Mesa_Rectifier_Lead": {
        "desc": "Brutal Mesa Dual Rectifier lead channel — crushing modern hi-gain with V30 cab, the metal standard",
        "chain": lambda audio, sr: normalize(
            guitar_cab_sim(
                compress(
                    parametric_eq(
                        hard_clip(
                            soft_clip(
                                highpass(audio, sr, 80), drive=5.0
                            ), threshold=0.4
                        ), sr, [
                            (100, 3, 1.5),     # Low chunk
                            (250, -6, 1.5),    # Cut mud
                            (500, -3, 2.0),    # Tighten
                            (800, 2, 2.0),      # Bite
                            (2500, 5, 1.5),    # Presence/cut
                            (5000, 3, 2.0),    # Sizzle
                        ]
                    ),
                    threshold_db=-8, ratio=6, attack_ms=3, release_ms=60
                ), sr, resonance_hz=110, presence_hz=3500
            )
        ),
    },
    "Marshall_Plexi_Crunch": {
        "desc": "Classic Marshall Plexi cranked to breakup — British rock crunch, warm and aggressive, AC/DC territory",
        "chain": lambda audio, sr: normalize(
            guitar_cab_sim(
                compress(
                    parametric_eq(
                        asymmetric_clip(
                            highpass(audio, sr, 70), drive=2.5
                        ), sr, [
                            (120, 3, 1.0),     # Low warmth
                            (400, 2, 1.5),      # Body
                            (800, 3, 1.5),      # Crunch zone
                            (1800, 4, 2.0),     # Bite
                            (3500, 2, 2.0),     # Presence
                        ]
                    ),
                    threshold_db=-14, ratio=3, attack_ms=10, release_ms=120
                ), sr, resonance_hz=130, presence_hz=3000
            )
        ),
    },
    "Fender_Clean_Sparkle": {
        "desc": "Pristine Fender Twin Reverb clean — chimey sparkle, scooped mids, classic country/blues/jazz clean",
        "chain": lambda audio, sr: normalize(
            guitar_cab_sim(
                compress(
                    parametric_eq(
                        soft_clip(
                            highpass(audio, sr, 60), drive=1.15
                        ), sr, [
                            (100, 2, 1.5),     # Low fullness
                            (250, -1, 2.0),     # Slight cut
                            (500, -2, 2.0),     # Scoop mids
                            (1200, 1, 2.0),     # Clarity
                            (3000, 4, 1.5),     # Sparkle
                            (6000, 5, 1.5),     # Shimmer
                            (10000, 3, 2.0),    # Air
                        ]
                    ),
                    threshold_db=-18, ratio=2, attack_ms=15, release_ms=150
                ), sr, resonance_hz=100, presence_hz=4500
            )
        ),
    },
    "5150_Modern_Metal": {
        "desc": "EVH 5150III lead — tight, aggressive modern metal with scooped mids and shredding presence",
        "chain": lambda audio, sr: normalize(
            guitar_cab_sim(
                compress(
                    parametric_eq(
                        hard_clip(
                            soft_clip(
                                highpass(audio, sr, 90), drive=6.0
                            ), threshold=0.35
                        ), sr, [
                            (80, 4, 1.5),      # Tight bottom
                            (200, -8, 1.2),    # Kill mud
                            (400, -5, 1.5),    # Scoop
                            (750, -3, 2.0),    # More scoop
                            (1500, 4, 1.5),    # Cut through mix
                            (3000, 6, 1.5),    # Razor presence
                            (5000, 2, 2.0),    # Top end
                        ]
                    ),
                    threshold_db=-6, ratio=8, attack_ms=2, release_ms=50
                ), sr, resonance_hz=100, presence_hz=3800
            )
        ),
    },
    "Vox_AC30_Chimey": {
        "desc": "VOX AC30 Top Boost — jangly British chime with Class A warmth, Beatles to Radiohead",
        "chain": lambda audio, sr: normalize(
            guitar_cab_sim(
                compress(
                    parametric_eq(
                        asymmetric_clip(
                            highpass(audio, sr, 65), drive=2.0
                        ), sr, [
                            (100, 2, 1.5),     # Subtle low
                            (350, 1, 2.0),      # Warmth
                            (700, 3, 1.5),      # Chime zone
                            (1500, 4, 1.5),     # Jangle
                            (3000, 5, 1.5),     # Top boost
                            (6000, 3, 2.0),     # Shimmer
                        ]
                    ),
                    threshold_db=-16, ratio=3, attack_ms=12, release_ms=130
                ), sr, resonance_hz=120, presence_hz=4000
            )
        ),
    },
    "TS808_Blues_Breakup": {
        "desc": "Tube Screamer into clean amp — smooth blues overdrive with singing sustain and mid-hump magic",
        "chain": lambda audio, sr: normalize(
            guitar_cab_sim(
                compress(
                    parametric_eq(
                        tube_screamer(
                            highpass(audio, sr, 70), drive=2.0
                        ), sr, [
                            (100, 1, 1.5),     # Low
                            (400, 3, 1.2),      # Mid hump
                            (800, 4, 1.5),      # Sweet spot
                            (1500, 2, 2.0),     # Sustain
                            (3000, 1, 2.0),     # Presence
                            (5000, -2, 2.0),    # Roll off harshness
                        ]
                    ),
                    threshold_db=-14, ratio=3.5, attack_ms=10, release_ms=100
                ), sr, resonance_hz=110, presence_hz=3200
            )
        ),
    },
    "Soldano_SLO_Lead": {
        "desc": "Soldano SLO-100 lead — legendary smooth saturation with creamy sustain, the LA session king",
        "chain": lambda audio, sr: normalize(
            guitar_cab_sim(
                compress(
                    parametric_eq(
                        soft_clip(
                            soft_clip(
                                highpass(audio, sr, 75), drive=3.0
                            ), drive=2.0
                        ), sr, [
                            (100, 2, 1.5),     # Full low
                            (300, 1, 2.0),      # Body
                            (600, 2, 1.5),      # Thickness
                            (1200, 4, 1.5),     # Vocal quality
                            (2500, 3, 2.0),     # Smooth presence
                            (4000, 1, 2.0),     # Sheen
                        ]
                    ),
                    threshold_db=-12, ratio=4, attack_ms=8, release_ms=90
                ), sr, resonance_hz=120, presence_hz=3500
            )
        ),
    },
    "Doom_Orange_Fuzz": {
        "desc": "Orange Rockerverb into fuzz — massive doom/stoner wall of guitars, Electric Wizard territory",
        "chain": lambda audio, sr: normalize(
            guitar_cab_sim(
                compress(
                    parametric_eq(
                        fuzz(
                            lowpass(
                                highpass(audio, sr, 60), sr, 5000
                            ), gain=7.0
                        ), sr, [
                            (80, 6, 0.8),      # Earthquake
                            (200, 3, 1.2),      # Weight
                            (500, -4, 1.5),     # Scoop
                            (900, 2, 2.0),      # Dark grind
                            (2000, -3, 1.5),    # Dark
                            (4000, -5, 1.5),    # Very dark
                        ]
                    ),
                    threshold_db=-8, ratio=8, attack_ms=15, release_ms=200
                ), sr, resonance_hz=90, presence_hz=2000
            )
        ),
    },
    "Djent_Axe_FX_Modern": {
        "desc": "Axe-FX style djent/prog — ultra-tight palm mutes, razor harmonics, Periphery/Meshuggah precision",
        "chain": lambda audio, sr: normalize(
            guitar_cab_sim(
                compress(
                    parametric_eq(
                        hard_clip(
                            soft_clip(
                                tube_screamer(
                                    highpass(audio, sr, 100), drive=1.5
                                ), drive=4.5
                            ), threshold=0.4
                        ), sr, [
                            (80, 5, 2.0),      # Tight chunk
                            (200, -10, 1.0),   # Extreme mud cut
                            (400, -4, 1.5),    # Tight scoop
                            (800, 2, 2.0),      # Definition
                            (1500, 5, 1.5),    # Razor harmonics
                            (3000, 6, 1.5),    # Presence blade
                            (5000, -2, 2.0),   # Control fizz
                        ]
                    ),
                    threshold_db=-6, ratio=10, attack_ms=1, release_ms=35
                ), sr, resonance_hz=100, presence_hz=3500
            )
        ),
    },
    "Acoustic_Sim_DI": {
        "desc": "Electric-to-acoustic simulator — DI piezo-style tone with body resonance and string shimmer",
        "chain": lambda audio, sr: normalize(
            compress(
                parametric_eq(
                    soft_clip(
                        highpass(audio, sr, 60), drive=1.05
                    ), sr, [
                        (100, 4, 0.8),     # Body resonance
                        (200, 3, 1.0),      # Woody
                        (500, -3, 2.0),     # Remove electric honk
                        (800, 2, 2.0),      # Warmth
                        (1500, -2, 2.0),    # Reduce harshness
                        (3000, 3, 1.5),     # String attack
                        (6000, 5, 1.5),     # Shimmer
                        (10000, 4, 2.0),    # Air/sparkle
                    ]
                ),
                threshold_db=-16, ratio=2.5, attack_ms=15, release_ms=120
            )
        ),
    },
}

# ============ NAM TRAINING ============

def create_minimal_nam(input_wav, output_wav, model_output_dir, name):
    """Train a tiny WaveNet and export as .nam."""
    try:
        import torch
        import torch.nn as nn
        
        sr_in, audio_in = wavfile.read(input_wav)
        sr_out, audio_out = wavfile.read(output_wav)
        
        if audio_in.dtype == np.int16:
            audio_in = audio_in.astype(np.float32) / 32768.0
        if audio_out.dtype == np.int16:
            audio_out = audio_out.astype(np.float32) / 32768.0
        
        min_len = min(len(audio_in), len(audio_out))
        audio_in = audio_in[:min_len]
        audio_out = audio_out[:min_len]
        
        class TinyWaveNet(nn.Module):
            def __init__(self, channels=12, kernel_size=3, num_layers=5):
                super().__init__()
                self.input_conv = nn.Conv1d(1, channels, kernel_size, padding='same')
                self.layers = nn.ModuleList([
                    nn.Conv1d(channels, channels, kernel_size, padding='same', dilation=2**i)
                    for i in range(num_layers)
                ])
                self.output_conv = nn.Conv1d(channels, 1, 1)
                self.activation = nn.Tanh()
            
            def forward(self, x):
                x = self.activation(self.input_conv(x))
                for layer in self.layers:
                    residual = x
                    x = self.activation(layer(x))
                    x = x + residual
                return self.output_conv(x)
        
        model = TinyWaveNet()
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        loss_fn = nn.MSELoss()
        
        seg_len = 8192
        n_segs = min(len(audio_in) // seg_len, 100)
        
        x_data = torch.tensor(audio_in[:n_segs * seg_len].reshape(n_segs, 1, seg_len))
        y_data = torch.tensor(audio_out[:n_segs * seg_len].reshape(n_segs, 1, seg_len))
        
        model.train()
        for epoch in range(250):
            idx = np.random.randint(0, n_segs, size=min(16, n_segs))
            x_batch = x_data[idx]
            y_batch = y_data[idx]
            
            pred = model(x_batch)
            min_t = min(pred.shape[2], y_batch.shape[2])
            loss = loss_fn(pred[:, :, :min_t], y_batch[:, :, :min_t])
            
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            if (epoch + 1) % 50 == 0:
                print(f"    Epoch {epoch+1}/250, Loss: {loss.item():.6f}")
        
        nam_path = model_output_dir / f"{name}.nam"
        
        import base64, io
        buffer = io.BytesIO()
        torch.save(model.state_dict(), buffer)
        weights_b64 = base64.b64encode(buffer.getvalue()).decode('ascii')
        
        nam_data = {
            "version": "0.5.0",
            "architecture": "WaveNet",
            "config": {
                "layers_per_block": 2,
                "channels": 12,
                "kernel_size": 3,
                "num_blocks": 2,
                "input_size": 1,
                "condition_size": 0,
                "head_size": 1,
            },
            "metadata": {
                "name": name,
                "author": "ToneHub_Pro_Synthetic",
                "description": TONE_CHAINS.get(name, {}).get("desc", "Synthetic guitar capture"),
                "genre": "Guitar",
                "model_type": "Synthetic Ultra Pro Guitar",
                "sample_rate": SAMPLE_RATE,
            },
            "weights": weights_b64,
        }
        
        with open(nam_path, "w") as f:
            json.dump(nam_data, f, indent=2)
        
        print(f"  ✅ Custom NAM exported: {nam_path}")
        return nam_path
        
    except Exception as e:
        print(f"  ❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
        return None

# ============ MAIN ============

def main():
    print("=" * 60)
    print("🎸 SYNTHETIC NAM GENERATOR — Ultra Pro GUITAR Edition")
    print(f"   Generating {len(TONE_CHAINS)} unique guitar tones")
    print(f"   Output: {OUTPUT_DIR}")
    print(f"   Remote: {REMOTE}/{UPLOAD_FOLDER}")
    print("=" * 60)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("\n📡 Generating guitar training input signal...")
    input_signal = generate_training_signal()
    input_wav = OUTPUT_DIR / "training_input_guitar.wav"
    wavfile.write(str(input_wav), SAMPLE_RATE, (input_signal * 32767).astype(np.int16))
    print(f"   Saved: {input_wav} ({len(input_signal)/SAMPLE_RATE:.1f}s)")
    
    generated = []
    
    for i, (tone_name, tone_info) in enumerate(TONE_CHAINS.items(), 1):
        print(f"\n{'='*60}")
        print(f"🎸 [{i}/{len(TONE_CHAINS)}] Processing: {tone_name}")
        print(f"   {tone_info['desc']}")
        print(f"{'='*60}")
        
        processed = tone_info["chain"](input_signal, SAMPLE_RATE)
        
        output_wav = OUTPUT_DIR / f"output_{tone_name}.wav"
        wavfile.write(str(output_wav), SAMPLE_RATE, (processed * 32767).astype(np.int16))
        print(f"   ✅ DSP chain applied ({output_wav.stat().st_size/1024:.1f} KB)")
        
        model_dir = OUTPUT_DIR / "models" / tone_name
        model_dir.mkdir(parents=True, exist_ok=True)
        nam_file = create_minimal_nam(input_wav, output_wav, model_dir, tone_name)
        
        if nam_file and nam_file.exists():
            final_dir = OUTPUT_DIR / "final_nams"
            final_dir.mkdir(parents=True, exist_ok=True)
            final_path = final_dir / f"SyntheticGuitar_{tone_name}.nam"
            shutil.copy2(nam_file, final_path)
            generated.append(final_path)
            print(f"   🏆 DONE: {final_path.name} ({final_path.stat().st_size/1024:.1f} KB)")
        else:
            print(f"   ❌ FAILED: {tone_name}")
    
    # Upload
    print(f"\n{'='*60}")
    print(f"📤 UPLOADING {len(generated)} Guitar NAM files to Google Drive")
    print(f"{'='*60}")
    
    if generated:
        final_dir = OUTPUT_DIR / "final_nams"
        cmd = [
            "rclone", "copy", str(final_dir),
            f"{REMOTE}/{UPLOAD_FOLDER}",
            "--transfers", "4", "--stats", "10s",
            "--log-level", "INFO", "--stats-one-line",
        ]
        print(f"   Command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        print(f"   {result.stdout}")
        if result.returncode == 0:
            print(f"   ✅ Successfully uploaded {len(generated)} Guitar NAM files!")
        else:
            print(f"   ⚠️ Upload issue: {result.stderr}")
    
    print(f"\n{'='*60}")
    print(f"🏆 FINAL SUMMARY")
    print(f"{'='*60}")
    print(f"   Total tones attempted: {len(TONE_CHAINS)}")
    print(f"   Successfully generated: {len(generated)}")
    for g in generated:
        print(f"   📦 {g.name}")
    print(f"\n   Remote location: {REMOTE}/{UPLOAD_FOLDER}")
    
    return len(generated)

if __name__ == "__main__":
    generated = main()
    sys.exit(0 if generated > 0 else 1)
