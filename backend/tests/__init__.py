import os
os.environ.setdefault("ADPLATFORM_ENVIRONMENT", "test")
os.environ.setdefault("ADPLATFORM_JWT_SECRET", "test-only-" + "x" * 40)
os.environ.setdefault("ADPLATFORM_DATABASE_URL", "sqlite+aiosqlite:///:memory:")