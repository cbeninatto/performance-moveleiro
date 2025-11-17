import pandas as pd

# Load mapping table ---------------------------------------------------

def load_category_map(path="data/categorias_map.csv"):
    df = pd.read_csv(path)
    df["pattern"] = df["pattern"].astype(str).str.upper()
    df["categoria"] = df["categoria"].astype(str)
    df["prioridade"] = df["prioridade"].astype(int)
    df = df.sort_values("prioridade")
    return df

CATEGORY_MAP = load_category_map()

# Main classification function -----------------------------------------

def map_categoria(descricao: str) -> str:
    text = (str(descricao) or "").upper()
    
    for _, row in CATEGORY_MAP.iterrows():
        if row["pattern"] in text:
            return row["categoria"]
    
    return "Outros"
