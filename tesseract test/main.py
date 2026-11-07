from rapidocr import RapidOCR

engine = RapidOCR()

result = engine("id_sample.jpg")
#print(result)
for text in result.txts:
    print(text)
 
for score in result.scores:
    print(score)
    

