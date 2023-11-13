function viewStats() {
  if (localStorage.getItem(window.location.pathname.replace("/blogs/", ""))) {
    const lastView = localStorage.getItem(window.location.pathname.replace("/blogs/", ""));
    if (new Date().getTime() - lastView < 60000) {
      setTimeout(() => {
        viewStats();
      }
        , 60000);
      return;
    }
  }
  localStorage.setItem(window.location.pathname.replace("/blogs/", ""), new Date().getTime());
  fetch(`/api/v1/statisics/views/${window.location.pathname.replace("/blogs/", "")}`, {
    method: "POST",
  })
    .then((response) => {
      if (response.status === 200) {
        return response.json();
      } else {
        Promise.reject(response.status);
        return;
      }
    })
    .catch((error) => {
      console.log(error);
      setTimeout(() => {
        viewStats();
      }
        , 60000);
    });
}

let commentForm = document.getElementById("comment-form");

commentForm.addEventListener("submit", (e) => {
  e.preventDefault();
  let comment = document.getElementById("comment-content").value;
  let slug = window.location.pathname.replace("/blogs/", "");

  if (!comment) {
    return;
  }

  let commentData = {
    comment: comment,
    slug: slug,
    csrf_token: document.getElementById("csrf_token").value,
  };
  fetch("/api/v1/user/comments", {
    method: "POST",
    body: JSON.stringify(commentData),
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => {
      return response.json();
    }
    )
    .then((data) => {
      if (data.status === "success") {
        window.location.reload();
      }
      else {
        createAlert("danger", data.message);
      }
    }
    )
    .catch((error) => {
      console.log(error);
    }
    );
}
);

function deleteComment(commentId) {
  fetch(`/api/v1/user/comments/${commentId}`, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => {
      return response.json();
    }
    )
    .then((data) => {
      if (data.status === "success") {
        deleteCommentsButtons = document.getElementsByClassName("delete-comment");
        for (let i = 0; i < deleteCommentsButtons.length; i++) {
          if (deleteCommentsButtons[i].getAttribute("data-comment-id") === commentId) {
            deleteCommentsButtons[i].parentElement.parentElement.remove();
            break;
          }
        }
      }
      else {
        createAlert("danger", data.message);
      }
    }
    )
    .catch((error) => {
      console.log(error);
    }
    );
}

function blockUser(userId) {
  fetch(`/api/v1/user/block/${userId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => {
      return response.json();
    }
    )
    .then((data) => {
      if (data.status === "success") {
        window.location.reload();
      }
      else {
        createAlert("danger", data.message);
      }
    }
    )
    .catch((error) => {
      console.log(error);
    }
    );
}

function deleteBlog(id) {
  if (!confirm("Are you sure you want to delete this blog?")) {
    return;
  }
  fetch(`/api/v1/admin/blogs/${id}`, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => {
      return response.json();
    }
    )
    .then((data) => {
      if (data.status === "success") {
        window.location.href = "/";
      }
      else {
        createAlert("danger", data.message);
      }
    }
    )
    .catch((error) => {
      console.log(error);
    }
    );
}

hljs.highlightAll(); // Ensure that the code blocks are still syntax highlighted

viewStats();

