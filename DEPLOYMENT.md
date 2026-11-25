# Veracust private enterprise deployment

This Docker package runs the Veracust detection engine inside the customer's controlled environment. In enterprise mode, audio is uploaded to and analyzed by this local container. The container sends only a deployment credential and minimal authorization/usage messages to Veracust's hosted control plane over HTTPS. It does not send audio bytes, filenames, transcripts, or detection output to the control plane.

The application writes a temporary working file during analysis and attempts to delete it in a `finally` block. This is not a guarantee about host snapshots, container-runtime diagnostics, backups, swap, or infrastructure-level retention. Configure those controls in the customer's environment.

## Architecture

- Customer audio is analyzed inside the customer Docker environment.
- Veracust retains the central Supabase project and controls subscriptions, deployment credentials, included/bonus usage, overage caps, and usage reservations.
- Before each private inspection, Docker asks the Veracust control plane to reserve one call.
- If the subscription is inactive, the deployment is revoked, the spending cap is reached, or the control plane cannot be reached, the inspection is not started.
- After a successful local analysis, Docker finalizes the reservation. Failed analyses release the reservation and are not billable.
- The private route is `POST /v1/private/verify`. The existing hosted evaluation route `POST /v1/verify` remains unchanged.

**Connectivity:** enterprise private mode requires outbound HTTPS to Veracust for every inspection authorization and finalization. It is not air-gapped and does not currently support offline usage queues. If Veracust's control plane is unavailable, private inspections fail closed rather than bypassing the spending cap.

## Requirements

- Docker Engine with Docker Compose plugin
- Outbound HTTPS from the customer container to `https://veracust-v0-2.onrender.com` (or the control-plane URL supplied by Veracust)
- A deployment token issued by Veracust for the customer's active subscription
- TLS and network access controls for the customer's own API endpoint

## 1. Configure the customer container

Copy the example file:

```bash
cp .env.example .env
```

Set:
- `VERACUST_CONTROL_PLANE_URL`: Veracust-hosted control-plane URL.
- `VERACUST_DEPLOYMENT_TOKEN`: one-time deployment credential supplied by Veracust.
- `FRONTEND_ORIGIN`: only if a browser frontend calls this API.

The enterprise private route does not require a customer Supabase project. Do not place Veracust's Supabase service-role key or administrator API key in the customer container. Do not commit `.env` to source control.

## 2. Start the engine

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

## 3. Call the private inspection endpoint

Send the audio file to the customer's local API, using the deployment token. Supply the same unique `Idempotency-Key` when retrying the same logical inspection:

```bash
curl -X POST http://localhost:8000/v1/private/verify \
  -H "Authorization: Bearer $VERACUST_DEPLOYMENT_TOKEN" \
  -F "file=@sample.wav"
```

In production, call this endpoint over the customer's private network or behind a TLS-terminating reverse proxy. Do not expose it publicly without access-control review.

## 4. Veracust hosted control-plane configuration

These variables belong only on Veracust's hosted API service (for example, the Render service), never in the customer's Docker environment:

- `SUPABASE_URL`: Veracust-owned production Supabase URL.
- `SUPABASE_SERVICE_ROLE_KEY`: Supabase service-role secret; keep it in the hosted secret manager.
- `VERACUST_ADMIN_API_KEY`: long random administrator secret used to provision deployments.
- Existing `SUPABASE_PUBLISHABLE_KEY` remains for the hosted evaluation/login routes.

The hosted API must have the enterprise billing schema applied before enabling customer deployments.

### Provision a deployment credential

First create/activate the customer's account and paid subscription in the Veracust billing administration workflow. The subscription must have:
- `status = active`
- a valid `current_period_start` and `current_period_end`
- the correct plan allowance and bonus allowance
- an explicit `overage_cap_usd_micros` value accepted by the customer
- billing consent timestamps and the accepted overage-rate version

Then call the hosted administrator endpoint:

```bash
curl -X POST https://veracust-v0-2.onrender.com/v1/admin/deployments \
  -H "X-Veracust-Admin-Key: $VERACUST_ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "CUSTOMER_ACCOUNT_UUID",
    "subscription_id": "ACTIVE_SUBSCRIPTION_UUID",
    "deployment_name": "customer-primary"
  }'
```

