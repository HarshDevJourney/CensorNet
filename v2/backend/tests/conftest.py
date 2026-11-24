import os

# throw-away stores so tests never touch real data: Redis DB 15 and the 'censor_test' Postgres database
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/15")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://censor:censor@127.0.0.1:5432/censor_test")
