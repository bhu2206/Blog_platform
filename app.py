from flask import Flask, render_template, request, redirect, session, flash, jsonify
import requests
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User, Post, Comment


app = Flask(__name__)

app.config["SECRET_KEY"] = "blog-secret-key"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///blog.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


db.init_app(app)


with app.app_context():
    db.create_all()


# =====================================================
# HOME
# =====================================================

@app.route("/")
def home():

    if "user_id" not in session:
        return redirect("/login")

    posts = Post.query.order_by(Post.id.desc()).all()

    quote = None

    try:

        response = requests.get(
            "https://api.quotable.io/quotes/random",
            timeout=5
        )

        if response.status_code == 200:

            data = response.json()

            if isinstance(data, list) and len(data) > 0:
                quote = data[0]

    except requests.RequestException:

        quote = None

    return render_template(
        "index.html",
        user=session["user"],
        posts=posts,
        quote=quote
    )


# =====================================================
# REGISTER
# =====================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:

            flash("Email already registered.")

            return redirect("/register")

        hashed_password = generate_password_hash(password)

        user = User(
            name=name,
            email=email,
            password=hashed_password
        )

        db.session.add(user)

        db.session.commit()

        flash("Registration successful! Please login.")

        return redirect("/login")

    return render_template("register.html")


# =====================================================
# LOGIN
# =====================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(
            email=email
        ).first()

        if user and check_password_hash(
            user.password,
            password
        ):

            session["user_id"] = user.id
            session["user"] = user.name
            session["email"] = user.email

            return redirect("/")

        flash("Invalid email or password.")

    return render_template("login.html")


# =====================================================
# LOGOUT
# =====================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# =====================================================
# CREATE POST
# =====================================================

@app.route("/create-post", methods=["GET", "POST"])
def create_post():

    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":

        title = request.form["title"]

        content = request.form["content"]

        post = Post(
            title=title,
            content=content,
            author=session["user"]
        )

        db.session.add(post)

        db.session.commit()

        flash("Blog post created successfully!")

        return redirect("/")

    return render_template("create_post.html")


# =====================================================
# VIEW SINGLE POST
# =====================================================

@app.route("/post/<int:id>")
def view_post(id):

    if "user_id" not in session:
        return redirect("/login")

    post = Post.query.get_or_404(id)

    comments = Comment.query.filter_by(
        post_id=id
    ).order_by(Comment.id.desc()).all()

    return render_template(
        "post.html",
        post=post,
        comments=comments,
        user=session["user"]
    )


# =====================================================
# EDIT POST
# =====================================================

@app.route("/edit-post/<int:id>", methods=["GET", "POST"])
def edit_post(id):

    if "user_id" not in session:
        return redirect("/login")

    post = Post.query.get_or_404(id)

    if post.author != session["user"]:

        return "You can only edit your own posts."


    if request.method == "POST":

        post.title = request.form["title"]

        post.content = request.form["content"]

        db.session.commit()

        flash("Post updated successfully!")

        return redirect(f"/post/{post.id}")


    return render_template(
        "edit_post.html",
        post=post
    )


# =====================================================
# DELETE POST
# =====================================================

@app.route("/delete-post/<int:id>")
def delete_post(id):

    if "user_id" not in session:
        return redirect("/login")

    post = Post.query.get_or_404(id)

    if post.author != session["user"]:

        return "You can only delete your own posts."


    # Delete comments belonging to this post
    Comment.query.filter_by(
        post_id=id
    ).delete()

    db.session.delete(post)

    db.session.commit()

    flash("Post deleted successfully!")

    return redirect("/")


# =====================================================
# ADD COMMENT
# =====================================================

@app.route("/post/<int:id>/comment", methods=["POST"])
def add_comment(id):

    if "user_id" not in session:
        return redirect("/login")

    post = Post.query.get_or_404(id)

    content = request.form["content"].strip()

    if not content:

        flash("Comment cannot be empty.")

        return redirect(f"/post/{id}")


    comment = Comment(

        content=content,

        author=session["user"],

        post_id=post.id

    )

    db.session.add(comment)

    db.session.commit()

    flash("Comment added successfully!")

    return redirect(f"/post/{id}")


# =====================================================
# DELETE COMMENT
# =====================================================

@app.route("/delete-comment/<int:id>")
def delete_comment(id):

    if "user_id" not in session:
        return redirect("/login")

    comment = Comment.query.get_or_404(id)

    if comment.author != session["user"]:

        return "You can only delete your own comments."


    post_id = comment.post_id

    db.session.delete(comment)

    db.session.commit()

    flash("Comment deleted successfully!")

    return redirect(f"/post/{post_id}")


# =====================================================
# REST API - GET ALL POSTS
# =====================================================

@app.route("/api/posts", methods=["GET"])
def api_get_posts():

    posts = Post.query.order_by(
        Post.id.desc()
    ).all()

    result = []

    for post in posts:

        result.append({

            "id": post.id,

            "title": post.title,

            "content": post.content,

            "author": post.author

        })

    return jsonify(result)


# =====================================================
# REST API - GET SINGLE POST
# =====================================================

