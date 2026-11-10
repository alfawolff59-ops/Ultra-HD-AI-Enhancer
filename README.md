# Ultra HD AI Enhancer — Android + AI Server

Turkish Android photo enhancer proof of concept. Android Java app sends an image to a Python FastAPI server, which calls Replicate's `nightmareai/real-esrgan` model. The server returns the improved PNG, which can be saved to Android's gallery.

## Requirements
- Android Studio with Android SDK 35, JDK 17 and internet access
- A hosted server with HTTPS (e.g. your own VPS/cloud service)
- A Replicate account and API token (paid usage may apply)

## 1. Run the server
```bash
cd server
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
export REPLICATE_API_TOKEN='YOUR_TOKEN'  # Windows PowerShell: $env:REPLICATE_API_TOKEN='YOUR_TOKEN'
uvicorn main:app --host 0.0.0.0 --port 8000
```
Deploy behind HTTPS. Set the API token as a secret environment variable on the server; NEVER put it in the Android app. Test: `GET https://your-server.example/health`.

## 2. Configure Android
Open the `android` folder in Android Studio. Add the following line to **android/gradle.properties** (or use `-PSERVER_URL=...` in Gradle invocation):
```properties
SERVER_URL=https://your-server.example/
```
Sync Gradle. Select **Build > Build APK(s)**. APK is generated at `android/app/build/outputs/apk/debug/app-debug.apk` once build succeeds. Install it on your Android phone. The app requires a reachable HTTPS backend.

## 3. Use
Choose a photo, select 2x or 4x, optionally enable face enhancement, tap enhance, and save the resulting PNG to `Pictures/Ultra HD AI Enhancer`.

## Important limitations
- This repository contains **source code, not a prebuilt APK**. The Android build was not executed in this environment.
- The AI server is not deployed; you must configure hosting and a valid Replicate API token.
- This is an MVP. For a public launch add authentication, rate limits, usage quotas, monitoring, abuse prevention, privacy policy, and a data-retention policy.
- Upload limit: 12 MB; input pixel limit: 20 MP. Larger outputs can consume significant device memory.
- The 2x/4x options increase dimensions; they do not guarantee actual recovered detail, 4K, or 8K resolution. The result depends on the source image.
- Uploaded photos are sent to your server and the third-party AI provider. Review the provider's data-handling terms before use.
- Model API input/output schemas can change. Confirm `nightmareai/real-esrgan` availability and its current API contract before production deployment.

## Phone-only GitHub Actions build
Upload the *contents* of this `UltraHDAIEnhancer` directory to the root of a GitHub repository (including `.github/workflows/build-apk.yml`). In GitHub, open **Actions > Android APK Derle > Run workflow**. Once successful, download `UltraHDAIEnhancer-debug-apk` from the workflow run's **Artifacts** section and extract the APK. GitHub's web interface may not make uploading a directory easy; use a phone Git client or upload files preserving folder paths. You can optionally add a repository Actions secret `SERVER_URL` with the HTTPS address of your deployed backend. This builds the Android client only; it does not host the AI server. The build has not been executed here.
