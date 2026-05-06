# SOLVIOR PROJECT — Planéta Centrum Kft.

Projekt- és pénzügyi menedzsment rendszer.

## Funkciók
- Projektek ügyfelenkénti kezelése
- Kimenő/bejövő számlák
- Alvállalkozói kifizetések + email értesítők
- Kintlévőség kimutatás
- Cash flow dashboard
- Projektenként készletkezelés + Excel import
- Riportok

## Railway Deploy

### 1. GitHub repo létrehozása
```bash
git init
git add -A
git commit -m "init: SOLVIOR PROJECT"
git remote add origin https://github.com/YOURUSERNAME/solvior-project.git
git push -u origin main
```

### 2. Railway
1. railway.app → New Project → Deploy from GitHub
2. Add PostgreSQL addon
3. Environment Variables beállítása:
```
SECRET_KEY=valami-titkos-kulcs-ide
DATABASE_URL=<Railway PostgreSQL URL - auto beállítja>
MAILGUN_API_KEY=<Mailgun API key>
MAILGUN_DOMAIN=mg.solvior.ee
MAILGUN_FROM=noreply@solvior.ee
```

### 3. Első belépés
- Nyisd meg: https://solvior-project.up.railway.app/setup
- Hozd létre az admin fiókot
- Ezután a /setup nem érhető el

## Excel import formátum (Készlet)
| Megnevezés | Cikkszám | Egység | Egységár | Készlet | Kategória |
|---|---|---|---|---|---|
| NYMHY 3x1.5 kábel | K001 | m | 450 | 5000 | Kábel |

## Tech stack
- Flask 3.0 + SQLAlchemy + Flask-Login
- PostgreSQL (Railway)
- Tabler UI + Chart.js
- Mailgun email
- Gunicorn
