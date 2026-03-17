# The Thai House Coin Exchange — Product Requirements Specification

**Version:** 1.1  
**Date:** March 16, 2026  
**Author:** Keith (Digital Factory Team)  
**Status:** Draft

---

## 1. Overview

Thai House Coin (THC) is an internal web application for a small work group that tracks a fictional cryptocurrency pegged to lunches at a local Thai restaurant. Users accumulate THC from specific individuals, and when they reach 1.0 THC from a single person, they can redeem it for a real-life Thai lunch purchased by that person.

THC has no actual monetary value. The app is a fun, social tool for the team.

---

## 2. Goals

- Track how much THC each user owes/is owed by every other user
- Provide a public, transparent ledger of all transactions
- Allow admins to manage users and invalidate fraudulent transactions
- Enable a bounty system as the **sole mechanism** for creating new THC
- Be hostable for free and accessible from any browser
- Be fun and feel like a "real" crypto exchange (tongue-in-cheek professional)

---

## 3. Users & Roles

### 3.1 User Types

| Role | Description |
|------|-------------|
| **Admin** | Full access. Can create accounts, invalidate transactions, and perform all user actions. |
| **User** | Can send THC, post/claim bounties, request redemptions, and view all public data. |

### 3.2 Account Management

- **Invite-only registration.** There is no public signup page. Only admins can create new user accounts.
- Admin creates an account with a username and temporary password.
- User logs in and is prompted to change their password on first login.
- Expected user count: fewer than 15 people.

### 3.3 Authentication

