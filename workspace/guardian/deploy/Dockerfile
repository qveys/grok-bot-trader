# Alternative conteneur (le superviseur guardianctl.sh reste la méthode par défaut).
# ATTENTION : restart:on-failure de Docker relancerait aussi après une mort (code 1) ;
# utiliser ce Dockerfile avec restart "no" et guardianctl.sh à l'extérieur, ou accepter
# que la relance après halt soit inoffensive (le code 2 refuse de rejouer un état mort).
FROM python:3.12-slim
WORKDIR /workspace/guardian
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY guardian ./guardian
CMD ["python", "-m", "guardian"]
