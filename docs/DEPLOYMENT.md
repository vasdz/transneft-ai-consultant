# Инструкция по развёртыванию

## Цель
On‑premise развёртывание одной системой: Nginx отдаёт фронтенд как статику и проксирует `/api` на FastAPI.

## Профиль ресурсов
- RAM: 16 GB+
- Диск: 20+ GB
- GPU: опционально (для cuda)

## Подготовка
Выполни INSTALLATION.md (модели загружены, БЗ проиндексирована).

## Nginx как единая точка входа

Структура:
- Фронтенд: `/var/www/transneft-ai/frontend` (скопируй содержимое `src/transneft_ai_consultant/frontend` сюда).
- Бэкенд: Uvicorn на 127.0.0.1:8000 (systemd‑сервис ниже).

Конфиг `/etc/nginx/sites-available/transneft-ai`:
server {
listen 80;
server_name transneft-ai.local;

root /var/www/transneft-ai/frontend;
index index.html;

location /api/ {
    proxy_pass http://127.0.0.1:8000/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location / {
    try_files $uri $uri/ /index.html;
}
}

Активация:
sudo ln -s /etc/nginx/sites-available/transneft-ai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

Важно:
- Убери `<script>window.API_BASE_URL=...</script>` или поставь `window.API_BASE_URL=''` (пусто), если фронтенд и бэкенд под одним доменом — тогда запросы идут на относительный `/api/...`.

## Сервис backend (systemd)

`/etc/systemd/system/transneft-ai.service`:
[Unit]
Description=Transneft AI Consultant (FastAPI)
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/opt/transneft-ai-consultant
Environment="PATH=/opt/transneft-ai-consultant/.venv/bin"
ExecStart=/opt/transneft-ai-consultant/.venv/bin/python -m src.transneft_ai_consultant.backend.api
Restart=always

[Install]
WantedBy=multi-user.target

Активировать:
sudo systemctl daemon-reload
sudo systemctl enable transneft-ai
sudo systemctl start transneft-ai
sudo systemctl status transneft-ai

## HTTPS (рекомендуется)

Сертификат (например, certbot) и смена `listen 443 ssl;` + `server_name` в конфиге. Для работы микрофона в браузере HTTPS обязателен в проде.

## Безопасность
- Ограничи доступ к Uvicorn (слушать 127.0.0.1).
- UFW пропусти только 80/443 снаружи.
- CORS в `.env` можно сузить до домена фронта.

## Мониторинг
tail -f rag_demo.log # логи приложения
sudo journalctl -u transneft-ai -f # логи сервиса

## Обновления
cd /opt/transneft-ai-consultant
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart transneft-ai
sudo systemctl reload nginx

## Проверка
curl http://127.0.0.1:8000/api/health

Открой в браузере http://transneft-ai.local