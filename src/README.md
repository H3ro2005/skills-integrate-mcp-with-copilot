# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Sign up for activities

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Configure teacher authentication. Set these environment variables before starting the app:

   - `TEACHER_CREDENTIALS_JSON`: a JSON object mapping each teacher username to their unique password
   - `SESSION_SECRET`: a randomly generated secret used to sign login sessions
   - `COOKIE_SECURE`: set to `true` when serving the app over HTTPS; use `false` for local HTTP development

   For local development, put these values in the ignored `.env` file (create one in the workspace root). It should contain:

   ```
   TEACHER_CREDENTIALS_JSON='{"teacher":"replace-with-a-unique-password"}'
   SESSION_SECRET=paste-a-random-secret-here
   COOKIE_SECURE=false
   ```

   Generate a session secret with:

   ```
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

   `SESSION_SECRET` must be at least 32 bytes. Add one entry per teacher to `TEACHER_CREDENTIALS_JSON`. Keep all credentials out of tracked files.

3. Run the application:

   ```
   set -a
   . ./.env
   set +a
   uvicorn src.app:app --reload
   ```

   For production, use your deployment's secret manager and enable secure cookies. Do not commit credentials.

4. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

Students can view activities and participants without signing in. Teachers must log in to sign up or unregister students.

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Sign up for an activity                                             |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

All data is stored in memory, which means data will be reset when the server restarts.
