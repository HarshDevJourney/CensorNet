import os

# use a throw-away Redis DB so tests never touch real data (DB 15)
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/15")
