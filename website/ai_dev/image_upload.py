import json
import re
import base64
from flask import Flask, render_template, request
import cloudinary.uploader
import openai
from io import BytesIO
from PIL import Image
import requests

OPEN_KEY = "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"
CLOUD_NAME = "dtqohanvi"
CLOUD_KEY = "437918759626267"
CLOUD_SECRET = "ZJ8f3zSFYoMk7q__4EUy6gOf3yQ"


cloudinary.config(
    cloud_name=("dtqohanvi"),
    api_key=("437918759626267"),
    api_secret=("ZJ8f3zSFYoMk7q__4EUy6gOf3yQ")
)

app = Flask(__name__)

openai.api_key = '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'  # Make sure this is set properly

def cloudinary_url_to_base64(url):
    response = requests.get(url)
    if response.status_code == 200:
        mime_type = response.headers.get("Content-Type", "image/png")
        encoded = base64.b64encode(response.content).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"
    else:
        raise Exception("Failed to download image from Cloudinary")

@app.route("/", methods=["GET", "POST"])
def upload():
    result = {}
    error = None

    if request.method == "POST":
        try:
            file = request.files.get("image")
            if not file:
                raise Exception("No image uploaded")

            # Upload to Cloudinary
            upload_result = cloudinary.uploader.upload(file)
            image_url = upload_result.get("secure_url")
            if not image_url:
                raise Exception("Cloudinary upload failed")

            # Convert to base64
            base64_image = cloudinary_url_to_base64(image_url)

            # OpenAI Vision Call
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Please analyze this image and return only a valid JSON object in this exact format:\n"
                            "{\n"
                            '  "console_brand": "PlayStation, Xbox, Nintendo, Sega, etc. or None",\n'
                            '  "console_model": "Model name if visible, e.g., PS5, Xbox Series X",\n'
                            '  "game_name": "The name of any visible or identifiable video game",\n'
                            '  "suggested_price: "The average price of the game/console",\n'
                            "}\n"
                            "Return only valid JSON. No explanation or markdown formatting."
                        )
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": base64_image}
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )

            raw_content = response.choices[0].message.content.strip()
            match = re.search(r'\{.*\}', raw_content, re.DOTALL)

            if not match:
                raise Exception("No valid JSON found in the model response")

            result_json = json.loads(match.group())

            # Assign fields
            result = {
                "console_brand": result_json.get("console_brand", "None"),
                "console_model": result_json.get("console_model", "None"),
                "game_name": result_json.get("game_name", "None"),
                "suggested_price": result_json.get("suggested_price", "None"),
            }

        except Exception as e:
            error = str(e)

    return render_template("upload.html", result=result, error=error)

if __name__ == "__main__":
    app.run(debug=True)