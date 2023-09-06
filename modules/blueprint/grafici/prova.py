from utility.model import Receiver

GRAFANA_URL = "http://localhost:3000"
API_KEY = "sa-prova1-87f3ea35-9838-4f7d-b092-282a5610671a"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


async def create_datasource_for_receiver(session_http, ricevitore: Receiver):
    data = {
        "name": ricevitore.name,
        "type": "postgresql",
        "url": f"http://localhost/{ricevitore.name}",
        "access": "proxy",
    }

    async with session_http.post(f"{GRAFANA_URL}/api/datasources", headers=headers, json=data) as response:
        if response.status == 200:
            print(f"Data source for {ricevitore.name} created!")
        else:
            resp_text = await response.text()
            print(
                f"Error creating data source for {ricevitore.name}. Status Code: {response.status}. Message: {resp_text}")


async def create_dashboard_for_receiver(session_http, ricevitore: Receiver):
    dashboard_data = {
        "dashboard": {
            "title": f"Dashboard for {ricevitore.name}",
            "panels": [
            ]
        },
        "folderId": 0,
        "overwrite": False
    }
    async with session_http.post(f"{GRAFANA_URL}/api/dashboards/db", headers=headers, json=dashboard_data) as response:
        if response.status == 200:
            print(f"Dashboard for {ricevitore.name} created!")
        else:
            print(
                f"Error creating dashboard for {ricevitore.name}. Status Code: {response.status}. Message: {response.text}")
