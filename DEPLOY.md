# Deploy: clinicmonitoring.ziyrak.org + clinicmonitoringapi.ziyrak.org

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

```bash
certbot --nginx -d clinicmonitoring.ziyrak.org -d clinicmonitoringapi.ziyrak.org
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
- https://clinicmonitoring.ziyrak.org/version.txt — bitta qator (`deploy-verify-v1` yoki `buildInfo` dagi yangi yorliq); agar HTML (bosh sahifa) chiqsa, yangi `dist` joylanmagan yoki noto‘g‘ri `root`.

Repository: [github.com/aiziyrak-coder/Monitoring](https://github.com/aiziyrak-coder/Monitoring)

## 8. Yangilanmayaptimi? (Actions + qo‘lda deploy)

1. GitHub → **Actions** → **CI and deploy** — oxirgi run **yashil**mi? Qizil bo‘lsa, **Secrets** (`DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`) va logni tekshiring.
2. **Qo‘lda deploy** (SSH kalit bilan serverga):
   ```bash
   ssh root@167.71.53.238 'cd /opt/clinicmonitoring && bash deploy/server-pull.sh && bash deploy/remote-update.sh'
   ```
3. **Actions dan qo‘lda ishga tushirish:** **Actions** → **CI and deploy** → **Run workflow** (branch: `main`). Bu ham `workflow_dispatch` orqali serverni yangilaydi (Secrets bo‘lishi shart).
