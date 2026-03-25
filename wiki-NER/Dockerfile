FROM public.ecr.aws/lambda/python:3.11

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY wiki_ner.py ${LAMBDA_TASK_ROOT}

CMD ["wiki_ner.lambda_handler"]