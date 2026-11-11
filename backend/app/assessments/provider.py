from urllib.parse import parse_qs, urlparse

from fastapi import HTTPException

from ..config import Settings
from .constants import TITLE
from .schemas import ProviderConfiguration


def configuration(settings: Settings) -> ProviderConfiguration:
    if settings.salesforce_dispatch_enabled:
        return ProviderConfiguration(
            title=TITLE,
            configured=bool(
                settings.salesforce_instance_url
                and settings.salesforce_client_id
                and settings.salesforce_client_secret
            ),
            synchronization="salesforce_flow",
        )
    return ProviderConfiguration(title=TITLE, configured=bool(settings.surveyvista_launch_url))


def configured_survey(settings: Settings) -> tuple[str, str, str]:
    url = settings.surveyvista_launch_url
    if not url:
        raise HTTPException(503, "SurveyVista launch is not configured")
    query = parse_qs(urlparse(url).query)
    # These identify the configured launch target, not a unique respondent/result.
    return url, query["recordId"][0], query["logicalId"][0]
