FROM public.ecr.aws/lambda/python:3.11

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY context_research.py ${LAMBDA_TASK_ROOT}

CMD ["context_research.lambda_handler"]