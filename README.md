# 🌱 Smart Krishi AI

**Smart Krishi AI** is an educational prototype designed to help farmers
explore crop recommendations using soil-related information and
illustrative crop economics.

## Features

-   Farmer registration and login
-   Farmer profile management
-   Soil and crop recommendation workflow
-   Prediction history
-   Administrator login and dashboard
-   MongoDB Atlas integration for persistent records
-   Flask-based web application with HTML templates and static assets

> **Note:** Recommendations and crop economics should be treated as
> educational/illustrative unless validated with reliable local
> agricultural data. This project is not a substitute for advice from an
> agricultural officer or soil-testing laboratory.

## Technology Stack

-   Python
-   Flask
-   HTML, CSS, JavaScript
-   MongoDB Atlas / PyMongo
-   Gunicorn for production hosting
-   Render for deployment

## Project Structure

``` text
Smart_Krishi_AI/
├── app.py
├── requirements.txt
├── data/
│   └── crop_data.csv
├── static/
├── templates/
│   ├── admin_login.html
│   ├── admin.html
│   ├── base.html
│   ├── dashboard.html
│   ├── history.html
│   ├── login.html
│   ├── profile.html
│   └── register.html
├── .env                 # Local secrets; do not commit
├── .gitignore
└── README.md
```

## Run Locally

### 1. Requirements

Install Python and Git. MongoDB Atlas is needed for database-backed
persistent records.

### 2. Open the project folder

Open a terminal in the folder containing `app.py`.

### 3. Create and activate a virtual environment (optional)

**Windows PowerShell:**

``` powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

``` bash
pip install -r requirements.txt
```

Make sure `requirements.txt` includes all dependencies imported by the
app, including Flask, `python-dotenv`, `pymongo` if used, and the
production server package needed for your environment.

### 5. Configure environment variables

Create a local `.env` file in the project root. Use your own values:

``` dotenv
FLASK_SECRET_KEY=replace_with_a_long_random_secret
MONGODB_URI=replace_with_your_mongodb_atlas_connection_string
MONGODB_DB=smart_agriculture
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=replace_with_a_strong_unique_password
```

-   Replace the example values with your own.
-   Do not commit `.env` to GitHub.
-   Never publish your MongoDB connection string or administrator
    password.
-   The database name must match the name expected by your app.

### 6. Start the application

If your Flask app object is named `app` in `app.py`, run:

``` bash
python app.py
```

Open the local URL printed in the terminal, commonly
`http://127.0.0.1:5000`.

## Deploy to Render

1.  Push the project to a GitHub repository.

2.  In the [Render Dashboard](https://dashboard.render.com/), select
    **New → Web Service** and connect the repository.

3.  Set the branch to `main` (or the branch you use).

4.  Set the build command:

    ``` bash
    pip install -r requirements.txt
    ```

5.  Set the start command, assuming the Flask instance is named `app` in
    `app.py`:

    ``` bash
    gunicorn app:app
    ```

6.  In the Render service's **Environment** settings, add these
    variables using your own secret values:

      -----------------------------------------------------------------------
      Key                                 Value
      ----------------------------------- -----------------------------------
      `MONGODB_URI`                       Your MongoDB Atlas connection
                                          string

      `MONGODB_DB`                        `smart_agriculture` (if this is the
                                          database used by your app)

      `FLASK_SECRET_KEY`                  A long, random secret

      `ADMIN_EMAIL`                       Your chosen administrator email

      `ADMIN_PASSWORD`                    A strong, unique administrator
                                          password
      -----------------------------------------------------------------------

7.  Save the environment variables and deploy. Check the Render logs for
    startup errors and confirm the application reports a successful
    MongoDB connection.

### MongoDB Atlas connectivity

-   Ensure the Atlas database user has the required permissions.
-   Ensure Atlas network access rules allow connections from the
    deployed service.
-   Prefer restricting network access where practical. Avoid broad
    network access rules unless needed for a temporary demo, and use
    strong credentials.
-   Confirm new records appear in the intended database after testing
    registration and predictions.

## Security Notes

-   Keep `.env` out of version control.
-   Use unique, strong administrator and database passwords.
-   Do not store credentials in source code or screenshots.
-   Use HTTPS through your hosting provider.
-   Validate inputs and apply appropriate authorization checks to
    administrative routes.
-   Avoid using real farmers' personal data in public demonstrations
    without permission.

## Troubleshooting

### Admin login says credentials are invalid

In Render, open the service's **Environment** settings and verify that
`ADMIN_EMAIL` and `ADMIN_PASSWORD` exist and are spelled exactly as
expected by `app.py`. Save changes and redeploy if needed. Enter the
same values on the admin login page.

### MongoDB connection fails

Check that `MONGODB_URI` is configured in Render, `MONGODB_DB` matches
the intended database, the connection string is correct, the Atlas
database user is valid, and network access rules permit the connection.
Never share the actual connection string publicly.

### Deployment succeeds but the site behaves incorrectly

Review the Render logs, verify that all dependencies are in
`requirements.txt`, confirm that `data/crop_data.csv` was committed, and
ensure the configured start command matches the Flask application
object.

## Educational Use

This project is intended for academic demonstration and learning.
Validate agronomic recommendations, soil thresholds, crop suitability,
and profit estimates with qualified agricultural sources before using
them for real farming decisions.
