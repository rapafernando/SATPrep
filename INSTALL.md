# Installing ScorePath on your server

This takes about 20 minutes. You need: your Ubuntu server (with Docker and Caddy already
running), your DuckDNS account, and this folder. Commands go in a terminal on the server
(SSH is fine). Lines starting with `#` are comments, not commands.

## 1. Get the project onto the server (from GitHub)

**One time, on your computer:** create an empty **private** repository on GitHub (for example
`scorepath`), then push this folder to it:

```bash
cd scorepath
git remote add origin git@github.com:YOURNAME/scorepath.git     # or the https:// address GitHub shows
git push -u origin main
```

**One time, on the server:** let the server read the private repository with a read-only key.
This is safer than a password or token, and GitHub never gives it write access.

```bash
ssh-keygen -t ed25519 -f ~/.ssh/scorepath_deploy -N "" -C "rapamedia scorepath"
cat ~/.ssh/scorepath_deploy.pub          # copy this whole line
```

On GitHub: the repository, **Settings**, **Deploy keys**, **Add deploy key**, paste the line,
leave "Allow write access" **unticked**. Then back on the server:

```bash
printf 'Host github-scorepath\n  HostName github.com\n  User git\n  IdentityFile ~/.ssh/scorepath_deploy\n  IdentitiesOnly yes\n' >> ~/.ssh/config
git clone git@github-scorepath:YOURNAME/scorepath.git
cd scorepath
```

(Prefer the zip? `scp scorepath.zip YOURUSER@YOUR_SERVER:~/`, then `unzip scorepath.zip -d scorepath`.
Updates then have to be copied by hand, so GitHub is easier.)

## 2. Create your settings file

```bash
cp .env.example .env
nano .env
```

Change these lines (the file explains each one):

| Setting | What to put |
| --- | --- |
| `ALLOWED_HOSTS` | `scorepath.YOURNAME.duckdns.org` (your new DuckDNS name, no `https://`) |
| `CSRF_TRUSTED_ORIGINS` | `https://scorepath.YOURNAME.duckdns.org` |
| `SECRET_KEY` | paste the output of `openssl rand -base64 48` |
| `POSTGRES_PASSWORD` | paste the output of `openssl rand -hex 24` |
| `DJANGO_SUPERUSER_USERNAME` / `_PASSWORD` | your admin login (pick a long password) |

Save with Ctrl+O, Enter, Ctrl+X. Then lock the file down: `chmod 600 .env`.

## 3. Start it

```bash
docker compose up -d --build
docker compose ps          # both services should say "running" / "healthy"
docker compose logs -f web # Ctrl+C to stop watching
```

The first start builds the image, creates the database, creates your admin account and
loads 24 sample questions. Quick check from the server itself:

```bash
curl http://127.0.0.1:8010/healthz     # prints {"status": "ok"}
```

## 4. Give it a web address

1. In your DuckDNS account, add a new domain, e.g. `scorepath`. Point it at the same
   public IP as your other names.
2. Add the new name to your DuckDNS updater (the script or cron job that keeps your IP
   current), the same way your existing names are listed.
3. Open your Caddyfile and paste the block from `deploy/Caddyfile.snippet`
   (change the name, keep everything else):

   ```bash
   sudo nano /etc/caddy/Caddyfile
   sudo caddy validate --config /etc/caddy/Caddyfile
   sudo systemctl reload caddy
   ```

   If your Caddy runs in Docker instead, add the block to that Caddyfile and reload it
   the way you do for your other sites. Inside a Caddy container, `127.0.0.1` means the
   container itself: use the server's LAN address (for example `192.168.1.50:8010`) and
   set `WEB_BIND=0.0.0.0` in `.env`, then `docker compose up -d`.
4. Caddy fetches the HTTPS certificate by itself on the first visit (needs your router's
   ports 80 and 443 forwarded to the server, which your other sites already use).
5. Open `https://scorepath.YOURNAME.duckdns.org` on your phone.

## 5. First steps as admin

1. Sign in at `/login/` with the admin account from `.env`.
2. Open **Admin** in the top menu (or go to `/console/`).
3. Share the link with your daughter and her friends. They tap **Create account**.
4. Their accounts wait as *pending*; open **Approvals** and press **Approve**. Until then
   they see "waiting for approval" when they try to sign in.
5. For a parent to see a child's progress: create a ScorePath account for the parent with
   role *Parent*, approve it, then in the Django admin (`/admin/`) open **Parent links**
   and add parent → child.

## 6. Make it an app on the phone

- **iPhone / iPad:** open the link in **Safari**, tap Share, then **Add to Home Screen**.
- **Android:** open in **Chrome**; a banner offers **Install**, or use the menu, then
  **Install app**.

