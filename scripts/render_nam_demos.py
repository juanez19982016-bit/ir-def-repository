#!/usr/bin/env python3
"""
NAM AUDIO DEMO GENERATOR
==========================
Generates listenable .wav audio demos for every synthetic NAM.
Takes a simulated clean guitar/bass DI signal, passes it through each
NAM model, and renders the output as playable .wav files.

The user can then listen to each demo in any media player to judge quality.
"""

import os, sys, json, subprocess, shutil, base64, io
import numpy as np
from pathlib import Path
from scipy import signal as sig
from scipy.io import wavfile

SAMPLE_RATE = 48000
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/tmp/nam_demos"))
REMOTE = os.environ.get("RCLONE_REMOTE", "gdrive2:IR_DEF_REPOSITORY")

# ============ REALISTIC DI SIGNAL GENERATORS ============

def gen_guitar_riff_di(sr=SAMPLE_RATE):
    """Generate a realistic clean guitar DI: power chords, single notes, palm mutes."""
    duration = 12.0  # 12 seconds of demo
    t = np.linspace(0, duration, int(sr * duration), dtype=np.float32)
    audio = np.zeros_like(t)
    
    def note(freq, start, dur, velocity=0.6):
        """Single note with realistic envelope."""
        n = int(dur * sr)
        s = int(start * sr)
        if s + n > len(audio):
            n = len(audio) - s
        tt = np.linspace(0, dur, n, dtype=np.float32)
        # Guitar-like envelope: fast attack, slow decay
        env = velocity * np.exp(-tt * 3.0) * (1 - np.exp(-tt * 200))
        # Note with harmonics (more realistic than pure sine)
        wave = (np.sin(2*np.pi*freq*tt) * 1.0 +
                np.sin(2*np.pi*freq*2*tt) * 0.5 +
                np.sin(2*np.pi*freq*3*tt) * 0.25 +
                np.sin(2*np.pi*freq*4*tt) * 0.12 +
                np.sin(2*np.pi*freq*5*tt) * 0.06)
        wave = wave / np.max(np.abs(wave) + 1e-10)
        audio[s:s+n] += (wave * env).astype(np.float32)
    
    def power_chord(root, start, dur, velocity=0.7):
        """Power chord: root + fifth + octave."""
        note(root, start, dur, velocity)
        note(root * 1.5, start, dur, velocity * 0.8)
        note(root * 2, start, dur, velocity * 0.6)
    
    def palm_mute(freq, start, dur=0.15, velocity=0.5):
        """Short palm-muted note."""
        n = int(dur * sr)
        s = int(start * sr)
        if s + n > len(audio):
            n = len(audio) - s
        tt = np.linspace(0, dur, n, dtype=np.float32)
        env = velocity * np.exp(-tt * 20.0) * (1 - np.exp(-tt * 500))
        wave = np.sin(2*np.pi*freq*tt) + np.sin(2*np.pi*freq*2*tt)*0.3
        wave = wave / np.max(np.abs(wave) + 1e-10)
        audio[s:s+n] += (wave * env).astype(np.float32)
    
    # === RIFF PATTERN ===
    E2 = 82.41; A2 = 110.0; D3 = 146.83; G3 = 196.0; B3 = 246.94; E4 = 329.63
    
    # Bar 1: Palm muted E chugs (0-3s)
    for i in range(12):
        palm_mute(E2, 0.0 + i * 0.25, 0.12, 0.6)
    
    # Bar 2: Power chords (3-6s)
    power_chord(E2, 3.0, 0.8, 0.75)
    power_chord(G3, 3.9, 0.6, 0.7)
    power_chord(A2, 4.6, 0.8, 0.75)
    power_chord(E2, 5.5, 0.5, 0.7)
    
    # Bar 3: Single note melody (6-9s)
    melody_notes = [E4, D3*2, B3, A2*2, G3, A2*2, B3, D3*2]
    for i, n_freq in enumerate(melody_notes):
        note(n_freq, 6.0 + i * 0.35, 0.3, 0.55)
    
    # Bar 4: Open chord ring out (9-12s)
    power_chord(E2, 9.0, 2.5, 0.8)
    power_chord(A2, 11.5, 0.5, 0.6)
    
    # Normalize
    mx = np.max(np.abs(audio))
    if mx > 0:
        audio = audio / mx * 0.85
    return audio

