from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Spacer, SimpleDocTemplate, PageBreak
from reportlab.lib.units import inch
import json
import os
from poem_utils import Poem  # Ensure this imports correctly with necessary methods

def create_pdf(poems, filename='The_Paris_Review_Anthology.pdf'):
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()

    # Define custom styles for the title, author, and body
    title_style = styles['Title']
    title_style.alignment = 1  # Center alignment
    title_style.fontSize = 16
    title_style.spaceAfter = 6

    author_style = ParagraphStyle('author', parent=styles['Italic'], fontSize=12, alignment=1, spaceAfter=12)

    body_style = styles['BodyText']
    body_style.fontSize = 12

    issue_style = ParagraphStyle('issue', parent=styles['Italic'], fontSize=10, spaceBefore=12)

    elements = []

    for poem in poems:
        title = Paragraph(f"{poem.title}", title_style)
        author = Paragraph(f"by {poem.author}", author_style)
        body = Paragraph(poem.body.replace('\r\n', '<br/>'), body_style)
        metadata = Paragraph(f"{poem.issue}<br/>Sent: {poem.sent_date}", issue_style)

        elements.append(title)
        elements.append(author)
        elements.append(Spacer(1, 0.2 * inch))
        elements.append(body)
        elements.append(Spacer(1, 0.2 * inch))
        elements.append(metadata)
        elements.append(PageBreak())

    doc.build(elements)

def load_poems(directory="saved_poems"):
    poems = []
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            with open(os.path.join(directory, filename), 'r') as file:
                poem_data = json.load(file)
                poem = Poem(**poem_data)  # Ensure Poem can be initialized like this
                poems.append(poem)
    return poems

if __name__ == "__main__":
    poems = load_poems()
    create_pdf(poems)