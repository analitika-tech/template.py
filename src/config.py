from pydantic_settings import BaseSettings, SettingsConfigDict

model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__")


class EmailSettings(BaseSettings):
    password: str
    sender: str
    server: str
    port: int


class GoogleSigninSettings(BaseSettings):
    id: str
    idp: str
    redirect_uri: str
    client_id: str
    client_secret: str


class S3(BaseSettings):
    access_key_id: str
    secret_access_key: str
    region: str
    bucket: str


class Settings(BaseSettings):
    google_mobile: GoogleSigninSettings

    postgress_connection_string: str

    access_token_lifetime: int  # seconds
    access_token_secret: str
    access_token_algorithm: str

    refresh_token_lifetime: int  # seconds
    refresh_token_secret: str
    refresh_token_algorithm: str

    confirm_email_token_lifetime: int  # hours
    confirm_email_token_secret: str
    confirm_email_token_algorithm: str

    environment: str

    apple_jwks_uri: str = "https://appleid.apple.com/auth/keys"
    apple_token_uri: str = "https://appleid.apple.com/auth/token"
    apple_revoke_uri: str = "https://appleid.apple.com/auth/revoke"
    apple_login_cert_base64: str
    apple_client_id: str
    apple_client_id_web: str
    apple_team_id: str
    apple_key_id: str
    apple_redirect_url: str

    email_settings: EmailSettings

    s3: S3

    model_config = model_config


settings = Settings()
