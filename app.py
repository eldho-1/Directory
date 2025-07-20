from flask import Flask, render_template, request, send_file
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import blue, black, red
from io import BytesIO
import zipfile
from werkzeug.utils import secure_filename

app = Flask(__name__)

def wrap_text(text, font_name, font_size, canvas_obj, max_width):
    words = text.split()
    lines = []
    line = ''
    for word in words:
        test_line = (line + ' ' + word).strip()
        if canvas_obj.stringWidth(test_line, font_name, font_size) <= max_width:
            line = test_line
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines

def remove_empty_columns(df):
    return df.dropna(axis=1, how='all')

def generate_paragraph_directory(df):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    margin = 50
    y = height - 60
    line_height = 16
    paragraph_gap = 20
    max_width = width - 2 * margin
    family_number = 1

    # Title
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(black)
    c.drawCentredString(width / 2, height - 40, "DIRECTORY")

    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width / 2, height - 60, "ST MARY'S BETHLEHEM ORTHODOX CHURCH, KULAPPARACHAL")

    y -= 30

    for _, row in df.iterrows():
        inserted_family_label = False

        for col in df.columns:
            value = str(row[col]).strip()
            if value and value.lower() != 'nan':

                # Insert "Family N" before Timestamp
                if not inserted_family_label and "timestamp" in col.lower():
                    c.setFont("Helvetica-Bold", 12)
                    c.setFillColor(red)
                    c.drawString(margin, y, f"Family {family_number}:")
                    y -= line_height
                    inserted_family_label = True

                # Column label
                c.setFont("Helvetica-Bold", 11)
                c.setFillColor(black)
                label_lines = wrap_text(f"{col}:", "Helvetica-Bold", 11, c, max_width)
                for line in label_lines:
                    c.drawString(margin, y, line)
                    y -= line_height
                    if y < 60:
                        c.showPage()
                        y = height - 60

                # Column value
                if "photo" in col.lower() or value.startswith("http"):
                    c.setFillColor(blue)
                else:
                    c.setFillColor(black)

                c.setFont("Helvetica", 10)
                value_lines = wrap_text(value, "Helvetica", 10, c, max_width)
                for line in value_lines:
                    c.drawString(margin + 20, y, line)
                    y -= line_height
                    if y < 60:
                        c.showPage()
                        y = height - 60

                y -= 6

        # If Timestamp wasn't found, still insert "Family N" at top
        if not inserted_family_label:
            c.setFont("Helvetica-Bold", 12)
            c.setFillColor(red)
            c.drawString(margin, y, f"Family {family_number}:")
            y -= line_height

        y -= paragraph_gap
        if y < 60:
            c.showPage()
            y = height - 60

        family_number += 1

    c.save()
    buffer.seek(0)
    return buffer

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        uploaded_file = request.files['csv_file']
        if uploaded_file:
            filename = secure_filename(uploaded_file.filename)

            try:
                if filename.endswith('.zip'):
                    with zipfile.ZipFile(uploaded_file) as zip_file:
                        csv_files = [f for f in zip_file.namelist() if f.endswith('.csv')]
                        if not csv_files:
                            return "No CSV file found in ZIP.", 400
                        with zip_file.open(csv_files[0]) as csv_file:
                            df = pd.read_csv(csv_file)
                elif filename.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    return "Please upload a CSV or ZIP file containing a CSV.", 400
            except Exception as e:
                return f"Error reading file: {str(e)}", 500

            cleaned_df = remove_empty_columns(df)
            pdf_file = generate_paragraph_directory(cleaned_df)
            return send_file(pdf_file, as_attachment=True, download_name="directory.pdf", mimetype='application/pdf')

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
