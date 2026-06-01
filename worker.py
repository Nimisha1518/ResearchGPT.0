from redis import Redis
from rq import Worker

from app import create_app

app = create_app()

if __name__ == "__main__":
    redis_url = app.config["REDIS_URL"]
    if not redis_url:
        raise RuntimeError("REDIS_URL is required to start the worker.")

    with app.app_context():
        worker = Worker(["default"], connection=Redis.from_url(redis_url))
        worker.work()
