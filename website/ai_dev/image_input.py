from openai import OpenAI

client = OpenAI(api_key="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")

response = client.responses.create(
    model="gpt-4.1",
    input=[
        {"role": "user", "content": "what teams are playing in this image?"},
        {
            "role": "user",
            "content": [
                {
                    "type": "input_image",
                    "image_url": "https://upload.wikimedia.org/wikipedia/commons/3/3b/LeBron_James_Layup_%28Cleveland_vs_Brooklyn_2018%29.jpg"
                }
            ]
        }
    ]
)

print(response.output_text)