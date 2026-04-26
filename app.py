import os
import json
import traceback
import requests
from flask import Flask, request, jsonify
from openai import OpenAI
from pypdf import PdfReader
from io import BytesIO

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

        # 1. PDF 다운로드
        pdf_response = requests.get(pdf_url, timeout=60)
        if pdf_response.status_code != 200:
            return jsonify({
                "error": "PDF download failed",
                "status": pdf_response.status_code,
                "url": pdf_url
            }), 400

        # 2. PDF에서 텍스트 추출
        pdf_file = BytesIO(pdf_response.content)
        reader = PdfReader(pdf_file)

        extracted_text = ""

        # 너무 길어지면 느려지므로 최대 20페이지까지만 우선 사용
        max_pages = min(len(reader.pages), 20)

        for i in range(max_pages):
            page_text = reader.pages[i].extract_text()
            if page_text:
                extracted_text += f"\n\n[Page {i + 1}]\n{page_text}"

        if not extracted_text.strip():
            return jsonify({
                "error": "PDF text extraction failed",
                "message": "PDF에서 텍스트를 추출하지 못했습니다. 스캔본 PDF일 가능성이 있습니다."
            }), 400

        # 3. 너무 긴 텍스트 제한
        extracted_text = extracted_text[:25000]

        prompt = f"""
너는 한국 의과대학 시험 문제 출제자다.

아래 강의록 텍스트만 근거로 5지선다 문제 5개를 만들어라.

조건:
- 반드시 제공된 강의록 텍스트 안의 내용만 근거로 출제
- 강의록에 없는 외부 지식 사용 금지
- 정답은 ①~⑤ 중 하나
- 해설에는 정답 근거를 포함
- 한국어로 작성
- JSON 배열만 출력
- 코드블록 금지
- 추가 설명 금지

출력 형식:
[
  {{
    "question": "문제",
    "choice_a": "선지1",
    "choice_b": "선지2",
    "choice_c": "선지3",
    "choice_d": "선지4",
    "choice_e": "선지5",
    "answer": "③",
    "explanation": "해설"
  }}
]

강의록 텍스트:
{extracted_text}
"""

        # 4. OpenAI 문제 생성
        response = client.responses.create(
            model="gpt-4o-mini",
            input=prompt
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