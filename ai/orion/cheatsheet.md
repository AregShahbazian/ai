# Orion — Flutter Command Cheatsheet

Run from repo root `~/git/orion`.
**`maplibre_gl` supports Android / iOS / web only — no desktop.** Web (Chrome) is the dev loop.

## First-time setup (once per machine / fresh clone)
```
flutter doctor                      # verify toolchain is healthy
flutter doctor --android-licenses   # accept Android SDK licenses (needed for device builds)
flutter pub get                     # fetch dependencies
flutter run -d chrome               # first launch in the browser
```

## Anytime dev (daily loop)
```
flutter run -d chrome               # launch web with hot reload
#   in the running session:  r = hot reload   R = hot restart   q = quit
flutter devices                     # list available targets
flutter analyze                     # static analysis
flutter logs                        # stream logs (when on a device)
```

## When dependencies change (edited pubspec.yaml)
```
flutter pub get                     # re-fetch after changing deps
flutter clean && flutter pub get    # if the build misbehaves after a change
# web map deps: ensure the maplibre-gl <script>/<link> in web/index.html
# still match the maplibre_gl plugin's required version
```

## Android device (Zenfone 10) — when you can connect it
```
# enable Developer Options + USB debugging on the phone, connect via USB
adb devices                         # confirm the phone is visible
flutter run                         # debug build on the device
./scripts/mobile/run.sh             # …or: filtered logs + records the VM Service URI
```

## Driving interactions remotely (the InteractionController bus)
```
# Web — in the browser DevTools console (window.orion, installed every build):
await orion.dispatch('hud.followMe.tap')
orion.logEvents(true); orion.dump(); orion.ids
orion.webnav.dump()                            # router location vs browser URL, canPop, stack depth
await orion.webnav.to('settings')              # navigate to a screen ('/' = back to map)

# Mobile — from the laptop, against a running ./scripts/mobile/run.sh (debug/profile):
./scripts/mobile/orion.sh dump                 # → captured interaction buffer
./scripts/mobile/orion.sh logEvents on=true    # toggle per-event logging
./scripts/mobile/orion.sh dispatch id=hud.followMe.tap
./scripts/mobile/orion.sh dispatch id=nav.screen.close     # back to the map
./scripts/mobile/orion.sh ids
./scripts/mobile/navto.sh settings             # nav.screen.open {screen:'settings'}
./scripts/mobile/webnav.sh                     # current screen route + nav state
./scripts/mobile/webnav.sh location            # just the active route
# URI auto-read from .dart_tool/orion_vmservice; localhost-forwarded (survives wifi switch)
```

## Build (release)
```
flutter build web --release         # → build/web/
flutter build apk --release         # → build/app/outputs/flutter-apk/app-release.apk
flutter build appbundle --release   # → build/app/outputs/bundle/release/  (Play Store upload)
```

## Install to connected device
```
flutter install                                                # install the release build
adb install -r build/app/outputs/flutter-apk/app-release.apk   # manual APK install
```

## Release signing (keystore) — only for Play Store builds
Not needed for dev. Debug signing works for `flutter run` on device. Set up once,
before the first `.aab` upload:
```
# 1. Generate the upload keystore (keep OUTSIDE the repo; back it up; remember passwords)
keytool -genkey -v -keystore ~/orion-upload-keystore.jks \
  -keyalg RSA -keysize 2048 -validity 10000 -alias upload

# 2. Create android/key.properties (gitignored) — points to the .jks + passwords
# 3. Wire android/app/build.gradle.kts release signingConfig to read key.properties
# 4. Enrol in Google Play App Signing (Google holds the app key; you keep the upload key)
```
⚠️ Losing the upload keystore means you can't update the app — back it up.

## Notes
- **Play Store upload** uses the `.aab` from `build appbundle`, signed with the release keystore (above).
- Desktop targets (`-d linux/windows/macos`) won't render the map — use web.
- iOS: configured for groundwork but not built (no Apple toolchain in use yet).
