# Moving ULTRA ERP to the cloud

This walks through taking the app off your laptop and onto a small
always-on server, with automatic daily backups to Backblaze B2. Follow
these in order — each step tells you exactly what to click or type.

Total cost: roughly **$6/month** for the server (DigitalOcean) + **a
few cents/month** for backups (Backblaze B2, priced per GB — this
app's data is tiny) + whatever your domain registrar charges yearly
for the domain (~$10-15/year).

---

## Step 1 — Create the DigitalOcean server

1. Go to [digitalocean.com](https://www.digitalocean.com) and create
   an account (you'll need to add a payment method — that part's on
   you, I can't do this step for you).
2. Click **Create → Droplets**.
3. Choose:
   - **Image:** Ubuntu 24.04 (LTS) x64
   - **Plan:** Basic → Regular → the $6/mo option (1 GB RAM / 25 GB SSD) is plenty
   - **Region:** whichever is closest to you/your staff
   - **Authentication:** Password is simplest if you're not familiar
     with SSH keys — set a strong root password and remember it
4. Click **Create Droplet**. After a minute you'll see its IP address
   (something like `164.90.123.45`) — write this down.

## Step 2 — Point your domain at the server

1. Go to wherever you bought your domain (Namecheap, Porkbun, etc.),
   find **DNS settings** for that domain.
2. Add an **A record**:
   - Host/Name: `erp` (or `@` if you want the bare domain, e.g. `yourcompany.com` instead of `erp.yourcompany.com`)
   - Value: the droplet's IP address from Step 1
   - TTL: leave default
3. This can take a few minutes up to an hour to "propagate" — it
   doesn't need to be done before Step 3, just before Step 5.

## Step 3 — Upload the app to the server

On your Mac, open Terminal and run (replace the IP with yours):

```
cd ~/Desktop
scp -r UltraERP-Web root@164.90.123.45:/root/
```

Type `yes` if asked about the connection's authenticity, then enter
the root password you set in Step 1 when prompted.

## Step 4 — Connect to the server and run the setup script

Still in Terminal:

```
ssh root@164.90.123.45
```

Enter the root password again. You're now typing directly on the
server. Run:

```
cd /root/UltraERP-Web
bash deploy/setup.sh
```

It'll ask for your domain name (the one from Step 2, e.g.
`erp.yourcompany.com`) — type it and press Enter. This step installs
everything and takes a few minutes. When it finishes, you'll see a
"Setup complete!" message.

Visit `https://erp.yourcompany.com` (your real domain) in a browser —
you should see the ULTRA ERP sign-in page, now with a padlock icon
(secure HTTPS) and reachable from anywhere, not just your office WiFi.

The very first run prints a super-admin username and password to the
terminal, exactly like it did on your laptop — save it the same way.

## Step 5 — Set up automatic backups to Backblaze B2

1. Go to [backblaze.com/cloud-storage](https://www.backblaze.com/cloud-storage)
   and create an account (has a free tier; you'll add payment info for
   anything beyond it, which for this app's data size will be pennies).
2. Once logged in, go to **B2 Cloud Storage → Buckets → Create a
   Bucket**. Name it something like `ultraerp-backups`, set it to
   **Private**. Create it.
3. Go to **Application Keys → Add a New Application Key**. Name it
   anything, restrict it to the bucket you just made, and click
   Create. **This is the only time it shows you the `applicationKey`
   — copy both the `keyID` and `applicationKey` somewhere safe right
   now.**
4. Back in your server's terminal (still SSH'd in from Step 4), run:
   ```
   bash /opt/ultraerp/deploy/setup_backups.sh
   ```
   It'll ask for the bucket name, keyID, and applicationKey from
   above. Paste each in when prompted (the applicationKey won't show
   as you type — that's normal, it's still being entered).
5. It runs a real backup immediately and confirms it worked, then sets
   up a daily 2 AM backup automatically. You're done.

## Moving your existing data over (if you already have companies set up on your laptop)

If you've already been using the laptop version and have real
companies/data you want to keep, do this **before** Step 3 above, on
your laptop:

```
cd ~/Desktop/UltraERP-Web
zip -r mydata.zip tenants ultra_erp_master.db
```

Then after Step 4 finishes on the server, upload and restore it:

```
scp mydata.zip root@164.90.123.45:/tmp/
ssh root@164.90.123.45
systemctl stop ultraerp
cd /opt/ultraerp
rm -rf tenants ultra_erp_master.db
unzip /tmp/mydata.zip
chown -R ultraerp:ultraerp tenants ultra_erp_master.db
systemctl start ultraerp
```

## Freeing up your laptop

Once you've confirmed the cloud version works (log in, check your
companies and data are all there), you can close the terminal on your
laptop for good — the server runs independently now, nothing on your
laptop needs to stay open or awake.

## Everyday maintenance

- **Check it's running:** SSH in and run `systemctl status ultraerp`
- **Restart it:** `systemctl restart ultraerp`
- **View recent logs:** `journalctl -u ultraerp -n 50`
- **Update the app later** (if I send you new files): upload the new
  folder like Step 3, SSH in, then:
  ```
  systemctl stop ultraerp
  cp -r /root/UltraERP-Web/* /opt/ultraerp/
  # do NOT copy tenants/ or ultra_erp_master.db - keep your real data
  chown -R ultraerp:ultraerp /opt/ultraerp
  sudo -u ultraerp /opt/ultraerp/venv/bin/pip install -r /opt/ultraerp/requirements.txt --quiet
  systemctl start ultraerp
  ```
- **Restore ONE company from a backup** (e.g. a customer accidentally
  deletes something and wants yesterday's data back): every company's
  backups live in their own folder in B2, completely separate from
  every other company — go to your B2 bucket, open the folder named
  after that company (its slug, shown in the admin panel), download
  the zip you want, then on the server:
  ```
  systemctl stop ultraerp
  cd /opt/ultraerp
  rm -rf tenants/the-company-slug
  unzip /path/to/the-company-slug_20260812_020000.zip
  chown -R ultraerp:ultraerp tenants/the-company-slug
  systemctl start ultraerp
  ```
  This only touches that one company's folder — every other company's
  data is completely untouched.
- **Restore everything** (disaster recovery, e.g. the whole server was
  lost): download every company's latest zip plus the one in
  `_platform/`, then follow the same restore steps shown above under
  "Moving your existing data over," repeating the `unzip` step once
  per company.

## How backups are organized

Every company's data is backed up **completely separately** — never
combined into one file with anyone else's — and **kept forever**: every
single day's backup stays in Backblaze B2 permanently, nothing is ever
auto-deleted there. A customer who joins today has an unbroken daily
history going back to day one, for as long as they're your customer.
In your Backblaze B2 bucket, you'll see:

```
ultraerp-backups/
  _platform/                        <- your companies/users/subscription list
    platform_20260811_020000.zip
    platform_20260812_020000.zip
    ...one more file added every single day, forever
  al-faisal-yarn-traders/           <- one folder per company
    al-faisal-yarn-traders_20260811_020000.zip
    al-faisal-yarn-traders_20260812_020000.zip
    ...one more file added every single day, forever
  chenab-ginners/
    chenab-ginners_20260811_020000.zip
    chenab-ginners_20260812_020000.zip
    ...
```

(The server's own local disk only keeps the last 3 days per company as
a fast same-day restore cache — B2 is the real, permanent archive.)

**On storage cost as this grows:** these are small SQLite database
files, typically a few MB each even for an active business. A rough
estimate: 100 customers, each backed up daily for 5 years, comes out
to roughly 15-20 GB total — well inside B2's free 10 GB tier at first,
and only a couple of dollars a month once you're past it (B2 is priced
around $6/TB/month). If this ever becomes a real cost concern as you
scale, a middle ground is easy to add later — e.g. keep every daily
backup for the first 90 days, then thin older ones down to one per
month — just let me know and I'll adjust `backup.sh`.

This means you can restore, hand over, or delete any one customer's
data without it ever touching another customer's backups — useful if
a customer ever asks for their data, cancels, or you just need to roll
back one company after a mistake. Each company also has an on-demand
"Download Backup" button in their own sidebar (already built into the
app) if they want a copy of their own data at any time, without
needing to involve you at all.

## If something goes wrong

Paste me whatever error you see (`systemctl status ultraerp` or
`journalctl -u ultraerp -n 50` are the most useful things to share) and
I'll help you work through it, the same way we've done for everything
else.
