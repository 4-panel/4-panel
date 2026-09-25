from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from database import SessionLocal, User
import uuid

app = FastAPI()

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):

    db = SessionLocal()
    users = db.query(User).all()
    db.close()

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"users": users}
    )


@app.post("/users/create")
def create_user(
    username: str = Form(...),
    expires: str = Form(...),
    traffic_limit: int = Form(...)
):

    db = SessionLocal()

    new_user = User(
        username=username,
        uuid=str(uuid.uuid4()),
        expires=expires,
        traffic_limit=traffic_limit,
        enabled=True
    )

    db.add(new_user)
    db.commit()
    db.close()

    return RedirectResponse("/", status_code=303)


@app.post("/users/{user_id}/toggle")
def toggle_user(user_id: int):

    db = SessionLocal()

    user = db.query(User).filter(User.id == user_id).first()

    if user:
        user.enabled = not user.enabled
        db.commit()

    db.close()

    return RedirectResponse("/", status_code=303)
