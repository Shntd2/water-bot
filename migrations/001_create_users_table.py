from app.config.database import engine, Base
from app.models.user_model import User


def upgrade():
    Base.metadata.create_all(bind=engine)


def downgrade():
    User.__table__.drop(bind=engine, checkfirst=True)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "down":
        downgrade()
    else:
        upgrade()
