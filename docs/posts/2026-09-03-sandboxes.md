---
date: 2026-09-03
tier: depth
tags:
- agents
- security
- nix
- systems
categories:
- engineering
authors:
- dylan
slug: on-reinventing-sandboxes
title: On reinventing sandboxes
description: >-
  Or why I built my own agent harness instead of using OpenClaw
license: CC-BY-4.0
---

I used to work in the same building as a company called `/dev/agents`, which is an incredibly provocative name.
It implies that the agent is not in a normal harness but somehow on your machine on a system level- deeply integrated into your OS, with kernel level drivers and file descriptors for interacting with "agents".

`/dev/agents` was bought by [Meta](add link) and as for I can tell, wasn't really working on system level things- just general computer use and showy vapor (there is no existing product) ware. The idea of an integrated agent is still really really fun.

<Narrative flow I need to flush out>
- I'm a huge Nix OS fan, system level tweaks are not as hard
 - OpenClaw came out and I had a massive sense of FOMO
 - Not dumb enough to run it raw. Burn money, risk compromising myself
 - other solutions Hermes, Iron Claw, whatever
 - been silently hacking on my own (cowboy)- with constraints that other harnesses hadn't totally embraced. Flexible, Auditable, Secure

Nix native (Hermes has this, there are open claw adapters)- but wanted something heavily tied to nix (auditable).

Also opted for a WASM runtime. Initially started building it Zellij as a zellij plugin. But realized that just being zellij could make it incredibly versatile- from running in browser, to a specialized wasmtime instance. Defining a clear boundary between wasm and runtimes also meant that I didn't have to commit to a particular implementation, and could easily hack around. More importantly, I figured the agent could hack on itself. For that- I need to consider security boundaries. Unbounded hacking by the agent is a smell- same issue I had with open claw itself- but nix offers the extensibility to provision very explicit system definitions so figured could use that as a basis for defining security boundaries.

I wanted something on my system. Able to restart my services, check my GPU stats- kill processes, rebuild my machine. Remembered Android uses user space. Coupled with a full embrace of systemd, c groups, netns you can get pretty close to bubblewrap. Gvisor by itself might be difficult to manage services- but with a thin wrapper compliance sheepdog acts as a syscall level boundary for controls. As I fleshed more of this out, I started to wonder in earnest what was the difference between my increasingly sophisticated walls and an actual "container" or sandbox. Not much, OCI compliance, part of the historical c-group evolution.
So implemented OCI defs, and proper isolation with landlock.

Recommend running somewhere between no permissions, just isolated user, and full sandbox mode. Cause I can still yell to my speaker "hey cowboy turn on the lights" and have it interact with home manager
