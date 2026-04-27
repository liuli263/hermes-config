---
name: tauri-linux-build-run-when-appimage-bundling-fails
description: On Linux, build and launch a Tauri app even when full `tauri build` exits non-zero because AppImage bundling cannot download AppRun. Verify whether the release binary and .deb/.rpm artifacts were still produced, then run the release binary directly.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [tauri, linux, build, appimage, packaging, troubleshooting]
    related_skills: [systematic-debugging]
---

# Tauri Linux: build/run despite AppImage bundling failure

Use this when:
- A Linux Tauri project runs `pnpm tauri build` / `cargo tauri build`
- The command fails near the end during AppImage bundling
- Error mentions downloading `AppRun` or network refusal/timeout
- You still need a runnable app or installable package quickly

## Key finding

A failed AppImage bundling step does NOT necessarily mean the whole build is unusable.
Often, before the final non-zero exit:
- the renderer build succeeded
- the Rust release binary was produced
- `.deb` and/or `.rpm` bundles were already generated

So do not stop at the final exit code. Inspect the outputs.

## Procedure

1. Confirm prerequisites
   - `node -v`
   - `pnpm -v`
   - `cargo -V`
   - `rustc -V`

2. Build normally first
   - In project root: `pnpm build`
   - Or directly: `pnpm tauri build`

3. If build exits non-zero during AppImage bundling, inspect for partial success
   Typical binary path:
   - `src-tauri/target/release/<app-binary>`

   Typical bundle paths:
   - `src-tauri/target/release/bundle/deb/`
   - `src-tauri/target/release/bundle/rpm/`
   - `src-tauri/target/release/bundle/appimage/`

4. Treat these as success signals
   - `Finished 'release' profile` appears in output
   - `Built application at: .../target/release/<binary>` appears
   - `.deb` or `.rpm` files exist under `bundle/`

5. Run the release binary directly
   From project root:
   - `./src-tauri/target/release/<app-binary>`

   For GUI apps, if you need the shell returned immediately, run in background and verify process state.

6. Verify the app is really running
   - `pgrep -af <app-binary>`
   - or `ps -p <pid> -o pid=,comm=,etime=,stat=,cmd=`

7. Check app logs if needed
   Many Tauri apps write logs under a user config directory. Read those logs to confirm startup and single-instance behavior.

## Interpretation rules

- If AppImage download fails with network-related errors such as `Connection refused`, do not report “build failed” without qualification.
- Report it precisely as:
  - AppImage packaging failed
  - release binary succeeded (if present)
  - deb/rpm packaging may also have succeeded (if present)
- For the user’s immediate need (“compile and run”), a working release binary counts as success.

## User-facing guidance template

Explain separately:
1. Where the runnable binary is
2. Whether it is already running
3. How to run it next time
4. Which installable packages were generated
5. Which packaging format failed and why

Example next-run command:
- `cd /path/to/project && ./src-tauri/target/release/<app-binary>`

Example rebuild-then-run:
- `cd /path/to/project && pnpm build && ./src-tauri/target/release/<app-binary>`

## Pitfalls

- Single-instance Tauri apps may exit immediately when launched a second time because they signal the already-running instance. Check existing processes/logs before assuming startup failed.
- A foreground launch that returns quickly is not always a crash; it may have handed control to an existing instance.
- AppImage failure can be a packaging/network issue, not a code/build issue.

## Verification checklist

- [ ] Release binary exists
- [ ] Process is running or existing instance is confirmed
- [ ] If present, `.deb`/`.rpm` artifact paths are captured
- [ ] AppImage failure reason is explicitly separated from binary success
- [ ] User gets exact next-run command
