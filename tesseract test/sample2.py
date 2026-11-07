import re
from rapidocr_onnxruntime import RapidOCR

engine = RapidOCR()
result = engine("id_sample.jpg")
pattern = r"\b\d{2}-\d{4}-\d{6}\b"

for text in result[0]:
    match = re.search(pattern, text[1])

    if match:
        print(f"Student found ID: {match.group()}")
        print(f"Confidence Score:{text[2]}")