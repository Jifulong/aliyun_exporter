from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_credentials.models import Config as CredentialConfig
from alibabacloud_tea_openapi.models import Config as OpenApiConfig


def build_credential_client(cfg: dict) -> CredentialClient:
    access_key_id = cfg.get('access_key_id')
    access_key_secret = cfg.get('access_key_secret')
    if access_key_id and access_key_secret:
        return CredentialClient(CredentialConfig(
            type='access_key',
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
        ))

    cred_type = cfg.get('type')
    if cred_type == 'oidc_role_arn':
        return CredentialClient(CredentialConfig(
            type='oidc_role_arn',
            role_arn=cfg.get('role_arn'),
            oidc_provider_arn=cfg.get('oidc_provider_arn'),
            oidc_token_file_path=cfg.get('oidc_token_file_path'),
            role_session_name=cfg.get('role_session_name'),
        ))

    # No explicit AK/SK configured: fall back to the default credential chain,
    # which auto-detects env AK/SK, then RRSA/OIDC env vars (injected by ACK's
    # RRSA webhook), then ECS RAM role, etc.
    return CredentialClient()


def build_openapi_config(region_id: str, credential_client: CredentialClient) -> OpenApiConfig:
    return OpenApiConfig(credential=credential_client, region_id=region_id)
