# WhatsApp HTTP API Contract

This project's runtime is locked to the **megaAPI** request/response shape.
Any backend that implements the contract below — including a custom
self-hosted clone — works as a drop-in replacement. Just point
`MEGA_HOST` (set during `setup_config`) at your host and the rest of the
code is unchanged.

This document is the source of truth. If you maintain a clone, your
implementation must match every field and path here.

## Authentication

Every call sends:

```
Authorization: Bearer {INSTANCE_TOKEN}
```

`INSTANCE_TOKEN` is per-instance and provided to the wizard during setup.
Token is sent on the command line of `curl`, so logs may capture it on
shared machines — same caveat as megaAPI.

## Endpoints

All paths are relative to `MEGA_HOST` (e.g. `https://apibusiness1.megaapi.com.br`).
`{instance}` is the instance name configured in `SESSIONS["N"].instance`.

| Method | Path | Purpose | Caller |
|--------|------|---------|--------|
| POST | `/rest/sendMessage/{instance}/text` | Send a text message | `send_message.py` |
| POST | `/rest/sendMessage/{instance}/mediaBase64` | Send an image (base64) | `send_message.py --type image` |
| POST | `/rest/webhook/{instance}/configWebhook` | Register the public webhook URL | `update_webhooks.py` |
| POST | `/rest/instance/downloadMediaMessage/{instance}` | Decrypt + return media bytes | `media_handler.py` |
| GET  | `/rest/instance/{instance}` | Health check (status only) | `doctor.py` |

## Outbound payloads

### Send text — `POST /rest/sendMessage/{instance}/text`

```json
{
  "messageData": {
    "to": "5511999999999",
    "text": "hello world\n\n*Claude Code*",
    "linkPreview": false
  }
}
```

- `to`: digits-only phone number, country code first.
- `text`: full message body. The `*Claude Code*` signature is appended
  by `send_message.py` automatically — clones must NOT add their own
  signature.
- `linkPreview`: always `false` in this project.

### Send image — `POST /rest/sendMessage/{instance}/mediaBase64`

```json
{
  "messageData": {
    "to": "5511999999999",
    "base64": "iVBORw0KGgoAAAA...",
    "fileName": "photo.jpg",
    "type": "image",
    "caption": "optional caption\n\n*Claude Code*",
    "gifPlayback": false,
    "mimeType": "image/jpeg",
    "viewOnce": false
  }
}
```

- `base64`: raw bytes base64-encoded (no `data:` prefix).
- `mimeType`: detected by file extension (`image/jpeg`, `image/png`, `image/webp`, `image/gif`).
- 16 MB cap enforced client-side before encoding.

### Configure webhook — `POST /rest/webhook/{instance}/configWebhook`

```json
{
  "messageData": {
    "webhookUrl": "https://random-words.trycloudflare.com/?session=1",
    "webhookEnabled": true
  }
}
```

Successful response:

```json
{ "error": false, "...": "..." }
```

The client checks `data.error is False` to declare success.

### Download media — `POST /rest/instance/downloadMediaMessage/{instance}`

```json
{
  "messageKeys": {
    "mediaKey": "...",
    "directPath": "/v/t62.7117-24/...",
    "url": "https://mmg.whatsapp.net/...",
    "mimetype": "audio/ogg; codecs=opus",
    "messageType": "audioMessage"
  }
}
```

Response is the decrypted media binary (raw bytes). Used for incoming
images and audio.

## Inbound webhook payload

Your backend must POST a JSON body to the registered `webhookUrl` for
every incoming WhatsApp message. The receiver (`webhook_server.py`)
reads the following fields:

```
data.key.remoteJid          string  e.g. "5511999999999@s.whatsapp.net" or "...@lid"
data.key.fromMe             bool    true if message was sent BY the instance number
data.key.id                 string  unique message id (used for dedup)
data.message.conversation                       string  plain text (when present)
data.message.extendedTextMessage.text           string  formatted text (alternate)
data.message.imageMessage.caption               string  image caption
data.message.imageMessage.mediaKey              string  decrypt key
data.message.imageMessage.directPath            string  CDN path
data.message.imageMessage.url                   string  encrypted URL
data.message.imageMessage.mimetype              string  e.g. "image/jpeg"
data.message.audioMessage.{mediaKey,directPath,url,mimetype}    same shape
data.message.videoMessage.{mediaKey,directPath,url,mimetype}    same shape (rejected)
data.pushName               string  contact display name
data.messageTimestamp       int     Unix timestamp (seconds)
data.messageType            string  optional top-level hint ("imageMessage" etc.)
```

`data.jid` is read as a fallback for `data.key.remoteJid`.

The receiver detects message type by either `data.messageType` (top-level)
or by the first key found inside `data.message` that matches one of
`audioMessage` / `imageMessage` / `videoMessage`. Plain text is detected
by `data.message.conversation` or `data.message.extendedTextMessage.text`.

## Whitelist behavior

The receiver applies a phone whitelist (`config.ALLOWED_PHONE`) BEFORE
writing to the JSONL queue. Messages from other numbers are dropped
silently. The clone does not need to enforce this — it's a client-side
filter.

## Versioning note

This contract reflects megaAPI as of 2026-04-30. Field names and paths
are stable in megaAPI's documented API. If a clone diverges, list the
differences in the clone's README and bump a contract-compatibility
note here.
