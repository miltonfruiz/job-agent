import app.config  # noqa: F401  (carga las variables de .env como side effect)
from fastapi import FastAPI

app = FastAPI(title="Job Application Agent")


@app.get("/health")
def health():
    return {"status": "ok"}


# TODO: endpoint POST /applications que reciba job_posting + cv,
# invoque build_graph().invoke(...) y devuelva el paquete final o
# el estado pausado en human_checkpoint.
