from app.database import engine
from sqlalchemy import inspect

inspector = inspect(engine)
columns = inspector.get_columns('patients')
print('Current patient table columns:')
for col in columns:
    print(f'  - {col["name"]}: {col["type"]}')
