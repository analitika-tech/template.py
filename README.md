# Voney.ML

Contains the business logic for the saving and retreving invoices, extracting invoice data from images, legal stuff required by Google and Apple to be served on url (privacy policy and product data).

### Setup
1. Install Docker

    Download Docker on [this link](https://www.docker.com/products/docker-desktop/) or installit using the script **(linux)**:
    ```sh
    curl https://get.docker.com/ | sh
    ```

2. Setup environment variables
    
    Contact someone on Backend (BE) team to get you the env variables and past them into the `.docker.env` file in the `root` of your project

3. Run the containers

    Run container in developemnt (supports hot reload so if any changes are made the container will hot reload):
    ```bash
    docker compose -f compose/debug/docker-compose.yml down && docker compose -f compose/debug/docker-compose.yml up --build
    ```

4. Access to Swagger
    ```
    http://localhost:8000/docs
    ```

5. [Apply migrations](#migrations)

    > Go under the **Apply Migrations** and run the command from within the container, to get access to the container follow the steps:
    ```sh
    # Get list of containers
    $ docker ps

    CONTAINER ID   IMAGE                COMMAND                  CREATED          STATUS        PORTS                              NAMES
    0e70daeca417   minio/minio:latest   "/usr/bin/docker-ent…"   13 seconds ago   Up 1 second   0.0.0.0:9000-9001->9000-9001/tcp   s3
    caf0e18fe330   postgres             "docker-entrypoint.s…"   13 seconds ago   Up 1 second   0.0.0.0:5432->5432/tcp             db
    e6032645b3fa   debug-api            "make run-debug"         13 seconds ago   Up 1 second   8000/tcp, 0.0.0.0:8000->80/tcp     voney.ml # 🔴 here it is

    # Take the id of the CONTAINER_ID of container voney.ml in this case
    $ docker exec -it e6032645b3fa sh

    # 

    # Now you are in the console and can execute commands from within
    # Apply migrations
    # uv run alembic upgrade head
    ```
6. Continue to next steps to create your own user

#### How to get access token as Google user?
> Prequest for this is `googl's client_id` you can find it in your .docker.env
```sh
# Go to swagger on http://localhost:8000/docs or curl 
curl -X 'POST' \
  'http://localhost:8000/api/identity/signin/redirect' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "client_id": "..."
}'

# You'll recieve response something like this:
{
  "succeeded": true,
  "data": "https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id=...&redirect_uri=http://localhost:8000/api/identity/signin/redirect/callback/deeplink&scope=openid%20profile%20email&aacess_type=offline",
  "errors": [],
  "info": null
}

# Copy the "data" property value and paste it into your browser, then you'll get the Google SignUp screen where you select or login account which you want to use

# Go to your Docker Compose Console and find the log:
voney.ml  | 2025-04-03 11:25:27,255 - uvicorn.access - INFO - 172.18.0.1:55394 - "GET /api/identity/signin/redirect/callback/deeplink?code=4%2F0Ab_5qlkOTlqN9YhjvojSwt1DIkyCiY5HyUh7MEvFPdFd3Z5GpZu9MY1QkF-0-8NtcQBWwQ&scope=email+profile+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fuserinfo.email+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fuserinfo.profile+openid&authuser=0&prompt=none HTTP/1.1" 307

# From here you will copy the ?code= query param value, in this case 4%2F0Ab_5qlkOTlqN9YhjvojSwt1DIkyCiY5HyUh7MEvFPdFd3Z5GpZu9MY1QkF-0-8NtcQBWwQ and paste it into the endpoint: /api/identity/signin/redirect/callback

# DISCLAIMER KEEP IN MIND THAT THE CODE PARAM IS STRINGIFIED AND IN THE CASE OF THIS CODE YOU SEE IN THE BEGINNING THAT THE CODE %2F=/ REPLACE THAT AND YOU GOOD TO GO 

curl -X 'POST' \
  'http://localhost:8000/api/identity/signin/redirect/callback?code=4/0Ab_5qlkOTlqN9YhjvojSwt1DIkyCiY5HyUh7MEvFPdFd3Z5GpZu9MY1QkF-0-8NtcQBWwQ' \
  -H 'accept: application/json' \
  -d ''

# Response
{
  "succeeded": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJnaXZlbl9uYW1lIjoiRFx1MDE3ZWVuYW4iLCJmYW1pbHlfbmFtZSI6IkRcdTAxN2VhZmlcdTAxMDciLCJlbWFpbCI6ImR6ZW5vLmR6YWZpY0BnbWFpbC5jb20iLCJzdWIiOiIyYjdiYzEyMC0wZGJiLTQ1YWUtOGE1Yy0wNWU2NmQyZTdmZWYiLCJpZHAiOiJnb29nbGUiLCJleHAiOjE3NDM2ODMzNDcsImlhdCI6MTc0MzY3OTc0N30.amrjJowqitFBOcxq2-oQNFEG86oLE-KQIXMCmCdHbD8",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6ImR6ZW5vLmR6YWZpY0BnbWFpbC5jb20iLCJzdWIiOiIyYjdiYzEyMC0wZGJiLTQ1YWUtOGE1Yy0wNWU2NmQyZTdmZWYiLCJpZHAiOiJnb29nbGUiLCJleHAiOjE3NDYyNzE3NDcsImlhdCI6MTc0MzY3OTc0NywidG9rZW5fdHlwZSI6InJlZnJlc2gifQ.w-4T28qS0snHRWHV_jFE7LUKUGmVwJQ-31-DWIMe2Y8",
    "expires_in": 3600,
    "token_type": "Bearer",
    "id_token": null
  },
  "errors": [],
  "info": null
}
```

## Testing
Access test under the `tests` folder, currently we have basic tests but in the future this block will be updated and expanded as the procedures evolve. For now write tests for your specific functionality, at least go through the happy flow.
 
## Code formatting

```bash
pip install black

black .
```

## Database
Install the necessary tooling for postgres from this [link](https://www.postgresql.org/download/), you'll need **pg_dump** to restore the db to your local db.

Tutorial from Dev db:
```sh
# Command will dump raw sql queries into restore.sql
pg_dump -Fc "*** CONNECTION STRING ***" > restore.sql

# to restore the db run following:
pg_restore -d "postgresql://admin:admin@localhost:5432/InvoiceDb" restore.sql

```

Connect to db over terminal:
```sh
psql -h <REMOTE HOST> -p <REMOTE PORT> -U <DB_USER> <DB_NAME>
# psql -h localhost -p 5432 -U admin InvoiceDb
# .... it will propt you to insert the password: admin
# .... InvoiceDb=#
# .... prequest is the psql tool
```

### Migrations

1. Adding:
    ```bash
    # if you are using the env
    alembic revision --autogenerate -m "name of migration"

    # if not prefix the command above with 
    uv run alembic revision --autogenerate -m "name of migration"
    ```

2. Applying:
    ```bash
    # if you are using the env
    alembic upgrade head

    # if not prefix the command above with 
    uv run alembic upgrade head
    ```

3. Reverting latest:
    ```bash
    # if you are using the env
    alembic downgrade -1

    # if not prefix the command above with 
    uv run alembic downgrade -1
    ```



