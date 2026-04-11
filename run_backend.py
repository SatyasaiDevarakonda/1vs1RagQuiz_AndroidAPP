"""
Unified Backend Launcher
Runs both the main backend (port 8000) and AI service (port 8001)
in a single terminal. Press Ctrl+C to stop both.

Usage:
    python run_backend.py
"""
import subprocess
import sys
import os
import signal


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(root, "backend")
    ai_service_dir = os.path.join(root, "backend", "ai-service")

    print("=" * 60)
    print("  1v1 RAG Quiz - Backend Launcher")
    print("=" * 60)
    print(f"  Backend API:   http://localhost:8000")
    print(f"  AI Service:    http://localhost:8001")
    print(f"  API Docs:      http://localhost:8000/docs")
    print(f"  Frontend:      Run 'cd frontend && npm run dev' in another terminal")
    print("=" * 60)
    print()

    # Start backend server
    backend_proc = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=backend_dir,
    )

    # Start AI service
    ai_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"],
        cwd=ai_service_dir,
    )

    def shutdown(signum=None, frame=None):
        print("\nShutting down services...")
        backend_proc.terminate()
        ai_proc.terminate()
        backend_proc.wait()
        ai_proc.wait()
        print("All services stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        # Wait for either process to exit
        while True:
            backend_rc = backend_proc.poll()
            ai_rc = ai_proc.poll()

            if backend_rc is not None:
                print(f"Backend exited with code {backend_rc}")
                ai_proc.terminate()
                break
            if ai_rc is not None:
                print(f"AI Service exited with code {ai_rc}")
                backend_proc.terminate()
                break

            # Sleep briefly to avoid busy-waiting
            import time
            time.sleep(0.5)
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
