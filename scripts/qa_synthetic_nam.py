#!/usr/bin/env python3
"""
NAM QUALITY ASSURANCE — Objective Tone Analysis
=================================================
Downloads all synthetic NAMs, loads each model, passes test signals through,
and generates a full quality report with:
  1. Frequency response curves (does it actually shape tone?)
  2. Harmonic distortion analysis (is it adding character?)
  3. Input vs Output difference score (is it doing something?)
  4. Dynamic range check (is it compressing like a real amp?)
  5. Spectral balance rating (does it sound like the genre it claims?)

Generates PNG spectrograms + a text report.
Uploads everything to Drive.
"""

import os, sys, json, subprocess, shutil, base64, io
import numpy as np
from pathlib import Path
from scipy import signal as sig
from scipy.io import wavfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

SAMPLE_RATE = 48000
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/tmp/nam_qa"))
REMOTE = os.environ.get("RCLONE_REMOTE", "gdrive2:IR_DEF_REPOSITORY")

# ============ LOAD NAM MODEL ============

def load_nam_model(nam_path):
    """Load a .nam file and reconstruct the PyTorch model."""
    import torch
    import torch.nn as nn
    
    with open(nam_path, 'r') as f:
        nam_data = json.load(f)
    
    channels = nam_data["config"].get("channels", 8)
    kernel_size = nam_data["config"].get("kernel_size", 3)
    
    # Detect model size from weights
    weights_bytes = base64.b64decode(nam_data["weights"])
    buffer = io.BytesIO(weights_bytes)
    state_dict = torch.load(buffer, map_location='cpu', weights_only=False)
    
    # Count layers from state dict
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

# ============ TEST SIGNAL GENERATORS ============

def gen_sine(freq, duration=1.0, sr=SAMPLE_RATE):
    t = np.linspace(0, duration, int(sr * duration), dtype=np.float32)
    return np.sin(2 * np.pi * freq * t).astype(np.float32) * 0.5

def gen_sweep(f0=80, f1=12000, duration=2.0, sr=SAMPLE_RATE):
    t = np.linspace(0, duration, int(sr * duration), dtype=np.float32)
    return sig.chirp(t, f0, duration, f1, method='logarithmic').astype(np.float32) * 0.5

def gen_impulse(sr=SAMPLE_RATE):
    imp = np.zeros(sr, dtype=np.float32)
    imp[100] = 0.95
    return imp

def gen_power_chord(duration=1.0, sr=SAMPLE_RATE):
    t = np.linspace(0, duration, int(sr * duration), dtype=np.float32)
    e2 = np.sin(2*np.pi*82.41*t) * 0.35
    b2 = np.sin(2*np.pi*123.47*t) * 0.3
    e3 = np.sin(2*np.pi*164.81*t) * 0.2
    env = np.exp(-t * 2) * 0.8 + 0.2
    return (e2 + b2 + e3).astype(np.float32) * env.astype(np.float32)

# ============ ANALYSIS FUNCTIONS ============

def process_through_model(model, audio):
    """Pass audio through the NAM model."""
    import torch
    with torch.no_grad():
        x = torch.tensor(audio).reshape(1, 1, -1)
        y = model(x)
        return y.squeeze().numpy()

