---
title: Example post: how this template works
date: 2026-10-23
categories: Writeups, Linux
cover: cover.jpg
summary: One or two sentences shown in link previews. Optional; defaults to the first paragraph.
draft: false
---

Copy this folder, rename it to your post's URL name (lowercase, hyphens, e.g. `ssh-hardening`), and edit this file. Folders starting with `_` are never built.

## Headings, text and links

Normal paragraphs, **bold**, *italic* and [links](https://example.com) work. Raw HTML also works if you ever need it.

## Pictures

Put images in the same folder as this file. The text in the quotes becomes the caption:

![Nmap scan output](scan.png "Nmap finds SSH open on port 22")

## Code

```bash
sudo sshd -T | grep -i passwordauthentication
```

> Quotes look like this.

| Tool | Use |
|------|-----|
| nmap | Port scanning |
| wireshark | Packet analysis |
