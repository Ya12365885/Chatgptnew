bot_token: "8190279144:AAErzPbECGw5Rm50okIz3WfYKstEfcaryOg"
import requests
import json
import time
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

# إعدادات Facebook
FACEBOOK_PAGE_ACCESS_TOKEN = 'EAAOQ6MhTogABO0KPtHaqZBk2JZAe09qaowHaRggX0GMHmPV57xeQVqwWGCC8XXSDkyUEI2BwL1MiDA4R65tAkVdlvoH8CqZBnOxFPxEgZAVuCO9rseadZBuQEd02a4xyrO8IfoXmd7jIdY5TA1EIKHRghT4a6FAxgOXqRDY8PnECTYmIEuFbHmB699bCyN3On8QZDZD'
FACEBOOK_GRAPH_API_URL = 'https://graph.facebook.com/v11.0/me/messages'

# إعدادات APIs
CHAT_API_URL = "https://prod-smith.vulcanlabs.co/api/v7/chat_android"
VISION_API_URL = "https://api.vulcanlabs.co/smith-v2/api/v7/vision_android"
GETIMG_API_URL = "https://api.getimg.ai/v1/stable-diffusion-xl/text-to-image"
GETIMG_API_KEY = "key-3XbWkFO34FVCQUnJQ6A3qr702Eu7DDR1dqoJOyhMHqhruEhs22KUzR7w631ZFiA5OFZIba7i44qDQEMpKxzegOUm83vCfILb"
VISION_AUTH_TOKEN = "FOcsaJJf1A+Zh3Ku6EfaNYbo844Y7168Ak2lSmaxtNZVtD7vcaJUmTCayc1HgcXIILvdmnzsdPjuGwqYKKUFRLdUVQQZbfXHrBUSYrbHcMrmxXvDu/DHzrtkPqg90dX/rSmTRnx7sz7pHTOmZqLLfLUnaO2XTEZLD0deMpRdzQE="
ASSEMBLYAI_API_KEY = "771de44ac7644510a0df7e9a3b8a6b7c"
GOOGLE_TTS_API_KEY = "AIzaSyBrHRq1560psTF4pnWChWGV4G1mgymWb8g"

# التخزين المحلي للمستخدمين
user_conversations = {}
current_access_token = None
message_queue = []
processing_lock = False

# ذاكرة تخزين مؤقت للتوكن
@lru_cache(maxsize=1)
def get_cached_access_token(session):
    return get_access_token(session)

def get_access_token(session):
    url = "https://chatgpt-au.vulcanlabs.co/api/v1/token"
    headers = {
        "Host": "chatgpt-au.vulcanlabs.co",
        "x-vulcan-application-id": "com.smartwidgetlabs.chatgpt",
        "accept": "application/json",
        "user-agent": "Chat Smith Android, Version 3.8.0(602)",
        "x-vulcan-request-id": "9149487891720485306508",
        "content-type": "application/json; charset=utf-8",
        "accept-encoding": "gzip"
    }
    payload = {
        "device_id": "F75FA09A4ECFF631",
        "order_id": "",
        "product_id": "",
        "purchase_token": "",
        "subscription_id": ""
    }
    try:
        response = session.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        return response.json().get('AccessToken')
    except requests.exceptions.RequestException as e:
        print(f"Error fetching access token: {e}")
        return None