def gen_bass_riff_di(sr=SAMPLE_RATE):
    """Generate a realistic clean bass DI: root notes, walks, slap hits."""
    duration = 12.0
    t = np.linspace(0, duration, int(sr * duration), dtype=np.float32)
    audio = np.zeros_like(t)
    
    def bass_note(freq, start, dur, velocity=0.7):
        n = int(dur * sr)
        s = int(start * sr)
        if s + n > len(audio):
            n = len(audio) - s
        tt = np.linspace(0, dur, n, dtype=np.float32)
        env = velocity * np.exp(-tt * 2.0) * (1 - np.exp(-tt * 150))
        # Bass has strong fundamental, weaker harmonics
        wave = (np.sin(2*np.pi*freq*tt) * 1.0 +
                np.sin(2*np.pi*freq*2*tt) * 0.35 +
                np.sin(2*np.pi*freq*3*tt) * 0.15 +
                np.sin(2*np.pi*freq*4*tt) * 0.05)
        wave = wave / np.max(np.abs(wave) + 1e-10)
        audio[s:s+n] += (wave * env).astype(np.float32)
    
    def slap_hit(freq, start, velocity=0.8):
        n = int(0.1 * sr)
        s = int(start * sr)
        if s + n > len(audio):
            n = len(audio) - s
        tt = np.linspace(0, 0.1, n, dtype=np.float32)
        env = velocity * np.exp(-tt * 30.0) * (1 - np.exp(-tt * 800))
        wave = np.sin(2*np.pi*freq*tt) + np.random.randn(n).astype(np.float32) * 0.15
        wave = wave / np.max(np.abs(wave) + 1e-10)
        audio[s:s+n] += (wave * env).astype(np.float32)
    
    E1 = 41.20; A1 = 55.0; D2 = 73.42; G2 = 98.0; E2 = 82.41
    
    # Bar 1: Steady eighth notes on E (0-3s)
    for i in range(6):
        bass_note(E1, i * 0.5, 0.45, 0.7)
    
    # Bar 2: Walking bass line (3-6s)
    walk = [E1, G2, A1, E2, D2, A1, G2, E1]
    for i, freq in enumerate(walk):
        bass_note(freq, 3.0 + i * 0.375, 0.35, 0.65)
    
    # Bar 3: Slap pattern (6-9s)
    slap_times = [6.0, 6.3, 6.6, 7.0, 7.3, 7.6, 8.0, 8.5]
    slap_notes = [E1, G2, E1, A1, G2, E1, A1, E1]
    for t_s, freq in zip(slap_times, slap_notes):
        slap_hit(freq, t_s, 0.75)
    
    # Bar 4: Long sustain (9-12s)
    bass_note(E1, 9.0, 3.0, 0.8)
    
    mx = np.max(np.abs(audio))
    if mx > 0:
        audio = audio / mx * 0.85
    return audio

# ============ MODEL LOADER ============

def load_nam_model(nam_path):
    import torch
    import torch.nn as nn
    
    with open(nam_path, 'r') as f:
        nam_data = json.load(f)
    
    channels = nam_data["config"].get("channels", 8)
    kernel_size = nam_data["config"].get("kernel_size", 3)
    
    weights_bytes = base64.b64decode(nam_data["weights"])
    buffer = io.BytesIO(weights_bytes)
    state_dict = torch.load(buffer, map_location='cpu', weights_only=False)
    
    layer_keys = [k for k in state_dict.keys() if k.startswith("layers.")]
    num_layers = len(set(k.split('.')[1] for k in layer_keys))
    
    class TinyWaveNet(nn.Module):
        def __init__(self, channels, kernel_size, num_layers):
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
    
    model = TinyWaveNet(channels, kernel_size, num_layers)
    model.load_state_dict(state_dict)
    model.eval()
    return model, nam_data

def process_audio(model, audio):
    import torch
    with torch.no_grad():
        x = torch.tensor(audio).reshape(1, 1, -1)
        y = model(x)
        out = y.squeeze().numpy()
    # Normalize output
    mx = np.max(np.abs(out))
    if mx > 0:
        out = out / mx * 0.9
    return out

# ============ MAIN ============

