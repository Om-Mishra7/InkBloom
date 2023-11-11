# Author: Om Mishra ( https://projectrexa.dedyn.io | https://github.com/Om-Mishra7 )
# Contact Detail: inkbloom@projectrexa.dedyn.io ( Do not spam this email address please :) )
# Written for the InkBloom Project
# Date Created: 03-11-2023
# Last Modified: 11-11-2023

"""
This file contains the server side code for the web application InkBloom, a powerful and versatile blog application that simplifies the process of creating, managing, and sharing your thoughts with the world.
"""

# Importing the required libraries

import os
import re
import secrets
from datetime import datetime, timezone
from email import utils
import json
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
    make_response,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_session import Session
from pymongo import MongoClient
from purgo_malum import client

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
limiter = Limiter(
    app=app,
    key_func=lambda: get_remote_address(),
    storage_uri=redis_url,
    storage_options={"connection_pool": str(pool)} if pool else None,
    strategy="moving-window",
)

# Application Utility Functions


def profanity_check(comment):
    """
    This function checks for profanity in the comment.
    """
    return client.contains_profanity(comment)


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


@app.context_processor
def app_version():
    return dict(service_version=service_version)


# After-request function for setting headers


@app.after_request
def add_header(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Cache-Control"] = "private, max-age=300"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers[
        "Strict-Transport-Security"
    ] = "max-age=31536000; includeSubDomains"
    response.headers[
        "Content-Security-Policy"
    ] = "default-src 'self' https://cdn.projectrexa.dedyn.io https://projectrexa.dedyn.io https://fonts.googleapis.com https://fonts.gstatic.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://avatars.githubusercontent.com "
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Connection"] = "keep-alive"
    return response


# Application User Routes


@app.route("/", methods=["GET"])
def index():
    """
    This function renders the home page of the application.
    """
    blogs = DATABASE["BLOGS"].find().sort("_id", -1).limit(10)
    featured_blogs = DATABASE["BLOGS"].find({"featured": True}).limit(3)
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
        suggested_blogs = (
            DATABASE["BLOGS"].find({"tags": {"$in": blog.get("tags", [])}}).limit(2)
        )
        print(suggested_blogs)


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


@app.route("/admin/blogs/create", methods=["GET", "POST"])
def create_blog():
    """
    Render the create blog page of the application.
    """
    if request.method == "POST":
        try:
            if session["logged_in"] and session["admin"]:
                blog_title = request.form.get("title")
                blog_content = request.form.get("content")
                category = request.form.get("category")
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
        except Exception as e:
            return {
                "status": "error",
                "message": f"Please fill all the fields correctly - {str(e)}",
            }, 400

        while DATABASE["BLOGS"].find_one({"slug": blog_slug}):
            blog_slug = blog_slug + "-" + secrets.token_hex(4)

        if category == "dev-log":
            if blog_content:
                blog_content = (
                    f"<h1> {datetime.now().strftime('%d %B %Y')} </h1> <br>"
                    + blog_content
                )
            else:
                return {
                    "status": "error",
                    "message": "Dev logs cannot be empty!",
                }, 400

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
            "category": category,
            "tags": blog_tags,
            "summary": blog_summary,
            "slug": blog_slug,
            "cover_image": blog_cover_image_url,
            "authour": authour,
            "authour_name": authour_name,
            "authour_profile_pic": session.get("profile_pic"),
            "featured": blog_featured,
            "read_time": len(blog_content.split(" ")) // 300,
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


# @app.route("/admin/blogs/edit/<blog_id>", methods=["GET", "POST"])
# def edit_blog(blog_id):
#     """
#     This function renders the edit blog page of the application
#     """


@app.route("/user/authorize", methods=["GET"])
def authentication():
    if session.get("logged_in"):
        return redirect(url_for("index"))

    error_message = request.args.get("error")
    if error_message:
        return {"status": "error", "message": error_message}

    next_url = request.args.get("next")
    if next_url:
        session["next"] = next_url

    github_auth_url = "https://github.com/login/oauth/authorize"
    github_auth_url += "?client_id=d47204e1b7b5ecd7a543"
    github_auth_url += (
        "&redirect_uri=https://blog.projectrexa.dedyn.io/user/github/callback"
    )
    github_auth_url += "&scope=user:email"

    return redirect(github_auth_url)