def send_chat_request(session, access_token, messages):
    headers = {
        "Host": "prod-smith.vulcanlabs.co",
        "authorization": f"Bearer {access_token}",
        "x-firebase-appcheck-error": "-2%3A+Integrity+API+error...",
        "x-vulcan-application-id": "com.smartwidgetlabs.chatgpt",
        "accept": "application/json",
        "user-agent": "Chat Smith Android, Version 3.8.0(602)",
        "x-vulcan-request-id": "9149487891720485379249",
        "content-type": "application/json; charset=utf-8",
        "accept-encoding": "gzip"
    }
    payload = {
        "model": "gpt-4",
        "user": "F75FA09A4ECFF631",
        "messages": messages,
        "nsfw_check": True,
        "functions": [
            {
                "name": "create_ai_art",
                "description": "Return this only if the user wants to create a photo or art...",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "The prompt to create art"
                        }
                    }
                }
            }
        ]
    }
    try:
        response = session.post(CHAT_API_URL, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending chat request: {e}")
        return None

def transcribe_audio(audio_url):
    try:
        # إعداد طلب التفريغ مع نموذج nano للغة العربية
        data = {
            "audio_url": audio_url,
            "language_code": "ar",
            "speech_model": "nano"
        }
        
        headers = {
            "authorization": ASSEMBLYAI_API_KEY,
            "content-type": "application/json"
        }
        
        print("جاري إرسال طلب التفريغ...")
        transcript_response = requests.post(
            "https://api.assemblyai.com/v2/transcript", 
            json=data, 
            headers=headers,
            timeout=30
        )
        
        response_json = transcript_response.json()
        print("الرد:", response_json)

        if "id" not in response_json:
            print("فشل في بدء التفريغ. الرد لا يحتوي على 'id'.")
            return None

        transcript_id = response_json["id"]
        polling_endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"

        # الانتظار لحين اكتمال التفريغ
        print("جاري تفريغ النص الصوتي...")
        while True:
            transcription_result = requests.get(polling_endpoint, headers=headers, timeout=10).json()

            if transcription_result['status'] == 'completed':
                print("\nالنص المستخرج:\n", transcription_result['text'])
                return transcription_result['text']
            elif transcription_result['status'] == 'error':
                print("حدث خطأ أثناء التفريغ:", transcription_result['error'])
                return None
            else:
                time.sleep(1)
                
    except Exception as e:
        print(f"Error in transcription: {e}")
        return None

def text_to_speech(text, sender_id):
    try:
        url = "https://texttospeech.googleapis.com/v1/text:synthesize"
        headers = {
            "x-goog-api-key": GOOGLE_TTS_API_KEY,
            "content-type": "application/json; charset=utf-8"
        }
        data = {
            "audioConfig": {
                "audioEncoding": "MP3",
                "effectsProfileId": [],
                "pitch": 0.0,
                "sampleRateHertz": 0,
                "speakingRate": 1.0,
                "volumeGainDb": 0
            },
            "input": {"text": text},
            "voice": {
                "languageCode": "ar-XA",
                "name": "ar-XA-Standard-C",
                "ssmlGender": "SSML_VOICE_GENDER_UNSPECIFIED"
            }
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=15)
        if response.status_code == 200:
            audio_content = response.json().get('audioContent')
            if audio_content:
                # تحويل base64 إلى bytes
                audio_bytes = base64.b64decode(audio_content)
                return audio_bytes
        return None
    except Exception as e:
        print(f"Error in text-to-speech: {e}")
        return None

def process_image(session, access_token, image_url, sender_id):
    try:
        # تحميل الصورة من فيسبوك
        image_response = requests.get(image_url, timeout=15)
        if image_response.status_code != 200:
            send_facebook_message(session, sender_id, "❌ لم أتمكن من تحميل الصورة التي أرسلتها.")
            return None
        
        # إعداد طلب Vision API
        boundary = "44cb511a-c1d4-4f51-a017-1352f87db948"
        headers = {
            "Host": "api.vulcanlabs.co",
            "x-auth-token": VISION_AUTH_TOKEN,
            "authorization": f"Bearer {access_token}",
            "x-firebase-appcheck-error": "-9%3A+Integrity+API",
            "x-vulcan-application-id": "com.smartwidgetlabs.chatgpt",
            "accept": "application/json",
            "user-agent": "Chat Smith Android, Version 3.9.11(720)",
            "x-vulcan-request-id": "9149487891748042373127",
            "content-type": f"multipart/form-data; boundary={boundary}",
            "accept-encoding": "gzip"
        }
        
        # بناء جسم الطلب
        data_part = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="data"\r\n'
            f"Content-Length: 145\r\n\r\n"
            '{"model":"gpt-4o-mini","user":"F75FA09A4ECFF631","messages":[{"role":"user","content":"ما هذا وعلى ما يحتوي"}],"nsfw_check":true}\r\n'
        )
        
        image_part = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="images[]"; filename="uploaded_image.jpg"\r\n'
            f"Content-Type: image/jpeg\r\n\r\n"
        )
        
        end_boundary = f"\r\n--{boundary}--\r\n"
        
        # بناء الطلب كاملاً
        body = data_part.encode() + image_part.encode() + image_response.content + end_boundary.encode()
        
        # إرسال الطلب
        response = session.post(VISION_API_URL, headers=headers, data=body, timeout=30)
        if response.status_code == 200:
            result = response.json()
            content = next(
                (choice.get('Message', {}).get('content', '') for choice in result.get('choices', [])),
                "لا أستطيع تحليل هذه الصورة."
            )
            return content
        else:
            print(f"Vision API error: {response.status_code}, {response.text}")
            return None
            
    except Exception as e:
        print(f"Error processing image: {e}")
        return None

