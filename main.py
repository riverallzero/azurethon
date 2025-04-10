from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from msrest.authentication import CognitiveServicesCredentials

import openai
import vobject

import time
import os
import re

from dotenv import load_dotenv
load_dotenv()

IMAGE_SAVE_DIR = "./tmp/img"
VCF_SAVE_DIR = "./tmp/vcf"
os.makedirs(IMAGE_SAVE_DIR, exist_ok=True)
os.makedirs(VCF_SAVE_DIR, exist_ok=True)

# start command process
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [[InlineKeyboardButton("명함 사진 - 연락처 파일 변환 서비스", callback_data="upload_image")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("서비스 버튼을 눌러주세요:", reply_markup=reply_markup)

# button callback process
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "upload_image":
        await query.message.reply_text("이미지를 보내주세요!")

# image receive process
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    photo = update.message.photo[-1]  # maximum resolution
    file = await context.bot.get_file(photo.file_id)

    file_path = os.path.join(IMAGE_SAVE_DIR, f"{photo.file_id}.jpg")
    await file.download_to_drive(file_path)
    print(f"saved image {file_path}")

    vcf_path = azure_ocr(
        image_paths=os.listdir(IMAGE_SAVE_DIR), 
        subscription_key=os.environ["AZURE_KEY"], 
        endpoint="https://azurethon-instance.cognitiveservices.azure.com/"
    )

    for vcf_path in vcf_path:
        if vcf_path and os.path.exists(vcf_path):
            await update.message.reply_document(document=open(vcf_path, "rb"))
            os.remove(vcf_path)

def make_contact(text_results):
    client = openai.OpenAI(api_key=os.environ["OPENAI_KEY"])

    response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "너는 OCR 추출된 정보를 명함처럼 정리해주는 도우미야."},
        {"role": "user", "content": f"{text_results}이 리스트에서 사람이름, 회사이름, 휴대폰번호가 뭐야?"}
    ]
)
    answer = response.choices[0].message.content

    v = vobject.vCard()

    name =  answer.split("\n")[0].split(":")[1]
    name = name.replace(" ", "")

    v.add("fn").value = name
    v.add("title").value = answer.split("\n")[1].split(":")[1]
    v.add("tel").value = re.sub("[^0-9]", "", answer.split("\n")[2].split(":")[1].strip())

    # save contact file as vcf 
    vcf_file = v.serialize()
    vcf_path = os.path.join(VCF_SAVE_DIR, f"{name}.vcf")
    with open(vcf_path, "w", encoding="utf-8") as f:
        f.write(vcf_file)

    return vcf_path

def azure_ocr(image_paths, subscription_key, endpoint):
    computervision_client = ComputerVisionClient(endpoint, CognitiveServicesCredentials(subscription_key))
    
    vcf_paths = []
    for image_path in image_paths:
        local_image = open(os.path.join(IMAGE_SAVE_DIR, image_path), "rb")

        read_response = computervision_client.read_in_stream(local_image, raw=True)
        read_operation_location = read_response.headers["Operation-Location"]
        operation_id = read_operation_location.split("/")[-1]

        while True:
            read_result = computervision_client.get_read_result(operation_id)
            if read_result.status not in ["notStarted", "running"]:
                break
            time.sleep(1)

        if read_result.status == OperationStatusCodes.succeeded:
            text_results = [line.text for text_result in read_result.analyze_result.read_results for line in text_result.lines]
            vcf_path = make_contact(text_results)
            vcf_paths.append(vcf_path)
        os.remove(os.path.join(IMAGE_SAVE_DIR, image_path))
    return vcf_paths


def main():
    TELEGRAM_API = os.environ["TELEGRAM_KEY"]
    app = Application.builder().token(TELEGRAM_API).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))

    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
