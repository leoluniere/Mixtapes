"""
Standalone YouTube Music login helper for Windows.
Uses Edge WebView2 via pywebview to capture auth cookies,
then writes them to a JSON file for Mixtapes to import.

Usage:
  login_helper.exe [--output PATH]

Writes captured headers JSON to:
  --output PATH   (default: %LOCALAPPDATA%/Mixtapes/login_headers.json)
"""

import json
import os
import sys
import time
import webview


OUTPUT_PATH = None


def get_default_output():
    appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    d = os.path.join(appdata, "Mixtapes")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "login_headers.json")


def check_cookies(window):
    """Runs in pywebview's background thread. Polls for auth cookies."""
    for attempt in range(120):
        time.sleep(1)
        try:
            url = window.get_current_url() or ""
        except Exception:
            continue

        if "music.youtube.com" not in url or "accounts.google.com" in url:
            continue

        print(f"[attempt {attempt}] On YouTube Music: {url}")

        # Strategy 1: pywebview get_cookies() — gets all cookies including HttpOnly
        try:
            cookies = window.get_cookies()
            print(f"  get_cookies() returned {len(cookies)} cookies")

            cookie_strs = []
            has_sapisid = False

            for cookie in cookies:
                # pywebview returns http.cookies.SimpleCookie objects
                # each SimpleCookie is a dict of {name: Morsel}
                for name, morsel in cookie.items():
                    value = morsel.coded_value
                    if name and value:
                        cookie_strs.append(f"{name}={value}")
                        if name in ("SAPISID", "__Secure-3PAPISID"):
                            has_sapisid = True
                            print(f"  Found auth cookie: {name}")

            if has_sapisid:
                _save_and_close(window, "; ".join(cookie_strs))
                return

        except Exception as e:
            print(f"  get_cookies() error: {e}")

        # Strategy 2: document.cookie — gets non-HttpOnly cookies (SAPISID is accessible)
        try:
            js_cookies = window.evaluate_js("document.cookie")
            if js_cookies:
                print(f"  document.cookie length: {len(js_cookies)}")
                if "SAPISID" in js_cookies:
                    print("  Found SAPISID via document.cookie!")
                    _save_and_close(window, js_cookies)
                    return
        except Exception as e:
            print(f"  evaluate_js error: {e}")

    print("Timed out waiting for auth cookies (120s).")


def _save_and_close(window, cookie_string):
    # Get user agent, with fallback
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    try:
        result = window.evaluate_js("navigator.userAgent")
        if result:
            ua = result
    except Exception:
        pass

    headers = {
        "Cookie": cookie_string,
        "User-Agent": ua,
    }

    output = OUTPUT_PATH or get_default_output()
    with open(output, "w") as f:
        json.dump(headers, f)

    print(f"Login successful! Headers saved to: {output}")
    window.destroy()


def main():
    global OUTPUT_PATH

    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--output" and i + 1 < len(args):
            OUTPUT_PATH = args[i + 1]

    window = webview.create_window(
        "Mixtapes - Login to YouTube Music",
        "https://accounts.google.com/ServiceLogin?ltmpl=music&service=youtube"
        "&uilel=3&passive=true"
        "&continue=https%3A%2F%2Fmusic.youtube.com%2Flibrary",
        width=700,
        height=600,
    )

    webview.start(func=check_cookies, args=(window,), private_mode=True)

    output = OUTPUT_PATH or get_default_output()
    if not os.path.exists(output):
        print("Login was cancelled or failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