def generate_and_send_images(session, recipient_id, prompt):
    try:
        # إرسال رسالة "جاري إنشاء الصورة"
        send_facebook_message(session, recipient_id, "⏳ جاري إنشاء الصور، الرجاء الانتظار...")
        
        headers = {
            'Host': 'api.getimg.ai',
            'Accept': 'application/json',
            'Authorization': f'Bearer {GETIMG_API_KEY}',
            'Content-Type': 'application/json',
            'User-Agent': 'okhttp/4.12.0',
            'Connection': 'keep-alive',
        }
        
        generated_seeds = set()  # لتخزين البذور المستخدمة لمنع تكرار الصور
        
        # إنشاء قائمة بجميع الطلبات أولاً
        requests_data = []
        for i in range(4):
            seed = int(time.time()) + i
            while seed in generated_seeds:
                seed += 1
            generated_seeds.add(seed)
            
            data = {
                'height': 1024,
                'width': 1024,
                'model': 'realvis-xl-v4',
                'prompt': prompt,
                'negative_prompt': 'nude, naked, porn, sexual, explicit, adult, sex, xxx, erotic, blowjob, masturbation, intercourse, hentai, vulgar, profane, obscene, dirty, slut, whore, rape, fetish, gangbang, threesome, stripper, escort,',
                'response_format': 'url',
                'seed': seed,
                'steps': 30,
            }
            requests_data.append(data)
        
        # إرسال جميع الطلبات بشكل متوازي
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(
                lambda d: requests.post(GETIMG_API_URL, headers=headers, json=d, timeout=30), 
                data) for data in requests_data]
            
            for future in as_completed(futures):
                try:
                    response = future.result()
                    if response.status_code == 200:
                        result = response.json()
                        image_url = result.get('url')
                        
                        if image_url:
                            # تحميل الصورة من الرابط
                            img_response = requests.get(image_url, timeout=30)
                            if img_response.status_code == 200:
                                # إرسال الصورة إلى فيسبوك
                                upload_url = "https://graph.facebook.com/v11.0/me/messages"
                                files = {
                                    'attachment': (f'image_{i}.jpg', img_response.content, 'image/jpeg')
                                }
                                params = {
                                    "access_token": FACEBOOK_PAGE_ACCESS_TOKEN,
                                    "recipient": json.dumps({"id": recipient_id}),
                                    "message": json.dumps({"attachment": {"type": "image", "payload": {}}})
                                }
                                
                                response = session.post(upload_url, params=params, files=files, timeout=15)
                                if response.status_code != 200:
                                    print(f"Error sending image to Facebook: {response.text}")
                            else:
                                print(f"Failed to download image from URL: {image_url}")
                        else:
                            print(f"No image URL in response:", result)
                    else:
                        print(f"Error in image generation API:", response.status_code, response.text)
                except Exception as e:
                    print(f"Error in image generation process: {e}")
        
        # إرسال رسالة تأكيد
        send_facebook_message(session, recipient_id, "✅ تم إنشاء الصور بنجاح!")
        
    except Exception as e:
        print(f"Error in image generation process: {e}")
        send_facebook_message(session, recipient_id, "❌ حدث خطأ أثناء إنشاء الصور، يرجى المحاولة لاحقًا.")

