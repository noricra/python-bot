"""
Configure CORS sur Backblaze B2 avec l'API Native B2
Permet les uploads directs depuis la Telegram Mini App
"""
import requests
import logging
import base64
from app.core import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_b2_auth_token():
    """Authenticate with B2 and get authorization token"""
    # Clean credentials
    key_id = settings.B2_KEY_ID.split('#')[0] if settings.B2_KEY_ID else None
    app_key = settings.B2_APPLICATION_KEY.split('#')[0] if settings.B2_APPLICATION_KEY else None

    # Encode credentials
    auth_string = f"{key_id}:{app_key}"
    auth_b64 = base64.b64encode(auth_string.encode()).decode()

    # Authenticate
    response = requests.get(
        'https://api.backblazeb2.com/b2api/v2/b2_authorize_account',
        headers={'Authorization': f'Basic {auth_b64}'}
    )

    if response.status_code != 200:
        logger.error(f"❌ Auth failed: {response.text}")
        return None, None, None

    data = response.json()
    return data['authorizationToken'], data['apiUrl'], data['accountId']

def get_bucket_id(auth_token, api_url, account_id, bucket_name):
    """Get bucket ID from bucket name"""
    response = requests.post(
        f"{api_url}/b2api/v2/b2_list_buckets",
        headers={'Authorization': auth_token},
        json={
            'accountId': account_id,
            'bucketName': bucket_name
        }
    )

    if response.status_code != 200:
        logger.error(f"❌ Failed to list buckets: {response.text}")
        return None

    data = response.json()
    buckets = data.get('buckets', [])

    if not buckets:
        logger.error(f"❌ Bucket '{bucket_name}' not found")
        return None

    return buckets[0]['bucketId']

def configure_cors(auth_token, api_url, account_id, bucket_id):
    """Configure CORS rules on the bucket"""

    cors_rules = [
        {
            "corsRuleName": "telegram-miniapp-upload",
            "allowedOrigins": [
                "https://python-bot-production-4f9a.up.railway.app",  # Miniapp Railway
                "https://uzeur.com",                                   # Site vitrine (futur)
                "https://www.uzeur.com"                               # Variante www
            ],
            "allowedOperations": [
                "b2_upload_file",
                "b2_upload_part",
                "b2_download_file_by_id",
                "b2_download_file_by_name"
            ],
            "allowedHeaders": ["*"],
            "exposeHeaders": ["x-bz-content-sha1", "x-bz-file-id", "x-bz-file-name"],
            "maxAgeSeconds": 3600
        }
    ]

    response = requests.post(
        f"{api_url}/b2api/v2/b2_update_bucket",
        headers={'Authorization': auth_token},
        json={
            'accountId': account_id,
            'bucketId': bucket_id,
            'corsRules': cors_rules
        }
    )

    if response.status_code != 200:
        logger.error(f"❌ Failed to update CORS: {response.text}")
        return False

    logger.info(f"✅ CORS configured successfully!")
    logger.info(f"📋 Rules: {cors_rules}")
    return True

def main():
    logger.info("🔧 Configuring CORS on Backblaze B2 (Native API)...")
    logger.info(f"📦 Bucket: {settings.B2_BUCKET_NAME}")

    # Step 1: Authenticate
    logger.info("1️⃣ Authenticating...")
    auth_token, api_url, account_id = get_b2_auth_token()

    if not auth_token:
        logger.error("❌ Authentication failed!")
        return False

    logger.info(f"✅ Authenticated! Account: {account_id}")

    # Step 2: Get Bucket ID
    logger.info("2️⃣ Getting bucket ID...")
    bucket_id = get_bucket_id(auth_token, api_url, account_id, settings.B2_BUCKET_NAME)

    if not bucket_id:
        logger.error("❌ Failed to get bucket ID!")
        return False

    logger.info(f"✅ Bucket ID: {bucket_id}")

    # Step 3: Configure CORS
    logger.info("3️⃣ Configuring CORS...")
    success = configure_cors(auth_token, api_url, account_id, bucket_id)

    if success:
        logger.info("\n✅ CORS configuration completed!")
        logger.info("✅ Direct uploads from Telegram Mini App are now allowed")
        logger.info("\n⚠️ Note: Il faut maintenant utiliser l'API B2 native pour les uploads,")
        logger.info("   pas les presigned URLs S3. Je vais modifier le code...")
    else:
        logger.error("\n❌ CORS configuration failed!")

    return success

if __name__ == "__main__":
    main()
