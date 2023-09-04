import aiohttp

GRAFANA_URL = "http://your_grafana_url:3000"
API_KEY = "YOUR_API_KEY"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


def create_datasource_for_receiver(receiver_name, session):
    receiver = get_receiver_info(receiver_name)

    data = {
        "name": receiver_name,
        "type": "postgresql",
        "url": f"http://your_data_source_url/{receiver_name}",
        "access": "proxy",

    }

    async with session.post(f"{GRAFANA_URL}/api/dashboards/db", headers=headers, json=data) as response:
        if response.status == 200:
            print(f"Data source for {receiver_name} created!")
        else:
            print(
                f"Error creating data source for {receiver_name}. Status Code: {response.status}. Message: {response.text}")


async def create_dashboard_for_receiver(receiver_name, session):

    dashboard_data = {
        "dashboard": {
            "title": f"Dashboard for {receiver_name}",
            "panels": [
            ]
        },
        "folderId": 0,  # Modifica se vuoi mettere la dashboard in una specifica cartella
        "overwrite": False
    }
    async with session.post(f"{GRAFANA_URL}/api/dashboards/db", headers=headers, json=dashboard_data) as response:
        if response.status == 200:
            print(f"Dashboard for {receiver_name} created!")
        else:
            print(
                f"Error creating dashboard for {receiver_name}. Status Code: {response.status}. Message: {response.text}")
