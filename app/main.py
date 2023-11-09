# Author: Om Mishra ( https://projectrexa.dedyn.io | https://github.com/Om-Mishra7 )
# Contact Detail: inkbloom@projectrexa.dedyn.io ( Do not spam this email address please :) )
# Written for the InkBloom Project
# Date Created: 03-11-2023
# Last Modified: 03-11-2023

"""
This file contains the server side code for the web application InkBloom, a powerful and versatile blog application that simplifies the process of creating, managing, and sharing your thoughts with the world.
"""

# Importing the required libraries

import os
import secrets
import datetime
import json
import requests
from dotenv import load_dotenv
import redis
from bson import ObjectId
from flask import (
    Flask,
    render_template,
    url_for,
    flash,
    redirect,
    request,
    session,
    abort,
    jsonify,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_session import Session
from pymongo import MongoClient
from purgo_malum import client

load_dotenv()  # Loading the environment variables


app = Flask(__name__)

with open("app/app.json", "r") as f:
    service_version = json.load(f)["service-version"]

# App Configuration

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")


# Session Configuration

app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_REDIS"] = redis.from_url(os.getenv("REDIS_URL"))
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_NAME"] = "inkbloom-session"

# Database Configuration

MONOGDB_CLIENT = MongoClient(os.getenv("MONGODB_URL"))
DATABASE = MONOGDB_CLIENT[os.getenv("MONGODB_DATABASE")]


# Session Initialization

Session(app)


# Rate Limiter Configuration

pool = redis.connection.BlockingConnectionPool.from_url(os.getenv("REDIS_URL"))
limiter = Limiter(
    app=app,
    key_func=lambda: get_remote_address(),
    storage_uri=os.getenv("REDIS_URL"),
    storage_options={"connection_pool": pool},
    strategy="moving-window",
)


@app.template_filter("format_timestamp")
def format_timestamp(s):
    return datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S.%f").strftime("%d %B %Y")


@app.context_processor
def app_version():
    return dict(service_version=service_version)


def profanity_check(comment):
    """
    This function checks for profanity in the comment.
    """
    return client.contains_profanity(comment)


# Application User Routes


@app.route("/", methods=["GET"])
def index():
    """
    This function renders the home page of the application.
    """
    blogs = DATABASE["BLOGS"].find().sort("_id", -1).limit(10)
    featured_blogs = DATABASE["BLOGS"].find({"featured": True}).limit(5)
    return render_template(
        "index.html",
        blogs=blogs,
        featured_blogs=featured_blogs,
        service_version=service_version,
    )


@app.route("/blogs", methods=["GET"])
def blogs():
    """
    This function renders the blogs page of the application.
    """
    blogs = DATABASE["BLOGS"].find().limit(10)
    return render_template("blogs.html", blogs=blogs)


@app.route("/blogs/<blog_slug>", methods=["GET"])
def blog(blog_slug):
    """
    This function renders the blog page of the application.
    """
    blog = DATABASE["BLOGS"].find_one({"slug": blog_slug})
    comments = DATABASE["COMMENTS"].find({"blog_slug": blog_slug})
    comments_list = []
    for comment in comments:
        comments_list.append(comment)

    if blog:
        return render_template("blog.html", blog=blog, comments=comments_list)
    abort(404)


@app.route("/admin/blogs/create", methods=["GET", "POST"])
def create_blog():
    """
    This function renders the create blog page of the application.
    """
    if request.method == "POST" and session["logged_in"] and session["admin"]:
        try:
            blog_title = request.form["title"]
            blog_content = request.form["content"]
            category = request.form["category"]
            blog_tags = request.form["tags"].split(",")
            for tag in blog_tags:
                if tag == "":
                    blog_tags.remove(tag)
                else:
                    blog_tags[blog_tags.index(tag)] = tag.strip().lower()
            blog_summary = request.form["summary"]
            blog_slug = blog_title.replace(" ", "-").lower()
            blog_cover_image = request.files["cover_image"]
            authour = session["user_id"]
            authour_name = session["user_name"]
            blog_featured = True if "featured" in blog_tags else False
            blog_tags = [tag for tag in blog_tags if tag != "featured"]
        except Exception as e:
            return {
                "status": "error",
                "message": "Please fill all the fields correctly - " + str(e),
            }, 400

        while True:
            if DATABASE["BLOGS"].find_one({"slug": blog_slug}):
                blog_slug = blog_slug + "-" + secrets.token_hex(4)
            else:
                break

        if category == "dev-log":
            blog_content = (
                f"<h1> {datetime.datetime.now().strftime('%d %B %Y')} </h1> <br>"
                + blog_content
            )

        if blog_cover_image.filename == "":
            return {"status": "error", "message": "No file found!"}, 400
        if blog_cover_image.content_type not in [
            "image/png",
            "image/jpeg",
            "image/jpg",
            "image/gif",
            "image/webp",
            "svg+xml",
        ]:
            return {"status": "error", "message": "Invalid file type!"}, 400
        if blog_cover_image:
            try:
                response = requests.post(
                    "http://ather.api.projectrexa.dedyn.io/upload",
                    files={"file": blog_cover_image.read()},
                    data={
                        "key": f"projectrexa/blog/assets/{secrets.token_hex(16)}",
                        "content_type": blog_cover_image.content_type,
                        "public": "true",
                    },
                    headers={"X-Authorization": os.getenv("ATHER_API_KEY")},
                    timeout=10,
                ).json()
                blog_cover_image = response["access_url"]
            except Exception as e:
                return {
                    "status": "error",
                    "message": "Something went wrong while uploading the file!",
                }, 500
        else:
            return {"status": "error", "message": "No cover image found!"}, 400

        blog = {
            "title": blog_title,
            "content": blog_content,
            "category": category,
            "tags": blog_tags,
            "summary": blog_summary,
            "slug": blog_slug,
            "cover_image": blog_cover_image,
            "authour": authour,
            "authour_name": authour_name,
            "authour_profile_pic": session["profile_pic"],
            "featured": blog_featured,
            "read_time": len(blog_content.split(" ")) // 300,
            "views": 0,
            "comments_count": 0,
            "created_at": datetime.datetime.now(),
        }
        DATABASE["BLOGS"].insert_one(blog)
        DATABASE["COMMENTS"].insert_one(
            {
                "blog_slug": blog_slug,
                "comment": "Please do not harass or abuse anyone in the comments section. We have a zero tolerance policy for harassment and abuse. If you are found to be violating our policy, you will be blocked from posting further comments.",
                "commented_by": "Moderation Bot",
                "user_name": "Moderation Bot",
                "user_profile_pic": "https://projectrexa.dedyn.io/assets/images/logo.png",
                "user_role": "admin",
                "created_at": datetime.datetime.now(),
            }
        )
        return {
            "status": "success",
            "message": "Blog created successfully!",
            "blog_slug": blog_slug,
        }, 200
    if session["logged_in"] and session["admin"]:
        return render_template("create_blog.html")


@app.route("/admin/blogs/edit/<blog_id>", methods=["GET", "POST"])
def edit_blog(blog_id):
    """
    This function renders the edit blog page of the application.
    """
    if (
        request.method == "POST"
        and session["logged_in"]
        and session["user_role"] == "admin"
    ):
        blog_title = request.form["blog_title"]
        blog_content = request.form["blog_content"]
        blog_featured = request.form["blog_featured"]
        blog_slug = request.form["blog_slug"]
        blog = {
            "title": blog_title,
            "content": blog_content,
            "featured": blog_featured,
            "slug": blog_slug,
        }
        DATABASE["BLOGS"].update_one({"_id": blog_id}, {"$set": blog})
        flash("Blog updated successfully!", "success")
        return redirect("/blogs")
    blog_data = DATABASE["BLOGS"].find_one({"_id": blog_id})
    if blog_data:
        return render_template("edit_blog.html", blog=blog_data)
    abort(404)


@app.route("/user/authorize", methods=["GET"])
def authentication():
    """
    This function renders the authentication page of the application.
    """
    if session.get("logged_in"):
        return redirect(url_for("index"))
    return redirect(
        "https://github.com/login/oauth/authorize?client_id=d47204e1b7b5ecd7a543&redirect_uri=https://blog.projectrexa.dedyn.io/user/github/callback&scope=user:email"
    )


@app.route("/user/github/callback")
def github_callback():
    """
    The github callback is used to log in to the contributor mode of the website.
    """
    if session.get("logged_in"):
        return redirect(url_for("index"))

    code = request.args.get("code")

    if code is None:
        print("No code provided")
        return redirect(url_for("index"))

    try:
        response = requests.post(
            "https://github.com/login/oauth/access_token?client_id={}&client_secret={}&code={}".format(
                os.getenv("GITHUB_CLIENT_ID"), os.getenv("GITHUB_CLIENT_SECRET"), code
            ),
            headers={"Accept": "application/json"},
            timeout=5,
        )

        user_data = requests.get(
            "https://api.github.com/user",
            headers={
                "Authorization": "Bearer {}".format(response.json()["access_token"])
            },
            timeout=5,
        ).json()

        if user_data["email"] is None:
            email = requests.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": "Bearer {}".format(response.json()["access_token"])
                },
                timeout=5,
            ).json()
            for record in email:
                if record["primary"] is True:
                    user_data["email"] = record["email"]
                    break

        user = DATABASE["USERS"].find_one({"_id": user_data["id"]})

        if user is None:
            DATABASE["USERS"].insert_one(
                {
                    "_id": user_data["id"],
                    "name": user_data["name"],
                    "email": user_data["email"],
                    "profile_pic": user_data["avatar_url"],
                    "admin": False,
                    "blocked": False,
                    "created_at": datetime.datetime.now(),
                }
            )

            user = DATABASE["USERS"].find_one({"_id": user_data["id"]})

        session["logged_in"] = True
        session["user_id"] = user_data["id"]
        session["user_name"] = user_data["name"]
        session["user_email"] = user_data["email"]
        session["profile_pic"] = user_data["avatar_url"]
        session["admin"] = user["admin"] if user else False

        return redirect(url_for("index"))
    except Exception as e:
        print(e)
        return redirect("/user/authorize" + "?error=Something went wrong!")


