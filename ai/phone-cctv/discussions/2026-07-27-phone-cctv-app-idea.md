# Phone-to-CCTV app — discussion (2026-07-27)

*Discussion in progress — this file is updated as the conversation continues.*

## Idea

Turn old smartphones into a CCTV system. Phones join a group (WiFi or mobile
network) with four roles/steps:

- **Connect** — phones join a group over WiFi or mobile network.
- **Setup** — configure which phones broadcast their camera (casters) and
  which are permitted to watch (viewers).
- **Cast** — caster phones (usually on home WiFi) start broadcasting.
- **Watch** — permitted phones view the stream(s).

## Open questions

1. Can casting work without a central server — i.e. caster phones act as
   their own server? (trivial on same local WiFi via mDNS/local discovery +
   direct streaming; harder across WAN/mobile data without at least a
   lightweight signaling/rendezvous step for NAT traversal — WebRTC/STUN-TURN
   or libp2p-style bootstrap.)

## Ideas to realize

- (none finalized yet — capturing as discussion continues)
