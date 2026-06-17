import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

print("=" * 60)
print("🔍 Google OAuth Final Check")
print("=" * 60)

client_id = settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY
client_secret = settings.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET

print(f"\n📋 Configuration:")
print(f"  Client ID: {client_id}")
print(f"  Client Secret: {'✅ SET' if client_secret else '❌ MISSING'}")
print(f"  Base URL: {settings.BASE_URL}")

# Check if FRONTEND_URL exists before printing
if hasattr(settings, 'FRONTEND_URL'):
    print(f"  Frontend URL: {settings.FRONTEND_URL}")
else:
    print("  Frontend URL: ⚠️ Not defined in settings.py")
    print("  → Add 'FRONTEND_URL = config('FRONTEND_URL')' to settings.py")

if client_id and client_secret:
    print("\n✅ Google OAuth is configured!")
    print("\n📌 Make sure these are in Google Cloud Console:")
    print("  • https://ettahospitalclone.vercel.app/auth/callback")
    print("  • https://ettahospitalclone.vercel.app/google-callback")
    print("  • https://hospitalback-clean-0fre.onrender.com/api/users/google-callback/")
else:
    print("\n❌ Missing credentials!")

print("\n" + "=" * 60)