@app.route("/user/sign-out", methods=["GET"])
def signout():
    """
    This function signs the user out of the application.
    """
    session.clear()
    return redirect(url_for("index"))


@app.route("/search")
def search_page():
    """
    This function renders the search page of the application.
    """
    return render_template("search.html")


# Application API Routes


@app.route("/api/v1/search", methods=["GET"])
def search():
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
            if len(blogs) < 1:
                return jsonify([]), 404
            return jsonify(blogs), 200
    else:
        return jsonify([]), 404


@app.route("/api/v1/blogs/<last_blog_id>", methods=["GET"])
def get_blogs(last_blog_id):
    """
    This function returns a list of blog posts.
    """
    blogs = DATABASE["BLOGS"].find({"_id": {"$lt": ObjectId(last_blog_id)}}).limit(5)
    if blogs is not None:
        # Convert ObjectId to strings for each blog in the result
        blogs = [
            {
                "_id": str(blog["_id"]),
                "title": blog["title"],
                "summary": blog["summary"],
                "slug": blog["slug"],
                "tags": blog["tags"],
                "cover_image": blog["cover_image"],
                "authour": blog["authour"],
                "authour_name": blog["authour_name"],
                "authour_profile_pic": blog["authour_profile_pic"],
                "featured": blog["featured"],
                "read_time": blog["read_time"],
                "views": blog["views"],
                "likes": blog["likes"],
                "comments_count": blog["comments_count"],
                "created_at": blog["created_at"].strftime("%d %B %Y"),
            }
            for blog in blogs
        ]
        return jsonify(blogs), 200
    abort(404)


