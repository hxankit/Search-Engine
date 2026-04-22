from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from app.search import search

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "query": "", "results": []})

@app.post("/search", response_class=HTMLResponse)
def do_search(request: Request, query: str = Form(...)):
    query   = query.strip()
    results = search(query) if query else []
    return templates.TemplateResponse("index.html", {"request": request, "query": query, "results": results})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)