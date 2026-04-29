import itertools
import os

from locust import HttpUser, between, task
from locust.exception import StopUser


PASSWORD = os.environ.get("LOCUST_PASSWORD", "LoadTest123!")

USERS = [
    f"loadtest{i:02d}@example.com"
    for i in range(1, 31)
]

USER_POOL = itertools.cycle(USERS)


class ARMSUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.email = next(USER_POOL)

        response = self.client.post(
            "/api/login/",
            json={
                "email": self.email,
                "password": PASSWORD,
            },
            name="login"
        )

        if response.status_code != 200:
            print(f"LOGIN FAILED: {self.email} -> {response.status_code}")
            raise StopUser()

        data = response.json()
        token = data.get("access")

        if not token:
            print(f"NO TOKEN: {self.email}")
            raise StopUser()

        self.client.headers.update({
            "Authorization": f"Bearer {token}"
        })

    @task(4)
    def rooms_list(self):
        self.client.get("/sites/rooms/", name="sites: rooms list")

    @task(3)
    def equipment_list(self):
        self.client.get("/assets/equipment/", name="assets: equipment list")

    @task(2)
    def department_list(self):
        self.client.get("/sites/departments/", name="sites: departments list")

    @task(1)
    def dashboard(self):
        self.client.get(
            "/analytics/health-check/health-overview/",
            name="analytics: health overview",
        )