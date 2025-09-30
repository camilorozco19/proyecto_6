from flask_swagger_ui import get_swaggerui_blueprint
from flask import Flask, render_template, request, redirect, jsonify, send_from_directory, url_for, session, flash
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
from werkzeug.utils import secure_filename
import os, json, bcrypt, pandas as pd
from pathlib import Path

from data_handler import (
    save_uploaded_file, get_last_dataframe,
    save_yelp_business_json, save_yelp_review_json,
    get_business_from_db, get_review_from_db   # 👈 añadido
)
from models import analyze_opportunities
from demand_analysis import analyze_reviews_from_df

BASE_DIR = os.path.dirname(__file__)
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
STORAGE = Path(__file__).parent / 'storage'
STORAGE.mkdir(exist_ok=True)

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'cambiame_por_una_clave_segura'
app.secret_key = 'cambiame_por_otra_clave_segura'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

jwt = JWTManager(app)

# Usuarios demo con contraseñas hasheadas con bcrypt
USERS = {
    'admin': {'password_hash': '$2b$12$yjQ7TDnXJU91kyFa64VH6O1.Ih2n25IUufg56FfG1V1f2PnDMLw0C', 'role': 'admin'},
    'analyst': {'password_hash': '$2b$12$RXkQTH6cOygQXZzLz3auoOvfyUp2.9zK6xqLKrvXDIA4ytG3IrIDK', 'role': 'analyst'},
    'entrepreneur': {'password_hash': '$2b$12$bEHyRSLyobRO8zVtjD446.efCTiEHNmE6G6NZdkxwrew1oKCM.buu', 'role': 'entrepreneur'}
}

# Swagger
SWAGGER_URL = '/api/docs'
API_URL = '/swagger.json'
swaggerui_blueprint = get_swaggerui_blueprint(SWAGGER_URL, API_URL, config={'app_name':"Sistema DSS - API"})
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

@app.route('/swagger.json')
def swagger_json():
    return send_from_directory('.', 'swagger.json')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET','POST'])
def login_page():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password', '')
        user = USERS.get(username)
        if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            flash('Usuario o contraseña incorrectos', 'danger')
            return redirect(url_for('login_page'))
        session['user'] = username
        session['role'] = user['role']
        flash(f'Bienvenido {username}', 'success')
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada', 'info')
    return redirect(url_for('index'))

