import os
import asyncio
from google import genai
from google.genai import types
from google.genai.errors import APIError
from datetime import datetime
from google.genai.types import Schema, Type
from google.genai.errors import APIError
from google.genai.types import Schema, Type 
import asyncio
import json
import google.genai as genai
from google.genai import types
from google.genai.errors import APIError
from dotenv import load_dotenv

class GeminiService:
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY_3")
        if not api_key:
            # Agar kalit bo'lmasa, ValueError xatosini tashlaymiz
            raise ValueError("❌ GEMINI_API_KEY muhit o'zgaruvchisi o'rnatilmagan.")
            
        # 2. Gemini mijozini ishga tushirish
        self.client = genai.Client(api_key=api_key)
        
        # 3. Modelni tanlash (Tezlik va sifat uchun)
        self.model = 'gemini-3-flash' 
        self.content_config = {
        "temperature": 0.7,
        "max_output_tokens": 8192,
    }

    def _clean_and_split_list(self, text: str) -> list:
        """
        AI dan olingan, raqamlangan/yulduzcha bilan berilgan matnni 
        toza sarlavhalar ro'yxatiga ajratadi.
        """
        if not text:
            return []
            
        # 1. Matnni qatorlarga ajratish
        lines = text.strip().split('\n')
        
        cleaned_list = []
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
                
            # 2. Raqamlar, yulduzcha yoki chiziq kabi prefikslarni tozalash
            
            # Raqamlangan ro'yxatni tozalash (masalan: "1. Kirish" -> "Kirish")
            if line[0].isdigit() and ('. ' in line or ') ' in line):
                try:
                    # Birinchi nuqta/qavsdan keyingi qismni olish
                    line = line.split('. ', 1)[-1].split(') ', 1)[-1].strip()
                except:
                    pass
            
            # Yulduzcha yoki chiziq kabi prefikslarni tozalash ("* Kirish" -> "Kirish")
            if line.startswith(('-', '*', '•')):
                line = line[1:].strip()

            # Matnni yana bir bor tekshirish va ro'yxatga qo'shish
            if line:
                cleaned_list.append(line)
                
        # Ro'yxatni tozalangan holda qaytarish
        return cleaned_list

    async def generate_chart_data(self, topic: str) -> dict | None:
        """
        Berilgan mavzu uchun diagramma ma'lumotlarini JSON formatida generatsiya qiladi
        (google-genai client va asyncio.to_thread yordamida).
        """
 
        system_prompt = (
            "Siz professional ma'lumotlar tahlilchisiz. Prezentatsiya uchun berilgan mavzuga mos keladigan "
            "va mantiqan to'g'ri bo'lgan 4-5 toifali (categories) diagramma ma'lumotlarini tuzing. "
            "Qiymatlar real foizlar yoki sonlar bo'lsin. Faqat so'ralgan JSON formatini qaytaring."
        )
        
        user_query = f"Mavzu: '{topic}'. Bu mavzu bo'yicha vizual diagramma yaratish uchun ma'lumotlar seriyasini tuzing. Ma'lumotlarning aniq qiymatlarini kiriting."

        # JSON sxemasini aniqlash (Diagramma ma'lumotlarining tuzilmasi)
        chart_schema = Schema(
            type=Type.OBJECT,
            properties={
                "title": Schema(type=Type.STRING, description="Diagrammaning sarlavhasi (Mavzuga mos kelishi kerak)."),
                "categories": Schema(type=Type.ARRAY, items=Schema(type=Type.STRING), description="Diagramma toifalari."),
                "series": Schema(
                    type=Type.ARRAY,
                    items=Schema(
                        type=Type.OBJECT,
                        properties={
                            "name": Schema(type=Type.STRING, description="Ma'lumotlar seriyasining nomi."),
                            "values": Schema(type=Type.ARRAY, items=Schema(type=Type.NUMBER), description="Raqamli qiymatlar.")
                        },
                        required=["name", "values"]
                    ),
                    description="Diagramma uchun ma'lumotlar seriyalari ro'yxati."
                )
            },
            required=["title", "categories", "series"]
        )
        
        # Konfiguratsiyani tayyorlash
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=chart_schema
        )

        model_name = "gemini-3-flash"
        # Yangi, toʻgʻri qator:
        contents = [types.Content(parts=[types.Part(text=user_query)])]


        try:
            # 3 marta qayta urinish mantig'i (Exponential Backoff bilan)
            for attempt in range(3):
                try:
                    # BLOCKING chaqiruvni async muhitda ishga tushiramiz
                    response = await asyncio.to_thread(
                        self.client.models.generate_content,
                        model=model_name,
                        contents=contents,
                        config=config
                    )
                    
                    # Natijani tekshirish
                    if not response.text:
                         raise ValueError("Generatsiya qilingan matn bo'sh keldi.")

                    # Natijani lug'atga aylantiramiz
                    json_text = response.text.strip()
                    return json.loads(json_text)
                    
                except APIError as e:
                    error_msg = str(e).upper()
                    if '503' in error_msg or 'UNAVAILABLE' in error_msg or 'RATE LIMIT EXCEEDED' in error_msg:
                        print(f"[CHART DATA] API Xatosi: {attempt+1}-urinishdan keyin qayta urinish...")
                        await asyncio.sleep(2 * (attempt + 1))
                    else:
                        print(f"[CHART DATA] Jiddiy API Xatosi. To'xtatildi: {e}")
                        raise 
                
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"[CHART DATA] JSON formatlash xatosi: {e}. Qayta urinish: {attempt+1}")
                    await asyncio.sleep(2 * (attempt + 1))
        
            print(f"[CHART DATA] Ma'lumot generatsiyasi 3 urinishdan keyin ham bajarilmadi: {topic}")
            return None
            
        except Exception as e:
            print(f"[CHART DATA] Kutilmagan Xato: {e}")
            return None
    
    async def generate_slide_content(self, topic: str, slide_title: str, lang: str) -> str:
        """
        Berilgan slayd sarlavhasi uchun tezis (bullet point) shaklida kontent generatsiya qiladi.
        Bu funksiya final_generation_start siklida chaqiriladi va to'g'ri argumentlarni qabul qilishi shart.
        """
        
        # Lang kodi xaritasi (4 ta til uchun)
        lang_map = {
            'uz': 'Uzbek language (Lotin yozuvida)',
            'kr': 'Uzbek language (Kirill yozuvida)', 
            'ru': 'Russian language (Русский язык)',
            'en': 'English language'
        }
        target_lang = lang_map.get(lang, 'Uzbek language (Lotin yozuvida)')

        prompt = (
            f"Generate content for a single presentation slide. "
            f"The content MUST be professional, highly informative, and focused on the Slide Title: '{slide_title}'. "
            f"The slide is part of a larger presentation on the topic: '{topic}'.\n"
            
            f"The content MUST be a list of exactly 4 to 6 short, descriptive bullet points. Each point should be a key takeaway, fact, or concise explanation.\n"
            
            f"Crucially, for presentation flow, your response MUST NOT contain any introductory sentences (like 'This slide discusses...') or concluding sentences. "
            f"The output must be ONLY the bullet points, using '*' ,'**' or '-' as the list marker, in the **{target_lang}**."
        )
        try:
            for attempt in range(3): 
                try:
                    response = await asyncio.to_thread(
                        self.client.models.generate_content,
                        model=self.model,
                        contents=prompt
                    )
                    return response.text.strip()
                
                except APIError as e:
                    error_msg = str(e).upper()
                    if '503' in error_msg or 'UNAVAILABLE' in error_msg or 'RATE LIMIT EXCEEDED' in error_msg:
                        print(f"[SLIDE CONTENT] API Xatosi ({slide_title[:15]}...): {attempt+1}-urinishdan keyin qayta urinish...")
                        await asyncio.sleep(2 * (attempt + 1))
                    else:
                        print(f"[SLIDE CONTENT] Jiddiy API Xatosi. To'xtatildi: {e}")
                        raise 

            print(f"[SLIDE CONTENT] Kontent generatsiyasi 3 urinishdan keyin ham bajarilmadi: {slide_title}")
            return "Kontent generatsiyasida xatolik yuz berdi. Iltimos, bu slayd uchun ma'lumotni qo'lda kiriting."
                
        except Exception as e:
            print(f"[SLIDE CONTENT] Kutilmagan Xato: {e}")
            return "Kontent generatsiyasida kutilmagan xatolik. Ma'lumotni qo'lda kiriting."
    
   
        """
        Berilgan slayd sarlavhasi va kontentiga mos keladigan
        asosiy vizual element (rasm/diagramma/infografika) uchun kalit so'z generatsiya qiladi.
        """
        
        target_lang = "English" 

        prompt = (
            f"Analyze the following slide title and content (in {lang}) and generate a single, concise, English keyword or short phrase (max 3 words) "
            f"that perfectly describes the best visual element (image, diagram, infographic) for this slide.\n"
            f"This keyword will be used for an image search.\n\n"
            f"SLIDE TITLE: {slide_title}\n"
            f"SLIDE CONTENT: {slide_content}\n\n"
            f"Output MUST be ONLY the keyword/phrase, without any explanation, quotes, or formatting."
        )
        
        try:
            for attempt in range(3): 
                try:
                    response = await asyncio.to_thread(
                        self.client.models.generate_content,
                        model=self.model,
                        contents=prompt
                    )
                    return response.text.strip().replace('"', '').replace("'", '').replace('.', '').replace('-', ' ')
                
                except APIError as e:
                    error_msg = str(e).upper()
                    if '503' in error_msg or 'UNAVAILABLE' in error_msg or 'RATE LIMIT EXCEEDED' in error_msg:
                        print(f"[VISUAL SUGGESTION] API Xatosi ({slide_title[:15]}...): {attempt+1}-urinishdan keyin qayta urinish...")
                        await asyncio.sleep(2 * (attempt + 1))
                    else:
                        print(f"[VISUAL SUGGESTION] Jiddiy API Xatosi. To'xtatildi: {e}")
                        raise 

            print(f"[VISUAL SUGGESTION] Vizual taklif 3 urinishdan keyin ham bajarilmadi: {slide_title}")
            return "Infographic" 
        except Exception as e:
            print(f"[VISUAL SUGGESTION] Kutilmagan Xato: {e}")
            return "Infographic" 
            
    async def generate_slide_titles(self, topic: str, num_slides: int, lang: str) -> str:
        """Berilgan mavzu uchun slayd sarlavhalari ro'yxatini (rejasini) generatsiya qiladi (Qayta urinish logikasi bilan)."""
        
        # Lang kodi xaritasi (4 ta til uchun)
        lang_map = {
            'uz': 'Uzbek language (Lotin yozuvida)',
            'kr': 'Uzbek language (Kirill yozuvida)', 
            'ru': 'Russian language (Русский язык)',
            'en': 'English language'
        }
        target_lang = lang_map.get(lang, 'Uzbek language (Lotin yozuvida)')

        prompt = (
            f"Generate exactly {num_slides} short, professional, and concise slide titles "
            f"for a presentation on the topic: '{topic}'. "
            f"The presentation MUST be logically divided into the following key sections: "
            f"(1) Fundamentals (Asosiy tushunchalar), (2) Core Technology (Texnologiya: LLM), and (3) Social Impact (Ijtimoiy ta'sir). "
            f"Ensure the titles cover these parts equally.\n"
            
            f"The titles MUST include 'Introduction', 'Conclusion', and 'References/Q&A' (or their equivalents in the target language).\n"
            
            f"The ENTIRE output must be a clean, numbered list of titles ONLY, without any section headings, explanations, or the topic title. "
            f"Use **{target_lang}**."
        )
        
        response_text = ""
        
        try:
            for attempt in range(3): 
                try:
                    response = await asyncio.to_thread(
                        self.client.models.generate_content,
                        model=self.model,
                        contents=prompt
                    )
                    response_text = response.text.strip()
                    return self._clean_and_split_list(response_text)
                
                except APIError as e:
                    error_msg = str(e).upper()
                    if '503' in error_msg or 'UNAVAILABLE' in error_msg or 'RATE LIMIT EXCEEDED' in error_msg:
                        print(f"[SLIDE TITLES] API Xatosi ({error_msg[:15]}...): {attempt+1}-urinishdan keyin qayta urinish...")
                        await asyncio.sleep(2 * (attempt + 1))
                    else:
                        print(f"[SLIDE TITLES] Jiddiy API Xatosi. To'xtatildi: {e}")
                        raise 

            print(f"[SLIDE TITLES] Reja generatsiyasi 3 urinishdan keyin ham bajarilmadi.")
            return [] 
                
        except Exception as e:
            print(f"[SLIDE TITLES] Kutilmagan Xato: {e}")
            return []

    async def generate_reja_titles(self, topic: str, num_sections: int, lang:str, work_type: str) -> list[str]:
        
        if work_type == 'mustaqil_ish':
            req_uz = "analitik, tahliliy va amaliy jihatdan yoʻnaltirilgan"
            req_ru = "аналитические, проблемно-ориентированные и практические"
            req_en = "analytical, problem-solving, and practically oriented"
            req_kr = "аналитик, таҳлилий ва амалий жиҳатдан йўналтирилган"
            
            first_chap_uz = "Birinchi bob 'Muammoning nazariy asoslari' yoki 'Masalaning tahlili' kabi tahliliy tushunchalar bilan bogʻliq boʻlishi shart."
            first_chap_ru = "Первая глава должна быть связана с 'Теоретическими основами проблемы' или 'Анализом ситуации'."
            first_chap_en = "The first chapter must be related to 'Theoretical Foundations of the Problem' or 'Situational Analysis'."
            first_chap_kr = "Биринчи боб 'Муаммонинг назарий асослари' ёки 'Масаланинг таҳлили' каби таҳлилий тушунчалар билан боғлиқ бўлиши шарт."
        else: # referat
            req_uz = "nazariy bilimni umumlashtiruvchi"
            req_ru = "обобщающие теоретические знания"
            req_en = "generalizing theoretical knowledge"
            req_kr = "назарий билимни умумлаштирувчи"
            
            first_chap_uz = "Birinchi bob 'Nazariy asos' yoki 'Tushunchalar' bilan bogʻliq boʻlishi shart."
            first_chap_ru = "Первая глава должна быть связана с 'Теоретическими основами' или 'Понятиями'."
            first_chap_en = "The first chapter must be related to 'Theoretical foundations' or 'Concepts'."
            first_chap_kr = "Биринчи боб 'Назарий асос' ёки 'Тушунчалар' билан боғлиқ бўлиши шарт."
        
        prompts = {
            'uz': f"""Mavzu: "{topic}". Ushbu **{work_type.replace('_', ' ')}** uchun talabaning ishi darajasida {num_sections} ta {req_uz} bob sarlavhasini **o'zbek tilida** generatsiya qil.
                    Talablar:
                    1. Format: Har bir sarlavhani yangi qatordan va hech qanday raqam qo'ymay faqat sarlavhaning o'zini (tekst) qoldir.
                    2. {first_chap_uz}""",

            'ru': f"""Тема: "{topic}". Сгенерируй {num_sections} {req_ru} заголовков глав для **{work_type.replace('_', ' ')}** на **русском языке** на уровне студенческой работы.
                    Требования:
                    1. Формат: Оставляй только сам заголовок (текст) с новой строки, без нумерации.
                    2. {first_chap_ru}""",

            'en': f"""Topic: "{topic}". Generate {num_sections} {req_en} academic section titles for this **{work_type.replace('_', ' ')}** **in English**.
                    Requirements:
                    1. Format: Put only the title text on a new line, without any numbering.
                    2. {first_chap_en}""",
                            
            'kr': f"""Мавзу: "{topic}". Ушбу **{work_type.replace('_', ' ')}** учун талабанинг иши даражасида {num_sections} та {req_kr} боб сарлавҳасини **Ўзбек тилида (Кирилл)** генерация қил.
                    Талаблар:
                    1. Формат: Ҳар бир сарлавҳани янги қатордан ва ҳеч қандай рақам қўймай фақат сарлавҳанинг ўзини (текст) қолдир.
                    2. {first_chap_kr}""",
        }

        prompt = prompts.get(lang, prompts['uz']) 
        
        # 2. Sinxron chaqiruvni asinxron ishga tushirish (QAYTA URINISHNI QO'SHAMIZ)
        for attempt in range(3): # 3 marta urinish
            try:
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model,
                    contents=prompt
                )
                # Agar muvaffaqiyatli bo'lsa, natijani qaytarish
                titles = [q.strip() for q in response.text.split('\n') if q.strip()]
                return titles[:num_sections]

            except APIError as e:
                print(f"Gemini API xatosi (Reja, {attempt+1}-urinish): {e}")
                if attempt < 2: # 2 urinishdan keyin kutish
                    await asyncio.sleep(2 * (attempt + 1)) 
                else:
                    return [] # Oxirgi urinishda ham xato bo'lsa
            except Exception as e:
                # Server disconnected xatosi ham shu yerga tushadi
                print(f"Boshqa kutilmagan xato (Reja, {attempt+1}-urinish): {e}")
                if attempt < 2: 
                    await asyncio.sleep(2 * (attempt + 1)) 
                else:
                    return [] # Oxirgi urinishda ham xato bo'lsa
        return [] # Barcha urinishlar tugadi

    async def generate_sub_titles(self, topic: str, main_title: str, lang:str, work_type: str, num_sub_sections: int = 3) -> list[str]:
        
        prompts = {
        'uz': f"""
                Mavzu: {topic}. Ish turi: {work_type.replace('_', ' ')}.
                Asosiy Bob Sarlavhasi: {main_title}

                Sizning vazifangiz - yuqoridagi asosiy bob sarlavhasi uchun mos keladigan {num_sub_sections} ta ichki band sarlavhasini **O'zbek tilida** generatsiya qilish. 
                Har bir sarlavhani yangi qatordan, hech qanday raqam qo'ymay, faqat toza sarlavhaning o'zini (tekst) qoldiring.
                """,
        'ru': f"""
                Тема: {topic}. Тип работы: {work_type.replace('_', ' ')}.
                Основной заголовок главы: {main_title}

                Ваша задача - сгенерировать {num_sub_sections} подзаголовков разделов, подходящих для вышеуказанного основного заголовка главы, на **Русском языке**.
                Оставляйте только чистый заголовок (текст) с новой строки, без нумерации.
                """,
        'en': f"""
                Topic: {topic}. Type of Work: {work_type.replace('_', ' ')}.
                Main Section Title: {main_title}

                Your task is to generate {num_sub_sections} subsection titles suitable for the main section title above **in English**.
                Output only the clean title text on a new line, without any numbering.
                """,
        'kr': f"""
                Мавзу: {topic}. Иш тури: {work_type.replace('_', ' ')}.
                Асосий Боб Сарлавҳаси: {main_title}

                Сизнинг вазифангиз - юқоридаги асосий боб сарлавҳаси учун мос келадиган {num_sub_sections} та ички банд сарлавҳасини **Ўзбек тилида (Кирилл)** генерация қилиш. 
                Ҳар бир сарлавҳани янги қатордан, ҳеч қандай рақам қўймай, фақат тоза сарлавҳанинг ўзини (текст) қолдиринг.
                """
        }

        prompt = prompts.get(lang, prompts['uz']) 
        
        try:
        # Avtomatik qayta urinishni qo'shing (masalan, 3 marta)
            for attempt in range(3):
                try:
                    response = await asyncio.to_thread(
                        self.client.models.generate_content,
                        model=self.model,
                        contents=prompt
                    )
                    return [q.strip() for q in response.text.split('\n') if q.strip()]
                except APIError as e:
                    if '503' in str(e) or 'UNAVAILABLE' in str(e):
                        print(f"503 xatosi. {attempt+1}-urinishdan keyin qayta urinish...")
                        await asyncio.sleep(2 * (attempt + 1)) # 2, 4, 6 soniya kutish
                    else:
                        raise # Boshqa xatolarni qayta yuborish
            # Agar 3 urinishdan keyin ham xato bo'lsa
            return []

        except Exception as e:
            print(f"Gemini API xatosi (Ichki sarlavhalar): {e}")
            return []
        
    async def generate_introduction_text(self, topic: str, work_type: str, lang:str, main_titles_list: list[str]) -> str:

        boblar_matni = "\n".join([f"- {title}" for title in main_titles_list])
        
        if work_type == 'mustaqil_ish':
            req_uz = "Kirish matni toʻliq va mukammal boʻlsin. Kirish so'zi bo'lmasin eng boshida. Matn ichida **MAVZUNING DOLZARBLIGI, TADQIQOT MAQSADI, TADQIQOT VAZIFALARI, ISHNING ILMIY VA AMALIY AHAMIYATI** gʻoyalarini oʻz ichiga olsin. "
            req_ru = "Введение должно быть полным и совершенным. Оно должно включать идеи **АКТУАЛЬНОСТИ, ЦЕЛИ И ЗАДАЧ ИССЛЕДОВАНИЯ, НАУЧНОЙ И ПРАКТИЧЕСКОЙ ЗНАЧИМОСТИ** работы."
            req_en = "The Introduction must be comprehensive. It must integrate the ideas of **RELEVANCE, RESEARCH AIM, RESEARCH OBJECTIVES, and the SCIENTIFIC and PRACTICAL SIGNIFICANCE** of the work."
            req_kr = "Кириш матни тўлиқ ва мукаммал бўлсин. Матн ичида **МАВЗУНИНГ ДОЛЗАРБЛИГИ, ТАДҚИҚОТ МАҚСАДИ, ТАДҚИҚОТ ВАЗИФАЛАРИ, ИШНИНГ ИЛМИЙ ВА АМАЛИЙ АҲАМИЯТИ** ғояларини ўз ичига олсин."
        else: # referat
            req_uz = "Matn ichida **Dolzarblik, Ishning maqsadi va Ishning vazifalari** haqidagi gʻoyalarni yashiring, ammo ularni alohida sarlavha bilan ajratmang."
            req_ru = "Включите идеи о **Актуальности, Цели и Задачи работы** в общий текст."
            req_en = "Integrate the ideas of **Relevance, Aim, and Objectives** within the text flow."
            req_kr = "Матн ичида **Долзарблик, Ишнинг мақсади ва Ишнинг вазифалари** ҳақидаги ғояларни яширинг, аммо уларни алоҳида сарлавҳа билан ажратманг."
        
        prompts = {
            'uz': f"""
                            **QAT'IY TALAB: JAVOBNI FAQQAT O'ZBEK TILIDA (LOTIN ALIFBOSIDA) GENERATSIYA QILING.**
                            Sizning vazifangiz: "{topic}" mavzusidagi **{work_type.replace('_', ' ')}** uchun ilmiy Kirish qismini **ixcham, 1 sahifadan oshmaydigan** hajmda yaratish.
                            Asosiy boblar sarlavhalari (Vazifalar uchun): {boblar_matni}
                            Talablar: 
                            1. {req_uz}
                            2. Barcha gʻoyalar uzluksiz matn oqimida boʻlsin.
                            3. Natijada faqat TOZA MATN bo'lsin. JAVOBINGIZNI HECH QANDAY TASHQI FORMATLASH BELGILARI, MASALAN BOLD BELGILARI (**), QO'SHTIRNOQ YOKI NUMERALAR BILAN O'RAB YOZMANG.
                            4. "Kirish" sarlavhasini qo'ymang. Matnni mantiqiy abzaslarga ajratmang.
                            5. Matn hajmi QATTIY talab 1 sahifadan oshmasin!!!.
                            """,
            'ru': f"""
                            **СТРОГОЕ ТРЕБОВАНИЕ: ГЕНЕРИРУЙТЕ ОТВЕТ ИСКЛЮЧИТЕЛЬНО НА РУССКОМ ЯЗЫКЕ.**
                            Ваша задача: создать научную Вводную часть для **{work_type.replace('_', ' ')}** на тему: "{topic}" в **компактном объеме, не превышающем 1 страницу**.
                            Заголовки Основных Глав (для определения Задач): {boblar_matni}
                            Требования: 
                            1. {req_ru}
                            2. Все идеи должны быть представлены в виде непрерывного текстового потока.
                            3. В результате должен быть только ЧИСТЫЙ ТЕКСТ. НЕ ОБОРАЧИВАЙТЕ ВАШ ОТВЕТ ВНЕШНИМИ СИМВОЛАМИ ФОРМАТИРОВАНИЯ, ТАКИМИ КАК ЗВЕЗДОЧКИ (**), КАВЫЧКИ ИЛИ НУМЕРАЦИЯ.
                            4. Не используйте заголовок "Введение". Не разбивайте текст на логические абзацы.
                            5. Требование к объему СТРОГОЕ: текст не должен превышать 1 страницу!!!.
                            """,
            'en': f"""
                            **STRICT REQUIREMENT: GENERATE THE RESPONSE EXCLUSIVELY IN ENGLISH.**
                            Your task: Generate an academic **Introduction** section for a **{work_type.replace('_', ' ')}** on the topic: "{topic}", keeping the size **compact and strictly not exceeding 1 page**.
                            Main Section Titles (for defining the Tasks/Objectives): {boblar_matni}
                            Requirements: 
                            1. {req_en}
                            2. All ideas must be presented in a continuous flow of text.
                            3. The result must be **PURE TEXT** only. DO NOT WRAP YOUR RESPONSE WITH ANY EXTERNAL FORMATTING CHARACTERS, SUCH AS BOLD MARKERS (**), QUOTES, OR NUMERATION.
                            4. Do not include the title "Introduction". Do not separate the text into logical paragraphs.
                            5. The size requirement is **STRICT**: the text must not exceed 1 page!!!.
                            """,
            'kr': f"""
                            **ҚАТЪИЙ ТАЛАБ: ЖАВОБНИ ФАҚАТ ЎЗБЕК ТИЛИДА (КИРИЛЛ АЛИФБОСИДА) ГЕНЕРАЦИЯ ҚИЛИНГ.**
                            Сизнинг вазифангиз: "{topic}" мавзусидаги **{work_type.replace('_', ' ')}** учун илмий Кириш қисмини **ихчам, 1 саҳифадан ошмайдиган** ҳажмда яратиш.
                            Асосий боблар сарлавҳалари (Вазифалар учун): {boblar_matni}
                            Талаблар: 
                            1. {req_kr}
                            2. Барча ғоялар узлуксиз матн оқимида бўлсин.
                            3. Натижада фақат **ТОЗА МАТН** бўлсин. ЖАВОБИНГИЗНИ ҲЕЧ ҚАНДАЙ ТАШҚИ ФОРМАТЛАШ БЕЛГИЛАРИ, МАСАЛАН **БОЛД БЕЛГИЛАРИ** (**), ҚЎШТИРНОҚ ЁКИ НУМЕРАЛАР БИЛАН ЎРАБ ЁЗМАНГ.
                            4. "Кириш" сарлавҳасини қўйманг. Матнни мантиқий абзацларга ажратманг.
                            5. Матн ҳажми ҚАТТИЙ талаб 1 саҳифадан ошмасин!!!.
                            """
        }
        prompt = prompts.get(lang, prompts['uz'])
        
        for attempt in range(3): # 3 marta urinish
            try:
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model,
                    contents=prompt
                )
                return response.text.strip() # Muvaffaqiyatli bo'lsa

            except Exception as e:
                # Server disconnected xatosi shu yerga tushadi
                print(f"Gemini API xatosi (Kirish, {attempt+1}-urinish): {e}")
                if attempt < 2: # 2 urinishdan keyin kutish
                    await asyncio.sleep(2 * (attempt + 1)) 
                else:
                    return "Kirish matnini generatsiya qilishda xato yuz berdi." # Oxirgi urinishda ham xato bo'lsa
        return "Kirish matnini generatsiya qilishda xato yuz berdi." # 
    
    async def generate_section_content(self, topic: str, main_title: str, work_type: str, lang:str, min_page_count :int, sub_titles_list: list[str], page_count:int , main_sections_count: int) -> str:
        print(f"max{page_count}\n min{min_page_count}")
        
        await asyncio.sleep(2)
      
        if main_sections_count == 2:
            if page_count == 15 and min_page_count == 10:
                max_word_count = (page_count - 5) * 200
                min_word_count = (min_page_count - 5) * 200
            elif page_count == 20 and min_page_count == 15:
                max_word_count =(page_count - 5) * 270
                min_word_count = (min_page_count - 5) * 270
        elif main_sections_count == 3:
            max_word_count = (page_count - 5) * 120
            min_word_count =  (min_page_count - 5) * 120
            
        
        
        #ichki_bandlar = "\n".join([f"- {title}" for title in sub_titles_list])
        
        if work_type == 'mustaqil_ish':
            instruction_uz = "**CHUQQUR TAHLILIY** matn generatsiya qil. Har bir fikrni ilmiy asoslang, dalillarni solishtiring va mustaqil xulosalar chiqaring. xulosa 1 saxifadan oshmasin. Amaliy jihatga e'tibor bering."
            instruction_ru = "**ГЛУБОКИЙ АНАЛИТИЧЕСКИЙ** текст. Научно обосновывай каждую идею, сравнивай факты и делай самостоятельные выводы. Сфокусируйтесь на практическом аспекте."
            instruction_en = "**DEEP ANALYTICAL** text. Scientifically justify each idea, compare evidence, and draw independent conclusions. Focus on the practical aspect."
            instruction_kr = "**ЧУҚҚУР ТАҲЛИЛИЙ** матн генерация қил. Ҳар бир фикрни илмий асосланг, далилларни солиштиринг ва мустақил хулосалар чиқаринг. Амалий жиҳатга эътибор беринг."
        else: # referat
            instruction_uz = "asosiy bobning mazmunini toʻliq yorituvchi ilmiy-ommabop **NAZORIY** matn generatsiya qil."
            instruction_ru = "научно-популярный **ТЕОРЕТИЧЕСКИЙ** текст, полностью раскрывающий содержание главы."
            instruction_en = "academic/popular-science **THEORETICAL** text fully covering the content of the main section. "
            instruction_kr = "асосий бобнинг мазмунини тўлиқ ёритувчи илмий-оммабоп **НАЗАРИЙ** матн генерация қил."
        
        
        prompts = {
            'uz': f"""
                    **QAT'IY TALAB: JAVOBNI FAQQAT O'ZBEK TILIDA (LOTIN ALIFBOSIDA) GENERATSIYA QILING.**

                    **!!! HAJM CHEKLOVI - BU ENG USTUVOR TALAB !!!**
                    MATN ANIQ VA QAT'IY ravishda **{min_word_count} so'zdan KAM** va **{max_word_count} so'zdan KO'P** bo'lmasligi kerak. Shuningdek, matn hajmi QAT'IY {page_count - 2} sahifadan OSHMASIN.

                    Talablar:
                        1. "{topic}" sarlavhasiga va ichki bandlarga tayanib, bobning mazmunini to'liq yorituvchi {instruction_uz}
                        2. Natijada faqat **TOZA MATN** bo'lishi kerak. JAVOBINGIZNI HECH QANDAY TASHQI FORMATLASH BELGILARI (QAT'IY MASALAN BOLD BELGILARI (**), (*), (##), (#), QO'SHTIRNOQ YOKI NUMERALAR) BILAN O'RAB YOZMANG.
                        3. Kontentni mantiqiy abzaslarga ajratmang.
                        4. "{topic}" sarlavhasini qo'ymang.
                    """,
            'ru': f"""
                            **СТРОГОЕ ТРЕБОВАНИЕ: ГЕНЕРИРУЙТЕ ОТВЕТ ИСКЛЮЧИТЕЛЬНО НА РУССКОМ ЯЗЫКЕ.**
                            
                            **!!! ОГРАНИЧЕНИЕ ПО ОБЪЕМУ - ЭТО ГЛАВНЫЙ ПРИОРИТЕТ !!!**
                            ТЕКСТ ДОЛЖЕН БЫТЬ СТРОГО НЕ МЕНЕЕ **{min_word_count} СЛОВ** и НЕ БОЛЕЕ **{max_word_count} СЛОВ**. Также ОБЯЗАТЕЛЬНО, чтобы объем текста НЕ ПРЕВЫШАЛ {page_count - 2} страниц.

                            Требования:
                                1. Опираясь на заголовок "{topic}" и внутренние разделы, сгенерируй текст, полностью раскрывающий содержание главы. {instruction_ru}
                                2. В результате должен быть только **ЧИСТЫЙ ТЕКСТ**. СТРОГО НЕ ОБОРАЧИВАЙТЕ ВАШ ОТВЕТ ВНЕШНИМИ СИМВОЛАМИ ФОРМАТИРОВАНИЯ (ТАКИМИ КАК ЗВЕЗДОЧКИ (**), (*), (##), (#), КАВЫЧКИ ИЛИ НУМЕРАЦИЯ).
                                3. Не разделяйте контент на логические абзацы.
                                4. Не используйте заголовок "{topic}".
                            """,
             'en': f"""
                    **STRICT REQUIREMENT: GENERATE THE RESPONSE EXCLUSIVELY IN ENGLISH.**
                    
                    **!!! VOLUME LIMIT IS THE TOP PRIORITY !!!**
                    THE TEXT MUST BE STRICTLY AT LEAST **{min_word_count} WORDS** and NO MORE THAN **{max_word_count} WORDS**. Additionally, the text volume MUST NOT EXCEED {page_count - 2} pages.

                    Requirements:
                        1. Based on the title "{topic}" and the provided subsections, generate content that fully covers the section's subject matter. {instruction_en}
                        2. The result must be **PURE TEXT** only. DO NOT WRAP YOUR RESPONSE WITH ANY EXTERNAL FORMATTING CHARACTERS (**STRICTLY** INCLUDING BOLD MARKERS (**), (*), (##), (#), QUOTES, OR NUMERATION).
                        3. Do not separate the content into logical paragraphs.
                        4. Do not include the title "{topic}".
                    """,
             'kr': f"""
                    **ҚАТЪИЙ ТАЛАБ: ЖАВОБНИ ФАҚАТ ЎЗБЕК ТИЛИДА (КИРИЛЛ АЛИФБОСИДА) ГЕНЕРАЦИЯ ҚИЛИНГ.**

                    **!!! ҲАЖМ ЧЕКЛОВИ - БУ ЭНГ УСТУВОР ТАЛАБ !!!**
                    МАТН АНИҚ ВА ҚАТЪИЙ равишда **{min_word_count} сўздан КАМ** ва **{max_word_count} сўздан КЎП** бўлмаслиги керак. Шунингдек, матн ҳажми ҚАТЪИЙ {page_count - 2}  саҳифадан ОШМАСИН.

                    Талаблар:
                        1. "{topic}" ушбу сарлавҳаларга таяниб, бобнинг мазмунини тўлиқ ёритувчи {instruction_kr}
                        2. Натижада фақат **ТОЗА МАТН** бўлиши керак. ЖАВОБИНГИЗНИ ҲЕЧ ҚАНДАЙ ТАШҚИ ФОРМАТЛАШ БЕЛГИЛАРИ (ҚАТЪИЙ МАСАЛАН **БОЛД БЕЛГИЛАРИ** (**), (*), (##), (#), ҚЎШТИРНОҚ ЁКИ НУМЕРАЛАР) БИЛАН ЎРАБ ЁЗМАНГ.
                        3. Контентни мантиқий абзацларга ажратманг.
                        4. "{topic}" сарлавҳасини қўйманг.
                    """,
        }
       
        prompt = prompts.get(lang, prompts['uz'])
         
        for attempt in range(3): # 3 marta urinish
            try:
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model,
                    contents=prompt,
                    config=self.content_config
                )
                return response.text.strip() # Muvaffaqiyatli bo'lsa
                
            except Exception as e:
                # Server disconnected xatosi shu yerga tushadi
                print(f"Gemini API xatosi (Bob kontenti, {attempt+1}-urinish): {e}")
                if attempt < 2: # 2 urinishdan keyin kutish
                    # Har safar kutish vaqtini oshiramiz (masalan, 2, 4 soniya)
                    await asyncio.sleep(2 * (attempt + 1)) 
                else:
                    return " 3 marta urinishdan Asosiy bob matnini generatsiya qilishda xato yuz berdi.........." # Oxirgi urinishda ham xato bo'lsa
        
        return "Asosiy bob matnini generatsiya qilishda xato yuz berdi." 

    async def generate_conclusion_text(self, topic: str, work_type: str, lang:str, final_reja_data: list[dict]) -> str:

        # Asosiy bob sarlavhalarini to'playmiz
        boblar_matni = "\n".join([f"- {data['main_title']}" for data in final_reja_data])
            
        if work_type == 'mustaqil_ish':
            req_uz = "Xulosa matni ishning **Maqsadi**ga erishilganini QAT'IY tasdiqlasin, asosiy topilmalarni umumlashtirsin **VA MAVZU BO'YICHA ANIQ AMALIY TAVSIYALAR/TAKLIFLAR**ni kiritsin.  Xulosa so'zi bo'lmasin eng boshida"
            req_ru = "Заключение должно СТРОГО подтвердить достижение Цели, обобщить ключевые выводы **И ВКЛЮЧИТЬ КОНКРЕТНЫЕ ПРАКТИЧЕСКИЕ РЕКОМЕНДАЦИИ/ПРЕДЛОЖЕНИЯ** по теме."
            req_en = "The Conclusion must STRICLY confirm the achievement of the Aim, summarize key findings, **AND INCLUDE SPECIFIC PRACTICAL RECOMMENDATIONS/SUGGESTIONS** on the topic."
            req_kr = "Хулоса матни ишнинг **Мақсади**га эришилганини ҚАТЪИЙ тасдиқласин, асосий топилмаларни умумлаштирсин **ВА МАВЗУ БЎЙИЧА АНИҚ АМАЛИЙ ТАВСИЯЛАР/ТАКЛИФЛАР**ни киритсин."
        else: # referat
            req_uz = "Xulosa matni ishning **Maqsadi**ga erishilganini tasdiqlasin va asosiy boblarda o'rganilgan barcha muhim topilmalarni qisqa va aniq umumlashtirsin."
            req_ru = "Заключение должно подтвердить достижение Цели и кратко обобщить все ключевые выводы."
            req_en = "The Conclusion must confirm the achievement of the Aim and briefly summarize all key findings."
            req_kr = "Хулоса матни ишнинг **Мақсади**га эришилганини тасдиқласин ва асосий бобларда ўрганилган барча муҳим топилмаларни қисқа ва аниқ умумлаштирсин."

        prompts = {
            'uz': f"""
                    Sizning vazifangiz: "{topic}" mavzusidagi ishning yakuniy Xulosa qismini generatsiya qilish.
                    
                    Talablar: 
                    1. {req_uz}
                    2. Xulosa **QAT'IY** ravishda **300 so'zdan OSHMASIN** (bu taxminan 1 sahifaga teng). Matn qisqa, tahliliy va mantiqiy yakuniy xulosalarni o'z ichiga olsin.
                    3. Natijada faqat **TOZA MATN** bo'lsin. JAVOBINGIZNI HECH QANDAY TASHQI FORMATLASH BELGILARI, MASALAN BOLD BELGILARI (**), QO'SHTIRNOQ YOKI NUMERALAR BILAN O'RAB YOZMANG.
                    4. "Xulosa" sarlavhasini qo'ymang.
                    """,
           'ru': f"""
                    Ваша задача: сгенерировать заключительную часть — Заключение — для работы на тему: "{topic}".
                    
                    ДОПОЛНИТЕЛЬНОЕ ТРЕБОВАНИЕ: Если тема "{topic}" написана не на русском языке, модель должна автоматически перевести ее на русский язык и использовать этот перевод в тексте заключения.
                    
                    Требования:
                    1. {req_ru}
                    2. Заключение должно **СТРОГО** составлять **НЕ БОЛЕЕ 300 СЛОВ** (это примерно равно 1 странице). Текст должен быть кратким, аналитическим и содержать логические финальные выводы.
                    3. В результате должен быть только **ЧИСТЫЙ ТЕКСТ**. НЕ ОБОРАЧИВАЙТЕ ВАШ ОТВЕТ ВНЕШНИМИ СИМВОЛАМИ ФОРМАТИРОВАНИЯ, ТАКИМИ КАК ЗВЕЗДОЧКИ (**), КАВЫЧКИ ИЛИ НУМЕРАЦИЯ.
                    4. Не используйте заголовок "Заключение".
                    """,
            'en': f"""
                    Your task: Generate the final Conclusion section for the work on the topic: "{topic}".
                    
                    ADDITIONAL REQUIREMENT: If the topic "{topic}" is not written in English, the model must automatically translate it into English and use that translation within the conclusion text.
                    
                    Requirements:
                    1. {req_en}
                    2. The Conclusion must **STRICTLY** be **NO MORE THAN 300 WORDS** (this is approximately 1 page). The text should be concise, analytical, and include logical final conclusions.
                    3. The result must be **PURE TEXT** only. DO NOT WRAP YOUR RESPONSE WITH ANY EXTERNAL FORMATTING CHARACTERS, SUCH AS BOLD MARKERS (**), QUOTES, OR NUMERATION.
                    4. Do not include the title "Conclusion".
                    """,
            'kr': f"""
                    Сизнинг вазифангиз: "{topic}" мавзусидаги ишнинг якуний Хулоса қисмини генерация қилиш.
                    
                    ҚЎШИМЧА ТАЛАБ: Агар мавзу "{topic}" ўзбек тилида (кирилл ёки лотин) ёзилмаган бўлса, модель уни автоматик равишда ўзбек тилига (кирилл алифбосига) таржима қилиши ва бу таржимадан хулоса матнида фойдаланиши шарт.
                    
                    Талаблар: 
                    1. {req_kr}
                    2. Хулоса **ҚАТЪИЙ** равишда **300 сўздан ОШМАСИН** (бу тахминан 1 саҳифага тенг). Матн қисқа, таҳлилий ва мантиқий якуний хулосаларни ўз ичига олсин.
                    3. Натижада фақат **ТОЗА МАТН** бўлсин. ЖАВОБИНГИЗНИ ҲЕЧ ҚАНДАЙ ТАШҚИ ФОРМАТЛАШ БЕЛГИЛАРИ, МАСАЛАН БОЛД БЕЛГИЛАРИ (**), ҚЎШТИРНОҚ ЁКИ НУМЕРАЛАР БИЛАН ЎРАБ ЁЗМАНГ.
                    4. "Хулоса" сарлавҳасини қўйманг.
                    """,
        }
        
        prompt = prompts.get(lang, prompts['uz']) 
        for attempt in range(3): 
            try:
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model,
                    contents=prompt
                )
                return response.text.strip()
                
            except Exception as e:
                print(f"Gemini API xatosi (Xulosa, {attempt+1}-urinish): {e}")
                if attempt < 2: 
                    await asyncio.sleep(2 * (attempt + 1)) 
                else:
                    return "Xulosa matnini generatsiya qilishda xato yuz berdi."
        
        return "Xulosa matnini generatsiya qilishda xato yuz berdi."

    async def generate_references_list(self, topic: str, lang:str, num_references: int = 10) -> str:
        
        prompts = {
            'uz': f"""
                                Sizning vazifangiz: "{topic}" mavzusidagi ilmiy ish uchun to'liq formatlangan Adabiyotlar ro'yxatini yaratish.

                    Talablar:
                    1. Ro'yxat kamida {num_references} ta manbadan iborat bo'lsin.
                    2. Manbalar turli xil (kitob, maqola, veb-sayt, dissertatsiya) bo'lsin.
                    3. Manbalarni ilmiy uslubda, muallif/nom/nashriyot/yil tartibida formatlang.
                    4. Faqat toza, **raqamlangan ro'yxatni** ("1.", "2.", "3." kabi) qaytaring.
                    5. JAVOBINGIZNI HECH QANDAY TASHQI BELGILAR, MASALAN YULDUZCHA (*), QO'SHTIRNOQ YOKI BOLD BELGILARI BILAN O'RAB YOZMANG. FAQAT RAQAMLANGAN RO'YXATNI KETMA-KET QAYTARISHINGIZ KERAK.
                    """,
            'ru': f"""
                    Ваша задача: создать полный, отформатированный список 'Источников литературы' для научной работы по теме "{topic}" **на русском языке**.
                    Требования:
                    1. Список должен содержать не менее {num_references} источников.
                    2. Отформатируйте источники в академическом стиле: автор/название/издательство/год. 
                    3. Возвращайте только чистый, **нумерованный список** (например, "1.", "2.", "3.").
                    4. НЕ ОБОРАЧИВАЙТЕ ВАШ ОТВЕТ НАРУЖНЫМИ СИМВОЛАМИ, ТАКИМИ КАК ЗВЕЗДОЧКИ (*), КАВЫЧКИ ИЛИ ЖИРНЫЙ ШРИФТ.
                    """,
            'en': f"""
                    Your task: create a complete, formatted 'References' list for the academic work on the topic "{topic}" **in English**.
                    Requirements: 
                    1. The list must contain at least {num_references} sources.
                    2. Format the sources in academic style: author/title/publisher/year. 
                    3. Return only a clean, **numbered list** (e.g., "1.", "2.", "3."). 
                    4. DO NOT WRAP YOUR RESPONSE WITH ANY EXTERNAL CHARACTERS, SUCH AS ASTERISKS (*), QUOTES, OR BOLD MARKERS.
                    """,
            'kr': f"""
                    Сизнинг вазифангиз: "{topic}" мавзусидаги илмий иш учун тўлиқ форматланган **Ўзбек тилида (Кирилл)** Адабиётлар рўйхатини яратиш.
                    Талаблар: 
                    1. Рўйхат камида
                    {num_references}
                    та манбадан иборат бўлсин.
                    2. Манбаларни илмий услубда, муаллиф/ном/нашриёт/йил тартибида форматланг.
                    3. Фақат тоза, **рақамланган рўйхатни** ("1.", "2.", "3." каби) қайтаринг. 
                    4. ЖАВОБИНГИЗНИ ҲЕЧ ҚАНДАЙ ТАШҚИ БЕЛГИЛАР, МАСАЛАН ЮЛДУЗЧА (*),(**), ҚЎШТИРНОҚ ЁКИ БОЛД БЕЛГИЛАРИ БИЛАН ЎРАБ ЁЗМАНГ.
                    """,
        }
        
        prompt = prompts.get(lang, prompts['uz']) 
        
        # QAYTA URINISH MANTIQI
        for attempt in range(3): 
            try:
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model,
                    contents=prompt
                )
                return response.text.strip()
                
            except Exception as e:
                print(f"Gemini API xatosi (Adabiyotlar, {attempt+1}-urinish): {e}")
                if attempt < 2: 
                    await asyncio.sleep(2 * (attempt + 1)) 
                else:
                    return "Adabiyotlar ro'yxatini generatsiya qilishda xato yuz berdi."
        
        return "Adabiyotlar ro'yxatini generatsiya qilishda xato yuz berdi."
    
    async def generate_title_page_content(self, work_type: str, lang: str) -> dict:
        """
        Tanlangan tilga asoslanib, Titul sahifasining barcha rasmiy va yorliq matnlarini generatsiya qiladi.
        Matnlar har qanday ta'lim yo'nalishiga (universal) mos.
        """
        
        # Rasmiy nomlar, shahar, yil va yorliqlarni turli tillarda saqlaydigan lug'at
        titles = {
            'uz': {
                'uni_name': "O'ZBEKISTON RESPUBLIKASI OLIY TA'LIM, FAN VA INNOVATSIYALAR VAZIRLIGI",
                'shahar_yil': "TOSHKENT - {year}",
                'work_title': "MUSTAQIL ISH" if work_type == 'mustaqil_ish' else "REFERAT",
                'label_topic': 'Mavzu',
                'label_bajaruvchi': "Bajaruvchi",
                'label_group': "Guruh",
                'label_rahbar': "Ilmiy rahbar",
                'title_intro': "KIRISH",
                'title_conclusion': "XULOSA",
                'title_references': "FOYDALANILGAN ADABIYOTLAR RO'YXATI",
            },
            'ru': {
                'uni_name': "МИНИСТЕРСТВО ВЫСШЕГО ОБРАЗОВАНИЯ, НАУКИ И ИННОВАЦИЙ РЕСПУБЛИКИ УЗБЕКИСТАН",
                'shahar_yil': "ГОРОД ТАШКЕНТ - {year}",
                'work_title': "САМОСТОЯТЕЛЬНАЯ РАБОТА" if work_type == 'mustaqil_ish' else "РЕФЕРАТ",
                'label_topic': 'Тема',
                'label_bajaruvchi': "Выполнил",
                'label_group': "Группа",
                'label_rahbar': "Научный руководитель",
                'title_intro': "ВВЕДЕНИЕ",
                'title_conclusion': "ЗАКЛЮЧЕНИЕ",
                'title_references': "СПИСОК ЛИТЕРАТУРЫ",
            },
            'en': {
                'uni_name': "MINISTRY OF HIGHER EDUCATION, SCIENCE AND INNOVATION OF THE REPUBLIC OF UZBEKISTAN",
                'shahar_yil': "TASHKENT - {year}",
                'work_title': "INDEPENDENT WORK" if work_type == 'mustaqil_ish' else "COURSE PAPER",
                'label_topic': 'Topic',
                'label_bajaruvchi': "Completed by",
                 'label_group': "Group",
                'label_rahbar': "Academic Supervisor",
                'title_intro': "INTRODUCTION",
                'title_conclusion': "CONCLUSION",
                'title_references': "REFERENCES",
            },
            'kr': {
                'uni_name': "ЎЗБЕКИСТОН РЕСПУБЛИКАСИ ОЛИЙ ТАЪЛИМ, ФАН ВА ИННОВАЦИЯЛАР ВАЗИРЛИГИ",
                'shahar_yil': "ТОШКЕНТ - {year}",
                'work_title': "МУСТАҚИЛ ИШ" if work_type == 'mustaqil_ish' else "РЕФЕРАТ",
                'label_topic': 'Мавзу',
                'label_bajaruvchi': "Бажарувчи",
                'label_group': "Группа",
                'label_rahbar': "Илмий раҳбар",
                'title_intro': "КИРИШ",
                'title_conclusion': "ХУЛОСА",
                'title_references': "ФОЙДАЛАНИЛГАН АДАБИЁТЛАР РЎЙХАТИ",
            }
        }
        
        current_year = datetime.now().year
        
        # Tanlangan til mavjud bo'lmasa, uzbek (lotin) zaxira sifatida ishlatiladi
        lang_titles = titles.get(lang, titles['uz'])
        
        # Placeholder'lar (joy tutgichlar)
        placeholders = {
            'topic_placeholder': 'MAVZU KIRITILMAGAN',
            'fio_placeholder': 'KIRITILMAGAN F.I.SH.',
            'uni_placeholder': 'KIRITILMAGAN TA`LIM MUASSASASI / KAFEDRA',
        }
        
        return {
            # Rasmiy Matnlar (Tilga bog'langan)
            'university_name': lang_titles['uni_name'],
            'city_year': lang_titles['shahar_yil'].format(year=current_year),
            'work_title_display': lang_titles['work_title'],
            
            # Titul sahifasidagi Yorliqlar (Labels - Tilga bog'langan)
            'label_topic': lang_titles['label_topic'],
            'label_bajaruvchi': lang_titles['label_bajaruvchi'],
            'label_group': lang_titles['label_group'],
            'label_rahbar': lang_titles['label_rahbar'],
            
            'title_intro': lang_titles['title_intro'],
            'title_conclusion': lang_titles['title_conclusion'],
            'title_references': lang_titles['title_references'],
            
            # Zaxira matnlar (Agar ma'lumotlar topilmasa ishlatiladi)
            **placeholders
    }
    
    async def translate_text(self, text: str, target_lang: str) -> str:
        # target_lang kodini matnga moslashtirish
        if target_lang == 'kr':
            lang_name = 'Uzbek (Cyrillic)'
        elif target_lang == 'ru':
            lang_name = 'Russian'
        elif target_lang == 'en':
            lang_name = 'English'
        else: # uz
            return text # O'zbek lotinidan O'zbek lotiniga tarjima qilish shart emas

        prompt = (
            f"Tarjima qil: '{text}'. Natijani faqat {lang_name} tilida va faqat tarjima qilingan matn sifatida bering. "
            "Matnni o'z ma'nosini yo'qotmagan holda va rasmiy uslubda tarjima qiling."
        )

        try:
            for attempt in range(3):
                try:
                    # Asinxron chaqiruv. self.client.models.generate_content allaqachon async
                    response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model,
                    contents=prompt
                    )
                    # Agar muvaffaqiyatli bo'lsa, natijani qaytaramiz
                    return response.text.strip()
                
                except APIError as e:
                    # 503 yoki Unavailable xatolarini tekshiramiz
                    if '503' in str(e) or 'UNAVAILABLE' in str(e) or 'Rate limit exceeded' in str(e):
                        print(f"[{target_lang}] Tarjima 503/Rate Limit xatosi. {attempt+1}-urinishdan keyin qayta urinish...")
                        await asyncio.sleep(2 * (attempt + 1)) # 2, 4, 6 soniya kutish
                    else:
                        raise # Boshqa xatolarni qayta yuborish
            
            # 3 urinishdan keyin ham muvaffaqiyat bo'lmasa, bo'sh satr qaytaramiz
            print(f"[{target_lang}] Tarjima 3 urinishdan keyin ham bajarilmadi.")
            return text # Tarjima qilinmagan asl matnni qaytarish xavfsizroq

        except Exception as e:
                print(f"Gemini API xatosi (Tarjima): {e}")
                # Xato bo'lsa ham, asl matnni qaytarish xavfsizroq, hujjati buzilmasligi uchun
                return text 