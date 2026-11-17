# Veracust private deployment (Docker)

This package runs the Veracust FastAPI service inside a customer-controlled Docker environment. Audio uploads are processed by the API container. The current application writes a temporary working file during analysis and attempts to delete it in a `finally` block; this is not a guarantee about host snapshots, container-runtime diagnostics, backups, swap, or infrastructure-level retention. Configure those controls in the customer's environment.

## Requirements

- Docker Engine with Docker Compose plugin
- Outbound HTTPS access from the API container to the configured Supabase project (current authentication and activity storage dependency)
- A customer-controlled Supabase project for isolated customer identity and audit metadata, or an explicitly approved shared project
- A browser frontend origin configured in `FRONTEND_ORIGIN`

## 1. Configure environment

Copy the example file and fill in the values:

```bash
cp .env.example .env
```

Set:
- `SUPABASE_URL`: customer Supabase project URL
- `SUPABASE_PUBLISHABLE_KEY`: that project's publishable key
- `FRONTEND_ORIGIN`: exact origin(s) of the customer-hosted dashboard, comma-separated

Do not put a Supabase service-role key in this file. The current API validates the user's bearer token and accesses the tables with that user's token.

The Supabase project must have the Veracust schema and row-level security policies for `policy_acceptances` and `evaluation_events`. Apply the migration supplied by Veracust to the customer's project before starting the API. Do not reuse the Veracust hosted-demo project for a customer production deployment unless that arrangement is explicitly approved.

## 2. Build and start

```bash
docker compose build
docker compose up -d
```

Check health:

```bash
curl http://localhost:8000/
docker compose logs -f veracust-api
```

API documentation is available at `http://localhost:8000/docs`.

## 3. Connect the dashboard

Set the customer dashboard's API base URL to the customer API address, for example:

```
https://veracust-api.customer.example.com
```

The browser must be able to reach this address over HTTPS. Configure the reverse proxy, TLS certificate, firewall rules, DNS, and `FRONTEND_ORIGIN` accordingly. Do not expose the API publicly without TLS and an access-control review.

## 4. Operational security checklist

- Keep `.env` out of source control and restrict access to it.
- Use a customer-controlled Supabase project and apply the supplied RLS policies.
- Restrict inbound access to the API to the customer dashboard / approved network.
- Terminate TLS at a trusted reverse proxy or load balancer.
- Review container logs and reverse-proxy logs to ensure they do not contain uploaded audio or credentials.
- Disable unnecessary request-body logging, tracing, and payload capture.
- Protect host storage, backups, snapshots, swap, and administrator access.
- Set resource limits and monitor CPU, RAM, disk, and request sizes.
- Keep Docker images and Python dependencies patched; pin and test dependency versions before production rollout.
- Perform security, privacy, and performance validation in the customer's environment before handling sensitive recordings.

## Important architecture note

This Docker package containerizes the current API and detection engine. It does **not** make the current application fully air-gapped: authentication, policy acceptance, and evaluation metadata still depend on Supabase over HTTPS. A fully disconnected/on-premises edition would require a separate local identity and audit-storage implementation, plus a customer-managed migration path. The current package must not be marketed as air-gapped.

## Current limitations

- The API currently uses Supabase authentication and the `policy_acceptances` / `evaluation_events` tables.
- The dashboard is a separate frontend and must be hosted by the customer or configured to call the customer's API.
- The Docker build is a starting deployment artifact; validate it against the target customer's OS, CPU architecture, audio formats, security controls, and workload before production use.
- Detection output is an evaluation signal, not a guarantee of fraud detection. Benchmark false-positive and false-negative rates on representative customer audio before operational decisions.
