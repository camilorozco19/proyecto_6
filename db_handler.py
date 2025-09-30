# db_handler.py
import pandas as pd
from sqlalchemy import create_engine

# Conexión a SQLite (se crea un archivo local dss.db en tu carpeta del proyecto)
engine = create_engine("sqlite:///dss.db")

def save_dataframe_to_db(df, table_name):
    """Guarda un DataFrame en SQLite (crea tabla si no existe)"""
    df.to_sql(table_name, engine, if_exists="replace", index=False)

def read_table_from_db(table_name):
    """Lee una tabla de SQLite y la devuelve como DataFrame"""
    return pd.read_sql(f"SELECT * FROM {table_name}", engine)
