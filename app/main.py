# Author: Om Mishra ( https://projectrexa.dedyn.io | https://github.com/Om-Mishra7 )
# Contact Detail: inkbloom@projectrexa.dedyn.io ( Do not spam this email address please :) )
# Written for the InkBloom Project
# Date Created: 03-11-2023
# Last Modified: 20-11-2023

"""
This file contains the server side code for the web application InkBloom, a powerful and versatile blog application that simplifies the process of creating, managing, and sharing your thoughts with the world.
"""

# Importing the required libraries

import os
import urllib.parse
import cgi
import html
import secrets
from datetime import datetime, timezone, timedelta
from email import message, utils
import json
import token
import requests
from dotenv import load_dotenv
import redis
from bson import ObjectId
from flask import (
    Flask,
    render_template,
    send_from_directory,
    url_for,
    flash,
    redirect,
    request,
    session,
    abort,
    jsonify,
    Response,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_session import Session
from pymongo import MongoClient
from purgo_malum import client
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException


# Loading the environment variables

load_dotenv()

# Initializing the application

app = Flask(__name__)

# Getting the service version

with open("app/app.json", "r") as f:
    service_version = json.load(f)["service-version"]

# App Configuration

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

# Session Configuration

redis_url = os.getenv("REDIS_URL")
if not redis_url:
    raise RuntimeError("Environment variable REDIS_URL not set")

app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_REDIS"] = redis.from_url(redis_url)
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_NAME"] = "inkbloom-session"

# Database Configuration

mongodb_url = os.getenv("MONGODB_URL")
if not mongodb_url:
    raise RuntimeError("Environment variable MONGODB_URL not set")

mongodb_database = os.getenv("MONGODB_DATABASE")
if not mongodb_database:
    raise RuntimeError("Environment variable MONGODB_DATABASE not set")

MONOGDB_CLIENT = MongoClient(mongodb_url)
DATABASE = MONOGDB_CLIENT[mongodb_database]


# Session Initialization

Session(app)

# Rate Limiter Configuration

pool = redis.connection.BlockingConnectionPool.from_url(redis_url)
if not pool:
    raise RuntimeError("Could not connect to redis")
limiter = Limiter(
    app=app,
    key_func=lambda: get_remote_address(),
    storage_uri=redis_url,
    storage_options={"connection_pool": pool},
    strategy="moving-window",
)

# Application Utility Functions


def profanity_check(comment):
    """
    This function checks for profanity in the comment.
    """
    return client.contains_profanity(comment)


def check_crsf_token(token):
    """
    This function checks for CSRF token in the request.
    """
    if not token:
        return False
    if token != session.get("csrf_token"):
        return False
    return True


def calculate_read_time(html_content, words_per_minute=200, image_time_seconds=12):
    text_content = re.sub(r"<[^>]*>", "", html_content)  # Remove HTML tags
    word_count = len(re.findall(r"\w+", text_content))

    text_read_time_minutes = word_count / words_per_minute

    image_count = len(re.findall(r"<img [^>]*>", html_content))
    image_read_time_seconds = image_count * image_time_seconds

    total_read_time_minutes = text_read_time_minutes + (image_read_time_seconds / 60)
    return int(total_read_time_minutes)


# Sendinblue API Configuration
configuration = sib_api_v3_sdk.Configuration()
configuration.api_key["api-key"] = os.getenv("SENDINBLUE_API_KEY")


def send_email(user_email, user_name, type, token):
    """
    This function sends an email to the user.
    """
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )

    if type == "newsletter_subscription_confirmation":
        subject = "Newsletter Subscription Confirmation | InkBloom"
        sender = {
            "name": "InkBloom | ProjectRexa",
            "email": "noreply@projectrexa.dedyn.io",
        }
        to = [{"email": user_email, "name": user_name}]
        reply_to = {
            "email": "inkbloom@projectrexa.dedyn.io",
            "name": "InkBloom | ProjectRexa",
        }
        html = render_template(
            "email/newsletter_subscription_confirmation.html",
            user_name=user_name.title(),
            user_email=user_email,
            token=token,
        )
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=to, html_content=html, reply_to=reply_to, sender=sender, subject=subject
        )

    else:
        return False
    try:
        api_instance.send_transac_email(send_smtp_email)
        return True
    except ApiException as e:
        return False


# Application Template Filters


@app.template_filter("format_timestamp")
def format_timestamp(s):
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S.%f").strftime("%d %B %Y")


