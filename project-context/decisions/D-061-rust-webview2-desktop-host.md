# D-061 — Rust WebView2 desktop host

## Status

Accepted for Stage 9 Windows productization.

## Context

The packaged Stage 9 runtime already owns a frozen Python supervisor/backend, the official Next.js standalone frontend and the product media/runtime closure. Before this decision, the supervisor opened `http://127.0.0.1:3000` in the user's default browser after the local backend and frontend became ready.

That transport proved the packaged application, but it did not provide the intended desktop product experience: the user saw browser tabs, browser chrome and a localhost address even though the application had been installed as UV Studio.

Rewriting the proven React/Next editing surface into another GUI toolkit would duplicate product logic and create a second presentation implementation. Bundling Electron would add another Chromium runtime despite Windows already providing the supported WebView2 runtime path.

## Decision

1. **Keep the frozen Python executable as the single packaged supervisor.** It remains responsible for release preflight, Project Store migration preparation, local backend startup, bundled Next frontend startup and bounded shutdown.
2. **Add one UV-owned Rust presentation component:** `desktop/uv-studio-desktop.exe`.
3. **The Rust component is presentation-only.** It does not own projects, commands, capabilities, provider configuration or canonical application state.
4. **Render the existing packaged frontend through Microsoft WebView2** inside a normal Win32 window. The internal navigation origin is fixed to `http://127.0.0.1:3000`.
5. **Do not fall back to the default browser for the product window.** If the required WebView2 Runtime is unavailable, fail closed with an actionable Windows error instead of silently changing the product surface.
6. **External navigation is explicit.** URLs outside the packaged loopback origin are cancelled in WebView2 and delegated to the system browser. New windows cannot escape the same rule.
7. **Closing the UV Studio window owns application lifetime.** Normal host exit causes the supervisor to stop the bundled Next process and backend child; a non-zero host exit is treated as a desktop-launch failure.
8. **WebView2 mutable profile data belongs under D-045 user data**, specifically `%LOCALAPPDATA%\UV Studio\webview2`, never inside the immutable versioned release payload.
9. **The desktop host is a D-044 release-manifest component.** Its executable is hashed with the immutable payload and is included in D-059 as an UV-owned signing target for any future public release.
10. **Rust release inputs are exact and product-owned.** Stage 9 pins Rust `1.97.1`, committed `desktop-host/Cargo.lock`, and `webview2-com` `0.39.1`; release staging uses Cargo `--locked` and records exact Cargo metadata/license evidence before D-044 hashing.
11. **WebView2 Runtime is a machine runtime dependency, not project state.** UV Studio does not bundle a second Chromium. Release/installed smoke must exercise the native host and successful navigation on the supported Windows runner.
12. **Browser E2E remains complementary evidence.** Playwright continues to prove deep product workflows against the packaged frontend/backend; the native-host smoke separately proves the Windows shell and WebView2 transport.

## Consequences

- Double-clicking UV Studio opens a dedicated application window without browser tabs or an address bar.
- Existing React/Next product work is preserved rather than reimplemented.
- Runtime memory/distribution cost stays below an Electron-style second Chromium bundle.
- The desktop host can later own desktop-only presentation integrations such as window state, file-drop, taskbar progress or native dialogs without becoming a second application-state authority.
- D-049 supervision remains valid, but its former default-browser presentation is superseded by this decision.
