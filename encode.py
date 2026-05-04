import base64

with open("teste.png", "rb") as f:
    img_b64 = base64.b64encode(f.read()).decode("utf-8")

print(img_b64)