"""Reset the running demo over HTTP (make demo-reset): logs in as admin.demo, POST /demo/reset."""

import httpx

from app.core.settings import get_settings


def main() -> None:
    settings = get_settings()
    with httpx.Client(base_url=settings.api_base_url, timeout=60) as client:
        login = client.post(
            "/auth/login", json={"username": "admin.demo", "password": settings.seed_password}
        )
        login.raise_for_status()
        token = login.json()["access_token"]
        r = client.post("/demo/reset", headers={"Authorization": f"Bearer {token}"})
        r.raise_for_status()
        body = r.json()
    print(  # noqa: T201 (CLI output)
        f"Demo reset: {body['customers']} synthetic customers (seed {body['seed']}) in "
        f"{body['seconds']}s; clock at {body['sim_now']}"
    )


if __name__ == "__main__":
    main()