@app.route("/api/v1/user/comments", methods=["POST"])
def post_user_comments():
    """
    This function updates the user comments.
    """
    if request.method == "POST" and session["logged_in"]:
        data = request.get_json()
        comment = data["comment"]
        blog_sulg = data["slug"]
        if comment:
            if len(comment) > 1000:
                return {
                    "status": "error",
                    "message": "Comment length cannot exceed 500 characters!",
                }, 400
            if profanity_check(comment):
                DATABASE["USERS"].update_one(
                    {"_id": session["user_id"]},
                    {"blocked": True},
                )
                return {
                    "status": "error",
                    "message": "Our system has detected that you have used profanity in your comment. You have been blocked from posting further comments!",
                }, 400
            if not DATABASE["BLOGS"].find_one({"slug": blog_sulg}):
                return {"status": "error", "message": "Invalid blog ID!"}, 400

            if DATABASE["USERS"].find_one({"_id": session["user_id"]})["blocked"]:
                return {
                    "status": "error",
                    "message": "You have been blocked from posting further comments!",
                }, 400
            DATABASE["BLOGS"].update_one(
                {"slug": blog_sulg},
                {
                    "$inc": {
                        "comments_count": 1,
                    },
                },
            )
            print(blog_sulg, comment)

            DATABASE["COMMENTS"].insert_one(
                {
                    "blog_slug": blog_sulg,
                    "comment": comment,
                    "commented_by": session["user_id"],
                    "user_name": session["user_name"],
                    "user_profile_pic": session["profile_pic"],
                    "user_role": "admin" if session["admin"] else "user",
                    "created_at": datetime.datetime.now(),
                }
            )
            return {"status": "success", "message": "Comment posted successfully!"}, 200
        abort(400)
    abort(401)


