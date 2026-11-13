FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 SLOVO_DATA_DIR=/data HOST=0.0.0.0 PORT=8080
WORKDIR /app
COPY requirements.txt .
COPY requirements.lock .
RUN pip install --no-cache-dir --upgrade "pip>=26.2" && pip install --no-cache-dir -r requirements.txt -c requirements.lock && useradd --uid 10001 --create-home slovo && mkdir /data && chown slovo:slovo /data && chmod 700 /data
COPY app.py accounts.py storage.py security.py speech.py serve.py wsgi.py ./
COPY data/vocabulary.json data/courses.py data/alphabet.py data/
COPY templates/ templates/
COPY static/ static/
COPY scripts/ scripts/
USER slovo
EXPOSE 8080
CMD ["python", "serve.py"]