# 🚀 Subida de múltiples archivos
@app.route('/upload', methods=['GET','POST'])
def upload_page():
    if 'user' not in session:
        return redirect(url_for('login_page'))

    if request.method == 'POST':
        files = request.files.getlist('file')
        if not files or files == [None]:
            flash("⚠️ No se seleccionó ningún archivo", "danger")
            return redirect(url_for('upload_page'))

        for f in files:
            if not f or f.filename == "":
                continue

            filename = secure_filename(f.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            f.save(file_path)

            try:
                lower = filename.lower()
                if lower.endswith('.json') and 'business' in lower:
                    save_yelp_business_json(file_path)
                    flash(f"✅ Archivo {filename} (business) procesado correctamente.", "success")
                elif lower.endswith('.json') and 'review' in lower:
                    save_yelp_review_json(file_path)
                    flash(f"✅ Archivo {filename} (review) procesado correctamente.", "success")
                else:
                    save_uploaded_file(file_path)
                    flash(f"✅ Archivo {filename} procesado correctamente.", "success")
            except Exception as e:
                flash(f"❌ Error al procesar {filename}: {str(e)}", "danger")

        return redirect(url_for('upload_page'))

    return render_template('upload.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    username = data.get('username'); password = data.get('password','')
    user = USERS.get(username)
    if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        return jsonify({'msg':'usuario o contraseña inválidos'}), 401
    token = create_access_token(identity={'username': username, 'role': user['role']})
    return jsonify({'access_token': token})

def require_login_browser():
    return 'user' in session

@app.route('/analysis')
def analysis_page():
    if not require_login_browser():
        return redirect(url_for('login_page'))
    df = get_last_dataframe()
    if df is None:
        return render_template('analysis.html', error='No hay datos cargados todavía.')
    table_html, summary, markers = analyze_opportunities(df, include_markers=True)
    return render_template('analysis.html', table_html=table_html, summary=summary, markers=json.dumps(markers))

@app.route('/api/analysis')
@jwt_required()
def api_analysis():
    df = get_last_dataframe()
    if df is None:
        return jsonify({'msg':'no data uploaded'}), 400
    table_html, summary, markers = analyze_opportunities(df, include_markers=True)
    return jsonify({'summary': summary, 'table_html': table_html, 'markers': markers})

# Demand analysis UI
@app.route('/demand')
def demand_page():
    if not require_login_browser():
        return redirect(url_for('login_page'))

    try:
        df = get_review_from_db()
    except Exception:
        return render_template('demand.html', error='No se encontraron reseñas en la base de datos (sube review.json).')

    if df is None or df.empty:
        return render_template('demand.html', error='No se encontraron reseñas en la base de datos (sube review.json).')

    results = analyze_reviews_from_df(df)
    return render_template(
        'demand.html',
        wordcloud=results['wordcloud_b64'],
        avg_sentiment=results['avg_sentiment'],
        time_series=results['time_series'],
        topics=results['topics']
    )

# Gap analysis UI
@app.route('/gap')
def gap_page():
    if not require_login_browser():
        return redirect(url_for('login_page'))

    try:
        bdf = get_business_from_db()
        rdf = get_review_from_db()
    except Exception:
        return render_template('gap.html', error='No hay datos en la base de datos (sube business.json y review.json).')

    if bdf is None or rdf is None or bdf.empty or rdf.empty:
        return render_template('gap.html', error='No hay datos en la base de datos (sube business.json y review.json).')

    # 🔹 Explota categorías
    s = bdf['categories'].fillna('').str.split(',').apply(lambda xs: [x.strip() for x in xs if x.strip()])
    exploded = bdf.assign(category_list=s).explode('category_list')

    # 🔹 Oferta
    cat_supply = exploded.groupby('category_list').agg(supply=('business_id','count')).reset_index()

    # 🔹 Demanda
    reviews_per_business = rdf.groupby('business_id').size().reset_index(name='reviews')
    merged = exploded.merge(reviews_per_business, on='business_id', how='left').fillna({'reviews':0})
    cat_demand = merged.groupby('category_list').agg(demand=('reviews','sum')).reset_index()

    # 🔹 Brecha
    gap = cat_supply.merge(cat_demand, on='category_list', how='outer').fillna(0)
    gap['gap'] = gap['demand'] - gap['supply']

    gap = gap.rename(columns={
        'category_list': 'Categoría',
        'supply': 'Cantidad de negocios (Oferta)',
        'demand': 'Cantidad de reseñas (Demanda)',
        'gap': 'Brecha (Demanda - Oferta)'
    })

    gap_sorted = gap.sort_values('Brecha (Demanda - Oferta)', ascending=False).head(10)

    best_row = gap_sorted.iloc[0] if not gap_sorted.empty else None
    recomendacion = "No hay datos suficientes para generar una recomendación."
    if best_row is not None:
        categoria = best_row["Categoría"]
        oferta = int(best_row["Cantidad de negocios (Oferta)"])
        demanda = int(best_row["Cantidad de reseñas (Demanda)"])
        brecha = int(best_row["Brecha (Demanda - Oferta)"])
        recomendacion = (
            f"La categoría con mayor oportunidad es **{categoria}**. "
            f"Actualmente existen {oferta} negocios frente a una demanda de {demanda} reseñas. "
            f"Esto genera una brecha de {brecha}, lo que indica una oportunidad clara."
        )

    table_html = gap_sorted.to_html(
        index=False,
        classes="table table-striped table-hover table-bordered text-center"
    )

    chart_labels = gap_sorted["Categoría"].tolist()
    chart_data = gap_sorted["Brecha (Demanda - Oferta)"].tolist()

    return render_template(
        'gap.html',
        table_html=table_html,
        recomendacion=recomendacion,
        chart_labels=chart_labels,
        chart_data=chart_data
    )

# API demand
@app.route('/api/demand')
@jwt_required()
def api_demand():
    try:
        df = get_review_from_db()
    except Exception:
        return jsonify({'msg':'no reviews in database'}), 400

    if df is None or df.empty:
        return jsonify({'msg':'no reviews in database'}), 400

    results = analyze_reviews_from_df(df)
    return jsonify(results)

# API gap
@app.route('/api/gap')
@jwt_required()
def api_gap():
    try:
        bdf = get_business_from_db()
        rdf = get_review_from_db()
    except Exception:
        return jsonify({'msg':'missing data in database'}), 400

    if bdf is None or rdf is None or bdf.empty or rdf.empty:
        return jsonify({'msg':'missing data in database'}), 400

    s = bdf['categories'].fillna('').str.split(',').apply(lambda xs: [x.strip() for x in xs if x.strip()])
    exploded = bdf.assign(category_list=s).explode('category_list')

    cat_supply = exploded.groupby('category_list').agg(supply=('business_id','count')).reset_index()

    reviews_per_business = rdf.groupby('business_id').size().reset_index(name='reviews')
    merged = exploded.merge(reviews_per_business, on='business_id', how='left').fillna({'reviews':0})
    cat_demand = merged.groupby('category_list').agg(demand=('reviews','sum')).reset_index()

    gap = cat_supply.merge(cat_demand, on='category_list', how='outer').fillna(0)
    gap['gap'] = gap['demand'] - gap['supply']

    out = gap.sort_values('gap', ascending=False).to_dict(orient='records')
    return jsonify({'gap': out})

# Descarga del histórico
@app.route('/download/history')
def download_history():
    fp = STORAGE / 'all_data.xlsx'
    if fp.exists():
        return send_from_directory(str(fp.parent), fp.name, as_attachment=True)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
