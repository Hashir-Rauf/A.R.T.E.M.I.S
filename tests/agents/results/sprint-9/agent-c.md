# sprint-9 / agent-c / chaos monkey
Verdict: PASS WITH ISSUES. Boundaries held against every attack tried (unticked folders, edited folder ids, 21 hand-made ops, injection phrases, outward approval, path traversal on the relay, cloned device, revoke). Real defects: reuse of a pairing code by a second browser hijacks the first phone's confirmation (B1), stale pairings can be confirmed into ghost devices (B2), and the relay address box resets to the deployed Cloudflare URL (U1). The run was cut short, so voice from the phone, web-search approval, replay and the audit view are NOT TESTED.

## What I did
1. Added two folders on the host, connected to the local relay ws://127.0.0.1:8026, started pairing.
2. On the phone context tried empty, partial, wrong, lower-case and 5+ wrong codes: lockout after 5 reaches the relay, then even the right code is refused. A correct lower-case code with trailing space is accepted (page upper-cases and trims).
3. Paired, confirmed, ticked docsA only; read localStorage and IndexedDB: localStorage holds only relay base, device id and name; the key is non-extractable and exportKey is blocked.
4. From the phone console called request() with unticked ids (1, 2, "1", 1.9, true, [1], huge) and an edited select option: all refused. 21 other ops (settings, erase, add_folder, delete_file, set_model, forget_key, send_email, search...) all answered "not available from a remote device".
5. Through the UI asked: list files (answered), delete everything (ARTEMIS says it has no delete), tidy (approval card; remote approval allowed for local file moves), email (card shown, Approve disabled, forced approve returned waiting_on_computer), search and prompt injection ("Left alone").
6. Copied localStorage into a new context: "This device's key is gone. Forget it and pair again." Removed the device on the host: phone gets no answer, "Your computer is not answering".
7. curl on the relay: traversal variants (../, %2e%2e, %5c, absolute) all 404; only index, manifest, sw and icon served. Raw WebSocket probes of bad paths closed with 4004.

## Backlog items checked
See the JSON. Pair a device PASS; relayed traffic unreadable PARTIAL (key handling and relay surface checked, ciphertext not inspected); never exceeds local PASS (folders, ops, email); revoke PASS; stage gate NOT TESTED from the UI.

## Bugs
- B1 medium: a second browser with the same valid code steals the confirmation (11-intruder-same-code.png, 14-hijack-phone-stuck-after-host-confirm.png), 4 reproductions.
- B2 low: a stale pairing can be confirmed into a ghost device.
- B3 low: non-dict requests get no reply; 7 tracebacks in tests/agents/work/s9-c/server.log.
- B4 low: relay ttl=abc closes with 1011.

## Not desired behavior
U1 relay box resets to the deployed Cloudflare URL and the Not connected note is stale; U2 indistinguishable device lists; U3 host not told of lockout; U4 misleading phone errors; U5 relay has no rate limit or security headers; U6 duplicate Check again buttons.

## Worked well
Lockout after 5 guesses; strict folder gating by id; allow-list of ops; outward approval kept on the computer; non-extractable device key; cloned device useless; instant revoke; relay static route safe.

## Not tested / blocked
Voice from phone (Allow talking off or on); web-search approval; frame replay; What changed audit of remote requests; stage gate (cannot be done from the UI). Time ran out. I did not use Save or Forget key. Pairing necessarily wrote device keys to the system keyring; only the device I removed was forgotten, others may remain.
