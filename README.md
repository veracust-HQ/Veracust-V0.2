<div align="center">

# Veracust
### Voice authenticity analysis for a world of synthetic media

**A developing audio-analysis platform exploring signals that may help identify AI-generated or manipulated speech.**

[Website](https://veracust-website.onrender.com) · [Product Hunt](https://www.producthunt.com/posts/veracust/embed) · [API docs](https://veracust-v0-2.onrender.com/docs) · [GitHub](https://github.com/veracust-HQ/Veracust-V0.2)

[![Release](https://img.shields.io/github/v/release/veracust-HQ/Veracust-V0.2)](https://github.com/veracust-HQ/Veracust-V0.2/releases)
[![Container](https://img.shields.io/badge/Container-GHCR-2496ED?logo=docker&logoColor=white)](https://github.com/veracust-HQ/Veracust-V0.2/pkgs/container/veracust-v0.2)
[![License](https://img.shields.io/badge/License-Proprietary-lightgrey)](#license)

</div>

---

## The challenge

AI voice generation is making convincing synthetic speech easier to create and distribute. That creates new risks for organisations that rely on voice interactions, including impersonation, social engineering and trust-and-safety review.

Veracust is being built to help investigate this challenge through audio signal analysis and a practical software workflow.

## What we're building

Veracust combines computational audio analysis with an API-oriented application architecture. The codebase includes signal-processing stages intended to examine measurable characteristics of an audio recording that may be relevant to synthetic or manipulated speech.

The goal is to provide an additional analytical signal for human review and broader verification workflows—not to replace identity checks, fraud controls or human judgement.

## Potential applications

- **Financial services:** add an audio-analysis signal to voice-based fraud review.
- **Contact centres:** support investigation of suspicious or unusual voice interactions.
- **Trust and safety:** help review potentially synthetic audio submitted to a platform.
- **Security teams:** explore audio authenticity as one layer in a wider verification process.

These are intended use cases, not claims of validated customer deployments.

## Product and technical direction

The current engineering direction includes:

- Digital signal processing and computational audio features.
- Analysis of speech and recording characteristics.
- An API workflow for submitting audio for evaluation.
- Container packaging for controlled, customer-managed testing.
- Continued evaluation across recording conditions, codecs and audio quality.

The specific methods and outputs may change as the product is researched and developed.

## Try the current evaluation API

- **API base:** https://veracust-v0-2.onrender.com
- **Interactive API documentation:** https://veracust-v0-2.onrender.com/docs
- **Website:** https://veracust-website.onrender.com

Hosted services may be unavailable during maintenance or when the hosting account has exhausted its included runtime allowance. The API surface may evolve; validate integrations against the current version before use.

Do not submit confidential, regulated or production customer recordings unless you have the necessary authorisation and have completed your own security and data-protection review. Use synthetic or otherwise authorised test audio during evaluation.

## Run with Docker

A versioned container image is published through GitHub Container Registry:

```bash
docker pull ghcr.io/veracust-hq/veracust-v0.2:v0.1.0
```

The current published release targets `linux/amd64`. Review [DEPLOYMENT.md](DEPLOYMENT.md) for deployment configuration and operating guidance before running the image.

The current enterprise control workflow requires outbound HTTPS connectivity to the Veracust control plane for inspection authorisation and usage finalisation. The current design is not air-gapped and does not provide offline usage queuing.

## Development and evaluation

The repository includes the application, Docker packaging, deployment configuration examples and CI workflows.

Useful project files:

| File | Purpose |
| --- | --- |
| `Dockerfile` | Container build definition |
| `docker-compose.yml` | Local Compose configuration |
| `.env.example` | Configuration template |
| `DEPLOYMENT.md` | Deployment and operating guidance |
| `.github/workflows/` | Automated build and release workflows |

For local evaluation:

1. Install Docker Engine or Docker Desktop with Linux container support.
2. Review `.env.example` and create a local `.env` file with the required values.
3. Follow [DEPLOYMENT.md](DEPLOYMENT.md).
4. Use synthetic or otherwise authorised test audio.
5. Validate the image, host environment, network behaviour, logging and failure modes before any operational use.

Never commit `.env` files, access tokens, customer audio or other secrets to source control.

## Security, privacy and responsible use

Veracust is an early-stage product. Before using it with sensitive workloads, assess what the selected configuration processes, stores, logs and transmits. Review host security, access controls, temporary files, backups, network egress, secret handling, retention and deletion practices.

Veracust does not currently claim a compliance certification, formal service-level agreement, independent penetration-test attestation or guaranteed classification accuracy.

Audio authenticity analysis is probabilistic in practice: recording devices, codecs, compression, background noise, language, speaker variation and new synthesis methods can affect results. Outputs should be treated as decision-support signals and independently evaluated on representative data before being used in consequential decisions.

## Roadmap

Our development priorities include:

- Broader and more representative evaluation.
- Continued research into acoustic and signal-level indicators.
- Improved reliability across real-world recording conditions.
- Clearer integration and deployment workflows.
- Stronger documentation for security, privacy and operational review.

Roadmap items are areas of work, not delivery commitments.

## Connect with Veracust

Follow the project and stay up to date:

- [Product Hunt — Veracust](https://www.producthunt.com/posts/veracust/embed)
- [X](https://x.com/Veracust_HQ)
- [Facebook](https://www.facebook.com/profile.php?id=61596658978153)
- [Instagram](https://www.instagram.com/veracust_official/)

For product, evaluation or commercial enquiries, visit the [Veracust website](https://veracust-website.onrender.com).

## Founder

**Utkarsh Dixit** — Founder, Veracust.

## License

This repository contains proprietary Veracust software. No rights to use, copy, modify, distribute or deploy the software are granted except as expressly agreed in writing by Veracust.

---

<div align="center">

**Veracust**  
*Exploring a more trustworthy future for voice.*

</div>
