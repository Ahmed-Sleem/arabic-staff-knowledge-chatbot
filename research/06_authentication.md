# Topic 6 — Authentication (Email + Password + Email OTP)

**Status:** Phase 2 — Deep Dive (in progress)
**Last update:** 2026-07-10

---

## Open questions

1. **Password hashing**: argon2id (recommended) vs bcrypt.
2. **OTP generation**: 6-digit numeric, expirable (5–10 min), single-use, rate-limited.
3. **OTP storage**: hashed in DB (not plaintext).
4. **Email delivery** for OTP:
   - Transactional email providers with free tier: Resend (3K/month free), Brevo (300/day), SendGrid (limited), AWS SES (cheap at scale), Mailgun, Postmark.
   - Self-hosted SMTP (MailHog for dev, real SMTP in prod).
5. **OTP flows**:
   - Login with password only.
   - Login with password + email OTP (every login? new device only? admin-toggle?).
   - Forgot password via email OTP.
6. **Session strategy**:
   - httpOnly + Secure + SameSite cookies (recommended for GPR-style app).
   - Server-side session store (Redis or DB) vs stateless JWT (with refresh).
7. **CSRF protection** — necessary for cookie sessions; can use double-submit cookie or SameSite=Lax.
8. **Account lockout / brute force** — rate-limit on login and OTP endpoints.
9. **Admin role** — first admin promoted by env var or DB seed; subsequent admins promoted via admin UI.
10. **Logout** — server-side invalidation.
11. **Audit logging** — log auth events (login, OTP requested, OTP verified, login failed).

---

## Findings (append below)


## Findings — Email + password + email OTP (FastAPI patterns)

### Source 1 — Scalekit "Passwordless authentication in FastAPI with Magic Links and OTP" (Feb 2026)
URL: https://www.scalekit.com/blog/fastapi-passwordless-magic-link-otp-implementation
- Pattern: API accepts email → server generates state → calls provider to issue credential → provider delivers OTP via email → client receives only safe metadata.
- Tokens short-lived (5–10 min).
- "Verification endpoints accept either a magic-link token or an OTP code and set the session cookie."
- "Email templates must not embed secrets; they render only a magic link that contains an opaque, short-lived token."
- Service-layer pattern: business logic in `app/core/auth.py`, endpoints in router. Easy to test.

### Source 2 — Binadit "FastAPI Email Verification & Password Reset Tutorial" (Jul 2026)
URL: https://binadit.com/tutorials/setup-fastapi-email-verification-and-password-reset
- Confirmed pattern: argon2/bcrypt hash + httpOnly session cookie + `samesite=lax`.
- Tokens: random + hashed in DB + `used` flag + `expires_at` field.
- Login flow with rate limit `@limiter.limit("10/minute")`.
- "Don't reveal if email exists" on password-reset endpoint (anti-enumeration).

### Source 3 — GitHub fastapi discussion #9142 "Cookie based JWT tokens" (Aug 2024)
URL: https://github.com/fastapi/fastapi/discussions/9142
- Recommended: access token in JSON body + refresh token in httpOnly cookie.
- For our case (web app with chat): simpler to use a single session cookie (server-side session in DB, or signed JWT cookie).
- HttpOnly=True + Secure=True + SameSite=Lax.

### Source 4 — blog.greeden.me "A Beginner's Guide to Serious Security Design with FastAPI" (Oct 2025)
URL: https://blog.greeden.me/en/2025/10/14/...
- Confirmed pattern: HttpOnly session cookie + CSRF token in separate non-HttpOnly cookie.
- JWT for API, session cookies for browser-centric apps.
- For our chat app (web UI, no mobile native yet): session cookie is the cleanest.

### Source 5 — Medium "User Authentication with checks in FastAPI"
- MailTrap for dev (sandbox), SendinBlue (now Brevo) for prod.
- Verification flow: register → email with token → /confirm-email/{token} → user.is_verified = True.

### Email provider comparison (Source 6 — resources.mailertogo.com, 2025)
| Provider | Free tier | Best for |
|---|---|---|
| Brevo | 9,000/month (300/day) | Max free volume |
| Resend | 3,000/month | React/Next.js stacks, dev experience |
| Mailer To Go | varies | Heroku/PaaS zero-config |
| Postmark | 100/month | Auth/OTP (separate streams, best deliverability) |
| Amazon SES | $0.10/1K (cheap at scale) | 50K+ emails/month |
| Mailgun | 100/day free | Inbound parsing, list validation |
| Mailjet | 6,000/month | No custom domain needed |

- "Postmark is the default pick for 2FA and OTP because it enforces transactional-only traffic, uses separate message streams, and consistently leads inbox-placement studies."
- "For high-volume auth flows (millions per month), Amazon SES with a dedicated IP is more affordable."
- "Avoid bundled marketing/transactional platforms like Brevo or Loops for OTP at serious volume, because shared infrastructure can let a single bad marketing campaign hurt your auth delivery for hours."

### Implication for our project
- **Our volume is low** (staff of one company, a few hundred OTPs/month at most). Any free tier is fine.
- **For our KSA customer:** Postmark isn't available in-region but their infrastructure is good. Brevo (EU) or Resend (US) are fine.
- **Recommendation:**
  - **Dev:** Mailtrap (free sandbox).
  - **Prod:** **Resend** (3,000/month free, modern API, great DX, simple templates). 
  - **If we need to upgrade later:** Postmark (separate streams, best for auth emails).
  - **If we go self-hosted for on-prem:** Postfix + SMTP relay. Documented as a config option.
- **OTP design (locked):**
  - 6 digits, numeric.
  - Stored hashed (argon2 of the OTP code) in DB.
  - Expiry: 10 minutes.
  - Single use (`used` flag).
  - Max 5 attempts (lock after 5 wrong codes).
  - Max 3 OTPs per email per hour (rate limit).
  - Email contains the code; no magic links.
- **Session strategy (locked):**
  - Server-side session in Postgres (`sessions` table) with random session ID.
  - Session ID in httpOnly + Secure + SameSite=Lax cookie.
  - Session expiry: 7 days, sliding renewal.
  - Logout: delete the session row, clear cookie.

