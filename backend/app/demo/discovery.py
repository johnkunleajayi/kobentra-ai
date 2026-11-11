"""Prepare fictional businesses in an initialized, isolated SQLite DB after normal login."""

import argparse
import json
from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from ..business.schemas import BusinessRegistration
from ..business.service import register_business
from ..config import Settings
from ..database import database_engine
from ..market_preferences.schemas import PreferenceInput, PreferencesInput
from ..market_preferences.service import save
from ..security import Principal

DEMO_ROOT = Path(__file__).resolve().parents[3] / "work" / "partner-discovery"
SCENARIO = (
    (
        {
            "name": "Fictional Demo — Lagos Pantry Foods",
            "sector": "Packaged food",
            "country": "Nigeria",
            "goal": "Fictional Lagos packaged-food producer seeking Ghanaian distributors.",
        },
        "Ghana",
        "Distributor",
    ),
    (
        {
            "name": "Fictional Demo — Accra Distribution",
            "sector": "Packaged food",
            "country": "Ghana",
            "goal": "Fictional Accra distributor serving Ghana, seeking food manufacturers as suppliers.",
        },
        "Nigeria",
        "Manufacturer",
    ),
)


def local_database(url):
    parsed = make_url(url)
    if (
        parsed.drivername != "sqlite+pysqlite"
        or parsed.host
        or parsed.username
        or parsed.password
        or parsed.query
        or not parsed.database
    ):
        raise ValueError("Only an isolated file-backed SQLite demo database is allowed")
    path = Path(parsed.database).resolve()
    if not path.is_relative_to(DEMO_ROOT.resolve()) or path == DEMO_ROOT.resolve():
        raise ValueError("Database must be inside D:/kobentra-ai/work/partner-discovery")
    if not path.is_file():
        raise ValueError("Initialize the isolated demo database and sign in normally first")
    return parsed.render_as_string(hide_password=False)


def prepare(url, owner_user_id, approve_publication=False):
    if not approve_publication:
        raise ValueError(
            "Explicit fictional publication approval is required before preparing data"
        )
    engine = database_engine(Settings(_env_file=None, database_url=local_database(url)))
    ids = []
    try:
        for values, country, partner_type in SCENARIO:
            with Session(engine) as db:
                business, _ = register_business(db, owner_user_id, BusinessRegistration(**values))
                ids.append(business.organization_id)
            with Session(engine) as db:
                save(
                    db,
                    Principal(owner_user_id),
                    business.organization_id,
                    PreferencesInput(
                        preferences=[PreferenceInput(country=country, partner_type=partner_type)]
                    ),
                )
    finally:
        engine.dispose()
    return {
        "fictional": True,
        "publication_approved": True,
        "business_ids": ids,
        "matching_discovery_business_ids": ids,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
    parser.add_argument(
        "--owner-user-id", required=True, help="Existing normally authenticated local user ID"
    )
    parser.add_argument("--approve-fictional-publication", action="store_true")
    args = parser.parse_args()
    try:
        result = prepare(args.database_url, args.owner_user_id, args.approve_fictional_publication)
    except Exception:
        parser.exit(
            1,
            "Demo preparation refused or incomplete. Check isolated database, user and approval. No remote calls are supported.\n",
        )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
