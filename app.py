import os
import json
import base64
import requests
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.route("/")
def home():
    return "Med Quiz API is running."

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()

    pdf_url = data.get("pdf_url")
    if not pdf_url:
        return jsonify({"error": "pdf_url is required"}), 400

    pdf_response = requests.get(pdf_url, timeout=60)
    if pdf_response.status_code != 200:
        return jsonify({"error": "PDF download failed", "status": pdf_response.status_code}), 400

    pdf_base64 = base64.b64encode(pdf_response.content).decode("utf-8")

    prompt = """
너는 한국 의과대학 시험 문제 출제자다.

첨부된 강의록 PDF 내용만 근거로 5지선다 문제 5개를 만들어라.

조건:
- 반드시 첨부 PDF 안의 내용만 근거로 출제
- 강의록에 없는 외부 지식 사용 금지
- 정답은 ①~⑤ 중 하나
- 해설에는 정답 근거를 포함
- 한국어로 작성
- JSON 배열만 출력
- 코드블록 금지
- 추가 설명 금지

출력 형식:
[
  {
    "question": "문제",
    "choice_a": "선지1",
    "choice_b": "선지2",
    "choice_c": "선지3",
    "choice_d": "선지4",
    "choice_e": "선지5",
    "answer": "③",
    "explanation": "해설"
  }
]
"""

    response = client.responses.create(
        model="gpt-4o-mini",
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_file",
                        "filename": "lecture.pdf",
                        "file_data": f"data:application/pdf;base64,{pdf_base64}",
                    },
                    {
                        "type": "input_text",
                        "text": prompt,
                    },
                ],
            }
        ],
    )

    text = response.output_text.strip()
    text = text.replace("```json", "").replace("```", "").strip()

    try:
        questions = json.loads(text)
    except Exception:
        return jsonify({"error": "JSON parse failed", "raw": text}), 500

    return jsonify({"questions": questions})