@app.template_filter("rss_timestamp")
def rss_timestamp(s):
    return utils.format_datetime(
        datetime.strptime(s, "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc)
    )


@app.template_filter("sitemap_timestamp")
def sitemap_timestamp(s):
    return s.strftime("%Y-%m-%d")


@app.template_filter("url_encode")
def urlencode(s):
    return urllib.parse.quote(s)


@app.context_processor
def app_version():
    return dict(service_version=service_version)


@app.context_processor
def csrf_token():
    session["csrf_token"] = secrets.token_hex(16)
    return dict(csrf_token=session["csrf_token"])


# After-request function for setting headers


@app.after_request
def add_header(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Cache-Control"] = "no-cache, must-revalidate"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers[
        "Strict-Transport-Security"
    ] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Connection"] = "keep-alive"
    return response


# Application User Routes


@app.route("/", methods=["GET"])
@app.route("/blogs", methods=["GET"])
def index():
    """
    This function renders the home page of the application.
    """
    if session.get("admin"):
        blogs = DATABASE["BLOGS"].find().sort("_id", -1).limit(10)
        featured_blogs = (
            DATABASE["BLOGS"].find({"featured": True}).sort("_id", -1).limit(3)
        )
        return render_template(
            "index.html",
            blogs=blogs,
            featured_blogs=featured_blogs,
        )

    blogs = DATABASE["BLOGS"].find({"visibility": "public"}).sort("_id", -1).limit(10)
    featured_blogs = (
        DATABASE["BLOGS"]
        .find({"featured": True, "visibility": "public"})
        .sort("_id", -1)
        .limit(3)
    )
    return render_template(
        "index.html",
        blogs=blogs,
        featured_blogs=featured_blogs,
    )


@app.route("/blogs/<blog_slug>", methods=["GET"])
def blog(blog_slug):
    """
    Render the blog page of the application.
    """
    blog = DATABASE["BLOGS"].find_one({"slug": blog_slug})
    comments = DATABASE["COMMENTS"].find({"blog_slug": blog_slug})
    comments_list = list(comments)
    if blog:
        if blog["visibility"] == "private" and session.get("admin") is False:
            abort(404)

        suggested_blogs = (
            DATABASE["BLOGS"].find({"tags": {"$in": blog.get("tags", [])}}).limit(2)
        )
        suggested_blogs = list(
            filter(lambda x: x.get("slug") != blog_slug, suggested_blogs)
        )
        return render_template(
            "blog.html",
            blog=blog,
            comments=comments_list,
            suggested_blogs=suggested_blogs,
            title=blog.get("title", ""),
            description=blog.get("summary", ""),
            image=blog.get("cover_image", ""),
        )

    if blog:
        return render_template(
            "blog.html",
            blog=blog,
            comments=comments_list,
            title=blog.get("title", ""),
            description=blog.get("summary", ""),
            image=blog.get("cover_image", ""),
        )
    abort(404)


"""
This function creates a new blog post and saves it to the database. It renders the create blog page of the application and handles the form submission. If the user is not logged in or is not an admin, it returns a 401 error. If the form is not filled correctly, it returns a 400 error. If the cover image is not found or is not a valid image format, it returns a 400 error. If there is an error while uploading the file, it returns a 500 error. If the blog is created successfully, it returns a 200 status code with the blog slug.
"""


@app.route("/admin/blogs/create", methods=["GET", "POST"])
def create_blog():
    """
    Render the create blog page of the application.
    """
    if request.method == "POST":
        try:
            if session["logged_in"] and session["admin"]:
                if request.form.get("csrf_token"):
                    if not check_crsf_token(request.form.get("csrf_token")):
                        return {
                            "status": "error",
                            "message": "The request was discarded because it did not contain a valid CSRF token!",
                        }, 400
                else:
                    return {
                        "status": "error",
                        "message": "The request was discarded because it did not contain a CSRF token!",
                    }, 400
                blog_title = request.form.get("title")
                blog_content = request.form.get("content")
                visibility = request.form.get("visibility")
                blog_tags = [
                    tag.strip().lower()
                    for tag in request.form.get("tags", "").split(",")
                    if tag.strip()
                ]
                blog_summary = request.form.get("summary")
                blog_slug = blog_title.replace(" ", "-").lower()
                blog_cover_image = request.files.get("cover_image")
                authour = session.get("user_id")
                authour_name = session.get("user_name")
                blog_featured = "featured" in blog_tags
                blog_tags = [tag for tag in blog_tags if tag != "featured"]
            else:
                abort(401)
        except Exception:
            return {
                "status": "error",
                "message": "Please fill all the fields correctly",
            }, 400

        while DATABASE["BLOGS"].find_one({"slug": blog_slug}):
            blog_slug = blog_slug + "-" + secrets.token_hex(4)

        if not blog_cover_image or blog_cover_image.filename == "":
            return {"status": "error", "message": "No cover image found!"}, 400

        valid_image_types = [
            "image/png",
            "image/jpeg",
            "image/jpg",
            "image/gif",
            "image/webp",
            "svg+xml",
        ]
        if blog_cover_image.content_type not in valid_image_types:
            return {
                "status": "error",
                "message": "The cover image does not have a valid image format!",
            }, 400

        try:
            response = requests.post(
                "http://ather.api.projectrexa.dedyn.io/upload",
                files={"file": blog_cover_image.read()},
                data={
                    "key": f"projectrexa/blog/assets/{secrets.token_hex(16)}",
                    "content_type": blog_cover_image.content_type,
                    "public": "true",
                },
                headers={"X-Authorization": os.getenv("ATHER_API_KEY") or ""},
                timeout=10,
            ).json()
            blog_cover_image_url = response.get("access_url")
        except Exception as e:
            return {
                "status": "error",
                "message": "Something went wrong while uploading the file!",
            }, 500

        if not blog_cover_image_url:
            return {"status": "error", "message": "No cover image found!"}, 400

        blog = {
            "title": blog_title,
            "content": blog_content,
            "visibility": visibility,
            "tags": blog_tags,
            "summary": blog_summary,
            "slug": blog_slug,
            "cover_image": blog_cover_image_url,
            "authour": authour,
            "authour_name": authour_name,
            "authour_profile_pic": session.get("profile_pic"),
            "featured": blog_featured,
            "read_time": calculate_read_time(blog_content),
            "views": 0,
            "comments_count": 0,
            "created_at": datetime.now(),
            "last_updated_at": datetime.now(),
        }

        DATABASE["BLOGS"].insert_one(blog)
        DATABASE["COMMENTS"].insert_one(
            {
                "blog_slug": blog_slug,
                "comment": "Please do not harass or abuse anyone in the comments section. We have a zero tolerance policy for harassment and abuse. If you are found to be violating our policy, you will be blocked from posting further comments.",
                "commented_by": "Moderation Bot",
                "user_name": "Moderation Bot",
                "user_profile_pic": "https://cdn.projectrexa.dedyn.io/favicon.ico",
                "user_role": "admin",
                "created_at": datetime.now(),
            }
        )

        return {
            "status": "success",
            "message": "Blog created successfully!",
            "blog_slug": blog_slug,
        }, 200

    elif session.get("logged_in") and session.get("admin"):
        return render_template("create_blog.html")
    else:
        abort(401)


@app.route("/admin/blogs/edit/<blog_id>", methods=["GET", "POST"])
def edit_blog(blog_id):
    """
    This function renders the edit blog page of the application
    """
    if request.method == "POST":
        try:
            if session["logged_in"] and session["admin"]:
                if request.form.get("csrf_token"):
                    if not check_crsf_token(request.form.get("csrf_token")):
                        return {
                            "status": "error",
                            "message": "The request was discarded because it did not contain a valid CSRF token!",
                        }, 400
                else:
                    return {
                        "status": "error",
                        "message": "The request was discarded because it did not contain a CSRF token!",
                    }, 400
                blog_title = request.form.get("title")
                blog_content = request.form.get("content")
                visibilty = request.form.get("visibility")
                blog_tags = [
                    tag.strip().lower()
                    for tag in request.form.get("tags", "").split(",")
                    if tag.strip()
                ]
                blog_summary = request.form.get("summary")
                blog_slug = blog_title.replace(" ", "-").lower()
                blog_cover_image = request.files.get("cover_image")
                authour = session.get("user_id")
                authour_name = session.get("user_name")
                blog_featured = "featured" in blog_tags
                blog_tags = [tag for tag in blog_tags if tag != "featured"]
            else:
                abort(401)
        except Exception:
            return {
                "status": "error",
                "message": "Please fill all the fields correctly",
            }, 400

        blog = DATABASE["BLOGS"].find_one({"_id": ObjectId(blog_id)})
        if not blog:
            return {"status": "error", "message": "Invalid blog ID!"}, 400

        if not blog_cover_image or blog_cover_image.filename == "":
            blog_cover_image_url = blog["cover_image"]
        else:
            valid_image_types = [
                "image/png",
                "image/jpeg",
                "image/jpg",
                "image/gif",
                "image/webp",
                "svg+xml",
            ]
            if blog_cover_image.content_type not in valid_image_types:
                return {
                    "status": "error",
                    "message": "The cover image does not have a valid image format!",
                }, 400

            try:
                response = requests.post(
                    "http://ather.api.projectrexa.dedyn.io/upload",
                    files={"file": blog_cover_image.read()},
                    data={
                        "key": f"projectrexa/blog/assets/{secrets.token_hex(16)}",
                        "content_type": blog_cover_image.content_type,
                        "public": "true",
                    },
                    headers={"X-Authorization": os.getenv("ATHER_API_KEY") or ""},
                    timeout=10,
                ).json()
                blog_cover_image_url = response.get("access_url")
            except Exception as e:
                return {
                    "status": "error",
                    "message": "Something went wrong while uploading the file!",
                }, 500

            if not blog_cover_image_url:
                return {"status": "error", "message": "No cover image found!"}, 400

        DATABASE["BLOGS"].update_one(
            {"_id": ObjectId(blog_id)},
            {
                "$set": {
                    "title": blog_title,
                    "content": blog_content,
                    "visibility": visibilty,
                    "tags": blog_tags,
                    "summary": blog_summary,
                    "slug": blog_slug,
                    "cover_image": blog_cover_image_url,
                    "featured": blog_featured,
                    "read_time": calculate_read_time(blog_content),
                    "last_updated_at": datetime.now(),
                }
            },
        )

        return {
            "status": "success",
            "message": "Blog updated successfully!",
            "blog_slug": blog_slug,
        }, 200

    elif session.get("logged_in") and session.get("admin"):
        blog = DATABASE["BLOGS"].find_one({"_id": ObjectId(blog_id)})
        if not blog:
            abort(404)
        blog["tags"].append("featured" if blog["featured"] else "")
        return render_template("create_blog.html", blog=blog)
    else:
        abort(401)


@app.route("/user/authorize", methods=["GET"])
def authorize():
    """
    This function renders the authorization page of the application.
    """
    if request.args.get("error"):
        return {"status": "error", "message": request.args.get("error")}, 400
    return redirect(url_for("authentication"))


@app.route("/user/authorize/projectrexa", methods=["GET"])
def authentication():
    if session.get("logged_in"):
        return redirect(url_for("index"))

    error_message = request.args.get("error")
    if error_message:
        return {"status": "error", "message": html.escape(error_message)}, 400

    next_url = request.args.get("next")
    if next_url:
        session["next"] = next_url

    if os.getenv("PROJECTREXA_CLIENT_ID") is None:
        return {
            "status": "error",
            "message": "The server was unable to process your request! | Error Code - 00001",
        }, 500

    projectrexa_auth_url = f"https://accounts.om-mishra.com/api/v1/oauth/authenticate?requestState={secrets.token_hex(16)}&applicationID={os.getenv('PROJECTREXA_CLIENT_ID')}&redirectURI=https://blog.projectrexa.dedyn.io/oauth-callback/projectrexa"

    return redirect(projectrexa_auth_url)


@app.route("/oauth-callback/projectrexa", methods=["GET"])
def oauth_callback():
    print(request.args.get("code"))
    if session.get("logged_in"):
        return redirect(url_for("index"))

    code = request.args.get("code")

    if code is None:
        return redirect(url_for("index"))

    try:
        projectrexa_token_url = "https://accounts.om-mishra.com/api/v1/oauth/user?applicationID={}&applicationSecret={}&token={}".format(
            os.getenv("PROJECTREXA_CLIENT_ID"),
            os.getenv("PROJECTREXA_CLIENT_SECRET"),
            code,
        )

        response = requests.post(
            projectrexa_token_url,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            data=json.dumps(
                {
                    "applicationID": os.getenv("PROJECTREXA_CLIENT_ID"),
                    "applicationSecret": os.getenv("PROJECTREXA_CLIENT_SECRET"),
                    "token": code,
                }
            ),
        )

        user_data = response.json()

        user = DATABASE["USERS"].find_one({"_id": user_data["user"]["userID"]})

        if user is None:
            DATABASE["USERS"].insert_one(
                {
                    "_id": user_data["user"]["userID"],
                    "account_id": user_data["user"]["userName"],
                    "name": user_data["user"]["firstName"]
                    + " "
                    + user_data["user"]["lastName"],
                    "profile_pic": user_data["user"]["userProfileImageURL"],
                    "admin": True
                    if user_data["user"]["userRole"] == "ADMIN"
                    else False,
                    "blocked": False,
                    "deleted": False,
                    "signup_method": "projectrexa",
                    "newsletter_enabled": False,
                    "preferred_theme": "noir nebula",
                    "created_at": datetime.now(),
                    "last_updated_at": datetime.now(),
                }
            )
            user = DATABASE["USERS"].find_one({"_id": user_data["user"]["userID"]})

        else:
            user_schema = {
                "account_id": user_data["user"]["userName"],
                "name": user_data["user"]["firstName"]
                + " "
                + user_data["user"]["lastName"],
                "profile_pic": user_data["user"]["userProfileImageURL"],
                "admin": user_data["user"]["userRole"] == "ADMIN",
                "blocked": False,
                "deleted": False,
                "signup_method": "projectrexa",
                "newsletter_enabled": False,
                "preferred_theme": "noir nebula",
                "created_at": datetime.now(),
                "last_updated_at": datetime.now(),
            }

            for key, value in user_schema.items():
                if user.get(key) is None:
                    DATABASE["USERS"].update_one(
                        {"_id": user_data["user"]["userID"]},
                        {"$set": {key: value}},
                    )
                else:
                    continue

            DATABASE["USERS"].update_one(
                {"_id": user_data["user"]["userID"]},
                {
                    "$set": {
                        "account_id": user_data["user"]["userName"],
                        "name": user_data["user"]["firstName"]
                        + " "
                        + user_data["user"]["lastName"],
                        "profile_pic": user_data["user"]["userProfileImageURL"],
                        "last_updated_at": datetime.now(),
                        "admin": True if user_data["user"]["userRole"] == "ADMIN" else False,
                    }
                },
            )

        if user is not None:
            if user.get("deleted", True):
                return redirect(
                    "/user/authorize"
                    + "?error=This account assosiated with this ProjectRexa account has been deleted!"
                )
            session["logged_in"] = True
            session["user_id"] = user.get("_id")
            session["account_id"] = user.get("account_id")
            session["user_name"] = user.get("name")
            session["profile_pic"] = user.get("profile_pic")
            session["newsletter_enabled"] = user.get("newsletter_enabled", False)
            session["admin"] = user.get("admin", False)
            session["blocked"] = user.get("blocked", False)

            return redirect(session.get("next") or url_for("index"))

    except Exception as e:
        return redirect("/user/authorize" + "?error=" + str(e))


@app.route("/user/sign-out", methods=["GET"])
def signout():
    """
    This function signs the user out of the application.
    """
    session.clear()
    return redirect(request.args.get("next") or url_for("index"))


@app.route("/search")
def search_page():
    """
    This function renders the search page of the application.
    """
    return render_template("search.html")


@app.route("/user/feedback")
def feedback_page():
    """
    This function renders the feedback page of the application.
    """
    if session.get("logged_in"):
        return render_template("feedback.html")
    return abort(401)


@app.route("/user/account")
def profile_page():
    """
    This function renders the profile page of the application.
    """
    if session.get("logged_in"):
        user = DATABASE["USERS"].find_one({"_id": session["user_id"]})
        comments = DATABASE["COMMENTS"].find({"commented_by": session["user_id"]})
        system_messages = (
            DATABASE["SYSTEM_MESSAGES"]
            .find({"user": session["user_id"]})
            .sort("_id", -1)
        ).limit(5)
        return render_template(
            "profile.html", user=user, comments=comments, notifications=system_messages
        )
    return abort(401)


@app.route("/user/<user_id>")
def user_page(user_id):
    """
    This function renders the user page of the application.
    """
    user = DATABASE["USERS"].find_one({"_id": int(user_id)})
    if user:
        comments = DATABASE["COMMENTS"].find({"commented_by": int(user_id)})
        return render_template("user.html", user=user, comments=comments)
    abort(404)


@app.route("/rss")
def rss():
    """
    This function renders the RSS feed of the application.
    """
    blogs = DATABASE["BLOGS"].find({"visibility": "public"}).sort("_id", -1)
    date = utils.format_datetime(datetime.now(timezone.utc))

    return (
        render_template("web-feed/rss.xml", blogs=blogs, date=date),
        200,
        {"Content-Type": "application/xml"},
    )


@app.route("/sitemap")
def sitemap():
    """
    This function renders the sitemap of the application.
    """
    blogs = DATABASE["BLOGS"].find({"visibility": "public"}).sort("_id", -1)
    # 2022-06-04
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return (
        render_template("web-feed/sitemap.xml", blogs=blogs, date=date),
        200,
        {"Content-Type": "application/xml"},
    )


@app.route("/robots.txt")
def robots():
    """
    This function renders the robots.txt of the application.
    """
    return (
        send_from_directory("static", "crawlers/robots.txt"),
        200,
        {"Content-Type": "text/plain"},
    )


@app.route("/ping")
def ping():
    """
    This function renders the ping page of the application.
    """
    return "pong", 200, {"Content-Type": "text/plain"}


# Application API Routes


@app.route("/api/v1/user", methods=["GET"])
def get_user():
    try:
        if session.get("logged_in"):
            return {
                "status": "success",
                "message": "You are logged in!",
            }, 200
        else:
            return {
                "status": "error",
                "message": "You are not authorized to access this page!",
            }, 401
    except Exception:
        return {
            "status": "error",
            "message": "The server was unable to process your request!",
        }, 500


@app.route("/api/v1/search", methods=["GET"])
def search():
    """
    This function returns the search results.
    """
    query = request.args.get("query")
    if query and len(query) > 2:
        # Allow only public blogs to be searched by non-admin users
        if session.get("admin"):
            blogs = (
                DATABASE["BLOGS"]
                .find(
                    {
                        "$or": [
                            {"title": {"$regex": query, "$options": "i"}},
                            {"tags": {"$regex": query, "$options": "i"}},
                            {"summary": {"$regex": query, "$options": "i"}},
                        ]
                    }
                )
                .limit(3)
            )
        else:
            blogs = (
                DATABASE["BLOGS"]
                .find(
                    {
                        "$and": [
                            {"visibility": "public"},
                            {
                                "$or": [
                                    {"title": {"$regex": query, "$options": "i"}},
                                    {"tags": {"$regex": query, "$options": "i"}},
                                    {"summary": {"$regex": query, "$options": "i"}},
                                ]
                            },
                        ]
                    }
                )
                .limit(3)
            )

        if blogs:
            blogs = [
                {
                    "_id": str(blog["_id"]),
                    "title": blog["title"],
                    "slug": blog["slug"],
                }
                for blog in blogs
            ]

            if not blogs:
                return jsonify([]), 404

            return jsonify(blogs), 200
    else:
        return jsonify([]), 404


@app.route("/api/v1/blogs/<last_blog_id>", methods=["GET"])
def get_blogs(last_blog_id):
    blogs = DATABASE["BLOGS"].find({"_id": {"$lt": ObjectId(last_blog_id)}}).limit(5)

    if blogs:
        blogs = [
            {
                "_id": str(blog["_id"]),
                "title": blog["title"],
                "summary": blog["summary"],
                "slug": blog["slug"],
            }
            for blog in blogs
        ]

        if not blogs:
            return jsonify([]), 404

        return jsonify(blogs), 200

    abort(404)


@app.route("/api/v1/user/comments", methods=["POST"])
@limiter.limit("5/minute")
def post_user_comments():
    if request.method == "POST" and session.get("logged_in"):
        data = request.get_json()
        comment = data.get("comment")
        blog_slug = data.get("slug")
        if data.get("csrf_token"):
            if not check_crsf_token(data.get("csrf_token")):
                return {
                    "status": "error",
                    "message": "The request was discarded because it did not contain a valid CSRF token!",
                }, 400
        else:
            return {
                "status": "error",
                "message": "The request was discarded because it did not contain a CSRF token!",
            }, 400

        if comment:
            if len(comment) > 1000:
                return {
                    "status": "error",
                    "message": "Comment length cannot exceed 1000 characters!",
                }, 400

            if profanity_check(comment) and not session["admin"]:
                DATABASE["USERS"].update_one(
                    {"_id": session["user_id"]}, {"$set": {"blocked": True}}
                )

                DATABASE["SYSTEM_MESSAGES"].insert_one(
                    {
                        "user": session.get("user_id"),
                        "message": f"Your most recent comment has been removed because it contained profanity. You have been blocked from posting further comments!, in case you think this is a mistake, please email us at <a href='mailto:support@projectrexa.dedyn.io'>support@projectrexa.dedyn.io</a>.<br><br>Original Comment - {comment}",
                        "created_at": datetime.now(),
                    }
                )

                session.clear()

                return {
                    "status": "error",
                    "message": "Your comment contains profanity. You have been blocked from posting further comments!",
                }, 400

            if not DATABASE["BLOGS"].find_one({"slug": blog_slug}):
                return {"status": "error", "message": "Invalid blog ID!"}, 400

            if DATABASE["USERS"].find_one({"_id": session["user_id"]}) is not None:
                if (
                    DATABASE["USERS"]
                    .find_one({"_id": session["user_id"]})
                    .get("blocked", False)
                ):
                    session.clear()

                    return {
                        "status": "error",
                        "message": "You have been blocked from posting further comments!",
                    }, 400

            else:
                return {
                    "status": "error",
                    "message": "The server was unable to process your request!",
                }, 500

            DATABASE["BLOGS"].update_one(
                {"slug": blog_slug},
                {"$inc": {"comments_count": 1}},
            )

            DATABASE["COMMENTS"].insert_one(
                {
                    "blog_slug": blog_slug,
                    "comment": comment,
                    "commented_by": session["user_id"],
                    "user_name": session["user_name"],
                    "user_profile_pic": session["profile_pic"],
                    "user_role": "admin" if session["admin"] else "user",
                    "created_at": datetime.now(),
                }
            )

            DATABASE["SYSTEM_MESSAGES"].insert_one(
                {
                    "user": session["user_id"],
                    "message": f"Your comment on the blog https://blog.projectrexa.dedyn.io/blogs/{blog_slug} has been saved successfully!",
                    "created_at": datetime.now(),
                }
            )

            return {"status": "success", "message": "Comment posted successfully!"}, 200

        return {
            "status": "error",
            "message": "Please make sure all the fields are filled correctly!",
        }, 400

    return {
        "status": "error",
        "message": "You are not authorized to access this page!",
    }, 401


@app.route("/api/v1/user/comments/<comment_id>", methods=["DELETE"])
def delete_user_comments(comment_id):
    if request.method == "DELETE" and session.get("logged_in"):
        comment = DATABASE["COMMENTS"].find_one({"_id": ObjectId(comment_id)})
        if comment:
            if comment["commented_by"] != session["user_id"] and not session["admin"]:
                return {
                    "status": "error",
                    "message": "You are not authorized to access this page!",
                }, 401
            DATABASE["COMMENTS"].delete_one({"_id": ObjectId(comment_id)})
            DATABASE["BLOGS"].update_one(
                {"slug": comment["blog_slug"]},
                {"$inc": {"comments_count": -1}},
            )
            return {
                "status": "success",
                "message": "Comment deleted successfully!",
            }, 200
        return {"status": "error", "message": "Invalid comment ID!"}, 400
    return {
        "status": "error",
        "message": "You are not authorized to access this page!",
    }, 401


@app.route("/api/v1/statisics/views/<blog_slug>", methods=["POST"])
@limiter.limit("5/minute")
def get_blog_views(blog_slug):
    blog = DATABASE["BLOGS"].find_one({"slug": blog_slug})

    if blog:
        DATABASE["BLOGS"].update_one({"slug": blog_slug}, {"$inc": {"views": 1}})
        return str(blog["views"])

    abort(404)


@app.route("/api/v1/user-content/upload", methods=["POST"])
@limiter.limit("10/minute")
def upload_user_content():
    if request.method == "POST" and session.get("logged_in") and session.get("admin"):
        file = request.files.get("file")

        if not file:
            return {"status": "error", "message": "No file found!"}, 400

        if file.filename == "":
            return {"status": "error", "message": "No file found!"}, 400

        allowed_content_types = [
            "image/png",
            "image/jpeg",
            "image/jpg",
            "image/gif",
            "image/webp",
            "svg+xml",
        ]

        if file.content_type not in allowed_content_types:
            return {"status": "error", "message": "Invalid file type!"}, 400

        try:
            response = requests.post(
                "http://ather.api.projectrexa.dedyn.io/upload",
                files={"file": file.read()},
                data={
                    "key": f"projectrexa/blog/assets/{secrets.token_hex(16)}",
                    "content_type": file.content_type,
                    "public": "true",
                },
                headers={"X-Authorization": os.getenv("ATHER_API_KEY") or ""},
                timeout=10,
            ).json()

            return {
                "status": "success",
                "message": "File uploaded successfully!",
                "location": f'https://wsrv.nl?url={response["access_url"]}&maxage=31d&q=100&output=webp',
            }, 200
        except Exception as e:
            return {
                "status": "error",
                "message": "Something went wrong while uploading the file!",
            }, 500

    abort(401)


@app.route("/api/v1/user/block/<user_id>", methods=["POST"])
def nuke_user(user_id):
    if request.method == "POST" and session.get("logged_in") and session.get("admin"):
        user = DATABASE["USERS"].find_one({"_id": int(user_id)})
        if user:
            if user.get("admin", False):
                return {
                    "status": "error",
                    "message": "Privilege level is not sufficient to perform this action!",
                }, 400
            DATABASE["USERS"].update_one(
                {"_id": int(user_id)}, {"$set": {"blocked": True}}
            )
            DATABASE["COMMENTS"].delete_many({"commented_by": int(user_id)})

            return {"status": "success", "message": "User blocked successfully!"}, 200

        return {"status": "error", "message": "Invalid user ID!"}, 400
    return {
        "status": "error",
        "message": "You are not authorized to access this page!",
    }, 401


@app.route("/api/v1/admin/blogs/<blog_id>", methods=["DELETE"])
def delete_blog(blog_id):
    if request.method == "DELETE" and session.get("logged_in") and session.get("admin"):
        blog = DATABASE["BLOGS"].find_one({"_id": ObjectId(blog_id)})
        if blog:
            DATABASE["BLOGS"].delete_one({"_id": ObjectId(blog_id)})
            DATABASE["COMMENTS"].delete_many({"blog_slug": blog["slug"]})
            return {
                "status": "success",
                "message": "Blog deleted successfully!",
            }, 200
        return {"status": "error", "message": "Invalid blog ID!"}, 400
    return {
        "status": "error",
        "message": "You are not authorized to access this page!",
    }, 401


@app.route("/api/v1/feedback", methods=["POST"])
@limiter.limit("5/minute")
def feedback():
    if request.method == "POST" and session.get("logged_in"):
        data = request.get_json()
        if data.get("csrf_token"):
            if not check_crsf_token(data.get("csrf_token")):
                return {
                    "status": "error",
                    "message": "The request was discarded because it did not contain a valid CSRF token!",
                }, 400
        else:
            return {
                "status": "error",
                "message": "The request was discarded because it did not contain a CSRF token!",
            }, 400
        feedback = data.get("feedback")
        if feedback:
            if len(feedback) > 10000:
                return {
                    "status": "error",
                    "message": "Feedback length cannot exceed 10000 characters!",
                }, 400
            DATABASE["FEEDBACK"].insert_one(
                {
                    "feedback": feedback,
                    "user": session.get("user_id"),
                    "user_name": session.get("user_name"),
                    "user_profile_pic": session.get("profile_pic"),
                    "created_at": datetime.now(),
                }
            )
            return {
                "status": "success",
                "message": "Thank you for your feedback, we will get back to you soon!",
            }, 200
        return {
            "status": "error",
            "message": "Please make sure all the fields are filled correctly!",
        }, 400
    return {
        "status": "error",
        "message": "You are not authorized to access this page!",
    }, 401


@app.route("/api/v1/users/<user_id>/unsubscribe", methods=["PUT"])
def unsubscribe(user_id):
    if request.method == "PUT":
        if json.loads(request.data).get("csrf_token"):
            if not check_crsf_token(json.loads(request.data).get("csrf_token")):
                return {
                    "status": "error",
                    "message": "The request was discarded because it did not contain a valid CSRF token!",
                }, 400
        user = DATABASE["USERS"].find_one({"_id": int(user_id)})
        if user:
            DATABASE["USERS"].update_one(
                {"_id": int(user_id)}, {"$set": {"newsletter_enabled": False}}
            )
            DATABASE["USERS"].update_one(
                {"_id": int(user_id)}, {"$set": {"email": None}}
            )
            DATABASE["SYSTEM_MESSAGES"].insert_one(
                {
                    "user": int(user_id),
                    "message": "You have been unsubscribed from the newsletter!",
                    "created_at": datetime.now(),
                }
            )
            return {
                "status": "success",
                "message": "Your subscription to the newsletter has been deactivated!",
            }, 200
        return {"status": "error", "message": "Invalid user ID!"}, 400
    return {
        "status": "error",
        "message": "You are not authorized to access this page!",
    }, 401


@app.route("/api/v1/users/<user_id>/subscribe", methods=["PUT"])
@limiter.limit("5/day")
def subscribe(user_id):
    if request.method == "PUT":
        if json.loads(request.data).get("csrf_token"):
            if not check_crsf_token(json.loads(request.data).get("csrf_token")):
                return {
                    "status": "error",
                    "message": "The request was discarded because it did not contain a valid CSRF token!",
                }, 400
        if json.loads(request.data).get("csrf_token"):
            if not check_crsf_token(json.loads(request.data).get("csrf_token")):
                return {
                    "status": "error",
                    "message": "The request was discarded because it did not contain a valid CSRF token!",
                }, 400

        user = DATABASE["USERS"].find_one({"_id": int(user_id)})
        if user:
            DATABASE["USERS"].update_one(
                {"_id": int(user_id)}, {"$set": {"newsletter_enabled": False}}
            )
            DATABASE["USERS"].update_one(
                {"_id": int(user_id)},
                {
                    "$set": {
                        "email": json.loads(request.data).get("email").strip().lower()
                    }
                },
            )

            user = DATABASE["USERS"].find_one({"_id": int(user_id)})

            if not user:
                return {
                    "status": "error",
                    "message": "The user associated with the given ID does not exist!",
                }, 400

            token = secrets.token_hex(16)

            DATABASE["TOKENS"].insert_one(
                {
                    "user": int(user_id),
                    "role": "newsletter-email-verification",
                    "email": user["email"],
                    "token": token,
                    "created_at": datetime.now(),
                }
            )

            if not send_email(
                user_email=user["email"],
                user_name=user["name"],
                token=token,
                type="newsletter_subscription_confirmation",
            ):
                return {
                    "status": "error",
                    "message": "Our systems are currently experiencing some issues, please try again later!",
                }, 500

            return {
                "status": "success",
                "message": "Please review your email for the verification link needed to activate your subscription",
            }, 200
        return {"status": "error", "message": "Invalid user ID!"}, 400
    return {
        "status": "error",
        "message": "You are not authorized to access this page!",
    }, 401


@app.route("/api/v1/user/newsletter/subscribe", methods=["GET"])
def newsletter_subscribe():
    """
    This functionverifies the email address of the user and activates the newsletter subscription.
    """
    token = request.args.get("token")
    if token:
        token = DATABASE["TOKENS"].find_one({"token": token})
        if (
            token
            and token["role"] == "newsletter-email-verification"
            and token["created_at"] + timedelta(hours=24) > datetime.now()
        ):
            DATABASE["USERS"].update_one(
                {"_id": token["user"]}, {"$set": {"newsletter_enabled": True}}
            )
            DATABASE["USERS"].update_one(
                {"_id": token["user"]}, {"$set": {"email": token["email"]}}
            )
            DATABASE["TOKENS"].delete_one({"token": token["token"]})
            DATABASE["SYSTEM_MESSAGES"].insert_one(
                {
                    "user": token["user"],
                    "message": "Your subscription to the newsletter has been activated!",
                    "created_at": datetime.now(),
                }
            )
            return redirect(url_for("profile_page"))
        return abort(404)


@app.route("/api/v1/users/<user_id>/export", methods=["GET"])
def export_user_data(user_id):
    if session.get("logged_in") and session.get("user_id") == int(user_id):
        user = DATABASE["USERS"].find_one({"_id": int(user_id)})
        if user:
            comments = DATABASE["COMMENTS"].find({"commented_by": int(user_id)})
            feedback = DATABASE["FEEDBACK"].find({"user": int(user_id)})
            system_messages = DATABASE["SYSTEM_MESSAGES"].find({"user": int(user_id)})

            # Without saving to a file
            content = f"This is an export of your data from InkBloom | ProjectRexa Blog.\nThis file contains sensitive information, please do not share this file with anyone.\n\nUser ID - {user['_id']}\nUser Name - {user['name']}\nUser Profile Picture - {user['profile_pic']}\nUser Signup Method - {user['signup_method']}\nUser Signup Date - {user['created_at']}\nUser Last Updated Date - {user['last_updated_at']}\n\nComments - \n\n"

            for comment in comments:
                content += f"Comment ID - {comment['_id']}\nCommented On - {comment['created_at']}\nComment - {comment['comment']}\n\n"

            content += "\n\nFeedback - \n\n"

            for feedback in feedback:
                content += f"Feedback ID - {feedback['_id']}\nFeedback Date - {feedback['created_at']}\nFeedback - {feedback['feedback']}\n\n"

            content += "\n\nSystem Messages - \n\n"

            for message in system_messages:
                content += f"Message ID - {message['_id']}\nMessage Date - {message['created_at']}\nMessage - {message['message']}\n\n"

            return Response(
                content,
                mimetype="text/plain",
                headers={
                    "Content-Disposition": f"attachment;filename={user['name']}.txt"
                },
            )

        return {
            "status": "error",
            "message": "Unable to find user associated with the given ID!",
        }, 400
    else:
        return {
            "status": "error",
            "message": "You are not authorized to access this page!",
        }, 401


@app.route("/api/v1/users/<user_id>/delete", methods=["DELETE"])
def delete_user(user_id):
    if session.get("logged_in") and session.get("user_id") == int(user_id):
        if json.loads(request.data).get("csrf_token"):
            if not check_crsf_token(json.loads(request.data).get("csrf_token")):
                return {
                    "status": "error",
                    "message": "The request was discarded because it did not contain a valid CSRF token!",
                }, 400
        user = DATABASE["USERS"].find_one({"_id": int(user_id)})
        if user:
            if session.get("user_id") != int(user_id):
                return {
                    "status": "error",
                    "message": "You don't have the permission to delete this account!",
                }, 401
            DATABASE["USERS"].update_one(
                {"_id": int(user_id)}, {"$set": {"deleted": True}}
            )
            DATABASE["COMMENTS"].update_many(
                {"commented_by": int(user_id)},
                {
                    "$set": {
                        "commented_by": "Deleted User",
                        "user_name": "Deleted User",
                        "user_profile_pic": "https://cdn.projectrexa.dedyn.io/projectrexa/blog/assets/3dbae37313bec7eac6117c9ddb8e2578",
                    }
                },
            )
            DATABASE["SYSTEM_MESSAGES"].insert_one(
                {
                    "user": int(user_id),
                    "message": "The request to delete your account has been processed successfully!",
                    "created_at": datetime.now(),
                }
            )

            session.clear()

            return {
                "status": "success",
                "message": "Your account has been deleted successfully!",
            }, 200
        return {
            "status": "error",
            "message": "Unable to find user associated with the given ID!",
        }, 400
    else:
        return {
            "status": "error",
            "message": "You are not authorized to access this page!",
        }, 401


# Error Handlers


@app.errorhandler(429)
@app.errorhandler(404)
@app.errorhandler(401)
@app.errorhandler(400)
@app.errorhandler(500)
def handle_errors(e):
    error_messages = {
        429: "Too many requests, please try again later!",
        404: "Page not found!",
        401: "You are not authorized to access this page!",
        400: "Bad request!",
        500: "Internal server error!",
    }
    status_code = getattr(e, "code", 500)
    return {
        "status": "error",
        "message": error_messages.get(status_code, "Unknown error"),
    }, status_code


if __name__ == "__main__":
    app.run(port=8000)
