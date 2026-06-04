# Orion — Flutter Command Cheatsheet

Short reference. Run from repo root `~/git/orion`.
**`maplibre_gl` supports Android / iOS / web only — no desktop.** Web is the dev loop.

## Setup / maintenance
```
flutter pub get            # fetch dependencies
flutter clean              # wipe build artifacts
flutter doctor             # toolchain health check
flutter analyze            # static analysis
flutter test               # unit / widget tests
```

## Run (dev)
```
flutter run -d chrome                        # web — primary dev loop
flutter run -d web-server --web-port 8080    # web, headless server
flutter devices                              # list available targets
flutter run                                  # default connected device
flutter run -d <device-id>                   # specific device
```

## Android device (Zenfone 10)
```
# enable Developer Options + USB debugging, connect via USB
adb devices                # confirm device is visible
flutter run                # debug build on device
flutter logs               # stream device logs
```

## Build (release)
```
flutter build web --release          # → build/web/
flutter build apk --release          # → build/app/outputs/flutter-apk/app-release.apk
flutter build appbundle --release    # → build/app/outputs/bundle/release/  (Play Store upload)
```

## Install to connected device
```
flutter install                                                # install release build
adb install -r build/app/outputs/flutter-apk/app-release.apk   # manual APK install
```

## Release signing (keystore) — only needed for Play Store builds
Not needed for Phase 1 / dev. Debug signing works for `flutter run` on device.
Set up once, before the first `.aab` upload:
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