def send_facebook_message(session, recipient_id, message_text):
    url = FACEBOOK_GRAPH_API_URL
    params = {"access_token": FACEBOOK_PAGE_ACCESS_TOKEN}
    headers = {"Content-Type": "application/json"}
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    try:
        response = session.post(url, params=params, headers=headers, data=json.dumps(data), timeout=10)
        if response.status_code != 200:
            print(f"Error sending message: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending message: {e}")

def send_facebook_audio(session, recipient_id, audio_bytes):
    try:
        upload_url = "https://graph.facebook.com/v11.0/me/messages"
        files = {
            'attachment': ('audio.mp3', audio_bytes, 'audio/mpeg')
        }
        params = {
            "access_token": FACEBOOK_PAGE_ACCESS_TOKEN,
            "recipient": json.dumps({"id": recipient_id}),
            "message": json.dumps({"attachment": {"type": "audio", "payload": {}}})
        }
        
        response = session.post(upload_url, params=params, files=files, timeout=15)
        if response.status_code != 200:
            print(f"Error sending audio to Facebook: {response.text}")
    except Exception as e:
        print(f"Error sending audio: {e}")

def handle_message(session, sender_id, message):
    global current_access_token, processing_lock
    
    # معالجة سريعة للردود الداخلية
    if 'text' in message and isinstance(message['text'], str):
        message_text = message['text'].lower()
        if 'مرحبا' in message_text or 'مرحبا بك' in message_text:
            send_facebook_message(session, sender_id, "كيف حالك؟")
            return
        elif 'كيفك' in message_text or 'كيف حالك' in message_text:
            send_facebook_message(session, sender_id, "أنا بخير، شكراً لك! كيف يمكنني مساعدتك؟")
            return
    
    # الحصول على التوكن مع التخزين المؤقت
    if not current_access_token:
        current_access_token = get_cached_access_token(session)
        if not current_access_token:
            print("Failed to get access token. Skipping message.")
            send_facebook_message(session, sender_id, "عذرًا، حدث خطأ في المصادقة. يرجى المحاولة لاحقًا.")
            return

    # معالجة المرفقات (الصور أو الصوت)
    if 'attachments' in message:
        attachments = message['attachments']['data']
        for attachment in attachments:
            mime_type = attachment.get('mime_type', '').lower()
            
            if 'image' in mime_type:
                image_url = None
                if 'image_data' in attachment and 'url' in attachment['image_data']:
                    image_url = attachment['image_data']['url']
                elif 'payload' in attachment and 'url' in attachment['payload']:
                    image_url = attachment['payload']['url']
                elif 'url' in attachment:
                    image_url = attachment['url']
                
                if image_url:
                    send_facebook_message(session, sender_id, "⏳ جاري تحليل الصورة، الرجاء الانتظار...")
                    
                    # معالجة الصورة في thread منفصل
                    with ThreadPoolExecutor() as executor:
                        future = executor.submit(process_image, session, current_access_token, image_url, sender_id)
                        try:
                            result = future.result(timeout=60)
                            if result:
                                send_facebook_message(session, sender_id, result)
                            else:
                                send_facebook_message(session, sender_id, "❌ لم أتمكن من تحليل الصورة.")
                        except Exception as e:
                            print(f"Error processing image: {e}")
                            send_facebook_message(session, sender_id, "❌ حدث خطأ أثناء معالجة الصورة.")
                else:
                    send_facebook_message(session, sender_id, "❌ لم أتمكن من الحصول على رابط الصورة.")
                return
                
            elif 'audio' in mime_type or 'voice' in mime_type or 'mpeg' in mime_type:
                audio_url = None
                if 'file_url' in attachment:
                    audio_url = attachment['file_url']
                elif 'payload' in attachment and 'url' in attachment['payload']:
                    audio_url = attachment['payload']['url']
                elif 'url' in attachment:
                    audio_url = attachment['url']
                elif 'audio_data' in attachment and 'url' in attachment['audio_data']:
                    audio_url = attachment['audio_data']['url']
                
                if audio_url:
                    if 'facebook.com' in audio_url and '?' not in audio_url:
                        audio_url += "?access_token=" + FACEBOOK_PAGE_ACCESS_TOKEN
                    
                    send_facebook_message(session, sender_id, "⏳ جاري تحويل الصوت إلى نص، الرجاء الانتظار...")
                    
                    # تحويل الصوت إلى نص في thread منفصل
                    with ThreadPoolExecutor() as executor:
                        future = executor.submit(transcribe_audio, audio_url)
                        try:
                            text = future.result(timeout=60)
                            if text:
                                send_facebook_message(session, sender_id, f"📝 النص المستخرج من الصوت:\n{text}")
                                
                                # معالجة النص كرسالة عادية
                                conversation_history = user_conversations.get(sender_id, [])
                                new_messages = conversation_history + [{"role": "user", "content": text}]
                                
                                response = send_chat_request(session, current_access_token, new_messages)
                                if response:
                                    response_message = next(
                                        (choice.get('Message', {}).get('content', '') for choice in response.get('choices', [])),
                                        "عذرًا، حدث خطأ في معالجة طلبك."
                                    )
                                    
                                    # إرسال الرد كنص
                                    send_facebook_message(session, sender_id, response_message)
                                    
                                    # تحويل الرد إلى صوت وإرساله في thread منفصل
                                    with ThreadPoolExecutor() as audio_executor:
                                        audio_future = audio_executor.submit(text_to_speech, response_message, sender_id)
                                        try:
                                            audio_bytes = audio_future.result(timeout=30)
                                            if audio_bytes:
                                                send_facebook_audio(session, sender_id, audio_bytes)
                                        except Exception as e:
                                            print(f"Error in audio conversion: {e}")
                                    
                                    # تحديث محادثة المستخدم
                                    user_conversations[sender_id] = new_messages + [{"role": "assistant", "content": response_message}]
                                else:
                                    send_facebook_message(session, sender_id, "❌ حدث خطأ في معالجة رسالتك الصوتية.")
                            else:
                                send_facebook_message(session, sender_id, "❌ لم أتمكن من تحويل الصوت إلى نص.")
                        except Exception as e:
                            print(f"Error in audio processing: {e}")
                            send_facebook_message(session, sender_id, "❌ حدث خطأ أثناء معالجة المقطع الصوتي.")
                else:
                    print(f"Audio attachment structure: {json.dumps(attachment, indent=2)}")
                    send_facebook_message(session, sender_id, "❌ لم أتمكن من الحصول على رابط المقطع الصوتي. يرجى إرسال المقطع مرة أخرى.")
                return
    
    # معالجة الرسائل النصية
    if 'text' not in message or not message['text']:
        return
        
    message_text = message['text']
    conversation_history = user_conversations.get(sender_id, [])
    new_messages = conversation_history + [{"role": "user", "content": message_text}]

    # تحديد الرد الافتراضي
    response_message = "عذرًا، حدث خطأ في معالجة طلبك."
    
    if message_text.startswith(("من انت", "من أنت", "من مطورك", "من صانعك", "من صاحبك")):
        response_message = "انا بوت ذكاء اصطناعي تم تطويري بواسطة Yacin Dz 🇩🇿 🇵🇸"
        send_facebook_message(session, sender_id, response_message)
    elif "اسرائيل" in message_text or "إسرائيل" in message_text:
        response_message = "عذرا انا لا اعرف ما تقول انا اعرف دولة فلسطين 🇵🇸 عاصمتها القدس"
        send_facebook_message(session, sender_id, response_message)
    else:
        # إرسال الطلب في thread منفصل
        with ThreadPoolExecutor() as executor:
            future = executor.submit(send_chat_request, session, current_access_token, new_messages)
            try:
                response = future.result(timeout=30)
                
                if not response:
                    current_access_token = get_cached_access_token(session)
                    if current_access_token:
                        future = executor.submit(send_chat_request, session, current_access_token, new_messages)
                        response = future.result(timeout=30)
                
                if response:
                    # التحقق مما إذا كانت الاستجابة تحتوي على طلب إنشاء صورة
                    image_request = False
                    for choice in response.get('choices', []):
                        if choice.get('Message', {}).get('function_call', {}).get('name') == 'create_ai_art':
                            try:
                                args = json.loads(choice['Message']['function_call']['arguments'])
                                prompt = args.get('prompt', '')
                                
                                if prompt:
                                    image_request = True
                                    # بدء عملية إنشاء الصور في thread منفصل
                                    with ThreadPoolExecutor() as img_executor:
                                        img_executor.submit(generate_and_send_images, session, sender_id, prompt)
                                    response_message = "تم استلام طلبك وسيتم إنشاء الصور قريبًا..."
                                else:
                                    response_message = "عذرًا، لم أتمكن من إنشاء الصور المطلوبة."
                                    send_facebook_message(session, sender_id, response_message)
                            except Exception as e:
                                print(f"Error processing image generation request: {e}")
                                response_message = "عذرًا، حدث خطأ أثناء محاولة إنشاء الصور."
                                send_facebook_message(session, sender_id, response_message)
                            break
                    
                    if not image_request:
                        response_message = next(
                            (choice.get('Message', {}).get('content', '') for choice in response.get('choices', [])),
                            "عذرًا، حدث خطأ في معالجة طلبك."
                        )
                        send_facebook_message(session, sender_id, response_message)
                        
                        # تحويل الرد إلى صوت وإرساله في thread منفصل
                        with ThreadPoolExecutor() as audio_executor:
                            audio_future = audio_executor.submit(text_to_speech, response_message, sender_id)
                            try:
                                audio_bytes = audio_future.result(timeout=30)
                                if audio_bytes:
                                    send_facebook_audio(session, sender_id, audio_bytes)
                            except Exception as e:
                                print(f"Error in audio conversion: {e}")
                else:
                    response_message = "عذرًا، حدث خطأ في معالجة طلبك."
                    send_facebook_message(session, sender_id, response_message)
            except Exception as e:
                print(f"Error in message processing: {e}")
                send_facebook_message(session, sender_id, "❌ حدث خطأ أثناء معالجة رسالتك.")
    
    # تحديث محادثة المستخدم
    user_conversations[sender_id] = new_messages + [{"role": "assistant", "content": response_message}]

