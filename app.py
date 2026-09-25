from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from database import SessionLocal, User, Admin

import hashlib
import uuid
import os
import io
import qrcode
from urllib.parse import quote


app = FastAPI()


# =========================
# SESSION
# =========================

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv(
        "SESSION_SECRET",
        "change-this-secret"
    )
)


# =========================
# TEMPLATES
# =========================

templates = Jinja2Templates(
    directory="templates"
)


# =========================
# PASSWORD HASH
# =========================

def hash_password(password):
    return hashlib.sha256(
        password.encode()
    ).hexdigest()


# =========================
# CREATE ADMIN
# =========================

def create_admin_if_missing():

    db = SessionLocal()

    try:

        admin = db.query(Admin).first()

        if not admin:

            username = os.getenv(
                "ADMIN_USERNAME",
                "admin"
            )

            password = os.getenv(
                "ADMIN_PASSWORD",
                "admin123"
            )

            new_admin = Admin(
                username=username,
                password_hash=hash_password(password)
            )

            db.add(new_admin)
            db.commit()

    finally:

        db.close()


create_admin_if_missing()


# =========================
# LOGIN CHECK
# =========================

def logged_in(request: Request):

    return (
        request.session.get("admin_id")
        is not None
    )


# =========================
# LOGIN PAGE
# =========================

@app.get(
    "/login",
    response_class=HTMLResponse
)
def login_page(request: Request):

    if logged_in(request):

        return RedirectResponse(
            "/",
            status_code=303
        )

    return templates.TemplateResponse(
        request=request,
        name="login.html"
    )


# =========================
# LOGIN
# =========================

@app.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):

    db = SessionLocal()

    try:

        admin = (
            db.query(Admin)
            .filter(
                Admin.username == username
            )
            .first()
        )

        password_hash = hash_password(password)

        if (
            not admin
            or password_hash != admin.password_hash
        ):

            return templates.TemplateResponse(
                request=request,
                name="login.html",
                context={
                    "error":
                    "Invalid username or password"
                },
                status_code=401
            )

        request.session["admin_id"] = admin.id

        return RedirectResponse(
            "/",
            status_code=303
        )

    finally:

        db.close()


# =========================
# LOGOUT
# =========================

@app.get("/logout")
def logout(request: Request):

    request.session.clear()

    return RedirectResponse(
        "/login",
        status_code=303
    )


# =========================
# DASHBOARD
# =========================

@app.get(
    "/",
    response_class=HTMLResponse
)
def dashboard(request: Request):

    if not logged_in(request):

        return RedirectResponse(
            "/login",
            status_code=303
        )

    db = SessionLocal()

    try:

        users = db.query(User).all()

        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={
                "users": users
            }
        )

    finally:

        db.close()


# =========================
# USERS PAGE
# =========================

@app.get(
    "/users",
    response_class=HTMLResponse
)
def users_page(request: Request):

    if not logged_in(request):

        return RedirectResponse(
            "/login",
            status_code=303
        )

    db = SessionLocal()

    try:

        users = db.query(User).all()

        return templates.TemplateResponse(
            request=request,
            name="users.html",
            context={
                "users": users
            }
        )

    finally:

        db.close()


# =========================
# CREATE USER
# =========================

@app.post("/users/create")
def create_user(
    request: Request,
    username: str = Form(...),
    expires: str = Form(...),
    traffic_limit: int = Form(...)
):

    if not logged_in(request):

        return RedirectResponse(
            "/login",
            status_code=303
        )

    db = SessionLocal()

    try:

        existing = (
            db.query(User)
            .filter(
                User.username == username
            )
            .first()
        )

        if existing:

            return RedirectResponse(
                "/users?error=user_exists",
                status_code=303
            )

        new_user = User(
            username=username,
            uuid=str(uuid.uuid4()),
            expires=expires,
            traffic_limit=traffic_limit,
            enabled=True
        )

        db.add(new_user)
        db.commit()

        return RedirectResponse(
            "/users",
            status_code=303
        )

    finally:

        db.close()


# =========================
# ENABLE / DISABLE USER
# =========================

@app.post(
    "/users/{user_id}/toggle"
)
def toggle_user(
    request: Request,
    user_id: int
):

    if not logged_in(request):

        return RedirectResponse(
            "/login",
            status_code=303
        )

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(
                User.id == user_id
            )
            .first()
        )

        if user:

            user.enabled = not user.enabled

            db.commit()

        return RedirectResponse(
            "/users",
            status_code=303
        )

    finally:

        db.close()


# =========================
# VLESS LINK
# =========================

def make_vless_link(user):

    host = os.getenv(
        "VLESS_HOST",
        "YOUR-SERVER-DOMAIN"
    )

    port = os.getenv(
        "VLESS_PORT",
        "443"
    )

    sni = os.getenv(
        "VLESS_SNI",
        host
    )

    username = quote(
        user.username,
        safe=""
    )

    link = (
        f"vless://"
        f"{user.uuid}@{host}:{port}"
        f"?type=tcp"
        f"&security=tls"
        f"&sni={quote(sni, safe='')}"
        f"#{username}"
    )

    return link


# =========================
# VLESS PAGE
# =========================

@app.get(
    "/users/{user_id}/vless",
    response_class=HTMLResponse
)
def vless_page(
    request: Request,
    user_id: int
):

    if not logged_in(request):

        return RedirectResponse(
            "/login",
            status_code=303
        )

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(
                User.id == user_id
            )
            .first()
        )

        if not user:

            return RedirectResponse(
                "/users",
                status_code=303
            )

        vless_link = make_vless_link(user)

        return templates.TemplateResponse(
            request=request,
            name="vless.html",
            context={
                "user": user,
                "vless_link": vless_link
            }
        )

    finally:

        db.close()


# =========================
# QR CODE
# =========================

@app.get(
    "/users/{user_id}/qr"
)
def qr_code(
    request: Request,
    user_id: int
):

    if not logged_in(request):

        return RedirectResponse(
            "/login",
            status_code=303
        )

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(
                User.id == user_id
            )
            .first()
        )

        if not user:

            return RedirectResponse(
                "/users",
                status_code=303
            )

        link = make_vless_link(user)

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4
        )

        qr.add_data(link)
        qr.make(fit=True)

        image = qr.make_image()

        buffer = io.BytesIO()

        image.save(
            buffer,
            format="PNG"
        )

        buffer.seek(0)

        return StreamingResponse(
            buffer,
            media_type="image/png"
        )

    finally:

        db.close()
