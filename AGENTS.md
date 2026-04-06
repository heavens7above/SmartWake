# Repository Guidelines

## Project Structure & Module Organization
`SmartWakeApp/` contains the Flutter client. App code lives in `lib/`, split into `screens/`, `services/`, `widgets/`, `models/`, and `theme/`; assets live in `SmartWakeApp/assets/`. `server/` contains the FastAPI backend: `main.py` boots the app, `src/modules/` holds route logic, `db/schema.sql` defines the database, and `tests/` cover API behavior. `termux/` contains the Android worker scripts, and `server/termux/` serves those files through `/install`; keep both copies in sync. `train/` stores the notebook for `server/src/model/sleep_model.pkl`, and `docs/` holds deployment notes.

## Build, Test, and Development Commands
Flutter app:
- `cd SmartWakeApp && flutter pub get` installs app dependencies.
- `cd SmartWakeApp && flutter analyze` runs the enforced lint set.
- `cd SmartWakeApp && flutter test` runs Dart tests.
- `cd SmartWakeApp && flutter run --dart-define=SMARTWAKE_API_KEY=...` starts the Android app locally.

Backend:
- `cd server && python -m venv .venv && source .venv/bin/activate` creates a Python environment.
- `cd server && pip install -r requirements.txt pytest` installs runtime and test dependencies.
- `cd server && API_KEY=dev-key BASE_URL=http://localhost:8000 DATABASE_URL=postgresql://... uvicorn main:app --reload` starts the API locally.
- `cd server && pytest` runs backend tests.

## Coding Style & Naming Conventions
Use Dart defaults in `SmartWakeApp/`: 2-space indentation, `PascalCase` for widgets/classes, `camelCase` for members, and `snake_case.dart` filenames. Respect `flutter_lints` in `analysis_options.yaml`, especially `prefer_const_*`, `use_key_in_widget_constructors`, and `avoid_print`. In Python, follow PEP 8 with 4-space indentation, `snake_case` modules/functions, and narrow route handlers that delegate validation and shared helpers to `server/src/modules/`.

## Testing Guidelines
Backend tests use `pytest` and `fastapi.testclient`; place new tests in `server/tests/test_*.py`. Prefer fixtures and `monkeypatch` to stub database and model behavior instead of hitting a live Postgres instance. No coverage threshold is configured, so cover every new endpoint, payload validator, and alarm/sleep state transition you change. Add Flutter tests under `SmartWakeApp/test/` for new UI or service logic.

## Commit & Pull Request Guidelines
Recent commits follow short, imperative subjects such as `refactor: improve sleep model loading...` or `Fix telemetry logging...`; keep that style and avoid one-word messages. PRs should state which layer changed, list env/config updates, link issues, and include screenshots for UI changes. If you modify worker scripts, call out whether both `termux/` and `server/termux/` were updated together.

## Security & Configuration Tips
Do not commit `.env` files, API keys, or database credentials. The backend requires `API_KEY` and database configuration via `DATABASE_URL` or `DB_*` variables; keep the same shared key in the server, Flutter app, and Termux workers.
