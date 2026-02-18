# 🎸 IR DEF Repository

> The world's largest automated free IR & NAM capture collection.  
> Uses GitHub Actions to download from 30+ sources, organize, and upload to Google Drive — **zero local bandwidth required**.

## 📊 Stats

Running the full pipeline downloads from:
- **20+ GitHub repositories** (ZIP archives + release assets)
- **TONE3000 API** (amps, pedals, IRs, full rigs)
- **7+ direct download sites** (Voxengo, EchoThief, Kalthallen, Forward Audio, etc.)

## 🗂️ Organization

Files are automatically organized by:
```
├── GUITARRA/            — Guitar IRs and NAM captures
│   ├── IRs/             — Impulse responses (WAV) by brand
│   │   ├── Marshall/
│   │   ├── Fender/
│   │   ├── Mesa_Boogie/
│   │   └── ...
│   └── NAM_Capturas/    — NAM/AIDA-X models
│       ├── Amps/        — Amp captures by brand
│       ├── Pedals/      — Overdrive, Distortion, Fuzz, Boost
│       └── Full_Rigs/   — Complete signal chain captures
├── BAJO/                — Bass IRs and captures
├── ELECTROACUSTICA/     — Acoustic/piezo correction IRs
└── UTILIDADES/          — Reverb IRs, mic emulations
```

## 🚀 Workflows

| Workflow | Description | Timeout |
|----------|-------------|---------|
| **Tier 1** | GitHub repos (pelennor2170, GuitarML, AIDA-X, etc.) + release assets | 120 min |
| **Tier 2** | TONE3000 API — Amps & Cabinet IRs | 350 min |
| **Tier 3** | TONE3000 API — Pedals, Full Rigs & Outboard | 350 min |
| **Tier 4** | Direct sites (Voxengo, EchoThief, Kalthallen, Forward Audio) | 120 min |
| **Tier 5** | Generate docs, validate files, final report | 60 min |
| **Run All** | Chains all tiers sequentially (can start from any tier) | All |

## ⚙️ Setup

1. **Fork this repo** or create a new one with these files
2. **Add repository secrets:**
   - `RCLONE_CONFIG_B64` — Base64-encoded rclone config with Google Drive access
   - `TONE3000_API_KEY` — TONE3000 API key (optional, for Tier 2-3)
3. **Go to Actions tab → 🚀 Run All Tiers → Run workflow**
4. Select which tier to start from (default: 1)

### Generating `RCLONE_CONFIG_B64`

```powershell
# On your local machine with rclone configured:
$config = Get-Content "$env:APPDATA\rclone\rclone.conf" -Raw
[Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($config))
```

## 🔧 Features

- **Smart Organization** — Detects brand, instrument, and file type from filenames and paths
- **Deduplication** — SHA-256 hash-based dedup prevents duplicate files
- **File Validation** — WAV RIFF header checks, JSON validity, minimum size
- **Cache System** — Download cache persists across runs via Google Drive
- **Error Recovery** — All steps use `if: always()` to continue on errors
- **Parallel Uploads** — rclone with 8 transfers and 64MB chunk size

## 📋 Sources

See [SOURCES.md](SOURCES.md) for the complete list of all sources and credits.

---

*All files come from verified free and open-source sources. Respect individual licenses.*
