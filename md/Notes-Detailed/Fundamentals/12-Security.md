# CHAPTER 12: SECURITY FUNDAMENTALS
*Protecting Systems and Data*

Security is not optional. Every system must consider authentication,
authorization, encryption, and defense against common attacks.

## SECTION 12.1: AUTHENTICATION (AuthN)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  AUTHENTICATION = "WHO ARE YOU?"                                      |
|                                                                         |
|  Verifying the identity of a user or service.                         |
|                                                                         |
|  AUTHENTICATION FACTORS:                                               |
|                                                                         |
|  1. SOMETHING YOU KNOW                                                 |
|     Password, PIN, security questions                                 |
|                                                                         |
|  2. SOMETHING YOU HAVE                                                 |
|     Phone (SMS code), hardware token, authenticator app              |
|                                                                         |
|  3. SOMETHING YOU ARE                                                  |
|     Fingerprint, face recognition, iris scan                         |
|                                                                         |
|  MULTI-FACTOR AUTHENTICATION (MFA):                                    |
|  Combine 2+ factors for stronger security                            |
|  Example: Password + Phone OTP                                       |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  PASSWORD SECURITY                                                     |
|                                                                         |
|  NEVER store plain text passwords!                                    |
|                                                                         |
|  CORRECT APPROACH:                                                     |
|                                                                         |
|  1. Hash password with slow algorithm                                 |
|     hash = bcrypt(password, cost=12)                                 |
|     or: argon2id(password)                                           |
|                                                                         |
|  2. Store hash in database                                            |
|     users.password_hash = "$2b$12$abc..."                           |
|                                                                         |
|  3. On login, hash input and compare                                 |
|     bcrypt.verify(input_password, stored_hash)                       |
|                                                                         |
|  WHY SLOW HASHING:                                                     |
|  Fast hashes (SHA256) = Attacker can try billions/second            |
|  Slow hashes (bcrypt) = Attacker limited to thousands/second        |
|                                                                         |
|  GOOD: bcrypt, argon2id, scrypt                                      |
|  BAD: MD5, SHA1, SHA256 (too fast)                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 12.2: SESSION MANAGEMENT

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SESSION-BASED AUTHENTICATION                                         |
|                                                                         |
|  Server stores session state, client has session ID.                  |
|                                                                         |
|  FLOW:                                                                 |
|                                                                         |
|  1. User logs in with username/password                              |
|  2. Server creates session, stores in DB/Redis                       |
|     session_id: abc123 > { user_id: 1, expires: ... }               |
|  3. Server sends session_id in cookie                                |
|     Set-Cookie: session_id=abc123; HttpOnly; Secure                 |
|  4. Browser sends cookie with every request                          |
|  5. Server looks up session, gets user                               |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |  Client                        Server                          |  |
|  |     |                             |                             |  |
|  |     |-- POST /login ------------->|                            |  |
|  |     |   {user, pass}              |                             |  |
|  |     |                             |                             |  |
|  |     |<-- Set-Cookie: session=abc -| (Store session in Redis)   |  |
|  |     |                             |                             |  |
|  |     |-- GET /profile ------------>|                            |  |
|  |     |   Cookie: session=abc       |                             |  |
|  |     |                             | (Lookup session in Redis)  |  |
|  |     |<-- User profile ------------|                            |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  COOKIE FLAGS:                                                         |
|  * HttpOnly: JavaScript can't access (prevents XSS theft)           |
|  * Secure: Only sent over HTTPS                                     |
|  * SameSite: Prevent CSRF (Strict/Lax/None)                        |
|                                                                         |
|  PROS: Easy logout (delete session), easy to invalidate             |
|  CONS: Server-side storage required, scaling challenges             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 12.3: JWT (JSON Web Tokens)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  JWT = STATELESS TOKEN                                                |
|                                                                         |
|  Token contains user info, signed by server. No server storage.      |
|                                                                         |
|  JWT STRUCTURE:                                                        |
|                                                                         |
|  header.payload.signature                                              |
|                                                                         |
|  eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTYifQ.signature               |
|  +---------------------+-------------------------+----------+         |
|       Header                  Payload              Signature          |
|       (base64)               (base64)              (base64)           |
|                                                                         |
|  HEADER:                                                               |
|  {                                                                     |
|    "alg": "HS256",    // Algorithm                                   |
|    "typ": "JWT"                                                       |
|  }                                                                     |
|                                                                         |
|  PAYLOAD (Claims):                                                     |
|  {                                                                     |
|    "sub": "user123",          // Subject (user ID)                   |
|    "name": "Alice",                                                   |
|    "role": "admin",                                                   |
|    "iat": 1704067200,         // Issued at                           |
|    "exp": 1704153600          // Expiration (24h later)             |
|  }                                                                     |
|                                                                         |
|  SIGNATURE:                                                            |
|  HMAC-SHA256(base64(header) + "." + base64(payload), secret)         |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  JWT FLOW                                                              |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |  Client                        Server                          |  |
|  |     |                             |                             |  |
|  |     |-- POST /login ------------->|                            |  |
|  |     |                             | Generate JWT                |  |
|  |     |<-- { token: "eyJ..." } -----|                            |  |
|  |     |                             |                             |  |
|  |     |-- GET /profile ------------>|                            |  |
|  |     |   Authorization: Bearer eyJ |                             |  |
|  |     |                             | Verify signature,          |  |
|  |     |                             | decode payload             |  |
|  |     |<-- User profile ------------|                            |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  PROS:                                                                 |
|  Y Stateless (no server storage)                                     |
|  Y Scalable (any server can verify)                                  |
|  Y Works across services (microservices)                            |
|                                                                         |
|  CONS:                                                                 |
|  X Can't revoke easily (token valid until expiry)                   |
|  X Larger than session ID                                           |
|  X Payload visible (don't put secrets!)                             |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  JWT BEST PRACTICES                                                    |
|                                                                         |
|  1. SHORT EXPIRY                                                       |
|     Access token: 15 min - 1 hour                                    |
|     Use refresh tokens for longer sessions                          |
|                                                                         |
|  2. USE REFRESH TOKENS                                                 |
|     Access token: Short-lived, in memory                            |
|     Refresh token: Longer, in HttpOnly cookie                       |
|     When access expires, use refresh to get new one                 |
|                                                                         |
|  3. REVOCATION STRATEGY                                                |
|     * Token blacklist (defeats stateless, but enables logout)       |
|     * Short expiry + refresh token rotation                         |
|                                                                         |
|  4. ALGORITHM SECURITY                                                 |
|     Y Use HS256 (shared secret) or RS256 (public/private key)      |
|     X Never accept alg: "none"                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 12.4: OAUTH 2.0

```
+-------------------------------------------------------------------------+
|                                                                         |
|  OAUTH 2.0 = DELEGATED AUTHORIZATION                                  |
|                                                                         |
|  "Allow app to access your resources without sharing password"        |
|                                                                         |
|  Example: "Login with Google" - App accesses your Google data        |
|                                                                         |
|  ROLES:                                                                |
|  * Resource Owner: You (the user)                                    |
|  * Client: The app wanting access                                    |
|  * Authorization Server: Google (issues tokens)                      |
|  * Resource Server: Google API (has your data)                       |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  AUTHORIZATION CODE FLOW (Most common for web apps)                  |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  User    Client App       Auth Server (Google)     Resource    |  |
|  |   |          |                    |                    |        |  |
|  |   |- Click "Login" -->|           |                    |        |  |
|  |   |                   |           |                    |        |  |
|  |   |<-- Redirect ------|           |                    |        |  |
|  |   |    to Google               |                    |        |  |
|  |   |                               |                    |        |  |
|  |   |-- Login to Google ----------->|                    |        |  |
|  |   |   Grant permission            |                    |        |  |
|  |   |                               |                    |        |  |
|  |   |<-- Redirect with code --------|                    |        |  |
|  |   |    ?code=abc123               |                    |        |  |
|  |   |                               |                    |        |  |
|  |   |--- code to app -->|           |                    |        |  |
|  |                       |           |                    |        |  |
|  |                       |-- Exchange code -->|           |        |  |
|  |                       |   + client_secret  |           |        |  |
|  |                       |                    |           |        |  |
|  |                       |<-- Access token ---|           |        |  |
|  |                       |                               |        |  |
|  |                       |-- API call with token -------->|        |  |
|  |                       |   Authorization: Bearer xyz    |        |  |
|  |                       |                               |        |  |
|  |                       |<-- User data -----------------|        |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  TOKENS:                                                               |
|  * Access Token: Short-lived, used to call APIs                     |
|  * Refresh Token: Long-lived, used to get new access tokens         |
|                                                                         |
|  SCOPES: Limit what app can access                                   |
|  Example: scope=email profile (read email and profile, not modify)  |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  OPENID CONNECT (OIDC)                                                |
|                                                                         |
|  OAuth 2.0 + Authentication                                          |
|                                                                         |
|  OAuth = Authorization only (what can app do)                        |
|  OIDC = Authentication + Authorization (who is the user)             |
|                                                                         |
|  Adds:                                                                 |
|  * ID Token (JWT with user info)                                     |
|  * UserInfo endpoint                                                 |
|  * Standard claims (sub, name, email)                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 12.5: AUTHORIZATION (AuthZ)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  AUTHORIZATION = "WHAT CAN YOU DO?"                                   |
|                                                                         |
|  After authentication, determine what user is allowed to access.     |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  1. ROLE-BASED ACCESS CONTROL (RBAC)                                  |
|  -------------------------------------                                  |
|                                                                         |
|  Assign permissions to roles, assign roles to users.                 |
|                                                                         |
|  Roles: Admin, Editor, Viewer                                        |
|                                                                         |
|  +-------------+------------+------------+------------+              |
|  | Permission  | Admin      | Editor     | Viewer     |              |
|  +-------------+------------+------------+------------+              |
|  | Create      | Y          | Y          | X          |              |
|  | Read        | Y          | Y          | Y          |              |
|  | Update      | Y          | Y          | X          |              |
|  | Delete      | Y          | X          | X          |              |
|  | Manage Users| Y          | X          | X          |              |
|  +-------------+------------+------------+------------+              |
|                                                                         |
|  User Alice: [Admin]                                                  |
|  User Bob: [Editor]                                                   |
|                                                                         |
|  CHECK:                                                                |
|  if user.hasRole('Admin') or user.hasRole('Editor'):                 |
|      allow_create()                                                   |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  2. ATTRIBUTE-BASED ACCESS CONTROL (ABAC)                            |
|  ---------------------------------------------                          |
|                                                                         |
|  Rules based on attributes of user, resource, environment.           |
|                                                                         |
|  POLICY EXAMPLE:                                                       |
|  "Allow if user.department == resource.department                    |
|   AND resource.classification != 'top-secret'                        |
|   AND current_time is during business hours"                        |
|                                                                         |
|  More flexible but more complex than RBAC                            |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  3. ACCESS CONTROL LISTS (ACL)                                        |
|  --------------------------------                                       |
|                                                                         |
|  Per-resource list of who can do what.                               |
|                                                                         |
|  Document "Budget.xlsx":                                              |
|  - Alice: read, write                                                |
|  - Bob: read                                                         |
|  - Finance Team: read, write                                         |
|                                                                         |
|  Common in file systems, cloud storage (S3 ACLs)                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 12.6: ENCRYPTION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ENCRYPTION FUNDAMENTALS                                              |
|                                                                         |
|  1. ENCRYPTION IN TRANSIT (TLS/HTTPS)                                 |
|  --------------------------------------                                 |
|                                                                         |
|  Protect data as it travels over the network.                        |
|                                                                         |
|  Client ---- encrypted tunnel (TLS) ---- Server                      |
|                                                                         |
|  TLS HANDSHAKE (Simplified):                                          |
|  1. Client: "Hello, I support these ciphers"                         |
|  2. Server: "Let's use this cipher, here's my certificate"          |
|  3. Client: Verifies certificate, generates session key              |
|  4. Both: Encrypt all data with session key                          |
|                                                                         |
|  REQUIREMENTS:                                                         |
|  * Valid TLS certificate (Let's Encrypt, CA)                        |
|  * Strong ciphers (TLS 1.2+, prefer 1.3)                            |
|  * HSTS header (force HTTPS)                                        |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  2. ENCRYPTION AT REST                                                |
|  -------------------------                                              |
|                                                                         |
|  Protect data stored on disk.                                        |
|                                                                         |
|  APPROACHES:                                                           |
|  * Full disk encryption (LUKS, BitLocker)                           |
|  * Database encryption (TDE - Transparent Data Encryption)          |
|  * Application-level encryption (encrypt before storing)            |
|                                                                         |
|  APPLICATION-LEVEL:                                                    |
|  encrypted_ssn = AES.encrypt(user.ssn, key)                          |
|  database.save(encrypted_ssn)                                        |
|                                                                         |
|  KEY MANAGEMENT:                                                       |
|  * Don't hardcode keys in code!                                      |
|  * Use KMS (AWS KMS, HashiCorp Vault)                               |
|  * Rotate keys periodically                                         |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  SYMMETRIC vs ASYMMETRIC ENCRYPTION                                   |
|                                                                         |
|  SYMMETRIC (Same key for encrypt/decrypt):                           |
|  * AES-256, ChaCha20                                                |
|  * Fast, good for large data                                        |
|  * Challenge: How to share key securely?                            |
|                                                                         |
|  ASYMMETRIC (Public/private key pair):                               |
|  * RSA, Ed25519                                                      |
|  * Public key encrypts, private key decrypts                        |
|  * Slower, used for key exchange and signatures                     |
|                                                                         |
|  IN PRACTICE (TLS):                                                    |
|  Use asymmetric to exchange symmetric key                            |
|  Use symmetric for actual data encryption                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 12.7: COMMON ATTACKS AND DEFENSES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  COMMON WEB VULNERABILITIES                                           |
|                                                                         |
|  1. SQL INJECTION                                                      |
|  -----------------                                                      |
|                                                                         |
|  ATTACK:                                                               |
|  Input: ' OR '1'='1' --                                              |
|  Query: SELECT * FROM users WHERE name = '' OR '1'='1' --'           |
|  > Returns all users!                                                |
|                                                                         |
|  DEFENSE:                                                              |
|  Y Parameterized queries / Prepared statements                       |
|    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))   |
|  Y ORM (abstracts SQL)                                               |
|  X Never concatenate user input into SQL                            |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  2. CROSS-SITE SCRIPTING (XSS)                                        |
|  ---------------------------------                                      |
|                                                                         |
|  ATTACK:                                                               |
|  User input: <script>steal(document.cookie)</script>                 |
|  Rendered in page > Script executes in victim's browser             |
|                                                                         |
|  DEFENSE:                                                              |
|  Y Escape output (HTML entities)                                     |
|    <script> > &lt;script&gt;                                        |
|  Y Content Security Policy (CSP) header                              |
|  Y HttpOnly cookies (JS can't access)                               |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  3. CROSS-SITE REQUEST FORGERY (CSRF)                                 |
|  -----------------------------------------                              |
|                                                                         |
|  ATTACK:                                                               |
|  User logged into bank.com                                           |
|  Visits evil.com with: <img src="bank.com/transfer?to=hacker">      |
|  Browser sends bank cookies > Transfer happens!                      |
|                                                                         |
|  DEFENSE:                                                              |
|  Y CSRF tokens (hidden form field, verify on server)                |
|  Y SameSite cookie attribute (Strict or Lax)                        |
|  Y Check Origin/Referer headers                                     |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  4. DENIAL OF SERVICE (DoS/DDoS)                                      |
|  --------------------------------                                       |
|                                                                         |
|  ATTACK:                                                               |
|  Flood server with requests until it can't respond                  |
|                                                                         |
|  DEFENSE:                                                              |
|  Y Rate limiting                                                     |
|  Y CDN (absorb traffic at edge)                                     |
|  Y DDoS protection (Cloudflare, AWS Shield)                         |
|  Y Auto-scaling                                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SECURITY - KEY TAKEAWAYS                                             |
|                                                                         |
|  AUTHENTICATION                                                        |
|  --------------                                                         |
|  * Hash passwords with bcrypt/argon2                                 |
|  * Use MFA for sensitive systems                                     |
|  * Session vs JWT: stateful vs stateless                            |
|                                                                         |
|  JWT                                                                   |
|  ----                                                                   |
|  * Stateless, scalable                                               |
|  * Short expiry + refresh tokens                                     |
|  * Can't revoke easily (use blacklist if needed)                    |
|                                                                         |
|  OAUTH 2.0 / OIDC                                                      |
|  -----------------                                                      |
|  * OAuth = delegated authorization                                   |
|  * OIDC = OAuth + authentication                                    |
|  * Authorization code flow for web apps                             |
|                                                                         |
|  AUTHORIZATION                                                         |
|  -------------                                                          |
|  * RBAC: Roles > Permissions                                        |
|  * ABAC: Attribute-based policies                                   |
|  * ACL: Per-resource permissions                                    |
|                                                                         |
|  ENCRYPTION                                                            |
|  ----------                                                             |
|  * In transit: TLS/HTTPS                                            |
|  * At rest: AES, database TDE                                       |
|  * Key management: KMS, Vault                                       |
|                                                                         |
|  COMMON ATTACKS                                                        |
|  --------------                                                         |
|  * SQL Injection > Parameterized queries                            |
|  * XSS > Escape output, CSP                                         |
|  * CSRF > CSRF tokens, SameSite cookies                             |
|  * DDoS > Rate limiting, CDN                                        |
|                                                                         |
|  INTERVIEW TIP                                                         |
|  -------------                                                         |
|  * Mention security proactively in designs                          |
|  * Discuss authN/authZ flow                                         |
|  * Know the difference between OAuth and OIDC                       |
|  * Understand encryption in transit vs at rest                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 12

