import os
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from django.core.mail import EmailMessage
from django.conf import settings

def get_logo_filename():
    """
    Finds the most recently modified logo file in core/static/core.
    Supports png, jpg, jpeg, webp, gif, svg, bmp.
    """
    valid_exts = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".bmp"}
    static_core_dir = os.path.join(settings.BASE_DIR, "core", "static", "core")
    
    if not os.path.exists(static_core_dir):
        return "logo.png"
        
    logo_files = []
    for f in os.listdir(static_core_dir):
        if f.lower().startswith("logo."):
            ext = os.path.splitext(f.lower())[1]
            if ext in valid_exts:
                filepath = os.path.join(static_core_dir, f)
                if os.path.isfile(filepath):
                    try:
                        mtime = os.path.getmtime(filepath)
                        logo_files.append((f, mtime))
                    except OSError:
                        pass
                        
    if logo_files:
        # Sort by mtime descending (newest first)
        logo_files.sort(key=lambda x: x[1], reverse=True)
        return logo_files[0][0]
        
    return "logo.png"

def generate_and_send_interview_report(session, turns, score, feedback):
    # 1. Generate PDF
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    exports_dir = os.path.join(settings.BASE_DIR, "exports")
    os.makedirs(exports_dir, exist_ok=True)
    pdf_filename = f"report_{session.session_id}_{ts}.pdf"
    pdf_path = os.path.join(exports_dir, pdf_filename)
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#6c5ce7'),
        alignment=0, # Left
        spaceAfter=10
    )
    
    section_heading = ParagraphStyle(
        'SecHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#1a1a2e'),
        spaceBefore=12,
        spaceAfter=8
    )
    
    normal_bold = ParagraphStyle(
        'NormalBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#4a5068')
    )
    
    body_text = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1a1a2e')
    )
    
    story = []
    
    # Left-side top corner Logo in PDF
    logo_filename = get_logo_filename()
    static_core_dir = os.path.join(settings.BASE_DIR, "core", "static", "core")
    logo_path = os.path.join(static_core_dir, logo_filename)
    if os.path.exists(logo_path):
        try:
            from PIL import Image as PILImage
            with PILImage.open(logo_path) as img:
                img_w, img_h = img.size
            aspect = img_w / img_h
            
            # Maintain aspect ratio with a target height of 35
            logo_height = 35
            logo_width = logo_height * aspect
            
            # Cap the maximum width to prevent oversized logos
            if logo_width > 220:
                logo_width = 220
                logo_height = logo_width / aspect
                
            logo_img = Image(logo_path, width=logo_width, height=logo_height)
            logo_img.hAlign = 'LEFT'
            story.append(logo_img)
            story.append(Spacer(1, 15))
        except Exception as e:
            # ReportLab might fail to load unsupported image formats like SVG natively or corrupted files.
            # Handle cleanly and log warnings instead of throwing a 500 error.
            print(f"Warning: Could not load logo in PDF: {e}")
    
    # Document Title
    story.append(Paragraph("KnowCraft Analytics", title_style))
    story.append(Paragraph("AI-Powered Voice Screening Report", ParagraphStyle('Sub', parent=styles['Normal'], fontSize=11, textColor=colors.HexColor('#5a6380'), spaceAfter=15)))
    
    story.append(Spacer(1, 10))
    
    # Candidate Profile Section
    story.append(Paragraph("Candidate Profile", section_heading))
    profile_data = [
        [Paragraph("<b>Candidate Name:</b>", normal_bold), Paragraph(session.candidate_name or "N/A", body_text)],
        [Paragraph("<b>Candidate Email:</b>", normal_bold), Paragraph(getattr(session, "candidate_email", "N/A") or "N/A", body_text)],
        [Paragraph("<b>Candidate Phone:</b>", normal_bold), Paragraph(getattr(session, "candidate_phone", "N/A") or "N/A", body_text)],
        [Paragraph("<b>Target Role:</b>", normal_bold), Paragraph(session.role_label or "N/A", body_text)],
        [Paragraph("<b>Company:</b>", normal_bold), Paragraph(session.company or "KnowCraft", body_text)],
        [Paragraph("<b>Date & Time:</b>", normal_bold), Paragraph(datetime.now().strftime("%B %d, %Y %I:%M %p"), body_text)]
    ]
    profile_table = Table(profile_data, colWidths=[150, 350])
    profile_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#eef2f7')),
    ]))
    story.append(profile_table)
    story.append(Spacer(1, 15))
    
    # AI Evaluation Score
    story.append(Paragraph("AI Performance Evaluation", section_heading))
    
    score_card_data = [
        [Paragraph(f"<b>Overall Match Score: {score}/100</b>", ParagraphStyle('Score', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, leading=16, textColor=colors.HexColor('#00b894')))],
        [Paragraph(f"<b>Feedback Summary:</b><br/>{feedback}", ParagraphStyle('Feedback', parent=styles['Normal'], fontSize=9.5, leading=13.5, textColor=colors.HexColor('#1a1a2e')))]
    ]
    score_table = Table(score_card_data, colWidths=[500])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#fcf3e8') if score < 70 else colors.HexColor('#eefdfa')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#00b894')),
        ('PADDING', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 15))
    
    # Interview Transcript
    story.append(Paragraph("Detailed Interview Transcript", section_heading))
    
    if not turns:
        story.append(Paragraph("No questions were answered during this interview screening session.", body_text))
    else:
        transcript_data = []
        for idx, turn in enumerate(turns, 1):
            q_para = Paragraph(f"<b>Q{idx}: {turn.question_text}</b>", ParagraphStyle('QStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9.5, leading=13.5, textColor=colors.HexColor('#6c5ce7')))
            a_para = Paragraph(f"<b>Candidate:</b> {turn.answer_text if turn.answer_text else '[No response]'}", ParagraphStyle('AStyle', parent=styles['Normal'], fontSize=9, leading=13, textColor=colors.HexColor('#1a1a2e')))
            transcript_data.append([q_para])
            transcript_data.append([a_para])
            transcript_data.append([Spacer(1, 4)])
            
        transcript_table = Table(transcript_data, colWidths=[500])
        transcript_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('TOPPADDING', (0,0), (-1,-1), 2),
        ]))
        story.append(transcript_table)
    
    doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    doc.build(story)
    
    # 2. Send Email
    try:
        subject = f"Interview Screening Report - {session.role_label} - {session.candidate_name}"
        body = f"""Dear {session.candidate_name},

Thank you for participating in the AI voice interview screening for the {session.role_label} role.

Your interview has been completed and analyzed by our AI evaluation engine.

---
Overall Match Score: {score}/100
Evaluation Feedback: {feedback}
---

Your detailed performance report and full transcript are attached to this email as a PDF. Our recruitment team will review your application and get in touch with you shortly.

Best regards,
KnowCraft Analytics Team
"""
        sender_email = getattr(settings, 'EMAIL_HOST_USER', None)
        dest_email = getattr(session, 'candidate_email', None)
        
        if sender_email and dest_email:
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=sender_email,
                to=[dest_email],
            )
            email.attach_file(pdf_path)
            email.send(fail_silently=False)
            print(f"Sent email successfully to {dest_email}")
            return True
        else:
            print(f"Email could not be sent: sender={sender_email}, recipient={dest_email}")
            return False
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