@app.route("/user/github/callback")
def github_callback():
    if session.get("logged_in"):
        return redirect(url_for("index"))

    code = request.args.get("code")

    if code is None:
        return redirect(url_for("index"))

    try:
        github_token_url = "https://github.com/login/oauth/access_token"
        github_token_url += f"?client_id={os.getenv('GITHUB_CLIENT_ID')}"
        github_token_url += f"&client_secret={os.getenv('GITHUB_CLIENT_SECRET')}"
        github_token_url += f"&code={code}"

        response = requests.post(
            github_token_url,
            headers={"Accept": "application/json"},
            timeout=5,
        )

        access_token = response.json()["access_token"]

        user_data = requests.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=5,
        ).json()

        if user_data["email"] is None:
            email_response = requests.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=5,
            ).json()

            for record in email_response:
                if record["primary"] is True:
                    user_data["email"] = record["email"]
                    break

        user = DATABASE["USERS"].find_one({"_id": user_data["id"]})

        if user is None:
            DATABASE["USERS"].insert_one(
                {
                    "_id": user_data["id"],
                    "name": user_data["name"] or "User",
                    "email": user_data["email"],
                    "profile_pic": user_data["avatar_url"],
                    "admin": False,
                    "blocked": False,
                    "created_at": datetime.now(),
                }
            )

            user = DATABASE["USERS"].find_one({"_id": user_data["id"]})

        session["logged_in"] = True
        session["user_id"] = user_data["id"]
        session["user_name"] = user_data["name"]
        session["user_email"] = user_data["email"]
        session["profile_pic"] = user_data["avatar_url"]
        if user is not None:
            session["admin"] = user.get("admin", False)
            session["blocked"] = user.get("blocked", False)

        return redirect(session.get("next") or url_for("index"))

    except Exception as e:
        return redirect("/user/authorize" + "?error=Something went wrong!")


@app.route("/user/sign-out", methods=["GET"])
def signout():
    """
    This function signs the user out of the application.
    """
    session.clear()
    if request.args.get("next"):
        return redirect(str(request.args.get("next")))
    return redirect(url_for("index"))


@app.route("/search")
def search_page():
    """
    This function renders the search page of the application.
    """
    return render_template("search.html")


@app.route("/rss")
def rss():
    """
    This function renders the RSS feed of the application.
    """
    blogs = DATABASE["BLOGS"].find().sort("_id", -1)
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
    blogs = DATABASE["BLOGS"].find().sort("_id", -1)
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


@app.route("/api/v1/search", methods=["GET"])
def search():
    """
    This function returns the search results.
    """
    query = request.args.get("query")
    if query and len(query) > 2:
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
def post_user_comments():
    if request.method == "POST" and session.get("logged_in"):
        data = request.get_json()
        comment = data.get("comment")
        blog_slug = data.get("slug")

        if comment:
            if len(comment) > 1000:
                return {
                    "status": "error",
                    "message": "Comment length cannot exceed 500 characters!",
                }, 400

            if profanity_check([comment]):
                DATABASE["USERS"].update_one(
                    {"_id": session["user_id"]}, {"$set": {"blocked": True}}
                )
                session.clear()
                return {
                    "status": "error",
                    "message": "Your comment contains profanity. You have been blocked from posting further comments!",
                }, 400

            if not DATABASE["BLOGS"].find_one({"slug": blog_slug}):
                return {"status": "error", "message": "Invalid blog ID!"}, 400

            if DATABASE["USERS"].find_one({"_id": session["user_id"]}).get("blocked"):
                return {
                    "status": "error",
                    "message": "You have been blocked from posting further comments!",
                }, 400

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

            return {"status": "success", "message": "Comment posted successfully!"}, 200

        abort(400)

    abort(401)


@app.route("/api/v1/statisics/views/<blog_slug>", methods=["POST"])
@limiter.limit("10/minute")
def get_blog_views(blog_slug):
    blog = DATABASE["BLOGS"].find_one({"slug": blog_slug})

    if blog:
        DATABASE["BLOGS"].update_one({"slug": blog_slug}, {"$inc": {"views": 1}})
        return str(blog["views"])

    abort(404)


@app.route("/api/v1/user-content/upload", methods=["POST"])
@limiter.limit("30/minute")
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
                "location": response["access_url"],
            }, 200
        except Exception as e:
            return {
                "status": "error",
                "message": "Something went wrong while uploading the file!",
            }, 500

    abort(401)


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
    app.run()
