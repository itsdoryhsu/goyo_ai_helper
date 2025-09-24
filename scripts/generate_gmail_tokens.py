import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request as GoogleAuthRequest

# Define the necessary scopes for Gmail and Calendar
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',  # Read access to emails
    'https://www.googleapis.com/auth/gmail.modify',   # For changing labels
    'https://www.googleapis.com/auth/calendar'         # Full access to calendars
]

def generate_tokens(credentials_file_path: str, token_file_path: str):
    """
    Runs the OAuth2 flow to generate a token.json file with the required scopes.
    This script is intended for one-time manual execution.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    abs_credentials_path = os.path.join(project_root, credentials_file_path)
    abs_token_path = os.path.join(project_root, token_file_path)

    # Force re-authentication by deleting the old token file if it exists
    if os.path.exists(abs_token_path):
        print(f"Removing existing token file to force re-authentication: {abs_token_path}")
        os.remove(abs_token_path)

    # Run the authorization flow
    try:
        flow = InstalledAppFlow.from_client_secrets_file(abs_credentials_path, SCOPES)
        creds = flow.run_local_server(port=0)
        
        # Save the new credentials
        with open(abs_token_path, 'w') as token:
            token.write(creds.to_json())
        print(f"SUCCESS: New token.json with updated scopes has been saved to {abs_token_path}")
        print("You can now run the main application.")

    except FileNotFoundError:
        print(f"ERROR: Credentials file not found at {abs_credentials_path}")
        print("Please ensure the client secrets file is correctly placed.")
    except Exception as e:
        print(f"An unexpected error occurred during token generation: {e}")

if __name__ == '__main__':
    # 為您的第一個帳戶生成憑證 (例如 account1)
    print("--- 為第一個 Gmail 帳戶生成憑證 (例如 itsdoryhsu@gmail.com) ---")
    generate_tokens(
        credentials_file_path='config/gmail_accounts/itsdoryhsu/client_secret_116792515704-lls6d06586hid1ipnbdeqgk1sfqmc7as.apps.googleusercontent.com.json',
        token_file_path='config/gmail_accounts/itsdoryhsu/token.json'
    )