def poll_facebook_messages():
    last_checked = int(time.time())
    processed_message_ids = set()
    
    with requests.Session() as session:
        while True:
            try:
                url = f"https://graph.facebook.com/v11.0/me/conversations?fields=messages.limit(5){{message,attachments,from,id}}&since={last_checked}&access_token={FACEBOOK_PAGE_ACCESS_TOKEN}"
                response = session.get(url, timeout=15)
                response.raise_for_status()
                conversations = response.json().get('data', [])
                
                # معالجة الرسائل بشكل متوازي
                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = []
                    for conversation in conversations:
                        for message in conversation['messages']['data']:
                            msg_id = message['id']
                            if msg_id not in processed_message_ids:
                                sender_id = message['from']['id']
                                message_content = message.get('message', {})
                                if isinstance(message_content, str):
                                    message_content = {'text': message_content}
                                
                                if 'attachments' in message:
                                    message_content['attachments'] = message['attachments']
                                
                                print(f"Received message from {sender_id}: {message_content}")
                                futures.append(executor.submit(handle_message, session, sender_id, message_content))
                                processed_message_ids.add(msg_id)
                    
                    # انتظار انتهاء جميع المهام
                    for future in as_completed(futures):
                        try:
                            future.result()
                        except Exception as e:
                            print(f"Error processing message: {e}")
                
            except requests.exceptions.RequestException as e:
                print(f"Error polling messages: {e}")
                time.sleep(0.1)
            
            last_checked = int(time.time())
            time.sleep(0.1)

if __name__ == "__main__":
    poll_facebook_messages()