from pptx import Presentation
from pptx.util import Inches, Pt 
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.enum.text import PP_ALIGN
from ai_service import GeminiService
from pptx.enum.chart import XL_CHART_TYPE
from pptx.chart.data import ChartData
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from lxml import etree
import os
import uuid

async def generate_pptx_file( doc_data, presentation_content,  temp_dir,  theme_path=None):
    
    if theme_path and os.path.exists(theme_path):
        prs = Presentation(theme_path) 
        print(f"✅ Prezentatsiya shablon '{theme_path}' yordamida yaratilmoqda.")
    else:
        prs = Presentation() 
        print("⚠️ Shablon topilmadi yoki ko'rsatilmadi. Standart dizayn ishlatilmoqda.")
    
    
    title_slide_layout = prs.slide_layouts[0] 
    content_slide_layout = prs.slide_layouts[1] 
    
    uni_kafedra = doc_data.get('uni_kafedra', 'Kafedra nomi kiritilmagan')
    student_fio = doc_data.get('student_fio', 'Talaba F.I.O.si')
    student_group = doc_data.get('student_group', 'Guruh raqami')
    
    slide = prs.slides[0]
    

    slide.shapes.title.text = (
        f"{uni_kafedra}"
    )
    
    subtitle_placeholder = slide.placeholders[1]
    
    info_text = (
        f"\n\n\n\nBajardi: {student_fio}\n"
        f"Guruh: {student_group}\n"
        f"Yil: {doc_data.get('year', 2024)}"
    )
    
    subtitle_placeholder.text = info_text
    

    tf = subtitle_placeholder.text_frame
    for p in tf.paragraphs:
        p.alignment = PP_ALIGN.LEFT 
        p.font.size = Pt(14)
        
    
    slide = prs.slides.add_slide(title_slide_layout)
    title_placeholder = slide.shapes.title

    title_placeholder.text = doc_data['topic']

    
    gemini_service_instance = GeminiService()
    
    chart_data_dict = await gemini_service_instance.generate_chart_data(title_placeholder.text)

    if chart_data_dict and 'categories' in chart_data_dict and 'series' in chart_data_dict:
        
        # 2. Ma'lumotlarni python-pptx formati ChartData ga o'tkazish
        chart_data = ChartData()
        chart_data.categories = chart_data_dict['categories']
        
        for series in chart_data_dict['series']:
            chart_data.add_series(series['name'], series['values'])

        # 3. Diagramma o'lchamlarini va turini belgilash
        x = Inches(2)
        y = Inches(2)
        cx = Inches(6)
        cy = Inches(4.5)
        
        # Diagramma turini dinamik tanlaymiz (Biz Ustunli (COLUMN) turini tanladik)
        chart_type = XL_CHART_TYPE.COLUMN_CLUSTERED 
        
        try:
            chart = slide.shapes.add_chart(
                chart_type, x, y, cx, cy, chart_data
            ).chart

            # Diagramma sarlavhasi (Gemini tomonidan generatsiya qilinganini ishlatamiz)
            chart.has_title = True
            chart.title.text_frame.text = chart_data_dict.get('title',  title_placeholder.text)
            
            chart.has_legend = True # Afsonani yoqish
            
            print(f"✅ Mavzu slaydiga dinamik '{chart_type.name}' diagramma joylashtirildi.")
            
        except Exception as e:
            print(f"❌ Dinamik diagramma joylashda xato yuz berdi: {e}")
    else:
        print("⚠️ Diagramma ma'lumotlari generatsiya qilinmadi yoki noto'g'ri formatda keldi. Diagramma qo'shilmadi.")

                
    left = Inches(3.5)
    top = Inches(7.5) 
    width = Inches(3) 
    height = Inches(2)

    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf_student = txBox.text_frame
    tf_student.clear()

    generated_file_path = None
    
    for item in presentation_content:
        slide_title = item["title"]
        slide_content_raw = item["content"]
        
        slide = prs.slides.add_slide(content_slide_layout)
        
        slide.shapes.title.text = slide_title
        
        body = slide.shapes.placeholders[1]
        tf = body.text_frame
        
        tf.clear() 
        content_lines = [line.strip().lstrip('*- ') for line in slide_content_raw.split('\n') if line.strip()]

        if not content_lines:
            tf.text = "Kontent topilmadi yoki generatsiya qilinmadi."
        else:
            tf.text = content_lines[0] 
            
            for line in content_lines[1:]: 
                p = tf.add_paragraph()
                p.text = line
                p.level = 0
        
       
        for paragraph in tf.paragraphs:
            paragraph.font.size = Pt(20) 
      
 
    unique_filename = f"PPTX_{uuid.uuid4().hex[:8]}.pptx"
    generated_file_path = os.path.join(temp_dir, unique_filename) 
    
    prs.save(generated_file_path)
    
     
        
    try:
        if not os.listdir(temp_dir):
             os.rmdir(temp_dir)
    except Exception:
        pass 
        
    return generated_file_path        