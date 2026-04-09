# Deploy: clinicmonitoring.ziyrak.org + clinicmonitoringapi.ziyrak.org

## Har safar: `main` ga push qilgandan keyin serverda (VPS)

**GitHub Actions** Secrets to‘g‘ri bo‘lsa, ko‘pincha deploy **o‘zi** ishlaydi — [Actions](https://github.com/aiziyrak-coder/Monitoring/actions) da oxirgi **CI and deploy** yashil ekanini tekshiring.

Qo‘lda yangilash kerak bo‘lsa, VPS ga kirib:

```bash
cd /opt/clinicmonitoring
sudo bash deploy/server-pull-restart.sh
```

Yoki bir qatorda (SSH bilan):

```bash
ssh root@167.71.53.238 'cd /opt/clinicmonitoring && sudo bash deploy/server-pull-restart.sh'
```

### Lokal mashinadan Paramiko (Python)

SSH kalit bilan bir buyruqda yuborish; **HTTPS** bu skriptda o‘zgarmaydi (mavjud nginx/cert ishlatiladi). Boshqa saytlarning nginx symlinklarini tegmaslik uchun: `--skip-nginx-purge` yoki `DEPLOY_SKIP_NGINX_PURGE=1`.

```powershell
pip install -r deploy/requirements-paramiko.txt
$env:DEPLOY_HOST="167.71.53.238"
$env:DEPLOY_USER="root"
$env:DEPLOY_SSH_KEY="$env:USERPROFILE\.ssh\id_ed25519"
python deploy/paramiko_deploy.py --skip-nginx-purge
```

```bash
pip install -r deploy/requirements-paramiko.txt
export DEPLOY_HOST=167.71.53.238 DEPLOY_SSH_KEY=~/.ssh/id_ed25519
python deploy/paramiko_deploy.py --skip-nginx-purge
```

Skript: `deploy/paramiko_deploy.py` — serverda `deploy/server-pull-restart.sh` ni ishga tushiradi.

Bu skript: `origin/main` bilan tenglashadi, `migrate`, frontend `build`, nginx, **`clinicmonitoring-backend` restart**, health tekshiruvi.

Tekshiruv: `curl -sS https://clinicmonitoringapi.ziyrak.org/api/health`

### Xavfsizlik (qisqa)

- **`DJANGO_DEBUG=false`** va **`DJANGO_SECRET_KEY`** (32+ belgi) productionda majburiy (`/etc/clinicmonitoring.env`, `chmod 600`).
- **REST** `POST .../vitals` ixtiyoriy **`DEVICE_INGEST_TOKEN`** bilan yopiladi (sarlavha `X-Device-Ingest-Token` yoki `Authorization: Bearer …`); **HL7 :6006** ga ta’sir qilmaydi. Tafsilot: `deploy/clinicmonitoring.env.example`.
- **CI:** `main` va PR da **backend** (`check`, `test`) + **frontend** (`lint`, `build`) ishlaydi; deploy faqat `main` push / workflow_dispatch.

---

## 1. DNS

Ikkala domen A yozuvi **167.71.53.238** ga ishora qilsin.

## 2. Server paketlari (Ubuntu/Debian)

```bash
apt update
apt install -y git nginx python3 python3-venv python3-pip nodejs npm certbot python3-certbot-nginx
```

## 3. SSH kalit (parolsiz deploy)

Lokal mashinada:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/clinicmonitoring_deploy -N ""
ssh-copy-id -i ~/.ssh/clinicmonitoring_deploy.pub root@167.71.53.238
```

GitHub repoda **Settings → Secrets and variables → Actions**:

| Secret | Qiymat |
|--------|--------|
| `DEPLOY_HOST` | `167.71.53.238` |
| `DEPLOY_USER` | `root` |
| `DEPLOY_SSH_KEY` | `~/.ssh/clinicmonitoring_deploy` faylining **to‘liq private** mazmuni |

**Root parolini repoga yoki Secretsga yozmang.**

## 4. Bir marta serverda bootstrap

Reponi klonlang yoki CI birinchi pushdan keyin `/opt/clinicmonitoring` yaratadi.

```bash
cd /opt/clinicmonitoring   # yoki clone qilingandan keyin
bash deploy/bootstrap-server.sh
nano /etc/clinicmonitoring.env   # DJANGO_SECRET_KEY ni almashtiring
systemctl restart clinicmonitoring-backend
```

## 5. HTTPS

**Muhim:** bitta buyruqda **ikkala** domen — aks holda brauzerda `NET::ERR_CERT_COMMON_NAME_INVALID` (sertifikat boshqa domen uchun bo‘ladi).

```bash
sudo certbot --nginx -d clinicmonitoring.ziyrak.org -d clinicmonitoringapi.ziyrak.org
```

Mavjud sertifikatga frontend domenini qo‘shish:

```bash
sudo certbot --nginx --expand -d clinicmonitoring.ziyrak.org -d clinicmonitoringapi.ziyrak.org
```

Tekshiruv (SAN ichida `clinicmonitoring.ziyrak.org` bo‘lishi kerak):

```bash
sudo openssl x509 -in /etc/letsencrypt/live/clinicmonitoring.ziyrak.org/fullchain.pem -noout -text | grep -A1 "Subject Alternative Name"
```

Agar `live/` papkasi faqat `clinicmonitoringapi.ziyrak.org` nomida bo‘lsa, `deploy/nginx/monitoring-active.conf` dagi `ssl_certificate` / `ssl_certificate_key` yo‘llarini shu papkaga o‘zgartiring yoki yuqoridagi certbotni qayta ishga tushiring.

Repodan yordamchi skript (serverda, repodan keyin):

```bash
cd /opt/clinicmonitoring && sudo bash deploy/fix-ssl-both-domains.sh
```

## 6. GitHubga push

Lokal:

```bash
git init
git add .
git commit -m "Initial ClinicMonitoring"
git branch -M main
git remote add origin https://github.com/aiziyrak-coder/Monitoring.git
git push -u origin main
```

`main` ga har pushda Actions frontendni tekshiradi va SSH orqali `deploy/remote-update.sh` ni ishga tushiradi.

## 7. Tekshiruv

- https://clinicmonitoringapi.ziyrak.org/api/health  
- https://clinicmonitoring.ziyrak.org  
- https://clinicmonitoring.ziyrak.org/version.txt — bitta qator (`platform-device-link-v1` yoki `buildInfo` dagi yangi yorliq); agar HTML (bosh sahifa) chiqsa, yangi `dist` joylanmagan yoki noto‘g‘ri `root`.
- HL7 uchun **6006/tcp** (VPS firewall + kerak bo‘lsa `bash deploy/open-hl7-port.sh`). Qurilma «oflayn» bo‘lsa — `GET /api/health` (`hl7`, `deviceOfflineAfterSec`) va server loglarini tekshiring.

Repository: [github.com/aiziyrak-coder/Monitoring](https://github.com/aiziyrak-coder/Monitoring)

## 8. Yangilanmayaptimi? (Actions + qo‘lda deploy)

### Nima uchun Cursor/AI serverga SSH qila olmaydi?

Agent sizning kompyuteringizdagi **SSH private kalitga kira olmaydi**. `ssh root@167.71.53.238` faqat sizda kalit (`~/.ssh/...` yoki ssh-agent) bo‘lsa ishlaydi. Shuning uchun deploy **GitHub Actions** (Secrets) yoki **quyidagi skript** orqali qilinadi.

### GitHub Actions

1. **Settings → Secrets and variables → Actions** da `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY` to‘liq va to‘g‘ri ekanini tekshiring (`DEPLOY_SSH_KEY` — butun private key matni, boshida `-----BEGIN` bilan).
2. **Actions** → **CI and deploy** — oxirgi run **yashil**mi? Qizil bo‘lsa logda xato: ko‘pincha Secrets yo‘q/noto‘g‘ri yoki serverda `npm ci` uzoq vaqt olgani uchun (workflowda `command_timeout: 45m`).
3. **Run workflow** (branch: `main`) — push ishlamasa ham serverni yangilaydi.

### Windows (PowerShell, bir xil buyruq)

Avval kalit yo‘lini muhitga qo‘ying, keyin repoda:

```powershell
$env:CLINICMON_DEPLOY_SSH_KEY = "$env:USERPROFILE\.ssh\clinicmonitoring_deploy"
.\deploy\run-remote-update.ps1
```

### Linux / macOS (qo‘lda)

```bash
ssh root@167.71.53.238 'cd /opt/clinicmonitoring && bash deploy/server-pull.sh && bash deploy/remote-update.sh'
```
