import itertools
import os

from locust import HttpUser, between, task
from locust.exception import StopUser


PASSWORD = os.environ.get("LOCUST_PASSWORD", "LoadTest123!")

DEPARTMENT_ID = "DPTGc2dP2aXPD"

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
            name="AUTH | login",
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

    # =================================================
    # OLD FRONTEND PATTERN
    # =================================================

    @task(3)
    def department_light_bundle(self):
        self.client.get(
            f"/sites/departments/{DEPARTMENT_ID}/users-light/",
            name="OLD OVERVIEW | users-light",
        )

        self.client.get(
            f"/sites/departments/{DEPARTMENT_ID}/locations-light/",
            name="OLD OVERVIEW | locations-light",
        )

        self.client.get(
            f"/sites/departments/{DEPARTMENT_ID}/equipment-light/",
            name="OLD OVERVIEW | equipment-light",
        )

        self.client.get(
            f"/sites/departments/{DEPARTMENT_ID}/consumables-light/",
            name="OLD OVERVIEW | consumables-light",
        )

        self.client.get(
            f"/sites/departments/{DEPARTMENT_ID}/accessories-light/",
            name="OLD OVERVIEW | accessories-light",
        )

    # =================================================
    # NEW AGGREGATE PATTERN
    # =================================================

    @task(3)
    def department_overview_assets(self):
        self.client.get(
            f"/sites/departments/{DEPARTMENT_ID}/overview-assets/",
            name="NEW OVERVIEW | aggregate-assets",
        )

    # =================================================
    # BASELINE TRAFFIC
    # =================================================

    # @task(2)
    # def rooms_list(self):
    #     self.client.get(
    #         "/sites/rooms/",
    #         name="BASELINE | rooms-list",
    #     )

    # @task(2)
    # def equipment_list(self):
    #     self.client.get(
    #         "/assets/equipment/",
    #         name="BASELINE | equipment-list",
    #     )

    # @task(1)
    # def dashboard(self):
    #     self.client.get(
    #         "/analytics/health-check/health-overview/",
    #         name="BASELINE | analytics-dashboard",
    #     )