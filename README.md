# Thereal's DanceFlow

## Run the site and registration backend locally

1. Install Python 3.9 or newer.
2. In PowerShell, open this folder and run:

   ```powershell
   .\start-danceflow.ps1
   ```

3. Choose an organizer dashboard password of at least 12 characters when prompted.
4. Open `http://127.0.0.1:8000/` in your browser.
5. Select **Organizer dashboard** at the bottom of the homepage and enter the password you chose to see sign-ups.

Keep the PowerShell window open while using the site. Press Ctrl+C there to stop the server. Registrations are stored in `registrations.sqlite3` in this folder and remain available the next time the server starts.

## Registration data

The registration form saves the dancer's name, email, chosen dance category, optional other-category description, optional experience, and registration time. The organizer dashboard requires the password configured when starting the server. Dancer passwords are not requested or stored.

Back up `registrations.sqlite3` securely. It contains personal information. Do not share the database or expose the organizer password.

## Hosting online

The server can use a hosting provider's `PORT`, a persistent SQLite database path via `DANCEFLOW_DB`, and a non-local bind address via `DANCEFLOW_HOST` (for example, `0.0.0.0`). Set `DANCEFLOW_ADMIN_PASSWORD` to a long, unique secret in the host's private environment settings; never put it in HTML or commit it to source control. Keep the SQLite database on persistent storage.

The included server speaks plain HTTP. Do not expose it directly to the public internet: put it behind a trusted HTTPS reverse proxy and use a hosting provider that supports persistent storage. The dashboard uses HTTP Basic authentication, so HTTPS is required online to protect its password and registration data in transit. Configure backups and restrict access to the database and host logs.
