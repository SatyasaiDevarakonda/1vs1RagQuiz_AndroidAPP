# 1v1 RAG Quiz — Android Native Client

A Java 17 + XML Android app (Material Components, dark "cyber" theme) that is a thin
client over the **real** backend in `backend/`. Auth is REST; the 1v1 battle itself
is driven entirely by **WebSocket events** on `/ws`, matching `backend/main.py` and
`backend/game_manager.py` exactly — the server is authoritative for timing, scoring
and correctness, the app only renders what it's told.

---

## Architecture

```
Android Client (Java + XML)
    ├── Retrofit 2 + Gson  → REST: /api/auth/*, /api/profile/history
    ├── OkHttp WebSocket   → /ws : create_room, join_room, toggle_ready,
    │                               submit_answer  (client → server)
    │                         connected, room_created, room_joined, player_joined,
    │                         player_ready_changed, countdown_*, game_started,
    │                         question, time_update, answer_accepted, answer_result,
    │                         scores_update, game_ended  (server → client)
    └── SQLiteOpenHelper   → local cache of extended profile fields
                              (address/gender/age/avatar — the backend has no columns
                              for these) and an offline-only login fallback
                │
                ▼ ws:// or http://
Python Backend (FastAPI on port 8000, MongoDB)
    ├── /api/auth/signup, /login, /guest, /me
    ├── /api/profile/history
    ├── /api/rooms/create-with-pdf, /{code}/exists
    └── /ws  (the real-time 1v1 game loop, server-authoritative scoring)
```

Screens: Splash → Login/Register/Guest → Main (Home / Battle Hub / History / Profile,
`BottomNavigationView`) → Lobby (room code, ready-up) → Quiz (timed MCQ battle) → Result.

## Prerequisites already set up on this machine

- **JDK 25** at `C:\Program Files\Java\jdk-25.0.2` (Gradle 8.14.6 runs fine on it)
- **Android SDK** at `C:\Users\satya\AppData\Local\Android\Sdk`
  (`platform-tools`, `build-tools;34.0.0`, `platforms;android-34`, `cmdline-tools;latest`,
  and an `android-34` emulator system image)
- An AVD named **`RagQuiz_Pixel6`** (created once via `avdmanager`)

You do **not** need Android Studio. Everything below runs from VS Code's integrated
terminal or the Command Palette.

## Running it — VS Code tasks

Open the `android/` folder as the VS Code workspace root, then **Terminal → Run Task…**:

1. **Android: Start Emulator (RagQuiz_Pixel6)** — boots the emulator (first boot is slow,
   ~1–2 min; leave it running).
2. **Android: Run (Build + Install + Launch)** — this is the default build task
   (Ctrl+Shift+B): assembles the debug APK, installs it on whatever device/emulator
   `adb` currently sees, and launches `SplashActivity`.
3. **Android: Logcat (app only)** — tails this app's logs if something looks wrong.

Re-run task 2 after every code change — no need to restart the emulator.

## Running it from a terminal directly

```bash
cd android
export JAVA_HOME="/c/Program Files/Java/jdk-25.0.2"
export ANDROID_HOME="/c/Users/satya/AppData/Local/Android/Sdk"

./gradlew assembleDebug      # → app/build/outputs/apk/debug/app-debug.apk
./gradlew installDebug       # installs on the running emulator/device
adb shell am start -n com.quiz.rag/.SplashActivity
```

## Before you tap "Quick Match" — start the backend

The app expects the backend reachable at `http://10.0.2.2:8000/` (the emulator's
special loopback alias to your PC's `localhost`) — this is already the default in
`net/ApiClient.java`, no app change needed for local testing.

```bash
# MongoDB must be running locally (or point backend/.env at MongoDB Atlas)
cd backend
pip install -r requirements.txt
python seed_questions.py      # once — seeds the question bank Quick Match draws from
python main.py                 # → http://localhost:8000
```

The AI-RAG service (`backend/ai-service`) and PDF-based room creation are **not**
wired into this Android build — the app only uses Quick Match / Join-by-code against
the random question bank, which needs just the main backend + MongoDB.

## Switching backends later (Render deployment)

**Profile tab → Server Connection URL.** Type the Render HTTPS URL and tap **Save URL**;
the app derives the matching `wss://` WebSocket URL automatically
(`net/ApiClient.getWsUrl()`). This is also how you'd point a real phone at your PC's
LAN IP instead of the emulator-only `10.0.2.2` address, e.g. `http://192.168.1.15:8000/`.

## What's deliberately not implemented

- **Competition / classroom mode** (`backend/competition.py`) — teacher-led sessions,
  polls, spectators. Out of scope for this client; it's a separate feature from the
  1v1 battle this app is built around.
- **PDF-upload AI question rooms** — the REST endpoint exists on the backend but this
  client doesn't expose a file picker for it (kept the mobile scope to Quick Match +
  Join-by-code, which is the actual 1v1 experience).