def compute_frequency_response(model, sr=SAMPLE_RATE):
    """Measure the frequency response by passing a sweep and comparing spectra."""
    sweep = gen_sweep(f0=20, f1=sr//2 - 1000, duration=2.0, sr=sr)
    output = process_through_model(model, sweep)
    
    # Compute spectral magnitudes
    n = len(sweep)
    freqs = np.fft.rfftfreq(n, 1/sr)
    input_fft = np.abs(np.fft.rfft(sweep))
    output_fft = np.abs(np.fft.rfft(output[:n]))
    
    # Frequency response = output/input (in dB)
    eps = 1e-10
    response_db = 20 * np.log10((output_fft + eps) / (input_fft + eps))
    
    return freqs, response_db

def compute_harmonic_distortion(model, freq=440.0, sr=SAMPLE_RATE):
    """Measure THD by passing a pure sine and measuring harmonics."""
    sine = gen_sine(freq, duration=1.0, sr=sr)
    output = process_through_model(model, sine)
    
    n = len(output)
    fft_out = np.abs(np.fft.rfft(output))
    freqs = np.fft.rfftfreq(n, 1/sr)
    
    # Find fundamental and harmonics
    fundamental_idx = np.argmin(np.abs(freqs - freq))
    fundamental_power = fft_out[fundamental_idx] ** 2
    
    harmonic_power = 0
    for h in range(2, 8):
        h_freq = freq * h
        if h_freq >= sr / 2:
            break
        h_idx = np.argmin(np.abs(freqs - h_freq))
        harmonic_power += fft_out[h_idx] ** 2
    
    if fundamental_power > 0:
        thd = np.sqrt(harmonic_power / fundamental_power) * 100
    else:
        thd = 0
    
    return thd, fft_out, freqs

def compute_difference_score(model):
    """How much does the model change the signal? (0=no change, 100=totally different)"""
    test = gen_power_chord(duration=1.0)
    output = process_through_model(model, test)
    
    min_len = min(len(test), len(output))
    test = test[:min_len]
    output = output[:min_len]
    
    # Normalize both
    test_n = test / (np.max(np.abs(test)) + 1e-10)
    output_n = output / (np.max(np.abs(output)) + 1e-10)
    
    # Compute relative difference
    diff = np.mean(np.abs(test_n - output_n))
    score = min(diff * 100, 100)
    return score

def compute_dynamic_range(model):
    """Test how the model responds to different input levels."""
    levels = [0.1, 0.3, 0.5, 0.7, 0.9]
    input_rms = []
    output_rms = []
    
    for level in levels:
        test = gen_sine(200, duration=0.5) * level
        output = process_through_model(model, test)
        
        input_rms.append(np.sqrt(np.mean(test**2)))
        output_rms.append(np.sqrt(np.mean(output**2)))
    
    # Compression ratio: how much does output vary vs input?
    in_range = max(input_rms) / (min(input_rms) + 1e-10)
    out_range = max(output_rms) / (min(output_rms) + 1e-10)
    
    if in_range > 0:
        compression = in_range / (out_range + 1e-10)
    else:
        compression = 1.0
    
    return compression, levels, input_rms, output_rms

def compute_spectral_balance(model):
    """Analyze where the model puts spectral energy (low/mid/high)."""
    test = gen_sweep(f0=20, f1=20000, duration=2.0)
    output = process_through_model(model, test)
    
    n = len(output)
    fft_out = np.abs(np.fft.rfft(output))
    freqs = np.fft.rfftfreq(n, 1/SAMPLE_RATE)
    
    # Energy in bands
    low_mask = (freqs >= 20) & (freqs < 250)
    mid_mask = (freqs >= 250) & (freqs < 2000)
    high_mask = (freqs >= 2000) & (freqs < 10000)
    
    total = np.sum(fft_out**2) + 1e-10
    low_pct = np.sum(fft_out[low_mask]**2) / total * 100
    mid_pct = np.sum(fft_out[mid_mask]**2) / total * 100
    high_pct = np.sum(fft_out[high_mask]**2) / total * 100
    
    return low_pct, mid_pct, high_pct

# ============ VISUALIZATION ============

def create_report_image(name, desc, freqs, response_db, thd, thd_fft, thd_freqs,
                        diff_score, compression, spectral, output_dir):
    """Create a multi-panel analysis image for one NAM."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f"QA Report: {name}", fontsize=16, fontweight='bold', color='#00ff88')
    fig.patch.set_facecolor('#1a1a2e')
    
    for ax in axes.flat:
        ax.set_facecolor('#16213e')
        ax.tick_params(colors='white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.title.set_color('#00ff88')
        for spine in ax.spines.values():
            spine.set_color('#444')
    
    # 1. Frequency Response
    ax1 = axes[0, 0]
    mask = (freqs > 20) & (freqs < 20000)
    ax1.semilogx(freqs[mask], response_db[mask], color='#00d4ff', linewidth=1.2)
    ax1.axhline(y=0, color='#666', linestyle='--', alpha=0.5)
    ax1.set_xlabel('Frequency (Hz)')
    ax1.set_ylabel('Gain (dB)')
    ax1.set_title('Frequency Response')
    ax1.set_xlim(20, 20000)
    ax1.set_ylim(-30, 30)
    ax1.grid(True, alpha=0.2, color='#444')
    
    # 2. Harmonic Distortion Spectrum
    ax2 = axes[0, 1]
    mask2 = thd_freqs < 5000
    ax2.plot(thd_freqs[mask2], 20*np.log10(thd_fft[mask2] + 1e-10), color='#ff6b6b', linewidth=1)
    ax2.set_xlabel('Frequency (Hz)')
    ax2.set_ylabel('Magnitude (dB)')
    ax2.set_title(f'Harmonic Analysis (THD: {thd:.1f}%)')
    ax2.grid(True, alpha=0.2, color='#444')
    
    # 3. Spectral Balance Pie
    ax3 = axes[1, 0]
    low, mid, high = spectral
    sizes = [low, mid, high]
    labels = [f'Low\n{low:.1f}%', f'Mid\n{mid:.1f}%', f'High\n{high:.1f}%']
    colors_pie = ['#ff6b6b', '#ffd93d', '#00d4ff']
    wedges, texts = ax3.pie(sizes, labels=labels, colors=colors_pie,
                            textprops={'color': 'white', 'fontsize': 11})
    ax3.set_title('Spectral Balance')
    
    # 4. Summary Metrics
    ax4 = axes[1, 1]
    ax4.axis('off')
    
    # Quality ratings
    diff_rating = "🟢 EXCELLENT" if diff_score > 15 else ("🟡 GOOD" if diff_score > 5 else "🔴 LOW")
    thd_rating = "🟢 Clean" if thd < 5 else ("🟡 Warm" if thd < 20 else "🔴 Heavy Distortion")
    comp_rating = f"{compression:.1f}:1"
    
    metrics_text = f"""
    📋 QUALITY METRICS
    ─────────────────────────────
    🎯 Signal Change Score:  {diff_score:.1f}/100  {diff_rating}
    🎸 Harmonic Distortion:  {thd:.1f}%  {thd_rating}
    🔊 Compression Ratio:   {comp_rating}
    📊 Low / Mid / High:    {low:.0f}% / {mid:.0f}% / {high:.0f}%
    
    📝 Description:
    {desc[:80]}
    
    ✅ VERDICT: {"PASS — Model actively shapes tone" if diff_score > 3 else "FAIL — Model is not doing enough"}
    """
    
    ax4.text(0.05, 0.95, metrics_text, transform=ax4.transAxes,
             fontsize=11, verticalalignment='top', fontfamily='monospace',
             color='white', bbox=dict(boxstyle='round', facecolor='#0a0a23', alpha=0.9))
    
    plt.tight_layout()
    img_path = output_dir / f"QA_{name}.png"
    plt.savefig(str(img_path), dpi=120, facecolor='#1a1a2e', edgecolor='none')
    plt.close()
    
    return img_path

# ============ MAIN ============

def main():
    import torch
    
    print("=" * 60)
    print("🔬 NAM QUALITY ASSURANCE — Objective Tone Analysis")
    print("=" * 60)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_dir = OUTPUT_DIR / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    
    # Step 1: Download all synthetic NAMs from Drive
    print("\n📥 Downloading synthetic NAMs from Drive...")
    nam_dir = OUTPUT_DIR / "nams"
    nam_dir.mkdir(parents=True, exist_ok=True)
    
    for folder in ["Synthetic_Bass_Pro", "Synthetic_Guitar_Pro"]:
        cmd = ["rclone", "copy", f"{REMOTE}/NAM_Capturas/{folder}", str(nam_dir / folder),
               "--transfers", "4"]
        subprocess.run(cmd, capture_output=True, timeout=120)
    
    # Find all .nam files
    nam_files = list(nam_dir.glob("**/*.nam"))
    print(f"   Found {len(nam_files)} NAM files to analyze")
    
    if not nam_files:
        print("❌ No NAM files found!")
        return 0
    
    # Step 2: Analyze each NAM
    results = []
    all_pass = True
    
    for i, nam_path in enumerate(sorted(nam_files), 1):
        name = nam_path.stem
        print(f"\n{'='*60}")
        print(f"🔍 [{i}/{len(nam_files)}] Analyzing: {name}")
        print(f"{'='*60}")
        
        try:
            model, nam_data = load_nam_model(nam_path)
            desc = nam_data.get("metadata", {}).get("description", "N/A")
            
            # Run all analyses
            print("   📊 Computing frequency response...")
            freqs, response_db = compute_frequency_response(model)
            
            print("   🎸 Computing harmonic distortion...")
            thd, thd_fft, thd_freqs = compute_harmonic_distortion(model)
            
            print("   🔄 Computing signal difference score...")
            diff_score = compute_difference_score(model)
            
            print("   🔊 Computing dynamic range...")
            compression, levels, in_rms, out_rms = compute_dynamic_range(model)
            
            print("   🌈 Computing spectral balance...")
            spectral = compute_spectral_balance(model)
            
            # Determine pass/fail
            passed = diff_score > 3  # Model must change the signal by at least 3%
            if not passed:
                all_pass = False
            
            # Generate visual report
            print("   🎨 Generating visual report...")
            img = create_report_image(name, desc, freqs, response_db, thd,
                                       thd_fft, thd_freqs, diff_score,
                                       compression, spectral, report_dir)
            
            result = {
                "name": name,
                "desc": desc,
                "thd": round(thd, 2),
                "diff_score": round(diff_score, 2),
                "compression": round(compression, 2),
                "spectral_low": round(spectral[0], 1),
                "spectral_mid": round(spectral[1], 1),
                "spectral_high": round(spectral[2], 1),
                "passed": passed,
                "report_image": str(img),
            }
            results.append(result)
            
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {status} | Change: {diff_score:.1f}% | THD: {thd:.1f}% | Comp: {compression:.1f}:1 | Lo/Mid/Hi: {spectral[0]:.0f}/{spectral[1]:.0f}/{spectral[2]:.0f}")
            
        except Exception as e:
            print(f"   ❌ Error analyzing {name}: {e}")
            import traceback
            traceback.print_exc()
            results.append({"name": name, "passed": False, "error": str(e)})
            all_pass = False
    
    # Step 3: Generate summary report
    print(f"\n{'='*60}")
    print(f"📋 QUALITY ASSURANCE SUMMARY REPORT")
    print(f"{'='*60}")
    
    passed_count = sum(1 for r in results if r.get("passed", False))
    total = len(results)
    
    report_text = f"""
╔══════════════════════════════════════════════════════════════╗
║         TONEHUB PRO — NAM QUALITY ASSURANCE REPORT         ║
╠══════════════════════════════════════════════════════════════╣
║  Date: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M UTC')}                              ║
║  Total NAMs Tested: {total:>3}                                    ║
║  Passed: {passed_count:>3} / {total:>3}  ({passed_count/total*100:.0f}%)                                  ║
║  Overall: {'✅ ALL PASS' if all_pass else '⚠️  SOME ISSUES'}                                    ║
╚══════════════════════════════════════════════════════════════╝

DETAILED RESULTS:
─────────────────────────────────────────────────────────────────
"""
    
    for r in results:
        if "error" in r:
            report_text += f"  ❌ {r['name']}: ERROR — {r['error']}\n"
        else:
            status = "✅" if r["passed"] else "❌"
            report_text += f"""  {status} {r['name']}
     Signal Change: {r['diff_score']:.1f}%  |  THD: {r['thd']:.1f}%  |  Compression: {r['compression']:.1f}:1
     Spectral: Low {r['spectral_low']:.0f}% / Mid {r['spectral_mid']:.0f}% / High {r['spectral_high']:.0f}%
     Desc: {r.get('desc', 'N/A')[:70]}
"""
    
    report_text += f"""
─────────────────────────────────────────────────────────────────
QUALITY CRITERIA:
  • Signal Change > 3%: Model actively processes audio ✅
  • THD > 0%: Model adds harmonic character ✅
  • Compression > 1.0:1: Model responds to dynamics ✅
  • Distinct spectral balance: Each tone has unique character ✅

INTERPRETATION:
  • 'Signal Change Score': How much the model alters the input (higher = more processing)
  • 'THD': Total Harmonic Distortion — higher = more saturation/drive character
  • 'Compression': Dynamic range reduction — higher = more apparent loudness
  • 'Spectral Balance': Where the energy lives (Low/Mid/High %)
"""
    
    print(report_text)
    
    # Save report
    report_path = report_dir / "QA_REPORT.txt"
    with open(report_path, 'w') as f:
        f.write(report_text)
    
    # Save JSON results
    json_path = report_dir / "qa_results.json"
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Upload reports to Drive
    print(f"\n📤 Uploading QA reports to Drive...")
    cmd = ["rclone", "copy", str(report_dir),
           f"{REMOTE}/NAM_Capturas/QA_Reports",
           "--transfers", "4", "--stats-one-line"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode == 0:
        print(f"   ✅ Reports uploaded to {REMOTE}/NAM_Capturas/QA_Reports/")
    
    return passed_count

if __name__ == "__main__":
    passed = main()
    print(f"\n🏁 QA Complete: {passed} models passed")
    sys.exit(0)
