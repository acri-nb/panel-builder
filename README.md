# panel-builder
## Database configuration

Set `DATABASE_URL` to your PostgreSQL connection URL before starting the backend. The loader scripts that use psycopg2 accept a PostgreSQL password through `PGPASSWORD` or a PostgreSQL password file.

The data processing and loader scripts use local source or generated datasets. Check the file paths in each script before running it.