def main():
    print("=" * 60)
    print("🎧 NAM AUDIO DEMO GENERATOR")
    print("   Rendering playable .wav demos for every NAM")
    print("=" * 60)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    demos_dir = OUTPUT_DIR / "playable_demos"
    demos_dir.mkdir(parents=True, exist_ok=True)
    
    # Download NAMs
    print("\n📥 Downloading NAMs from Drive...")
    nam_dir = OUTPUT_DIR / "nams"
    nam_dir.mkdir(parents=True, exist_ok=True)
    
    for folder in ["Synthetic_Bass_Pro", "Synthetic_Guitar_Pro"]:
        cmd = ["rclone", "copy", f"{REMOTE}/NAM_Capturas/{folder}", str(nam_dir / folder),
               "--transfers", "4"]
        subprocess.run(cmd, capture_output=True, timeout=120)
    
    nam_files = sorted(nam_dir.glob("**/*.nam"))
    print(f"   Found {len(nam_files)} NAMs")
    
    # Generate DI signals
    print("\n🎸 Generating clean DI reference signals...")
    guitar_di = gen_guitar_riff_di()
    bass_di = gen_bass_riff_di()
    
    # Save clean DI as reference
    guitar_di_path = demos_dir / "00_REFERENCE_Clean_Guitar_DI.wav"
    bass_di_path = demos_dir / "00_REFERENCE_Clean_Bass_DI.wav"
    wavfile.write(str(guitar_di_path), SAMPLE_RATE, (guitar_di * 32767).astype(np.int16))
    wavfile.write(str(bass_di_path), SAMPLE_RATE, (bass_di * 32767).astype(np.int16))
    print(f"   ✅ Clean Guitar DI: {guitar_di_path.name} ({len(guitar_di)/SAMPLE_RATE:.1f}s)")
    print(f"   ✅ Clean Bass DI: {bass_di_path.name} ({len(bass_di)/SAMPLE_RATE:.1f}s)")
    
    # Process each NAM
    rendered = 0
    for i, nam_path in enumerate(nam_files, 1):
        name = nam_path.stem
        is_bass = "Bass" in name
        di_signal = bass_di if is_bass else guitar_di
        instrument = "Bass" if is_bass else "Guitar"
        
        print(f"\n🔊 [{i}/{len(nam_files)}] Rendering: {name}")
        
        try:
            model, nam_data = load_nam_model(nam_path)
            desc = nam_data.get("metadata", {}).get("description", "N/A")
            print(f"   📝 {desc[:70]}")
            
            # Process
            output = process_audio(model, di_signal)
            
            # Save demo
            demo_path = demos_dir / f"{name}_DEMO.wav"
            wavfile.write(str(demo_path), SAMPLE_RATE, (output * 32767).astype(np.int16))
            
            # Quick stats
            input_rms = np.sqrt(np.mean(di_signal**2))
            output_rms = np.sqrt(np.mean(output**2))
            
            print(f"   ✅ Rendered: {demo_path.name}")
            print(f"   📊 Input RMS: {input_rms:.4f} → Output RMS: {output_rms:.4f}")
            rendered += 1
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Upload demos to Drive
    print(f"\n{'='*60}")
    print(f"📤 Uploading {rendered} audio demos to Google Drive...")
    print(f"{'='*60}")
    
    cmd = ["rclone", "copy", str(demos_dir),
           f"{REMOTE}/NAM_Capturas/Audio_Demos",
           "--transfers", "4", "--stats-one-line", "--log-level", "INFO"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    if result.returncode == 0:
        print(f"   ✅ All demos uploaded to: {REMOTE}/NAM_Capturas/Audio_Demos/")
    else:
        print(f"   ⚠️ Upload issue: {result.stderr[:200]}")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"🎧 DEMO GENERATION COMPLETE")
    print(f"{'='*60}")
    print(f"   Total demos rendered: {rendered}")
    print(f"   Duration per demo: 12 seconds")
    print(f"   Format: 16-bit WAV, {SAMPLE_RATE}Hz")
    print(f"   Location: {REMOTE}/NAM_Capturas/Audio_Demos/")
    print(f"\n   🎵 Included reference files:")
    print(f"      • 00_REFERENCE_Clean_Guitar_DI.wav (clean guitar)")
    print(f"      • 00_REFERENCE_Clean_Bass_DI.wav (clean bass)")
    print(f"\n   ℹ️  Compare each demo against the clean reference")
    print(f"       to hear exactly what each NAM does to the signal!")
    
    return rendered

if __name__ == "__main__":
    rendered = main()
    sys.exit(0 if rendered > 0 else 1)
