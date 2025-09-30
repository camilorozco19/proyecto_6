import pandas as pd, os
from pathlib import Path
from yelp_utils import extract_business_table, extract_reviews_table
from sqlalchemy import create_engine

# --- Configuración de storage y SQLite ---
storage = Path(__file__).parent / 'storage'
storage.mkdir(exist_ok=True)

last_data_csv = storage / 'last_data.csv'
all_data_xlsx = storage / 'all_data.xlsx'
sqlite_db = Path(__file__).parent / "dss.db"  # archivo SQLite local

# Conexión a SQLite con SQLAlchemy
engine = create_engine(f"sqlite:///{sqlite_db}")

# --- Funciones auxiliares ---
def save_to_sqlite(df, table_name):
    """Guarda un DataFrame en la base SQLite"""
    df.to_sql(table_name, engine, if_exists="replace", index=False)

def read_from_sqlite(table_name):
    """Lee una tabla de SQLite como DataFrame"""
    return pd.read_sql(f"SELECT * FROM {table_name}", engine)

# --- Funciones principales ---
def save_uploaded_file(filepath):
    try:
        if filepath.endswith('.csv'):
            df = pd.read_csv(filepath)
        elif filepath.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(filepath)
        elif filepath.endswith('.json'):
            name = Path(filepath).name.lower()
            if 'business' in name:
                df = extract_business_table(filepath)
            elif 'review' in name:
                df = extract_reviews_table(filepath)
            else:
                try:
                    df = pd.read_json(filepath)
                except ValueError:
                    df = pd.read_json(filepath, lines=True)
        else:
            df = pd.read_csv(filepath)
    except Exception as e:
        raise Exception(f"Error al procesar archivo: {e}")

    # normalizar nombres de columnas
    df.columns = [c.strip() for c in df.columns]

    # guardar last_data.csv
    if last_data_csv.exists():
        try:
            os.remove(last_data_csv)
        except Exception:
            pass
    df.to_csv(last_data_csv, index=False)

    # guardar historial en Excel (cada upload una hoja)
    sheet_name = Path(filepath).stem[:30]
    if all_data_xlsx.exists():
        with pd.ExcelWriter(all_data_xlsx, mode="a", engine="openpyxl", if_sheet_exists="replace") as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    else:
        with pd.ExcelWriter(all_data_xlsx, mode="w", engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    # guardar copias específicas + SQLite
    if Path(filepath).suffix == '.json' and 'review' in Path(filepath).name.lower():
        out = storage / 'review.csv'
        df.to_csv(out, index=False)
        save_to_sqlite(df, "review")

    if Path(filepath).suffix == '.json' and 'business' in Path(filepath).name.lower():
        out = storage / 'business.csv'
        df.to_csv(out, index=False)
        save_to_sqlite(df, "business")

    return True

def save_yelp_business_json(filepath, nrows=None):
    df = extract_business_table(filepath, nrows=nrows)
    # guardar last_data y Excel
    if last_data_csv.exists():
        try:
            os.remove(last_data_csv)
        except Exception:
            pass
    df.to_csv(last_data_csv, index=False)
    sheet_name = Path(filepath).stem[:30]
    if all_data_xlsx.exists():
        with pd.ExcelWriter(all_data_xlsx, mode="a", engine="openpyxl", if_sheet_exists="replace") as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    else:
        with pd.ExcelWriter(all_data_xlsx, mode="w", engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    # guardar business.csv y SQLite
    df.to_csv(storage / 'business.csv', index=False)
    save_to_sqlite(df, "business")
    return df

def save_yelp_review_json(filepath, nrows=None):
    df = extract_reviews_table(filepath, nrows=nrows)
    outpath = storage / 'review.csv'
    df.to_csv(outpath, index=False)
    save_to_sqlite(df, "review")
    return df

def get_last_dataframe():
    if last_data_csv.exists():
        return pd.read_csv(last_data_csv)
    return None

def get_business_from_db():
    return read_from_sqlite("business")

def get_review_from_db():
    return read_from_sqlite("review")