The response contains a random deployment token exactly once. Deliver it securely to the customer and store it as `VERACUST_DEPLOYMENT_TOKEN`. Supabase stores only its SHA-256 hash. If the token is lost or compromised, revoke that deployment and issue a replacement.

## 5. Veracust business payout onboarding (India / INR)

The recommended payment provider for Veracust's India-based INR collections is **Razorpay**, subject to merchant onboarding, KYC, business eligibility and provider approval. Razorpay advertises support for Indian payment methods including UPI, cards and net banking, and describes settlement for eligible international collections; exact availability depends on the approved merchant account and product configuration ([Razorpay India payments](https://razorpay.com/accept-international-payments-from-india/)).

### Where to enter the bank details

1. Use the owner-only **Business payout setup** panel in the hosted Veracust dashboard.
2. Select **Start Razorpay onboarding** and complete merchant/business verification directly with Razorpay.
3. Add the business settlement bank account in Razorpay's secure onboarding/dashboard flow.
4. Wait for Razorpay to approve the merchant account and confirm the settlement configuration.
5. Keep the Razorpay merchant account identifiers and API credentials in Veracust's hosted API secret manager only when the payment integration is implemented.

Veracust intentionally does not collect or store the bank account number, IFSC, UPI PIN, net-banking password, card PIN or OTP. Do not send these details in chat, commit them to GitHub, put them in Docker customer environment files, or enter them into the public evaluation dashboard.

### Integration status

The owner panel is an onboarding handoff only. **Razorpay checkout, payment creation, signature verification, webhook processing, refunds, reconciliation and automatic subscription activation are not yet implemented.** Do not accept customer payments or mark subscriptions active based on screenshots or manual claims. Those flows must be implemented and tested end-to-end before going live.

When the payment integration is ready, configure provider credentials as encrypted environment secrets on the Veracust hosted API service. Never expose the Razorpay key secret or webhook secret to frontend JavaScript or customer containers.

## 6. Customer plan selection and billing consent

The authenticated workspace exposes enterprise plan selection and explicit billing consent. The API verifies the signed-in Supabase user, resolves exactly one active usage account, reads the active plan catalog, calculates a monthly overage cap equal to 90% of the plan's monthly-equivalent price (rounded to the nearest cent), and records acceptance of the plan price, $0.005 overage rate, and spending cap. Consent creates or updates a `pending_payment` subscription only; it does not activate service or collect payment. Card collection and payment processing are not implemented.

## 7. Billing behavior

- One successfully completed local analysis counts as one call.
- Failed decoding/analysis attempts release their reservation and do not count.
- Included calls are consumed before bonus calls; overage begins after both are exhausted.
- Overage is currently configured at USD $0.005 per successful call.
- The monthly overage spending cap is enforced centrally. The reserve operation rejects a call that would exceed it.
- Usage notifications are queued at 80% and 95%; notification delivery still needs an email/dashboard worker.
- At the cap, new inspections are blocked.
- The plan allowance and bonus are subscription-term totals; the overage spending cap is tracked by calendar-month segment within the subscription term.

## 8. Current implementation boundaries

This change provides deployment-token provisioning, central authorization, reservation/finalization, and local analysis integration. It does **not** yet implement card collection/payment processing, payment-provider webhooks, subscription purchase/renewal automation, invoice settlement, notification delivery, an enterprise dashboard, or automated recovery of reservations left pending after a process or network crash. Those are required before commercial launch.

The admin endpoint requires an active subscription row already created by a trusted billing administrator. Never activate subscriptions based solely on a browser request or customer-supplied payment claim.

## 9. Operational security checklist

- Keep customer deployment tokens in a secret manager; rotate/revoke compromised tokens.
- Keep service-role and admin keys only in Veracust's hosted secret manager.
- Restrict customer API ingress to approved private networks and use TLS.
- Disable request-body logging and payload capture.
- Review host storage, backups, snapshots, swap, and administrator access.
- Protect logs so they do not contain uploaded audio, filenames, credentials, or transcripts.
- Set CPU, memory, disk, and request-size limits.
- Patch and pin dependencies; build and test images for each target architecture.
- Validate false-positive and false-negative rates on representative customer audio before operational decisions.

Detection output is an evaluation signal, not a guarantee of fraud detection.
