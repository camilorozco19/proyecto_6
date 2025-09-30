import pandas as pd

def analyze_opportunities(df, include_markers=False):
    if 'categories' not in df.columns:
        return ('', {'error': 'El archivo no tiene columna categories.'}, [])

    # Separar categorías
    s = df['categories'].fillna('')
    s = s.str.split(',').apply(lambda xs: [x.strip() for x in xs if x.strip()])

    # Expandir DataFrame
    exploded = df.loc[s.index].copy()
    exploded = exploded.assign(category_list=s)
    exploded = exploded.explode('category_list')

    # ----------------------------
    # Manejo flexible de reseñas
    # ----------------------------
    if 'review_count' in exploded.columns:
        # Caso business.json
        grouped = exploded.groupby('category_list').agg(
            businesses_count=('business_id', 'count'),
            avg_reviews=('review_count', 'mean'),
            total_reviews=('review_count', 'sum')
        ).reset_index().rename(columns={'category_list': 'category'})
    else:
        # Caso review.json → contamos reseñas
        reviews_per_business = df.groupby('business_id').size().reset_index(name='reviews')
        merged = exploded.merge(reviews_per_business, on='business_id', how='left').fillna({'reviews': 0})

        grouped = merged.groupby('category_list').agg(
            businesses_count=('business_id', 'count'),
            avg_reviews=('reviews', 'mean'),
            total_reviews=('reviews', 'sum')
        ).reset_index().rename(columns={'category_list': 'category'})

    # Calcular oportunidad
    grouped['opportunity'] = grouped['avg_reviews'] / (grouped['businesses_count'] + 1)

    # Ordenar
    result = grouped.sort_values('opportunity', ascending=False).head(10)

    # Renombrar columnas
    result = result.rename(columns={
        'category': 'Categoría',
        'businesses_count': 'Cantidad de negocios',
        'avg_reviews': 'Promedio de reseñas',
        'total_reviews': 'Total de reseñas',
        'opportunity': 'Oportunidad'
    })

    # Convertir tabla
    table_html = result.to_html(classes="table table-striped", index=False)

    # 📌 Generar recomendación automática
    best_row = result.iloc[0] if not result.empty else None
    recommendation = "No hay datos suficientes para generar una recomendación."
    if best_row is not None:
        categoria = best_row["Categoría"]
        negocios = int(best_row["Cantidad de negocios"])
        promedio = round(best_row["Promedio de reseñas"], 1)
        oportunidad = round(best_row["Oportunidad"], 2)

        recommendation = (
            f"La categoría con mayor potencial de inversión es **{categoria}**. "
            f"Actualmente existen {negocios} negocios en este sector, con un promedio de {promedio} reseñas. "
            f"El índice de oportunidad calculado es {oportunidad}. "
            f"Esto sugiere que abrir un nuevo negocio en esta categoría podría captar la demanda insatisfecha."
        )

    summary = {
        "note": "Se muestran las categorías con mayor oportunidad calculada.",
        "recommendation": recommendation
    }

    # Marcadores (mapa)
    markers = []
    if include_markers and 'latitude' in df.columns and 'longitude' in df.columns:
        for _, row in df.iterrows():
            if pd.notnull(row.get('latitude')) and pd.notnull(row.get('longitude')):
                markers.append({
                    "lat": row['latitude'],
                    "lon": row['longitude'],
                    "name": row.get('name', ''),
                    "categories": row.get('categories', ''),
                    "reviews": row.get('review_count', row.get('reviews', 0)),
                    "city": row.get('city', '')
                })

    return table_html, summary, markers
