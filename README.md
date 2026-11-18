<div align="center">

# Veracust
### Enterprise voice authenticity analysis

**Assess whether an audio sample may contain synthetic or manipulated speech.**

[![Docker release](https://img.shields.io/badge/container-GHCR-blue)](https://github.com/veracust-HQ/Veracust-V0.2/pkgs/container/veracust-v0.2)
[![Release](https://img.shields.io/github/v/release/veracust-HQ/Veracust-V0.2)](https://github.com/veracust-HQ/Veracust-V0.2/releases)
[![License](https://img.shields.io/badge/license-proprietary-lightgrey)]()

[Website](https://veracust-website.onrender.com) · [API documentation](https://veracust-v0-2.onrender.com/docs) · [Releases](https://github.com/veracust-HQ/Veracust-V0.2/releases)

</div>

---

## Overview

Veracust is developing an audio authenticity analysis platform for organizations that need to assess the risk of AI-generated or manipulated speech in voice-based workflows.

The platform combines signal-processing features, audio analysis, and an API workflow to help teams evaluate suspicious audio and decide when additional verification is appropriate. It is intended to support—not replace—identity verification, fraud controls, human review, or other security measures.

**Current stage:** Veracust is an early-stage product. The hosted evaluation service and versioned Docker packaging are available for controlled testing. Enterprise production deployments, independent performance validation, formal security assessments, and service-level commitments must be agreed and verified before operational use.

## Who it is for

Potential use cases include:

- Financial services and contact centres assessing voice-based fraud risk.
- Trust and safety teams reviewing potentially synthetic audio.
- Enterprises evaluating voice authenticity controls for internal workflows.
- Security teams integrating audio analysis into a broader verification process.

These are target use cases, not claims of validated deployment at named customers.

## How it works

At a high level, an audio sample is processed by the Veracust analysis service. The current codebase includes signal-processing and audio-analysis stages intended to extract indicators relevant to synthetic or manipulated speech. Results should be treated as an analytical signal and interpreted in the context of the recording channel, audio quality, and the organization's own risk policy.

A production decision should not rely on a single model score or analysis result. Veracust recommends a layered workflow that can route uncertain cases to secondary verification or human review.

## Deployment options

### Hosted evaluation

The hosted API is available for evaluation and integration testing:

- API: https://veracust-v0-2.onrender.com
- Interactive API documentation: https://veracust-v0-2.onrender.com/docs

Do not submit confidential, regulated, or production customer recordings unless you have completed an appropriate data-protection and security review and have authorization to do so.

### Customer-controlled Docker deployment

A versioned container image is published through GitHub Container Registry:

```bash
docker pull ghcr.io/veracust-hq/veracust-v0.2:v0.1.0
```

The current release workflow builds for `linux/amd64`. See [Deployment Guide](DEPLOYMENT.md) for configuration and operating instructions.

**Important deployment notes:**

- The enterprise control workflow currently requires outbound HTTPS connectivity to the Veracust control plane for inspection authorization and usage finalization.
- The current design is not air-gapped and does not provide offline usage queuing.
- If the control plane cannot authorize or finalize an inspection, the enterprise workflow is designed to fail closed.
- Audio processing is performed by the customer-side service in the intended customer-controlled deployment model. Control-plane messages are designed for usage authorization and accounting; review the implementation and deployment configuration before relying on any data-handling assumption.
- Customers remain responsible for their host security, access controls, logs, temporary storage, backups, snapshots, swap, monitoring, and network egress policies.

A successful container build or synthetic test is not, by itself, evidence of production readiness.

## Security and privacy approach

Veracust is designed to support customer-controlled processing for enterprise deployments. The intended architecture keeps audio analysis on the customer-controlled runtime and uses the central control plane for deployment authorization and usage accounting.

Before deployment, customers should validate:

1. What data is processed, stored, logged, and transmitted by their chosen configuration.
2. Host-level controls for temporary files, logs, backups, snapshots, and swap.
3. Network egress and TLS configuration.
4. Authentication, deployment-token handling, and secret rotation.
5. Retention, deletion, incident response, and access policies.

Do not place Supabase service-role credentials, administrative API keys, or other Veracust operator secrets in a customer container. Use only the deployment credentials issued for that customer environment.

Veracust does not claim a compliance certification or guarantee that every recording can be classified correctly. Security and privacy requirements should be assessed with the Veracust team before handling sensitive workloads.

## API

The deployed API's OpenAPI specification and interactive endpoint documentation are available at:

https://veracust-v0-2.onrender.com/docs

The API surface may evolve while the product is in active development. Integrators should pin versions and validate behavior in a non-production environment before rollout.

## Enterprise plans and usage

Enterprise plans are being developed around subscription allowances and usage-based overage accounting. The current backend includes plan and usage-accounting components, but payment processing and automated collection are not yet live.

Commercial terms, activation, deployment credentials, and any applicable usage limits must be confirmed in a written agreement before a customer is activated. Do not treat example or test database records as an active subscription.

## Development and testing

The repository contains the application, Docker packaging, deployment configuration examples, and CI workflows.

Useful files:

- `Dockerfile` — container build definition.
- `docker-compose.yml` — local Compose configuration.
- `.env.example` — configuration template; replace placeholders with authorized values.
- `DEPLOYMENT.md` — deployment and operating guidance.
- `.github/workflows/` — automated build and release workflows.

For local testing:

1. Install Docker Engine or Docker Desktop with the required Linux container support.
2. Review `.env.example` and create a local `.env` file with the required deployment configuration.
3. Follow the steps in [DEPLOYMENT.md](DEPLOYMENT.md).
4. Use synthetic or otherwise authorized test audio.
5. Validate the exact image, host environment, network behavior, logging, and failure modes before any customer rollout.

Never commit `.env`, access tokens, customer audio, or other secrets to source control.

## Current limitations

- The product is under active development and is not represented as independently validated for every codec, language, recording environment, or attack type.
- Detection performance, false-positive rates, and false-negative rates must be measured on representative customer data before operational decisions are based on the system.
- The enterprise control plane currently requires outbound HTTPS; offline and air-gapped operation are not supported.
- The current published container release targets `linux/amd64`.
- Payment processing, automated invoicing, and live subscription collection are not yet implemented.
- No formal SLA, penetration-test attestation, or compliance certification is claimed in this repository.

## Support and commercial enquiries

For product information, evaluation discussions, or enterprise deployment planning, use the contact channel published on the [Veracust website](https://veracust-website.onrender.com).

## Repository

This repository contains proprietary Veracust software. No rights to use, copy, modify, distribute, or deploy the software are granted except as expressly agreed in writing by Veracust.

---

<div align="center">

**Veracust**  
*Voice authenticity analysis for enterprise workflows.*

</div>
