# Clarus-IoT

**Clarus-IoT** — локальный интеллектуальный ML-сервис для анализа IoT / сетевого трафика.  
Проект реализует полный pipeline асинхронного анализа CSV-файлов с сетевыми потоками и предоставляет Web-интерфейс для взаимодействия с ML-моделями.

Проект предназначен для локального запуска (Docker Compose) и демонстрирует архитектуру промышленного ML-сервиса.

---

## Основные возможности

- регистрация и логин пользователей (JWT);
- управление подпиской (billing, месячная подписка);
- загрузка CSV-файлов с сетевым трафиком;
- асинхронный ML-анализ через очередь RabbitMQ;
- бинарная классификация:
  - атака / нет атаки;
- мультиклассовая классификация (тип атаки);
- просмотр истории расчетов;
- скачивание CSV с результатами (`is_attack`, `attack_type`);
- Web UI (SPA) + REST API.

---

## ML-пайплайн

CSV (без колонок attack / category / subcategory)

↓

Бинарная ML-модель (XGBoost)
→ is_attack

↓

если is_attack = 1

↓

Мультиклассовая ML-модель (XGBoost)
→ attack_type

↓

Результат:
агрегированная статистика
CSV с добавленными колонками:
is_attack, attack_type

---

## Архитектура

### Backend
- FastAPI
- PostgreSQL
- RabbitMQ
- ML Worker (XGBoost: binary + multiclass)
- JWT-аутентификация
- Subscription / Billing сервис

### Frontend
- React + TypeScript
- Vite
- SPA (Single Page Application)
- UI на Tailwind-подобных компонентах
- отдаётся через Nginx

### Infra
- Docker Compose
- Nginx как reverse-proxy и SPA-сервер
- Named volumes:
  - `uploads` — CSV и результаты
  - `models` — ML-модели

---

## Структура проекта

. ├── app/ # Backend + ML worker 

├── web/ # Frontend (React + Vite)

├── deploy/nginx/ # Nginx конфигурация 

├── data/

│ └── test_data.csv # Тестовый CSV для проверки

├── docker-compose.yml

├── Dockerfile

├── .env.example

└── README.md

---

## Требования

- Docker
- Docker Compose
- Свободный порт **80**
- Свободные порты **5432**, **5672**, **15672** (Postgres, RabbitMQ)

---

## Запуск проекта

### 1. Клонировать репозиторий

```bash
git clone <repo_url>
cd clarus-iot
2. Создать .env
скопировать содержимое .env.example в файл.env
3. Запустить проект
docker compose up -d --build
Первый запуск может занять несколько минут (сборка frontend и ML-зависимостей).
Доступные сервисы
Сервис	URL
Web UI	http://localhost
Swagger API	http://localhost/docs
RabbitMQ UI	http://localhost:15672
PostgreSQL	localhost:5432
Проверка работоспособности
Шаг 1. Открыть Web UI
http://localhost
Шаг 2. Зарегистрироваться / войти
email: любой
password: любой
Шаг 3. Активировать подписку
В Dashboard:
открыть блок Billing
нажать «Продлить на месяц»
убедиться, что подписка стала active
Шаг 4. Загрузить тестовый CSV
Использовать файл:
data/test_data.csv
Загрузить через блок «Загрузка CSV»
Шаг 5. Дождаться завершения job
статус: queued → running → done
открыть job из списка
Шаг 6. Проверить результаты
отображается summary:
количество строк
количество атак
доля атак
топ-класс атаки
нажать Download scored CSV
CSV скачивается и содержит колонки:
 - is_attack
 - attack_type