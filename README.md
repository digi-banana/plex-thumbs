# Plex Thumbs

The React frontend for managing your local Plex BIF synchronization.

## Setup

1.  **Install dependencies**:
    ```bash
    npm install
    ```

2.  **Run**:
    ```bash
    npm start
    ```

## Note on Backend Integration
The UI is configured to communicate with the Plex BIF Backend at `http://localhost:8000`. Ensure that the [Plex BIF Server repository](https://github.com/your-username/plex-bif-server) is running on the same host or update the API calls in `src/App.js`.
