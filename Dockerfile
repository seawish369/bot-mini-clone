FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY kb ./kb
COPY assistant ./assistant
COPY main.py ask.py ./

RUN chmod -R a+rX /app \
    && useradd --create-home app \
    && mkdir -p /app/articles \
    && chown app /app/articles
USER app

ENTRYPOINT ["python"]
CMD ["main.py"]