It opens full screen with its own icon. (It is still the website underneath; that is
what makes updates instant.) The `/install/` page in the app shows the same steps.

## Ads later (off by default)

Nothing is shown until you turn it on: Admin → **Settings** → tick *Show ads*
and paste the code from your ad network. Members you mark **Ad-free** in the Members list
never see ads (your admin account starts ad-free). Ads appear only on the home, progress
and end-of-session pages, never on a question.

Before turning ads on, read the "Ads and young users" section of `replica/architecture.md`:
if members are under 13 or 18, ad networks have special rules and you will likely need a
privacy policy and non-personalised ads.

## Backups

```bash
./deploy/backup.sh                 # saves to /mnt/media/backups/scorepath, keeps 14
```

Run it nightly: `crontab -e` and add

```
30 3 * * * cd /home/YOURUSER/scorepath && ./deploy/backup.sh >> /tmp/scorepath-backup.log 2>&1
```

Restore (this replaces the current data):

```bash
docker compose down
docker compose up -d db
gunzip -c /mnt/media/backups/scorepath/scorepath-YYYYMMDD-HHMMSS.sql.gz | \
  docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS $POSTGRES_DB" -c "CREATE DATABASE $POSTGRES_DB OWNER $POSTGRES_USER" && psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
docker compose up -d
```

## Updating later (from GitHub)

On your computer, make a change, then `git commit` and `git push`. On the server:

```bash
cd ~/scorepath
./deploy/update.sh
```

It shows what is coming in, backs up the database, pulls, rebuilds, waits until the site
answers, and sets `APP_VERSION` to the new commit so phones refresh their cached files. Your
`.env` and your data stay as they are. Database changes run by themselves on start.

If something goes wrong it prints the commands to look at the logs and to go back to the
previous version. `./deploy/update.sh` refuses to run if the folder has local edits, so keep
all changes in GitHub and never edit files on the server.

To update on a schedule instead, add to `crontab -e` (for example Sundays at 04:10):

```
10 4 * * 0 cd /home/YOURUSER/scorepath && ./deploy/update.sh >> /tmp/scorepath-update.log 2>&1
```

## Adding questions

Copy `learn/data/sample_questions.json` to `learn/data/my_items.json`, edit it (same
format), then rebuild and load it:

```bash
docker compose up -d --build
docker compose exec web python manage.py seed_content --file /app/learn/data/my_items.json
```

or add them one by one in `/admin/` under **Questions**. Only add questions you wrote or
have the right to use; the 24 bundled ones are original.

## Troubleshooting

- **Site not reachable from outside:** `curl -I https://scorepath.YOURNAME.duckdns.org`
  from your phone's mobile data (not home Wi-Fi). Check `docker compose ps`, then
  `sudo journalctl -u caddy -n 50`.
- **"Bad Request (400)":** the address you typed is not in `ALLOWED_HOSTS`.
- **"CSRF verification failed" when signing in:** `CSRF_TRUSTED_ORIGINS` must start with
  `https://` and match the address exactly. After editing `.env` run
  `docker compose up -d`.
- **Cannot sign in over plain http** (testing on your home network): set
  `HTTPS_ONLY=False`, put the server's LAN address in `ALLOWED_HOSTS`, and set
  `WEB_BIND=0.0.0.0`. Set all three back before sharing the link.
- **NordVPN with kill switch is on and Docker or the site breaks:** the VPN firewall
  blocks Docker's private network. Whitelist Docker's subnets and the LAN, for example
  `nordvpn whitelist add subnet 172.16.0.0/12` and `nordvpn whitelist add subnet 192.168.0.0/16`.
  Incoming visitors to a VPN-connected server also need port forwarding on the VPN side,
  which NordVPN does not offer; if the server must stay on the VPN, the site will only
  work from your home network.
- **Forgot the admin password:** `docker compose exec web python manage.py changepassword admin`
- **Locked out after too many wrong passwords:** wait an hour, or
  `docker compose exec web python manage.py axes_reset`
- **Where are the logs:** `docker compose logs --tail=100 web`


## Looking after members

- **Someone forgot their password:** Admin console, Members, "Reset password". A new password is shown once; tell them to change it under Me, Change password. (No email is sent, because the site has no email service.)
- **Someone lost a phone:** they sign in elsewhere and use Me, "Sign out everywhere". Or reset their password as above, which also signs them out everywhere.
- **Someone leaves:** they can use Me, "Delete my account", which removes all their data at once. You can also use "Remove access" in the console to block them but keep their history.
- **Privacy page** is at /privacy/. If you switch ads on, it says an ad network is involved. Edit `templates/accounts/privacy.html` if you add other services.
