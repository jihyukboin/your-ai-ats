GMS KEY 발급 방법
1.좌측 메뉴에서 "Key 발급 신청" > "Key 발급 신청서 작성하기"를 클릭합니다.
2.사용 계획을 작성하고 "제출하기"를 클릭합니다.
3.신청서가 승인되면, 좌측 메뉴 "Key 조회"에서 발급된 Key를 확인할 수 있습니다.
알림
별도의 교보재로 지급되는 GMS Key는 별도의 신청 없이, 교보재 배포 시기에 생성 및 제공됩니다.
주의
GMS Key는 외부에 노출해서는 안 됩니다. 브라우저나 모바일 앱의 클라이언트 코드에 직접 하드코딩하지 말고, 서버 환경 변수나 전용 KMS에서 불러와 사용하시기 바랍니다.
GMS Key 정보 API로 확인하기
아래의 방법을 통해 GMS Key의 전체 크레딧, 사용 크레딧, 잔여 크레딧과 만료일시를 확인할 수 있습니다.
요청 양식
bash
 copy code
curl "https://gms.ssafy.io/gmsapi/key-info" \
    -X GET \
    -H "authorization: Bearer $GMS_KEY"
응답 양식
bash
 copy code
{
  "totalCredit": number,   // 전체 크레딧
  "usedCredit": number,    // 사용 크레딧
  "remainCredit": number,  // 잔여 크레딧
  "expiredDate": string    // 만료 일시 (KST)
}
사용 방법
GMS를 통해 API를 호출할 때는 기존 AI API와 동일한 파라미터와 Body를 사용합니다. 다만 엔드포인트만을 GMS API 엔드포인트로 변경하면 됩니다.
GMS API 엔드포인트: https://gms.ssafy.io/gmsapi/
그리고 기존에 사용하려고 했던 엔드포인트를 path로 추가하면 됩니다. 예를 들어 openai의 gpt-4.1모델이라면
GMS를 통한 OpenAI 엔드포인트: https://gms.ssafy.io/gmsapi/api.openai.com/v1/responses
Authorization
모델 별로 Authorization의 위치와 명칭이 각각 다릅니다. OpenAI 모델은 Header로 "Authorization : Bearer {API_KEY}"을 사용하고, Gemini 모델은 Header로 "x-goog-api-key: {API_KEY}"를 사용합니다. 각 모델의 기존 API_KEY가 들어가는 자리에 GMS Key를 넣어주면 됩니다.
REST API 방식
OpenAI OpenAI의 gpt-4.1 모델을 예시로 보겠습니다. GMS API로 호출하기 위해서는 다음과 같이 호출하면 됩니다.
bash
 copy code
curl "https://gms.ssafy.io/gmsapi/api.openai.com/v1/responses" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $GMS_KEY" \
    -d '{ 
        "model": "gpt-4.1",
        "input": "Write a one-sentence bedtime story about a unicorn."
    }'
Gemini Gemini의 gemini-2.5-flash 모델을 예시로 보겠습니다. GMS API로 호출하기 위해서는 다음과 같이 호출하면 됩니다.
bash
 copy code
curl "https://gms.ssafy.io/gmsapi/generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent" \
  -H 'Content-Type: application/json' \
  -H "x-goog-api-key: $GMS_KEY" \  
  -X POST \
  -d '{
    "contents": [
      {
        "parts": [
          {
            "text": "How does AI work?"
          }
        ]
      }
    ]
  }'
SDK 방식
생성형 AI 서비스들은 REST API 외에도 파이썬, 자바스크립트 라이브러리를 제공하고 있습니다. 이러한 라이브러리에도 GMS를 적용할 수 있습니다. 우선 OpenAI 라이브러리 활용 방법을 설명드리겠습니다.
OpenAI SDK 설치
bash
 copy code
pip install openai
OpenAI SDK가 설치되면, example.py라는 파일을 만들고 예제 코드를 복사하여 붙여넣으세요:
python
 copy code
from openai import AsyncOpenAI
import os
import getpass
import asyncio

# GMS KEY를 입력하는 단계입니다. 실제 서비스에서는 환경변수나 KMS를 활용하세요!
if not os.environ.get("OPENAI_API_KEY"):
  os.environ["OPENAI_API_KEY"] = getpass.getpass("GMS KEY를 입력하세요: ")

# 중요! OpenAI의 BASE_URL을 GMS로 설정합니다. 
client = AsyncOpenAI(base_url="https://gms.ssafy.io/gmsapi/api.openai.com/v1")

