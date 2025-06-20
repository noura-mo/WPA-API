import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    df = pd.read_csv("Final dataset.csv")
    df['strength_value'] = pd.to_numeric(df['strength_value'], errors='coerce').fillna(0)
    df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
except Exception as e:
    print(f"Error loading file: {e}")
    df = pd.DataFrame()

class MedicineRequest(BaseModel):
    active_ingredient: str
    strength: float
    form: str

def calculate_priority(active_match, strength_diff, form_match, med_price, strength_input):
    if active_match == 1 and form_match == 1 and strength_diff == 0:
        return 100.0
    strength_percentage = (1 - strength_diff / strength_input) * 100 if strength_diff != float('inf') else 0
    price_factor = (1 / (1 + np.log1p(med_price))) * 100 if med_price > 0 and not np.isnan(med_price) else 0
    priority_score = (0.5 * (active_match * 100)) + (0.2 * strength_percentage) + (0.2 * form_match * 100) + (0.1 * price_factor)
    return round(priority_score, 2)

def find_medicines(active_ingredient, strength, form):
    priority_list = []
    for _, row in df.iterrows():
        med_strength = row['strength_value']
        med_price = row['price'] if pd.notna(row['price']) else float('inf')
        usage = row['Uses'] if 'Uses' in df.columns and pd.notna(row['Uses']) else "N/A"

        strength_diff = abs(med_strength - strength)
        active_match = 1 if pd.notna(row['composition']) and active_ingredient.lower() in row['composition'].lower() else 0

        form_match = 0
        if pd.notna(row['form']):
            form_values = [f.strip().lower() for f in str(row['form']).split(',')]
            if form.lower() in form_values:
                form_match = 1

        priority = calculate_priority(active_match, strength_diff, form_match, med_price, strength)

        if active_match:
            priority_list.append({
                "Trade Name": row['Medicine Name'],
                "Active Ingredient": row['composition'],
                "Strength": f"{med_strength}mg",
                "Pharmaceutical Form": row['form'],
                "Priority": priority,
                "Price (EGP)": round(med_price, 2),
                "Indication": usage
            })

    return sorted(priority_list, key=lambda x: (-x["Priority"], x["Price (EGP)"]))

@app.post("/get_best_medicine")
async def get_best_medicine(request: MedicineRequest):
    results = find_medicines(request.active_ingredient, request.strength, request.form)
    if not results:
        raise HTTPException(status_code=404, detail="No matching medicines found")
    return {"Available_medicines": results}
