import os
import json
import base64
import traceback
import requests
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)

@app.route("/")
def home():
    return "Med Quiz API is running."

@app.route("/generate", methods=["POST"])
def generate():
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return jsonify({"error": "OPENAI_API_KEY is missing"}), 500

        client = OpenAI(api_key=api_key)

        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON received"}), 400

        pdf_url = data.get("pdf_url")
        if not pdf_url:
            return jsonify({"error": "pdf_url is required"}), 400

        pdf_response = requests.get(pdf_url, timeout=60)

        if pdf_response.status_code != 200:
            return jsonify({
                "error": "PDF download failed",
                "status": pdf_response.status_code,
                "url": pdf_url
            }), 400

        pdf_base64 = base64.b64encode(pdf_response.content).decode("utf-8")

        prompt = """
첨부된 강의록 PDF 내용만 근거로 한국 의과대학 5지선다 문제 5개를 만들어라.
외부 지식 사용 금지.
JSON 배열만 출력.
코드블록 금지.

형식:
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
                            "file_data": f"data:application/pdf;base64,{pdf_base64}"
                        },
                        {
                            "type": "input_text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )

        text = response.output_text.strip()
        text = text.replace("```json", "").replace("```", "").strip()

        questions = json.loads(text)

        return jsonify({"questions": questions})

    except Exception as e:
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500