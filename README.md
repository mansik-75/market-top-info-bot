# Это ТГ бот для развертывания при помощи yandex cloud function и yandex api gateway.

## Возможности бота: принятие контактов от пользователей и отправка их в админский чат

Для развертывания бота:
- Cоздать публичный yandex cloud function
- Создать yandex api gateway:
```
openapi: 3.0.0
info:
  title: Sample API
  version: 1.0.0
paths:
  /:
    post:
      x-yc-apigateway-integration:
        type: cloud-functions
        function_id: <your-function-id>
      operationId: <your-name>

```
- Выполнить команду для создания webhook:
```
curl \
> --request POST \
> --url https://api.telegram.org/bot<your-bot-token>/setWebhook \
> --header 'content-type: application/json' \
> --data '{"url": "<api-gw-url>"}'

```
