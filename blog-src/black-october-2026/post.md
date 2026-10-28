---
title: Summary of Black October 2026 
date: 2026-10-23
categories: Writeups, Linux
cover: cover.jpg
summary: One of the oldest 0 days ever known
draft: true
---

# Black October 2026

  

In mid to late October of 2026 , Severe clusters of cyber security incidents occurred that effected almost entirety of the internet . Security researchers and threat intelligence firm ScruteX tracked over 28 distinct incidents, with a sharp concentration of critical disclosures hitting within a 48-hour window on October 20–21. AI tools were used to discover , exploit flaws and targeted payloads were used to attack in a large scale.

  

# Major Incidents

## 1. PHP2Shell (CVE-2026-109618 & CVE-2026-109619)
PHP2Shell is the nickname for two critical PHP core vulnerabilities that can give an unauthenticated remote attacker code execution on the web server. PHP fixed them in an emergency release on October 21, in versions 8.5.12, 8.4.27, 8.3.36, and 8.2.35.

## 2. eMudhra Intermediate CA Compromise
On October 17, a researcher known as Wayne told the browser root programs and eMudhra that he had recovered the private keys for eight of eMudhra’s intermediate CA certificates. He proved it by signing a message with each key. Six of the eight were for TLS (websites) and two were for code signing, all using the secp384r1 elliptic curve. [<i>source]('https://braindetox.kr/en/posts/emudhra_intermediate_ca_private_key_leak.html')

## 3. Node2Shell (CVE-2026-111497)
Node2Shell is the nickname Imperva gave to CVE-2026-111497, a memory-corruption bug in the Brotli decompressor bundled with Node.js. A crafted compressed stream can lead to remote code execution.

## 4. GitLab Server RCE (CVSS 10.0)
This is CVE-2026-110264, a maximum-severity (CVSS 10.0) unauthenticated remote code execution flaw in self-managed GitLab. GitLab fixed it on October 21, 2026. It can let an attacker run code on a self-managed server without logging in, and it reaches back to GitLab 7.0.