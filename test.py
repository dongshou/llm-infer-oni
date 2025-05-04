from openai import OpenAI

client = OpenAI(
    api_key="EMPTY",  # vLLM不需要验证key
    base_url="http://192.168.31.247:8000/v1"  # vLLM服务地址
)

response = client.chat.completions.create(
    model="your_model_name",  # 与--served-model-name一致
    messages=[{"role": "user", "content": "你好！"}]
)
print(response.choices[0].message.content)