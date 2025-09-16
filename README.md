## Setup Instructions

After cloning this repo,

Enter the 'linkedin_analytics' directory in a terminal session(`cd linkedin_analytics`) and then run:

```bash
python3 -m venv venv
```

Followed by:

```bash
source venv/bin/activate
```

This is to create and activate a virtual environment. Next step is to install the required dependencies by running:

```bash
pip install -r requirements.txt
```

After setting up Postgresql with an empty database, create a .env file with DB_URL, JWT secrets and algorithm. Sample .env:

```bash
DB_URL=postgresql://postgres:password@localhost:5432/postgres
JWT_ACCESS_SECRET=3775dc25d37bee774990c7a1bff78226
JWT_REFRESH_SECRET=6b4a403769e345a8b9a106c198a0b8fe
JWT_ALGORITHM=HS256
```

Now run:

```bash
alembic upgrade head
```

This will hopefully create all the tables with required schema.

To seed your first admin, run:

```bash
python seed_admin.py
```

Now, let's set up the Uvicorn server at _localhost:8000_ (or some other availabe port):

```bash
uvicorn main:app --reload --port 8000
```