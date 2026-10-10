# Einrichtung der LXC auf Proxmox

Ziel: Eine unprivilegierte Debian-LXC mit Docker und Tailscale, in der Tandoor (später unser Fork) mit PostgreSQL läuft. Erreichbar **nur** über Tailscale unter `http://rezepte` bzw. `https://rezepte.<tailnet>.ts.net`.

> Platzhalter: `<CTID>` = Container-ID (z. B. `120`), `rezepte` = Hostname im Tailnet, `<tailnet>` = dein Tailnet-Name (z. B. `tail1234`). Befehle mit `pve#` laufen auf dem Proxmox-Host, `lxc#` in der LXC (als root).

---

## 1. LXC anlegen

### Template holen

```bash
pve# pveam update
pve# pveam available --section system | grep debian
pve# pveam download local debian-12-standard_12.12-1_amd64.tar.zst   # Namen aus der Liste übernehmen (Debian 12 oder 13)
```

### Container erstellen

Per Web-Oberfläche („Create CT") oder per Befehl:

```bash
pve# pct create <CTID> local:vztmpl/debian-12-standard_12.12-1_amd64.tar.zst \
  --hostname rezepte \
  --unprivileged 1 \
  --features nesting=1,keyctl=1 \
  --cores 2 --memory 2048 --swap 512 \
  --rootfs local-lvm:16 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --onboot 1 \
  --password    # fragt das root-Passwort ab
```

- **unprivileged 1**: sicherer Standard.
- **nesting=1**: nötig für Docker in der LXC.
- **keyctl=1**: nötig für Docker in *unprivilegierten* LXCs.
- 2 GB RAM reichen für Tandoor + PostgreSQL bei 1–2 Nutzern; 16 GB Disk für System, Images und DB (Bilder wachsen mit der Zeit – ggf. später vergrößern: `pct resize <CTID> rootfs +10G`).

### `/dev/net/tun` für Tailscale freigeben

Tailscale braucht das TUN-Device. Container **gestoppt** lassen und auf dem Host in `/etc/pve/lxc/<CTID>.conf` ergänzen:

```
lxc.cgroup2.devices.allow: c 10:200 rwm
lxc.mount.entry: /dev/net/tun dev/net/tun none bind,create=file
```

(Ab Proxmox VE 8.1 geht alternativ auch `dev0: /dev/net/tun` – eine der beiden Varianten reicht.)

```bash
pve# pct start <CTID>
pve# pct enter <CTID>
lxc# ls -l /dev/net/tun        # muss existieren: crw-rw-rw- ... 10, 200
```

## 2. Grundsystem

```bash
lxc# apt update && apt full-upgrade -y
lxc# apt install -y ca-certificates curl gnupg git cron
lxc# timedatectl set-timezone Europe/Berlin
```

## 3. Docker installieren (offizielles Repository)

```bash
lxc# install -m 0755 -d /etc/apt/keyrings
lxc# curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
lxc# chmod a+r /etc/apt/keyrings/docker.asc
lxc# echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
      > /etc/apt/sources.list.d/docker.list
lxc# apt update
lxc# apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
lxc# docker run --rm hello-world     # Test
lxc# docker compose version          # muss v2.x zeigen
```

## 4. Tailscale in der LXC

```bash
lxc# curl -fsSL https://tailscale.com/install.sh | sh
lxc# tailscale up --hostname rezepte
```

Den angezeigten Link im Browser öffnen und das Gerät im Tailnet bestätigen. Danach:

```bash
lxc# tailscale status
lxc# tailscale ip -4                 # Tailscale-IP (100.x.y.z) für ALLOWED_HOSTS notieren
```

Im Tailscale-Admin (https://login.tailscale.com/admin/machines):
- **Key expiry deaktivieren** für `rezepte` (sonst fliegt der Server nach 180 Tagen raus).
- **MagicDNS** einschalten (DNS-Tab), damit `http://rezepte` funktioniert.

Kein Port-Forwarding im Router. Die LXC ist im LAN zwar per IP erreichbar; wer das verhindern will, kann Port 80 per Firewall auf das Interface `tailscale0` beschränken (Proxmox-Firewall für den CT oder `HTTP_PORT=100.x.y.z:80` in der `.env`, dann lauscht Docker nur auf der Tailscale-IP).

## 5. App deployen

```bash
lxc# git clone https://github.com/NFrankM/recipes /opt/rezept-app
lxc# cd /opt/rezept-app && git checkout main-custom
lxc# cd deploy
lxc# cp .env.example .env
lxc# chmod 600 .env
lxc# nano .env
```

In `.env` setzen:
- `SECRET_KEY` → `openssl rand -base64 48 | tr -d '\n=/+'; echo`
- `POSTGRES_PASSWORD` → `openssl rand -hex 24`
- `ALLOWED_HOSTS` → `rezepte,rezepte.<tailnet>.ts.net,<tailscale-ip>`
- `CSRF_TRUSTED_ORIGINS` → `http://rezepte,http://rezepte.<tailnet>.ts.net,https://rezepte.<tailnet>.ts.net`

```bash
lxc# docker compose config >/dev/null && echo "Konfiguration ok"
lxc# docker compose up -d
lxc# docker compose logs -f web_recipes     # warten bis "Starting gunicorn"
```

Im Browser (Gerät im Tailnet): `http://rezepte` → Tandoor fragt beim ersten Aufruf nach dem Admin-Konto.

## 6. Optional (empfohlen): HTTPS mit `tailscale serve`

Ein echtes HTTPS-Zertifikat ist nicht nur schöner: Browser erlauben einige Funktionen nur in „sicheren Kontexten" – z. B. die **Bildschirmsperre verhindern (Wake Lock) im Kochmodus** und die **Installation als App auf dem Homescreen (PWA)**.

1. Im Tailscale-Admin unter **DNS → HTTPS Certificates** aktivieren.
2. In der LXC:
   ```bash
   lxc# tailscale serve --bg 80
   lxc# tailscale serve status
   ```
3. Aufruf: `https://rezepte.<tailnet>.ts.net` (die https-Origin muss in `CSRF_TRUSTED_ORIGINS` stehen, siehe oben).

Abschalten: `tailscale serve reset`.

## 7. Backup einrichten

Siehe [BACKUP.md](BACKUP.md) (NAS mounten, Cron-Eintrag, Restore-Test).

## 8. Prüfen

```bash
lxc# docker compose ps                         # beide Container "running"/"healthy"
lxc# curl -sI http://localhost | head -1       # HTTP/1.1 302 o. ä.
lxc# docker compose exec db_recipes psql -U djangouser -d djangodb -c '\dx'   # pg_trgm/unaccent sollten auftauchen
# vom Handy/Laptop im Tailnet:
http://rezepte
```

## Häufige Probleme

| Symptom | Ursache / Lösung |
|---|---|
| `docker: ... permission denied` / Overlay-Fehler | `nesting=1,keyctl=1` fehlen → CT stoppen, `pct set <CTID> --features nesting=1,keyctl=1` |
| `tailscaled: /dev/net/tun does not exist` | Abschnitt „/dev/net/tun freigeben" fehlt, CT neu starten |
| `Bad Request (400)` | Hostname fehlt in `ALLOWED_HOSTS` |
| `CSRF verification failed` beim Login | exakte Origin (Schema + Host) fehlt in `CSRF_TRUSTED_ORIGINS` |
| nginx startet nicht wegen IPv6 | In der LXC IPv6 deaktiviert → IPv6 im CT aktivieren (`net0 ... ip6=auto`) |
