import os

def make_sample(infile, outfile, n_lines=10000):
    """Toma las primeras n_lines de infile y las guarda en outfile."""
    with open(infile, 'r', encoding='utf-8') as fin, open(outfile, 'w', encoding='utf-8') as fout:
        for i, line in enumerate(fin):
            if i >= n_lines:
                break
            fout.write(line)

if __name__ == "__main__":
    # Crear carpeta uploads si no existe
    os.makedirs("uploads", exist_ok=True)

    # Guardar los subconjuntos directamente en uploads/
    make_sample("business.json", os.path.join("uploads", "business_sample.json"), n_lines=5000)
    make_sample("review.json", os.path.join("uploads", "review_sample.json"), n_lines=10000)

    print("✅ Subconjuntos creados en la carpeta 'uploads/'")
    print("   - uploads/business_sample.json")
    print("   - uploads/review_sample.json")