- Username + password authentication.
- Passwords are hashed and salted (never stored in plain text).
- Session-based login (user stays logged in until they log out or the session expires).
- No email-based password reset (admin can manually reset a user's password if needed).

---

## 4. Core Concepts

### 4.1 Source-Tagged Balances

This is the most important design concept in the app. THC is **not fungible across sources.** Every coin is tagged with who it came from.

**Example:**
- Alice sends Keith 0.3 THC
- Bob sends Keith 0.7 THC
- Keith does NOT have "1.0 THC" to spend freely
- Keith has 0.3 THC (from Alice) and 0.7 THC (from Bob) — two separate tracked balances

This means the app tracks a **balance matrix**: every user-to-user pair has its own running balance.

### 4.2 Minting (Bounty-Only)

- **There is no admin minting.** The only way new THC enters circulation is through completed bounties.
- When a bounty is completed and confirmed by the poster, fresh THC is minted and credited to the claimant, **source-tagged to the poster** (see Section 5).
- This keeps the coin supply tied directly to community activity and prevents arbitrary inflation.

### 4.3 Sending THC

- Any user can send THC to any other user.
- When sending, the sender specifies: **recipient** and **amount**.
- The sent THC is deducted from the sender's total balance (drawn from any source — the sender does not choose which source to spend from).
- The recipient receives the THC tagged as **coming from the sender** (not from the sender's original source). This keeps the model simple: source = last person who sent it to you.
- Minimum send amount: 0.01 THC.
- A user cannot send more THC than their total balance.

### 4.4 Redemption

Redemption is the act of "cashing in" 1.0 THC from a single person for a real-life Thai lunch.

**Flow:**
1. User A accumulates ≥ 1.0 THC from User B (across one or many transactions).
2. User A initiates a redemption request targeting User B.
3. User B receives a notification/pending request.
4. User B **accepts** the redemption (confirming they will buy the lunch).
5. Upon acceptance: 1.0 THC (from User B → User A) is **burned** (permanently removed from circulation).
6. Any excess remains. If User A had 1.3 THC from User B, after redemption they have 0.3 THC from User B.

**Rules:**
- Only the person who is owed can initiate a redemption.
- Only the person who owes can accept/confirm.
- A pending redemption can be cancelled by the initiator before it is accepted.
- User B can decline a redemption (e.g., if it was a mistake). Declined redemptions return to normal state with no coins burned.

### 4.5 Burning

- THC is removed from circulation when a redemption is accepted.
- There is no other mechanism for burning coins (other than admin invalidation — see 4.6).
- Burned THC is recorded in the ledger as a burn transaction for transparency.

### 4.6 Admin Transaction Invalidation

- Admins can **invalidate** any transaction in the ledger to prevent tampering or correct mistakes.
- An invalidated transaction is not deleted — it remains visible in the ledger but is marked as `invalidated` with a timestamp and the admin who invalidated it.
- When a transaction is invalidated, all affected balances are recalculated by replaying the remaining valid transactions.
- Invalidation is recorded as its own entry in the ledger for full transparency (everyone can see that it happened and who did it).
- Use cases: correcting accidental sends, reversing fraudulent bounty completions, fixing any data integrity issues.

---

## 5. Bounty System

### 5.1 Overview

Any user can post a bounty — a task with a THC reward. Bounties are the **only way** new THC enters circulation. When a bounty is completed, fresh THC is minted and credited to the claimant, source-tagged to the poster.

### 5.2 Bounty Lifecycle

```
OPEN → CLAIM SUBMITTED → REVIEWED BY POSTER → COMPLETED (closed)
                                             → REJECTED (reopens bounty)
         ↘ CANCELLED (by poster, if no pending claims)
```

1. **Post:** Any user creates a bounty with a title, description, and reward amount (max 5.0 THC).
2. **Open:** The bounty is visible to all users. Anyone can attempt the task.
3. **Submit Claim:** When a user believes they have completed the task, they submit a claim. The claim includes a **message to the poster** explaining what they did or providing proof of completion. Multiple users can submit claims on the same bounty, but each user is rate-limited to **one claim submission per bounty per 10 minutes** (prevents spam).
4. **Review:** The poster reviews submitted claims. For each claim, the poster can:
   - **Approve:** Marks the bounty as completed. Fresh THC is minted and credited to the approved claimant, source-tagged to the poster.
   - **Reject:** The claim is rejected. The claimant can submit again after the 10-minute cooldown. The bounty remains open.
5. **Cancel:** The poster can cancel a bounty if no claims are pending review. Cancelled bounties are closed with no payout.

### 5.3 Bounty Rules

- Reward THC is **minted fresh** upon completion (new coins enter circulation).
- **Maximum reward: 5.0 THC per bounty.**
- The minted coins are **source-tagged to the poster**, meaning they count toward the poster → claimant balance. This means bounty rewards can eventually be redeemed as real lunches.
- The poster cannot claim their own bounty.
- **Multiple claims are allowed** — any number of users can submit claims, but only one can be approved (first approval closes the bounty).
- **Rate limit:** Each user can only submit one claim per bounty every 10 minutes.
- **Per-user bounty limit:** Each user can have a maximum of **5 open bounties** at any time. This prevents spamming the board.
- The poster is the sole judge of completion.

### 5.4 Bounty Data

| Field | Description |
|-------|-------------|
| Title | Short description of the task |
| Description | Detailed requirements (supports basic text) |
| Reward | Amount of THC (0.01–5.0 THC) |
| Posted by | The user who created the bounty |
| Status | Open, Completed, Cancelled |
| Claims | List of submitted claims (see below) |
| Completed at | Timestamp of completion (if completed) |

**Bounty Claims:**

| Field | Description |
|-------|-------------|
| Claimant | The user submitting the claim |
| Message | Text from the claimant explaining completion / proof |
| Status | Pending, Approved, Rejected |
| Submitted at | Timestamp of claim submission |

---

## 6. Public Ledger

### 6.1 All Data Is Public

Every user can see:
- **All balances:** Every user's total THC balance and the per-source breakdown (who owes whom how much).
- **Transaction history:** Every send, bounty payout, burn, and invalidation, with timestamps and participants.
- **Bounty board:** All bounties (open, claimed, completed, cancelled).

### 6.2 Ledger Entries

Each transaction in the ledger records:

| Field | Description |
|-------|-------------|
| Timestamp | When it occurred |
| Type | `send`, `redeem`, `burn`, `bounty_payout`, `invalidation` |
| From | Source user (or "BOUNTY" for bounty payouts) |
| To | Recipient user |
| Amount | THC amount |
| Memo | Optional note (e.g., bounty title, reason for minting) |

---

## 7. Pages & UI

### 7.1 Page Map

| Page | Access | Description |
|------|--------|-------------|
| **Login** | Public | Username/password login form |
| **Dashboard** | All users | Personal balance summary, pending redemptions, recent activity |
| **Wallet** | All users | Detailed breakdown: how much THC you have from each person, send THC form |
| **Leaderboard** | All users | Ranked list of users by total THC balance |
| **Ledger** | All users | Chronological log of all transactions, filterable by user/type |
| **Bounty Board** | All users | List of all bounties with status, claim/complete actions |
| **Redemptions** | All users | Pending redemption requests (incoming and outgoing) |
| **Admin Panel** | Admins only | Create users, reset passwords, invalidate transactions |

### 7.2 Design Direction

- **Thai restaurant menu aesthetic** — warm colors, simple layout, clean typography inspired by a classic Thai menu. Think cream/off-white backgrounds, warm reds and golds, simple borders, and friendly readable fonts.
- Tongue-in-cheek branding. "The Thai House Coin Exchange" should feel charming and playful, not corporate.
- Mobile-responsive (people will use this on their phones at lunch).

---

## 8. Technical Architecture

### 8.1 Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Backend** | Python + Flask | Beginner-friendly, large ecosystem, aligns with Keith's learning goals |
| **Database** | SQLite | Zero setup, file-based, perfect for small user counts |
| **Frontend** | HTML + CSS + JavaScript (Jinja2 templates) | No frontend framework needed — server-rendered pages keep it simple |
| **Auth** | Flask-Login + Werkzeug password hashing | Battle-tested session management |
| **Hosting** | Render.com (free tier) | Free, supports Flask + SQLite, easy deployment from GitHub |

### 8.2 Database Schema (Conceptual)

**users**
- id, username, display_name, password_hash, role (admin/user), is_active, must_change_password, created_at

**transactions**
- id, type (send/burn/bounty_payout), from_user_id, to_user_id, amount, memo, is_invalidated, invalidated_by, invalidated_at, created_at

**balances** (derived/cached — could also be computed from transactions)
- holder_user_id, source_user_id, amount

**redemptions**
- id, requester_id, target_id, amount, status (pending/accepted/declined/cancelled), created_at, resolved_at

**bounties**
- id, poster_id, title, description, reward_amount, status (open/completed/cancelled), created_at, completed_at

**bounty_claims**
- id, bounty_id, claimant_id, message, status (pending/approved/rejected), submitted_at

### 8.3 Key Technical Decisions

- **Balances are derived from transactions.** The transaction log is the source of truth. Balances can be recomputed at any time by replaying the ledger. A cached `balances` table can be maintained for fast reads but should always be rebuildable.
- **SQLite concurrency.** With <15 users, SQLite's write lock will not be a problem. Use WAL (Write-Ahead Logging) mode for better concurrent read performance.
- **No email integration.** All notifications are in-app (pending redemptions, bounty claims). No email server needed.
- **No real crypto.** There is no blockchain, no wallet addresses, no cryptographic signing. This is a traditional web app with a database that tracks balances.

### 8.4 Hosting Notes

- **Render.com free tier** will sleep the app after inactivity (~15 min). First request after sleep takes ~30 seconds to spin up. This is acceptable for the group's usage.
- **SQLite on Render:** Render's free tier uses ephemeral disk, meaning the SQLite database could be lost on redeploy. **Mitigation options:**
  - Use Render's free PostgreSQL database instead of SQLite (slightly more complex setup but persistent).
  - Use a file-backed SQLite with periodic backups to a free cloud storage.
  - Accept the risk and keep a backup strategy (export/import).
- **Recommendation:** Start with SQLite for simplicity during development, then migrate to PostgreSQL for production hosting on Render. Flask-SQLAlchemy makes this migration straightforward (change one connection string).

---

## 9. Security Considerations

Even though this is a fun internal tool, basic security hygiene matters:

- Passwords hashed with Werkzeug's `generate_password_hash` (uses PBKDF2 by default).
- All forms protected against CSRF (Cross-Site Request Forgery) using Flask-WTF.
- SQL injection prevented by using an ORM (SQLAlchemy) or parameterized queries.
- Role-based access checks on every admin endpoint.
- Rate limiting on login attempts to prevent brute force (optional but recommended).
- HTTPS enforced (Render provides free SSL).

---

## 10. Future Considerations (Out of Scope for V1)

These are ideas that may be worth building later but are NOT part of the initial release:

- **Transfer history per pair:** A detailed view showing all transactions between two specific users.
- **Achievements/badges:** "First redemption," "Bounty hunter," etc.
- **Coin denominations or decimals beyond 0.01.**
- **Multi-claim bounties:** Allowing multiple people to complete the same bounty.
- **Scheduled/recurring bounties.**
- **Push notifications or Slack integration.**
- **Coin splitting on send:** Letting the sender choose which source to draw from.
- **Exchange rate fluctuations:** A fun feature where the "value" of THC fluctuates randomly.
- **Chart/graph of balances over time.**

---

## 11. Open Questions

1. **What should happen to a deleted user's open bounties?** Recommendation: auto-cancel any open bounties posted by the deactivated user and reject any pending claims they submitted.
2. **Should there be a total coin supply cap?** Currently uncapped — new THC is minted with every completed bounty. This could be revisited if inflation becomes a concern.
3. **Can admins invalidate redemptions that are already accepted?** This would require "un-burning" coins. Recommendation: yes, for data integrity, but it should be rare.

### 11.1 Resolved Decisions

| Question | Decision |
|----------|----------|
| Admin minting? | No. Bounties are the only way to mint THC. |
| Max bounty reward? | 5.0 THC per bounty. |
| User deletion? | Soft-delete (mark inactive), preserve all history. |
| App name? | The Thai House Coin Exchange |

---

## 12. MVP Milestone Plan

For a beginner-friendly build approach, here's a suggested order of implementation:

| Phase | What to Build | Why This Order |
|-------|--------------|----------------|
| **Phase 1** | Project setup, database models, user auth (login/logout) | Foundation — nothing works without this |
| **Phase 2** | Admin panel (create users, reset passwords) | You need users before anything else |
| **Phase 3** | Bounty board (post, claim, complete bounties) | This is how coins are created — must come before wallets have anything in them |
| **Phase 4** | Wallet page (view balances, send THC) | Now that coins exist via bounties, users can view and trade them |
| **Phase 5** | Public ledger | Transparency — and it's mostly a read-only view |
| **Phase 6** | Redemption system | The "payoff" feature — this is where THC becomes real |
| **Phase 7** | Admin transaction invalidation | Safety net for the economy |
| **Phase 8** | Leaderboard, polish, deploy to Render | Final touches and go live |

Each phase is a working checkpoint — you can demo and use the app after each one.
