# myFlyItalyAdsb 🛩️

myFlyItalyAdsb is a lightweight web application designed to allow each user to visualize real-time flight data from their individual receiver. It integrates directly with `readsb`, `mlat-server` and provides a real-time flight table similar to VRS. Moreover, it offers comprehensive reporting features and the flexibility to modify aircraft details.

![index screenshot](index_screenshot.png)

## Features 🌟

- **Real-time Map**: Visualize aircraft data without transmitting each `aircraft.json` to the server. Direct integration with `readsb`. Html is from `tar1090`
- **Live Flight Table**: A detailed table displaying all real-time flights, akin to VRS.
- **Database & Reporting**: Get insights from historical data. Reports can be filtered based on the receiver.
- **Aircraft Modification**: Edit any aircraft field effortlessly, including tagging an aircraft as military.
- **MLAT Connections Map**: Visualize the MLAT connections between the user's receiver and others on an interactive map, showcasing the network synergy.

## Access 🚪

Access is straightforward:
1. Direct access via the IP from which data is transmitted.
2. Through a unique UUID in /login page.

## Prerequisites 🛠️

- An instance of `mlat-server`.
- A properly compiled version of `readsb`:
  - Ensure it prints UUIDs in `aircraft.json`.
  - Should be executed with `--ingest` and `--net-receiver-id` flags.

## Installation ⚙️

_in progress..._

## Contribution ✨

Contributions are always welcome! If you wish to contribute, please open an issue or send a pull request.

## License 📄

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## Acknowledgments 👏

- Special thanks to wiedehopf and all open-source libraries and tools used in this project.
- Icons used are sourced from [IconFinder](https://www.iconfinder.com/).

---

If you encounter any issues or have suggestions, please open an issue on GitHub.