@app.route("/api/posts/<int:id>", methods=["GET"])
def api_get_post(id):

    post = Post.query.get_or_404(id)

    comments = Comment.query.filter_by(
        post_id=id
    ).all()

    comment_data = []

    for comment in comments:

        comment_data.append({

            "id": comment.id,

            "content": comment.content,

            "author": comment.author

        })


    return jsonify({

        "id": post.id,

        "title": post.title,

        "content": post.content,

        "author": post.author,

        "comments": comment_data

    })


# =====================================================
# REST API - CREATE POST
# =====================================================

@app.route("/api/posts", methods=["POST"])
def api_create_post():

    if "user_id" not in session:

        return jsonify({
            "error": "Login required"
        }), 401


    data = request.get_json()

    if not data:

        return jsonify({
            "error": "JSON data required"
        }), 400


    title = data.get("title")

    content = data.get("content")


    if not title or not content:

        return jsonify({

            "error": "Title and content are required"

        }), 400


    post = Post(

        title=title,

        content=content,

        author=session["user"]

    )

    db.session.add(post)

    db.session.commit()


    return jsonify({

        "message": "Post created successfully",

        "post": {

            "id": post.id,

            "title": post.title,

            "content": post.content,

            "author": post.author

        }

    }), 201


# =====================================================
# REST API - UPDATE POST
# =====================================================

@app.route("/api/posts/<int:id>", methods=["PUT"])
def api_update_post(id):

    if "user_id" not in session:

        return jsonify({
            "error": "Login required"
        }), 401


    post = Post.query.get_or_404(id)


    if post.author != session["user"]:

        return jsonify({
            "error": "You can only edit your own posts"
        }), 403


    data = request.get_json()

    if not data:

        return jsonify({
            "error": "JSON data required"
        }), 400


    if "title" in data:

        post.title = data["title"]


    if "content" in data:

        post.content = data["content"]


    db.session.commit()


    return jsonify({

        "message": "Post updated successfully",

        "post": {

            "id": post.id,

            "title": post.title,

            "content": post.content,

            "author": post.author

        }

    })


# =====================================================
# REST API - DELETE POST
# =====================================================

@app.route("/api/posts/<int:id>", methods=["DELETE"])
def api_delete_post(id):

    if "user_id" not in session:

        return jsonify({
            "error": "Login required"
        }), 401


    post = Post.query.get_or_404(id)


    if post.author != session["user"]:

        return jsonify({
            "error": "You can only delete your own posts"
        }), 403


    Comment.query.filter_by(
        post_id=id
    ).delete()


    db.session.delete(post)

    db.session.commit()


    return jsonify({

        "message": "Post deleted successfully"

    })


# =====================================================
# REST API - GET COMMENTS
# =====================================================

@app.route("/api/posts/<int:id>/comments", methods=["GET"])
def api_get_comments(id):

    Post.query.get_or_404(id)

    comments = Comment.query.filter_by(
        post_id=id
    ).order_by(Comment.id.desc()).all()


    result = []


    for comment in comments:

        result.append({

            "id": comment.id,

            "content": comment.content,

            "author": comment.author,

            "post_id": comment.post_id

        })


    return jsonify(result)


# =====================================================
# REST API - CREATE COMMENT
# =====================================================

@app.route("/api/posts/<int:id>/comments", methods=["POST"])
def api_create_comment(id):

    if "user_id" not in session:

        return jsonify({
            "error": "Login required"
        }), 401


    post = Post.query.get_or_404(id)


    data = request.get_json()


    if not data:

        return jsonify({
            "error": "JSON data required"
        }), 400


    content = data.get("content")


    if not content:

        return jsonify({
            "error": "Comment content is required"
        }), 400


    comment = Comment(

        content=content,

        author=session["user"],

        post_id=post.id

    )


    db.session.add(comment)

    db.session.commit()


    return jsonify({

        "message": "Comment added successfully",

        "comment": {

            "id": comment.id,

            "content": comment.content,

            "author": comment.author,

            "post_id": comment.post_id

        }

    }), 201


# =====================================================
# REST API - DELETE COMMENT
# =====================================================

@app.route("/api/comments/<int:id>", methods=["DELETE"])
def api_delete_comment(id):

    if "user_id" not in session:

        return jsonify({
            "error": "Login required"
        }), 401


    comment = Comment.query.get_or_404(id)


    if comment.author != session["user"]:

        return jsonify({
            "error": "You can only delete your own comments"
        }), 403


    db.session.delete(comment)

    db.session.commit()


    return jsonify({

        "message": "Comment deleted successfully"

    })
# =====================================================
# SEARCH POSTS
# =====================================================

@app.route("/search")
def search():

    if "user_id" not in session:
        return redirect("/login")

    keyword = request.args.get("keyword", "").strip()

    if keyword:

        posts = Post.query.filter(
            Post.title.contains(keyword)
        ).order_by(Post.id.desc()).all()

    else:

        posts = Post.query.order_by(
            Post.id.desc()
        ).all()

    return render_template(
        "index.html",
        user=session["user"],
        posts=posts,
        keyword=keyword
    )

# =====================================================
# RUN
# =====================================================

if __name__ == "__main__":

    app.run(debug=True)