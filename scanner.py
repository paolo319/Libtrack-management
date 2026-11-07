import re
from rapidocr import RapidOCR

engine = RapidOCR()

result = engine("id_sample.jpg")

pattern = r"\b\d{2}-\d{4}-\d{6}\b"

for text in result.txts:
    match = re.search(pattern, text)
    score = result.scores[result.txts.index(text)]

    if match:
        print("Student ID:", match.group())
        print(f"Confidence Score: {score * 100:.2f}%")

