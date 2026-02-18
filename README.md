# IR DEF Repository

Automated download system for the world's largest free IR & NAM capture collection.
Uses GitHub Actions to download from 30+ sources, organize, and upload to Google Drive — zero local bandwidth required.

## Workflows

| Workflow | Description |
|----------|-------------|
| Tier 1 | GitHub repositories (pelennor2170, GuitarML, etc.) |
| Tier 2 | TONE3000 API — Amps & IRs |
| Tier 3 | TONE3000 API — Pedals & Full Rigs |
| Tier 4 | Direct sites (Forward Audio, GGWPTECH, etc.) |
| Tier 5 | Documentation & validation |
| Run All | Chains all tiers sequentially |

## Setup

1. Add secrets: `RCLONE_DRIVE_TOKEN`, `TONE3000_API_KEY`
2. Go to Actions tab → Run All → Run workflow
