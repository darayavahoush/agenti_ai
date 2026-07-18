import psycopg2
import sys

# Test connection with different credentials
configs = [
    {
        "name": "vaaksiddhi (password)",
        "host": "localhost",
        "port": 5433,
        "user": "postgres",
        "password": "password",
        "database": "vaaksiddhi"
    },
    {
        "name": "vaaksudhi (Lavanya123)",
        "host": "localhost",
        "port": 5433,
        "user": "postgres",
        "password": "Lavanya123",
        "database": "vaaksudhi"
    },
    {
        "name": "postgres (password)",
        "host": "localhost",
        "port": 5433,
        "user": "postgres",
        "password": "password",
        "database": "postgres"
    },
]

for config in configs:
    try:
        conn = psycopg2.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            database=config["database"]
        )
        print(f"✅ Successfully connected to: {config['name']}")
        conn.close()
        sys.exit(0)
    except psycopg2.OperationalError as e:
        print(f"❌ Failed to connect to {config['name']}: {e}")
    except Exception as e:
        print(f"❌ Error with {config['name']}: {e}")

print("\n⚠️ Could not connect to any database configuration")
print("Please check:")
print("1. PostgreSQL is running (it is)")
print("2. Database credentials are correct")
print("3. Database exists")