@app.route("/api/v1/statisics/views/<blog_slug>", methods=["POST"])
# Rate limit if blog ID is same
@limiter.limit("10/minute")
def get_blog_views(blog_slug):
    """
    This function returns the number of views of a blog post.
    """
    blog = DATABASE["BLOGS"].find_one({"slug": blog_slug})
    if blog:
        DATABASE["BLOGS"].update_one({"slug": blog_slug}, {"$inc": {"views": 1}})
        return str(blog["views"])
    abort(404)


@app.route("/api/v1/user-content/upload", methods=["POST"])
@limiter.limit("30/minute")
def upload_user_content():
    """
    This function uploads the user content to the server.
    """
    if request.method == "POST" and session["logged_in"] and session["admin"]:
        if "file" not in request.files:
            return {"status": "error", "message": "No file found!"}, 400
        file = request.files["file"]
        if file.filename == "":
            return {"status": "error", "message": "No file found!"}, 400
        if file.content_type not in [
            "image/png",
            "image/jpeg",
            "image/jpg",
            "image/gif",
            "image/webp",
            "svg+xml",
        ]:
            return {"status": "error", "message": "Invalid file type!"}, 400
        if file:
            response = requests.post(
                "http://ather.api.projectrexa.dedyn.io/upload",
                files={"file": file.read()},
                data={
                    "key": f"projectrexa/blog/assets/{secrets.token_hex(16)}",
                    "content_type": file.content_type,
                    "public": "true",
                },
                headers={"X-Authorization": os.getenv("ATHER_API_KEY")},
                timeout=10,
            ).json()

            return {
                "status": "success",
                "message": "File uploaded successfully!",
                "location": response["access_url"],
            }, 200
    abort(401)


# Error Handlers


@app.errorhandler(429)
def ratelimit_handler(e):
    return {
        "status": "error",
        "message": "Too many requests, please try again later!",
    }, 429


if __name__ == "__main__":
    app.run(debug=True)
