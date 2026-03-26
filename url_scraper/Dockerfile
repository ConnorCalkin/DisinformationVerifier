FROM public.ecr.aws/lambda/python:3.11

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY url_scraper.py .

CMD [ "url_scraper.lambda_handler" ]