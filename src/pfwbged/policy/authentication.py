from pas.plugins.affinitic.providers.openidconnect import OpenIDConnect
from authomatic.providers.oauth2 import PROVIDER_ID_MAP


__all__ = ("AzureOIDC",)


class AzureOIDC(OpenIDConnect):

    provider_id = "azure"

    authorization_scope = [
        "openid",
        "email",
        "profile",
    ]

PROVIDER_ID_MAP.append(AzureOIDC)
