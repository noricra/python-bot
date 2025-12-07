"""
Script pour configurer CORS sur le bucket Backblaze B2
Permet les uploads directs depuis la Telegram Mini App
"""
import boto3
import logging
from app.core import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def configure_b2_cors():
    """Configure CORS rules on B2 bucket to allow direct uploads from Telegram Mini App"""

    if not settings.B2_KEY_ID or not settings.B2_APPLICATION_KEY:
        logger.error("❌ B2 credentials not configured")
        return False

    try:
        # Clean credentials (remove anything after #)
        key_id = settings.B2_KEY_ID.split('#')[0] if settings.B2_KEY_ID else None
        app_key = settings.B2_APPLICATION_KEY.split('#')[0] if settings.B2_APPLICATION_KEY else None

        logger.info(f"Using Key ID: {key_id[:10]}...")

        # Initialize B2 client
        s3_client = boto3.client(
            's3',
            endpoint_url=settings.B2_ENDPOINT,
            aws_access_key_id=key_id,
            aws_secret_access_key=app_key
        )

        # Define CORS configuration
        cors_configuration = {
            'CORSRules': [
                {
                    'AllowedOrigins': [
                        'https://web.telegram.org',
                        'https://oauth.telegram.org',
                        '*'  # Pour développement - à restreindre en production
                    ],
                    'AllowedMethods': ['GET', 'PUT', 'POST', 'DELETE', 'HEAD'],
                    'AllowedHeaders': [
                        'Content-Type',
                        'Content-Length',
                        'Authorization',
                        'x-amz-*',
                        '*'
                    ],
                    'ExposeHeaders': [
                        'ETag',
                        'Content-Length',
                        'x-amz-request-id'
                    ],
                    'MaxAgeSeconds': 3600
                }
            ]
        }

        # Apply CORS configuration
        s3_client.put_bucket_cors(
            Bucket=settings.B2_BUCKET_NAME,
            CORSConfiguration=cors_configuration
        )

        logger.info(f"✅ CORS configured successfully on bucket: {settings.B2_BUCKET_NAME}")

        # Verify configuration
        response = s3_client.get_bucket_cors(Bucket=settings.B2_BUCKET_NAME)
        logger.info(f"📋 Current CORS rules: {response['CORSRules']}")

        return True

    except Exception as e:
        logger.error(f"❌ Failed to configure CORS: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Configuring CORS on Backblaze B2 bucket...")
    print(f"📦 Bucket: {settings.B2_BUCKET_NAME}")
    print(f"🌐 Endpoint: {settings.B2_ENDPOINT}")
    print()

    success = configure_b2_cors()

    if success:
        print("\n✅ CORS configuration completed!")
        print("✅ Direct uploads from Telegram Mini App are now allowed")
    else:
        print("\n❌ CORS configuration failed!")
        print("Please check your B2 credentials and bucket permissions")
