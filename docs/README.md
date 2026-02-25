# LLM Switchboard (DGX Spark, aarch64)

## 1) Overview
LLM Switchboard — это FastAPI gateway + Redis/RQ worker + vLLM backend manager, который гарантирует, что **одновременно активна только одна модель в памяти**.

Почему так:
- Большие модели не помещаются вместе в VRAM/RAM.
- Один worker (concurrency=1) + глобальный lock исключают гонки при switch.
- Смена модели происходит через stop/kill контейнера backend, чтобы гарантированно освободить память.

## 2) Quickstart

```bash
cd /opt/llm-switchboard
cp .env.example /etc/llm-gateway.env
# Отредактируйте API ключи и пути
```

1. Установка зависимостей:
```bash
bash scripts/install_prereqs.sh
```

2. Настройка конфигов:
- `configs/models.yaml`
- `configs/gateway.yaml`

3. Подтянуть vLLM image:
```bash
bash scripts/pull_vllm_image.sh
```

4. Опционально скачать модели:
```bash
MODELS_YAML_PATH=/opt/llm-switchboard/configs/models.yaml bash scripts/download_models.sh
```

5. Запуск Redis + сервисов:
```bash
bash scripts/start_all.sh
sudo systemctl enable --now jupyter@$(whoami).service
```

6. Проверка:
```bash
bash scripts/smoke_test.sh
```

## 3) Модели и конфигурация
`configs/models.yaml` содержит логические имена:
- `gpt-oss120`
- `qwen3-30b`
- `qwen3-235b-4bit`

Для каждой модели:
- `source.type`: `local_path` или `huggingface_repo`
- `source.value`: путь или HF repo
- `backend.image`
- `backend.port`
- `backend.vllm_args`
- `quantization` (например `awq/gptq`) для 4bit модели

Таймауты и политики в `configs/gateway.yaml` (`SWITCH_TIMEOUT_SEC`, `INFERENCE_TIMEOUT_SEC`, и т.д.).

## 4) Публичный API через Tailscale Funnel (*.ts.net)

Включить Funnel (публичный HTTPS):
```bash
bash scripts/setup_tailscale_funnel.sh http://127.0.0.1:8000 443
bash scripts/print_tailscale_urls.sh
```

Проверка:
```bash
curl https://<your-node>.ts.net/health
```

Выключить Funnel:
```bash
sudo tailscale funnel reset
```

> Funnel публикует сервис в интернет, поэтому `GATEWAY_API_KEY` обязателен.

## 5) JupyterLab и удалённая разработка
Jupyter слушает только `127.0.0.1:8888`, а доступ предоставляется через tailnet:

```bash
bash scripts/setup_tailscale_serve_jupyter.sh http://127.0.0.1:8888 8443
```

Альтернатива: SSH port-forward:
```bash
ssh -L 8888:127.0.0.1:8888 <user>@<tailscale-host>
```

### VS Code Remote-SSH
1. Установите extension Remote-SSH.
2. Подключитесь к Tailscale hostname DGX.
3. Выберите Python interpreter `/opt/llm-switchboard/.venv/bin/python`.

### PyCharm remote interpreter
1. Add Interpreter -> SSH.
2. Host: tailscale hostname/IP.
3. Python path: `/opt/llm-switchboard/.venv/bin/python`.

### Remote Jupyter
Используйте URL из `tailscale serve status` или SSH-forward URL `http://127.0.0.1:8888`.

## 6) API примеры curl

```bash
# health (может быть открыт без ключа)
curl http://127.0.0.1:8000/health

# models
curl -H "X-API-Key: $GATEWAY_API_KEY" http://127.0.0.1:8000/v1/models

# async chat completion
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "X-API-Key: $GATEWAY_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"gpt-oss120","messages":[{"role":"user","content":"Hello"}],"async":true}'

# job status
curl -H "X-API-Key: $GATEWAY_API_KEY" http://127.0.0.1:8000/jobs/<job_id>

# job result
curl -H "X-API-Key: $GATEWAY_API_KEY" http://127.0.0.1:8000/jobs/<job_id>/result

# job cancel
curl -X POST -H "X-API-Key: $GATEWAY_API_KEY" http://127.0.0.1:8000/jobs/<job_id>/cancel

# extended status
curl -H "X-API-Key: $GATEWAY_ADMIN_API_KEY" http://127.0.0.1:8000/status

# queue info
curl -H "X-API-Key: $GATEWAY_ADMIN_API_KEY" http://127.0.0.1:8000/queue
```

## 7) Troubleshooting
- Логи gateway:
```bash
journalctl -u llm-gateway.service -f
```
- Логи worker:
```bash
journalctl -u llm-worker.service -f
```
- Логи jupyter:
```bash
journalctl -u jupyter@$(whoami).service -f
```
- Логи backend контейнера:
```bash
docker logs -f llm-backend-active
```
- Redis недоступен: проверьте `docker ps` и `REDIS_URL`.
- Модель не стартует: уменьшите `--max-model-len`, проверьте quantization/weights.
- Зависшая генерация: `POST /jobs/{id}/cancel` (running job => hard cancel backend).
- Ручная остановка backend:
```bash
docker rm -f llm-backend-active
```
