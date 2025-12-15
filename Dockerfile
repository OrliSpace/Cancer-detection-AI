
FROM python:3.10-slim


WORKDIR /app


COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY tcia_dicom_to_nifti.py .

ENTRYPOINT ["python", "tcia_dicom_to_nifti.py"]