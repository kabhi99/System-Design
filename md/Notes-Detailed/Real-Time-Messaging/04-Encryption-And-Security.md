# REAL-TIME MESSAGING SYSTEM - HIGH LEVEL DESIGN

CHAPTER 4: END-TO-END ENCRYPTION & SECURITY

## SECTION 1: END-TO-END ENCRYPTION (E2EE) OVERVIEW

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS END-TO-END ENCRYPTION?                                         |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  * Only sender and recipient can read messages                    |  |
|  |  * Server stores encrypted blobs, cannot decrypt                  |  |
|  |  * Even if server is compromised, messages are safe               |  |
|  |                                                                   |  |
|  |  WITHOUT E2EE:                                                    |  |
|  |                                                                   |  |
|  |  Alice --> Server (can read) --> Bob                              |  |
|  |             "Hello Bob"                                           |  |
|  |                                                                   |  |
|  |  WITH E2EE:                                                       |  |
|  |                                                                   |  |
|  |  Alice --> Server --> Bob                                         |  |
|  |       "xK9#mZ..."  (encrypted)                                    |  |
|  |                                                                   |  |
|  |  Only Alice and Bob have keys to decrypt.                         |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  KEY CONCEPTS                                                           |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  ASYMMETRIC ENCRYPTION (Public/Private Key)                       |  |
|  |  * Each user has key pair: public + private                       |  |
|  |  * Public key: shared with everyone                               |  |
|  |  * Private key: never leaves device                               |  |
|  |  * Encrypt with public > only private can decrypt                 |  |
|  |                                                                   |  |
|  |  SYMMETRIC ENCRYPTION                                             |  |
|  |  * Single shared key for encrypt/decrypt                          |  |
|  |  * Faster than asymmetric                                         |  |
|  |  * Used for actual message content                                |  |
|  |                                                                   |  |
|  |  KEY EXCHANGE                                                     |  |
|  |  * Use asymmetric to exchange symmetric keys                      |  |
|  |  * Diffie-Hellman or ECDH                                         |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2: SIGNAL PROTOCOL (Used by WhatsApp, Signal)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SIGNAL PROTOCOL COMPONENTS                                             |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  1. IDENTITY KEY PAIR                                             |  |
|  |     * Long-term key pair (Ed25519)                                |  |
|  |     * Created once, identifies user                               |  |
|  |     * Public part uploaded to server                              |  |
|  |                                                                   |  |
|  |  2. SIGNED PRE-KEY                                                |  |
|  |     * Medium-term key (rotated periodically)                      |  |
|  |     * Signed by identity key                                      |  |
|  |     * Uploaded to server                                          |  |
|  |                                                                   |  |
|  |  3. ONE-TIME PRE-KEYS                                             |  |
|  |     * Batch of ephemeral keys                                     |  |
|  |     * Each used once, then discarded                              |  |
|  |     * Provides forward secrecy                                    |  |
|  |                                                                   |  |
|  |  KEY BUNDLE (uploaded to server):                                 |  |
|  |  {                                                                |  |
|  |    "identity_key": "...",     // Public identity key              |  |
|  |    "signed_prekey": "...",    // Signed by identity               |  |
|  |    "signature": "...",        // Proof of signing                 |  |
|  |    "one_time_prekeys": [      // 100 ephemeral keys               |  |
|  |      "key1", "key2", ...                                          |  |
|  |    ]                                                              |  |
|  |  }                                                                |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  X3DH: EXTENDED TRIPLE DIFFIE-HELLMAN                                   |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Initial key exchange when Alice first messages Bob:              |  |
|  |                                                                   |  |
|  |  1. Alice fetches Bob's key bundle from server                    |  |
|  |                                                                   |  |
|  |  2. Alice generates ephemeral key pair                            |  |
|  |                                                                   |  |
|  |  3. Alice computes shared secret using:                           |  |
|  |     DH1 = DH(Alice_identity, Bob_signed_prekey)                   |  |
|  |     DH2 = DH(Alice_ephemeral, Bob_identity)                       |  |
|  |     DH3 = DH(Alice_ephemeral, Bob_signed_prekey)                  |  |
|  |     DH4 = DH(Alice_ephemeral, Bob_one_time_prekey)                |  |
|  |                                                                   |  |
|  |     shared_secret = KDF(DH1 || DH2 || DH3 || DH4)                 |  |
|  |                                                                   |  |
|  |  4. Alice encrypts message with shared_secret                     |  |
|  |                                                                   |  |
|  |  5. Alice sends encrypted message + her ephemeral public key      |  |
|  |                                                                   |  |
|  |  6. Bob receives, computes same shared_secret, decrypts           |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  DOUBLE RATCHET ALGORITHM                                               |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  After initial exchange, keys evolve with each message:           |  |
|  |                                                                   |  |
|  |  DIFFIE-HELLMAN RATCHET (per message exchange)                    |  |
|  |  * New DH key pair per exchange                                   |  |
|  |  * Forward secrecy: past messages safe if key compromised         |  |
|  |                                                                   |  |
|  |  SYMMETRIC RATCHET (per message)                                  |  |
|  |  * KDF chain: key(n+1) = KDF(key(n))                              |  |
|  |  * Old keys discarded after use                                   |  |
|  |                                                                   |  |
|  |  MESSAGE KEY DERIVATION:                                          |  |
|  |                                                                   |  |
|  |  chain_key_0 --KDF--> chain_key_1 --KDF--> chain_key_2            |  |
|  |       |                    |                    |                 |  |
|  |       v                    v                    v                 |  |
|  |  message_key_0       message_key_1       message_key_2            |  |
|  |                                                                   |  |
|  |  Each message encrypted with unique key.                          |  |
|  |  Compromising one key doesn't reveal others.                      |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3: GROUP E2EE (Sender Keys)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CHALLENGE                                                              |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Naive approach: Encrypt message N times for N members            |  |
|  |  * 100 member group = encrypt 100 times = SLOW                    |  |
|  |                                                                   |  |
|  |  Solution: SENDER KEYS                                            |  |
|  |                                                                   |  |
|  |  1. Each sender generates a "sender key" for the group            |  |
|  |                                                                   |  |
|  |  2. Sender distributes their sender key to all members            |  |
|  |     (encrypted pairwise using Signal Protocol)                    |  |
|  |                                                                   |  |
|  |  3. Sender encrypts message ONCE with sender key                  |  |
|  |                                                                   |  |
|  |  4. Server broadcasts encrypted message to all members            |  |
|  |                                                                   |  |
|  |  5. Each member decrypts using sender's sender key                |  |
|  |                                                                   |  |
|  |  SENDER KEY ROTATION:                                             |  |
|  |  * When member leaves: rotate all sender keys                     |  |
|  |  * When member joins: distribute existing sender keys             |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  SENDER KEY FLOW                                                        |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  SETUP (Alice joins group with Bob, Carol, Dave):                 |  |
|  |                                                                   |  |
|  |  1. Alice generates sender_key_alice                              |  |
|  |  2. Alice encrypts sender_key_alice for Bob (Signal Protocol)     |  |
|  |  3. Alice encrypts sender_key_alice for Carol                     |  |
|  |  4. Alice encrypts sender_key_alice for Dave                      |  |
|  |  5. Alice sends these 3 encrypted keys                            |  |
|  |                                                                   |  |
|  |  SENDING MESSAGE:                                                 |  |
|  |                                                                   |  |
|  |  1. Alice encrypts "Hello group" with sender_key_alice            |  |
|  |  2. Server broadcasts encrypted message                           |  |
|  |  3. Bob, Carol, Dave decrypt with their copy of alice's key       |  |
|  |                                                                   |  |
|  |  MEMBER LEAVES:                                                   |  |
|  |                                                                   |  |
|  |  Dave leaves group                                                |  |
|  |  1. Alice generates new sender_key_alice'                         |  |
|  |  2. Alice distributes to Bob, Carol (not Dave)                    |  |
|  |  3. Dave can't decrypt future messages                            |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4: KEY VERIFICATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SAFETY NUMBERS / SECURITY CODES                                        |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Problem: How to verify you're talking to the real person?        |  |
|  |           (Not a man-in-the-middle)                               |  |
|  |                                                                   |  |
|  |  Solution: Safety Numbers                                         |  |
|  |                                                                   |  |
|  |  GENERATION:                                                      |  |
|  |  safety_number = hash(alice_identity_key + bob_identity_key)      |  |
|  |                                                                   |  |
|  |  Displayed as:                                                    |  |
|  |  * 60-digit number                                                |  |
|  |  * QR code                                                        |  |
|  |                                                                   |  |
|  |  VERIFICATION:                                                    |  |
|  |  * Alice and Bob meet in person                                   |  |
|  |  * Compare numbers or scan each other's QR code                   |  |
|  |  * If match: no MITM                                              |  |
|  |                                                                   |  |
|  |  KEY CHANGE ALERT:                                                |  |
|  |  * If Bob's identity key changes (new phone, reinstall)           |  |
|  |  * Alice sees: "Bob's safety number has changed"                  |  |
|  |  * Could be legitimate OR attack                                  |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5: MEDIA ENCRYPTION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ENCRYPTED MEDIA FLOW                                                   |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Sending an image:                                                |  |
|  |                                                                   |  |
|  |  1. Client generates random AES key for this media                |  |
|  |                                                                   |  |
|  |  2. Client encrypts image with AES key                            |  |
|  |     encrypted_image = AES_encrypt(image, media_key)               |  |
|  |                                                                   |  |
|  |  3. Client uploads encrypted blob to server/CDN                   |  |
|  |     Server returns: media_url                                     |  |
|  |                                                                   |  |
|  |  4. Client sends message containing:                              |  |
|  |     {                                                             |  |
|  |       "type": "image",                                            |  |
|  |       "media_url": "https://cdn/abc123",                          |  |
|  |       "media_key": "...",  // Encrypted with recipient's key      |  |
|  |       "sha256": "...",     // Verify integrity                    |  |
|  |       "thumbnail": "..."   // Small encrypted preview             |  |
|  |     }                                                             |  |
|  |                                                                   |  |
|  |  5. Recipient decrypts message, gets media_key                    |  |
|  |                                                                   |  |
|  |  6. Recipient downloads encrypted blob from media_url             |  |
|  |                                                                   |  |
|  |  7. Recipient decrypts image with media_key                       |  |
|  |                                                                   |  |
|  |  SERVER SEES:                                                     |  |
|  |  * Encrypted blob (can't decrypt)                                 |  |
|  |  * File size                                                      |  |
|  |  * Who sent to whom                                               |  |
|  |                                                                   |  |
|  |  SERVER CANNOT SEE:                                               |  |
|  |  * Actual image content                                           |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 6: SECURITY CONSIDERATIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THREAT MODEL                                                           |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  E2EE PROTECTS AGAINST:                                           |  |
|  |  Y Server breach (messages unreadable)                            |  |
|  |  Y Network eavesdropping                                          |  |
|  |  Y Malicious server operators                                     |  |
|  |  Y Government subpoenas for message content                       |  |
|  |                                                                   |  |
|  |  E2EE DOES NOT PROTECT AGAINST:                                   |  |
|  |  X Compromised device (malware on phone)                          |  |
|  |  X Screenshots by recipient                                       |  |
|  |  X Metadata (who talks to whom, when)                             |  |
|  |  X Physical access to unlocked phone                              |  |
|  |                                                                   |  |
|  |  METADATA VISIBLE TO SERVER:                                      |  |
|  |  * Sender and recipient IDs                                       |  |
|  |  * Timestamp                                                      |  |
|  |  * Message size                                                   |  |
|  |  * IP addresses                                                   |  |
|  |  * Device info                                                    |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  KEY STORAGE                                                            |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Private keys stored on device only:                              |  |
|  |                                                                   |  |
|  |  iOS: Keychain (hardware-backed on devices with Secure Enclave)   |  |
|  |  Android: Keystore (hardware-backed on some devices)              |  |
|  |  Desktop: Encrypted local storage                                 |  |
|  |                                                                   |  |
|  |  BACKUP CONSIDERATIONS:                                           |  |
|  |  * iCloud/Google Drive backup may include message database        |  |
|  |  * WhatsApp: Optional encrypted backup (user provides key)        |  |
|  |  * Signal: No cloud backup by design                              |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  PHONE NUMBER VERIFICATION                                              |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Registration flow:                                               |  |
|  |                                                                   |  |
|  |  1. User enters phone number                                      |  |
|  |  2. Server sends SMS with 6-digit code                            |  |
|  |  3. User enters code in app                                       |  |
|  |  4. Server verifies code                                          |  |
|  |  5. App generates key pairs                                       |  |
|  |  6. App uploads public keys to server                             |  |
|  |                                                                   |  |
|  |  SIM SWAP PROTECTION:                                             |  |
|  |  * PIN/password for account recovery                              |  |
|  |  * Two-factor authentication                                      |  |
|  |  * Registration lock (Signal feature)                             |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

END OF CHAPTER 4
