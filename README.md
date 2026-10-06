# F!X BAN — Internet Edition

This version is **not LAN-based**. The Tkinter desktop client communicates with a Python Flask API over HTTP/HTTPS, so users can connect from different networks.

## Architecture

- `client.py` — Python/Tkinter desktop GUI.
- `server.py` — Python Flask internet API.
- SQLite — shared database on the server.
- HTTPS — should be provided by your hosting platform (Render, Railway, VPS reverse proxy, etc.).

No JavaScript frontend is required.

## Local server test

Install:

    pip install -r requirements.txt

Start:

    python server.py

The API will listen on port 8000.

Then run:

    python client.py

Enter:

    http://127.0.0.1:8000

For an internet deployment, replace that with your HTTPS server URL.

## Default administrator

Username: `admin`
Password: `Admin@123`

After logging in, create your own admin account from `USER ACCESS`. Change/remove the default account for a real deployment.

## Internet deployment

A simple option is a Python web host such as Render.

1. Put `server.py`, `requirements.txt`, and `render.yaml` in a Git repository.
2. Create a web service from the repository.
3. The service uses:
   `gunicorn server:APP`
4. The platform gives you an HTTPS URL.
5. Put that HTTPS URL into `client.py` when users log in.

### Database note

The included SQLite database is fine for a small private project. On many cloud platforms, the normal filesystem can be temporary. For important production data, use a persistent disk or move the database to PostgreSQL.

## Security

- Change the default admin password.
- Set a strong `FIXBAN_SECRET` environment variable.
- Use HTTPS in production.
- Do not expose SQLite or database files to clients.
- For a larger production system, add rate limiting, audit logs, password reset, 2FA, and PostgreSQL.

## Permissions

`admin`:
- Add person
- Edit person
- Delete person
- Create users
- Make users admins/viewers
- Delete user accounts

`user`:
- View the people directory
- Open person profiles
- No editing or account-management access

When an admin changes the shared database, another client sees the updated information the next time it refreshes. The current implementation intentionally uses normal HTTP API calls rather than a persistent LAN socket.
