# Phase 1 · Map Shell — Review

Verification for [`prd.md`](prd.md) / [`tasks.md`](tasks.md). Tick items (✅) as
verified. See [`../../cheatsheet.md`](../../cheatsheet.md) for the full command set.

## Build & run

Run from repo root `~/git/orion`.

**Web (primary dev loop):**
```
flutter pub get
flutter run -d chrome                 # or: -d web-server --web-port 8080
```

**Android — Asus Zenfone 10** (enable Developer Options + USB debugging, connect USB):
```
flutter devices                       # confirm the phone shows up
flutter run                           # debug build on device
# release build + install:
flutter build apk --release
flutter install                       # or: adb install -r build/app/outputs/flutter-apk/app-release.apk
```

**Desktop:** not supported — `maplibre_gl` has no Linux/Windows/macOS target. Use web.

## Round 1 — initial map-shell verification (pending)

1. [ ] App launches **directly to a full-screen map**; no other UI/navigation.
2. [ ] Renders OpenFreeMap `liberty` tiles.
3. [ ] Gestures work: pan, pinch + double-tap zoom, rotate, tilt.
4. [ ] Initial view frames the **whole Philippines**; correct across window sizes & after rotation.
5. [ ] **Portrait + landscape** both work; map reframes on rotation.
6. [ ] **Offline:** browse online, then network off → indicator shows, cached tiles render, **no error screen**, app usable → back online → indicator hides.
7. [ ] **No permission prompts** (no location).
8. [ ] Attribution (OpenFreeMap / OpenMapTiles / OSM) visible (web + device).
9. [ ] App identity correct: name **Orion** + `track`'s icon; builds & pans smoothly on the **Zenfone 10**.
