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

Verified on the **Zenfone 10 via `flutter run` (2026-06-04)** — app builds and runs on device.

1. [x] App launches **directly to a full-screen map**; no other UI/navigation. ✅ device
2. [x] Renders OpenFreeMap `liberty` tiles. ✅ device
3. [x] Gestures work: pan, pinch + double-tap zoom, rotate, tilt. ✅ device
4. [x] Initial view frames the **whole Philippines**; correct across window sizes & after rotation. ✅ device
5. [x] **Portrait + landscape** both work; map reframes on rotation. ✅ device
6. [x] **Offline:** browse online, then network off → indicator shows, cached tiles render, **no error screen**, app usable → back online → indicator hides. ✅ device
7. [x] **No permission prompts** (no location). ✅ device
8. [x] Attribution (OpenFreeMap / OpenMapTiles / OSM) visible (web + device). ✅ device
9. [x] App identity / runs on the **Zenfone 10** — builds & runs via `flutter run`. ✅ device  _(launcher name/icon to confirm on a release install)_

**Round 1: PASS — Phase 1 / map-shell verified on device (2026-06-04).** Only the
launcher name/icon remains to confirm on a release-APK install (cosmetic).
