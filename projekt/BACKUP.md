# Backup & Restore

Zwei Ebenen:
1. **App-Backup (dieses Dokument):** nächtlich `pg_dump` + Medien auf das NAS, Rotation 7 täglich / 4 wöchentlich. Damit lässt sich die App auf jeder neuen LXC wiederherstellen.
2. **Proxmox-Backup der ganzen LXC** (vzdump, Datacenter → Backup), z. B. wöchentlich. Schneller Komplett-Rückweg, ersetzt aber nicht 1. (ein laufendes PostgreSQL im Snapshot ist nur „crash-konsistent").

> **Vor jedem Tandoor-Update** (neues Image, Merge von Upstream): `deploy/backup.sh` von Hand ausführen und den Restore-Test (unten) machen. Tandoor-Migrationen lassen sich **nicht zurückrollen**.

---

## Aufbau der Sicherung

```
/mnt/nas/rezept-backup/
├── backup.log
├── daily/
│   ├── 2026-10-10_030001/
│   │   ├── db.dump          # pg_dump -Fc (custom format)
│   │   ├── media.tar.gz     # Inhalt von /opt/recipes/mediafiles
│   │   ├── info.txt         # Zeitpunkt, Image-Version, Host
│   │   └── SHA256SUMS
│   └── …                    # die letzten 7
└── weekly/                  # Kopie der Sonntagssicherung, die letzten 4
```

Eine Sicherung wird zuerst in `daily/.<zeit>.unvollstaendig` geschrieben, geprüft (`pg_restore --list`, `tar -t`, Prüfsummen) und erst dann umbenannt. Ein halbfertiger Lauf taucht also nie als gültige Sicherung auf.

## 1. NAS in die LXC bringen

Eine **unprivilegierte** LXC darf selbst kein NFS/SMB mounten. Deshalb mountet der Proxmox-Host das NAS und reicht den Ordner per Bind-Mount durch.

```bash
# Auf dem Proxmox-Host: NAS als Storage einbinden (Web-UI: Datacenter → Storage → Add → NFS/SMB)
# oder klassisch in /etc/fstab, z. B. nach /mnt/nas-rezept

pve# mkdir -p /mnt/nas-rezept/rezept-backup
pve# pct set <CTID> -mp0 /mnt/nas-rezept/rezept-backup,mp=/mnt/nas/rezept-backup
pve# pct reboot <CTID>
```

**Rechte:** root in der unprivilegierten LXC ist auf dem Host UID `100000`. Der Ordner auf dem NAS muss für diese UID beschreibbar sein:
- NFS: Export mit `all_squash,anonuid=<uid>` oder Ordner `chown 100000:100000` (auf dem Host).
- SMB/CIFS: beim Mount auf dem Host `uid=100000,gid=100000` angeben.

Test in der LXC:

```bash
lxc# touch /mnt/nas/rezept-backup/test && rm /mnt/nas/rezept-backup/test && echo ok
lxc# mountpoint /mnt/nas/rezept-backup     # "is a mountpoint"
```

`backup.sh` bricht mit Exit-Code 2 ab, wenn das Ziel kein Mount ist (NAS nicht da) – so läuft die lokale Platte nicht voll.

## 2. Konfiguration

```bash
lxc# cd /opt/rezept-app/deploy
lxc# cat > backup.conf <<'EOF'
BACKUP_DIR=/mnt/nas/rezept-backup
KEEP_DAILY=7
KEEP_WEEKLY=4
WEEKLY_DAY=7          # Sonntag
BACKUP_ENV=0          # 1 = .env mitsichern (enthält Passwörter, nur wenn das NAS vertrauenswürdig ist)
EOF
lxc# ./backup.sh ; echo "Exit-Code: $?"
```

`backup.conf` ist lokal und wird nicht committet (enthält keine Secrets, aber Pfade dieses Servers). Alle Variablen sind im Kopf von `deploy/backup.sh` beschrieben.

| Exit-Code | Bedeutung |
|---|---|
| 0 | ok |
| 1 | Konfigurationsfehler |
| 2 | Ziel nicht verfügbar (NAS nicht gemountet / nicht beschreibbar) |
| 3 | DB-Dump fehlgeschlagen |
| 4 | Medien-Sicherung fehlgeschlagen |
| 5 | Prüfung der Sicherung fehlgeschlagen |
| 6 | Rotation fehlgeschlagen |
| 7 | Backup läuft bereits |

## 3. Cron-Eintrag

```bash
lxc# crontab -e
```

```cron
# Rezept-App: Backup jede Nacht um 03:00
0 3 * * * /opt/rezept-app/deploy/backup.sh >> /var/log/rezept-backup.log 2>&1 || echo "Rezept-Backup fehlgeschlagen (Exit $?)" | logger -t rezept-backup
```

Kontrolle am nächsten Morgen:

```bash
lxc# tail -20 /mnt/nas/rezept-backup/backup.log
lxc# ls -l /mnt/nas/rezept-backup/daily
```

Tipp: Wer eine Benachrichtigung möchte, ersetzt `logger` durch einen Aufruf von z. B. ntfy/Gotify/Mail.

## 4. Restore

```bash
lxc# cd /opt/rezept-app/deploy
lxc# ./restore.sh /mnt/nas/rezept-backup/daily/2026-10-10_030001
```

Das Skript prüft die Prüfsummen, fragt nach `JA`, stoppt Tandoor, legt die Datenbank neu an, spielt den Dump ein, ersetzt die Medien und startet alles wieder.

Optionen: `--nur-db`, `--nur-medien`, `--projekt <name>` (in ein separates Compose-Projekt), `--ja` (ohne Rückfrage).

**Neue LXC (Totalausfall):** LXC nach [SETUP_LXC.md](SETUP_LXC.md) aufsetzen, gleiche Image-Version wie in `info.txt` der Sicherung in `.env` eintragen, `docker compose up -d`, einmal warten bis Tandoor läuft, dann `./restore.sh …`.

## 5. Restore-Test (vor jedem Update und z. B. einmal im Monat)

Der Test spielt die letzte Sicherung in ein **zweites Compose-Projekt** mit eigenen Volumes und Port 8081 ein. Das Live-System bleibt unberührt.

```bash
lxc# cd /opt/rezept-app/deploy
lxc# ./backup.sh                                            # frische Sicherung
lxc# LETZTE=$(ls -1d /mnt/nas/rezept-backup/daily/2* | tail -1); echo $LETZTE
lxc# HTTP_PORT=8081 ./restore.sh --projekt rezept-test --ja "$LETZTE"
lxc# HTTP_PORT=8081 docker compose -p rezept-test logs -f web_recipes    # warten auf "Starting gunicorn"
```

Prüfen (Checkliste):

- [ ] `curl -sI http://localhost:8081 | head -1` liefert eine Antwort (200/302)
- [ ] Im Browser `http://rezepte:8081` öffnen und mit den normalen Zugangsdaten einloggen
- [ ] Anzahl Rezepte stimmt ungefähr mit dem Live-System überein:
      `docker compose -p rezept-test exec db_recipes sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tc "select count(*) from cookbook_recipe"'`
- [ ] Ein Rezept mit Foto öffnen → Bild wird angezeigt
- [ ] Einkaufsliste / eigene Varianten („Unsere Version") sind da

Aufräumen (löscht nur das Testprojekt samt seiner Volumes):

```bash
lxc# HTTP_PORT=8081 docker compose -p rezept-test down -v
```

Ergebnis mit Datum kurz notieren (z. B. unten in dieser Datei), damit klar ist, wann zuletzt erfolgreich getestet wurde.

### Protokoll Restore-Tests

| Datum | Sicherung | Ergebnis | Bemerkung |
|---|---|---|---|
| | | | |
