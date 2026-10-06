# Payments service

Асинхронный сервис процессинга платежей: FastAPI, PostgreSQL, RabbitMQ (FastStream).

## Запуск

```bash
docker compose up -d --build
```

- API: http://localhost:8000/docs (ключ `X-API-Key: secret-key`)
- RabbitMQ: http://localhost:15672 (guest/guest)
- Полученные вебхуки: http://localhost:9000/webhooks

## Примеры

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "X-API-Key: secret-key" \
  -H "Idempotency-Key: order-1" \
  -H "Content-Type: application/json" \
  -d '{"amount": "1234.56", "currency": "RUB", "description": "order 1", "metadata": {"order_id": 1}, "webhook_url": "http://webhook-mock:9000/webhooks/ok"}'

curl http://localhost:8000/api/v1/payments/<payment_id> -H "X-API-Key: secret-key"
```

Для проверки ретраев и DLQ: `"webhook_url": "http://webhook-mock:9000/webhooks/fail"` (всегда отвечает 500).

## Как устроено

- **api** сохраняет платеж и событие в таблицу `outbox` в одной транзакции. Outbox relay (фоновая задача в api) публикует события в очередь `payments.new`.
- **consumer** читает `payments.new`, эмулирует платеж (2-5 сек, 90% успех), обновляет статус и отправляет вебхук.
- **Идемпотентность**: уникальный `Idempotency-Key`, повтор с тем же телом возвращает тот же платеж, с другим телом - 422. Повторная доставка сообщения не проводит платеж второй раз: строка платежа блокируется на время списания, а `payment_id` передается шлюзу как ключ идемпотентности.
- **Retry**: при ошибке отправки вебхука сообщение уходит в очередь с задержкой, всего 3 попытки (повторы через 1s и 2s), после этого - в `payments.dlq`.

## Тесты

```bash
uv sync
uv run pytest
```
