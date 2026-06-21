FROM python:3.11-slim

RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    TRANSFORMERS_CACHE=/home/user/.cache/huggingface \
    HF_HOME=/home/user/.cache/huggingface

WORKDIR $HOME/app

COPY --chown=user requirements.txt .
RUN pip install --user --no-cache-dir --upgrade pip && \
    pip install --user --no-cache-dir -r requirements.txt && \
    pip install --user --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY --chown=user . .

EXPOSE 7860
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