async def main():
    res_text = ""
    stream = await client.chat.completions.create(
        model='gpt-4.1',
        messages=[{"role": "system", "content": "당신은 Friday라는 이름의 긍정 에너지 가득한 AI입니다."}, {"role": "user", "content": "안녕! 오늘 기분 어때?"}],
        max_tokens=1024,
        stream=True,
    )
    async for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            res_text += chunk.choices[0].delta.content
            print(chunk.choices[0].delta.content, end="", flush=True)
    print("\n\n---------\n전체 응답:\n", res_text)

if __name__ == "__main__":
    asyncio.run(main())
예제에서는 Stream으로 답변하도록 요청했습니다. 보통 system 내부에서 LLM을 사용하는 경우 일반 응답으로 요청하고, 유저에게 최종적으로 전달되는 응답은 Stream으로 요청합니다.
Gemini SDK 설치
이번에는 gemini sdk 사용법을 설명드리겠습니다. 우선 gemini sdk 라이브러리를 설치합니다.
bash
 copy code
pip install google-genai
OpenAI SDK가 설치되면, example.py라는 파일을 만들고 예제 코드를 복사하여 붙여넣으세요:
python
 copy code
import os
import getpass
from google import genai

# GMS KEY를 입력하는 단계입니다. 실제 서비스에서는 환경변수나 KMS를 활용하세요!
if not os.environ.get("GEMINI_API_KEY"):
    os.environ["GEMINI_API_KEY"] = getpass.getpass("GMS KEY를 입력하세요: ")

# Gemini 클라이언트 생성 (base_url을 GMS로 설정)
client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"],
    http_options={"base_url": "https://gms.ssafy.io/gmsapi/generativelanguage.googleapis.com"}
)

def main():
    # Gemini 스트리밍 응답 예시 (동기 제너레이터)
    stream = client.models.generate_content_stream(
        model="gemini-2.5-flash",
        contents="안녕? 오늘 기분이 어때?"
    )
    print("Gemini 스트리밍 응답:")
    for chunk in stream:
        if hasattr(chunk, "text") and chunk.text:
            print(chunk.text, end="", flush=True)
    print("\n\n---------\n전체 응답 스트림 완료")

if __name__ == "__main__":
    main()
Langchain 방식
이번에는 Langchain에서 GMS를 사용하는 예제를 보여드리겠습니다. 우선 Langchain 라이브러리를 설치합니다.
bash
 copy code
pip install langchain
Langchain 라이브러리가 설치되면, example_lang.py라는 파일을 만들고 예제 코드를 복사하여 붙여넣으세요:
python
 copy code
import getpass
import os
from langchain.chat_models import init_chat_model

# GMS KEY를 입력하는 단계입니다. 실제 서비스에서는 환경변수나 KMS를 활용하세요!
if not os.environ.get("OPENAI_API_KEY"):
  os.environ["OPENAI_API_KEY"] = getpass.getpass("GMS KEY를 입력하세요: ")

# 중요! langchain의 BASE_URL을 GMS로 설정합니다. 
os.environ["OPENAI_API_BASE"] = "https://gms.ssafy.io/gmsapi/api.openai.com/v1"


model = init_chat_model("gpt-4o-mini", model_provider="openai")

response = model.invoke("Hello, world!. 한국어로 대답해줘.")
print(response) 
위와 같이 BASE_URL만 변경해주면 GMS적용 여부를 쉽게 ON/OFF 할 수 있습니다!

gpt-6-sol
OpenAI의 차세대 고성능 텍스트 생성 모델
고정밀 문제 해결과 깊이 있는 데이터 해석으로 고품질 서비스 실현
POST https://gms.ssafy.io/gmsapi/api.openai.com/v1/responses
OpenAI의 차세대 고성능 텍스트 생성 모델입니다.
gpt-6-sol은 복잡한 코딩 및 에이전트 기반 워크플로우에 최적화되어 있습니다.
컨텍스트 창(Context window) : 1,050,000 tokens
최대 출력 토큰(Max output) : 128,000 tokens
Quick Example
bash
 copy code
curl "https://gms.ssafy.io/gmsapi/api.openai.com/v1/responses" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GMS_KEY" \
  -d '{
    "model": "gpt-6-sol",
    "input": "Hello, World!"
  }'
크레딧 비용
Input	Output
0.02	0.1
알림
사용한 토큰 수 x 비용만큼 크래딧이 차감됩니다.
참고 문서
엔드포인트를 반드시 https://gms.ssafy.io/gmsapi/로 변경하고, 환경 변수를 사용해 호출해야 합니다.
세부 파라미터·응답 포맷은 OpenAI Responses 공식 레퍼런스와 동일합니다.
참고: OpenAI Responses API reference