# Lambda의 Python 3.11 런타임을 기반으로 설정
FROM public.ecr.aws/lambda/python:3.11

# 작업 디렉토리 설정
WORKDIR /app

# requirements.txt 복사
COPY requirements.txt .

# 필요한 라이브러리 설치
RUN pip install -r requirements.txt

# Python 코드 복사
COPY lambda_function.py .

# Lambda에서 사용할 핸들러 설정
CMD ["lambda_function.lambda_handler"]