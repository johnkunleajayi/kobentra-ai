from alembic import context
from sqlalchemy.engine import make_url

from app.assessments import models as assessment_models  # noqa: F401
from app.config import Settings
from app.database import database_engine
from app.models import Base
from app.qualification import models as qualification_models  # noqa: F401

settings = Settings()
# Never put the credential-bearing URL into Alembic's interpolated config/logs.
url = make_url(settings.database_url.get_secret_value())
batch = url.get_backend_name() == "sqlite"
if context.is_offline_mode():
    context.configure(
        url=url, target_metadata=Base.metadata, literal_binds=True, render_as_batch=batch
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = database_engine(settings)
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection, target_metadata=Base.metadata, render_as_batch=batch
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()
