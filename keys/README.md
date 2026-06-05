# Keys

- **`pubkey.hex`** — the operator's Ed25519 **public** key. Committed to the repo
  and published so anyone can verify the signed head. Safe to share.
- **Private key** — NEVER goes in the repo. It lives only as the GitHub Actions
  secret `SIGNING_KEY_HEX`.

## Generate a keypair

```
python3 sign.py keygen
```

This writes `keys/pubkey.hex` (commit it) and prints the PRIVATE key hex once.
Copy the private hex into your repo's GitHub Actions secret `SIGNING_KEY_HEX`
(Settings → Secrets and variables → Actions). Do not store it anywhere in git.

If the private key is ever lost, you simply generate a new keypair and publish
the new public key — past signatures remain verifiable against the old public
key as long as it stays published (and past heads stay anchored via OpenTimestamps).
