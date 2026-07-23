from alibabacloud_credentials.provider import OIDCRoleArnCredentialsProvider, RamRoleArnCredentialsProvider

from aliyun_exporter.credential import build_credential_client


def test_build_credential_client_oidc_single_hop():
    client = build_credential_client({
        'type': 'oidc_role_arn',
        'role_arn': 'acs:ram::111:role/local',
        'oidc_provider_arn': 'acs:ram::111:oidc-provider/x',
        'oidc_token_file_path': '/tmp/token',
    })
    assert client.cloud_credential.type_name == 'oidc_role_arn'
    assert isinstance(client.cloud_credential.provider, OIDCRoleArnCredentialsProvider)


def test_build_credential_client_oidc_chained_cross_account():
    # cross-account access: target role trusts our account's root/roles
    # rather than our OIDC provider directly, so we chain: OIDC -> local
    # role -> remote role.
    client = build_credential_client({
        'type': 'oidc_role_arn',
        'role_arn': 'acs:ram::111:role/local',
        'oidc_provider_arn': 'acs:ram::111:oidc-provider/x',
        'oidc_token_file_path': '/tmp/token',
        'assume_role_arn': 'acs:ram::222:role/remote',
    })
    assert client.cloud_credential.type_name == 'ram_role_arn'
    assert isinstance(client.cloud_credential.provider, RamRoleArnCredentialsProvider)
    assert client.cloud_credential.provider._role_arn == 'acs:ram::222:role/remote'
    assert isinstance(client.cloud_credential.provider._credentials_provider, OIDCRoleArnCredentialsProvider)
